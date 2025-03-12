import subprocess
import time
import os
import re

def is_coding_query(query):
    """
    Determine if a user query is related to coding tasks.
    
    Args:
        query (str): The user's input query
        
    Returns:
        bool: True if the query is related to coding, False otherwise
    """
    # Check for explicit mentions of claude/code or the prefix
    if query.lower().startswith('claude:'):
        return True
        
    if 'claude' in query.lower() or 'code' in query.lower():
        return True
        
    # Check for coding-related keywords
    coding_keywords = [
        'write', 'create', 'edit', 'modify', 'file', 'code', 'script', 'program',
        'function', 'class', 'method', 'variable', 'python', 'javascript', 'html',
        'css', 'read file', 'list files', 'directory', 'import', 'export', 'implement',
        'debug', 'fix', 'error', 'compile', 'build', 'test', 'run'
    ]
    
    # Check if any of the coding keywords are in the query
    for keyword in coding_keywords:
        if keyword in query.lower():
            return True
            
    return False

def is_file_operation_prompt(prompt):
    """
    Determine if the prompt likely involves file operations.
    
    Args:
        prompt (str): The prompt to analyze
        
    Returns:
        bool: True if the prompt likely involves file operations
    """
    file_op_keywords = [
        'create file', 'write file', 'edit file', 'modify file', 'delete file',
        'read file', 'open file', 'save file', 'new file', 'make file',
        'create directory', 'make directory', 'mkdir', 'list files', 'list directory',
        '.py', '.js', '.html', '.css', '.md', '.txt', '.json', '.csv', '.xml'
    ]
    
    # Check if any of the file operation keywords are in the prompt
    for keyword in file_op_keywords:
        if keyword in prompt.lower():
            return True
    
    # Also check regex pattern for verbs followed by file/directory
    if re.search(r'(read|write|edit|create|modify|delete)\s+(file|directory)', prompt.lower()):
        return True
            
    return False

def run_claude_command(prompt, handle_permissions=True, directory=None, debug=False):
    """
    Executes a Claude command following strict rules:
    1. For file operations: Handle initial trust and one file permission prompt with increased wait times
    2. For other queries: Use the -p flag with NO permission handling
    
    Args:
        prompt: The prompt to send to Claude
        handle_permissions: Whether to automatically handle permission prompts
        directory: Optional directory to navigate to before running Claude
        debug: Whether to print debug information
    
    Returns:
        str: Status message
    """
    # Determine if this prompt likely involves file operations
    is_file_op = is_file_operation_prompt(prompt)
    
    # Escape special characters in the prompt for AppleScript
    escaped_prompt = prompt.replace('"', '\\"').replace("'", "\\'").replace("\\", "\\\\")
    
    applescript = f'''
    tell application "Terminal"
        activate
        set newTab to do script ""
        -- Wait for Terminal to fully load
        delay 2
    '''
    
    # Add directory navigation if specified
    if directory:
        # Escape the directory path for AppleScript
        escaped_directory = directory.replace('"', '\\"').replace("'", "\\'").replace("\\", "\\\\")
        applescript += f'''
        -- Change to the specified directory
        do script "cd {escaped_directory}" in newTab
        delay 1
        '''
    
    # Choose between interactive mode and one-shot mode based on the prompt type
    if is_file_op:
        # INTERACTIVE MODE with strict permission handling for file operations
        applescript += '''
        -- Run Claude in interactive mode
        do script "claude" in newTab
        -- Wait for Claude to fully load
        delay 3
        
        -- Handle initial trust permission (first pop-up)
        delay 2
        do script "y" in newTab
        delay 0.5
        do script "" in newTab  -- Press return
        delay 2
        
        -- Press Enter to acknowledge any initial Claude message
        do script "" in newTab  -- Press Enter
        delay 2
        '''
        
        # Type the actual prompt
        applescript += f'''
        -- Type the prompt
        do script "{escaped_prompt}" in newTab
        delay 1
        do script "" in newTab  -- Press return
        
        -- Increased wait time before handling file permission pop-up
        delay 8
        
        -- Handle file permission pop-up (second pop-up)
        do script "y" in newTab
        delay 0.5
        do script "" in newTab  -- Press return
        
        -- No more interaction after this point
        '''
    else:
        # ONE-SHOT MODE for regular queries - NO permission handling
        applescript += f'''
        -- Run Claude with -p flag for one-shot execution with no permission handling
        do script "claude -p \\"{escaped_prompt}\\"" in newTab
        
        -- No permission handling for one-shot mode
        '''
    
    applescript += '''
    end tell
    '''
    
    # Create temporary file for the AppleScript
    script_path = "/tmp/run_claude.scpt"
    with open(script_path, "w") as f:
        f.write(applescript)
    
    # Execute the AppleScript
    try:
        if debug:
            mode = "interactive mode (file operations)" if is_file_op else "one-shot mode (-p flag without permission handling)"
            location = f" in directory: {directory}" if directory else ""
            print(f"Executing Claude in {mode}{location}")
        
        result = subprocess.run(["osascript", script_path], capture_output=True, text=True)
        
        if debug:
            print(f"AppleScript Output: {result.stdout}")
            if result.stderr:
                print(f"AppleScript Error: {result.stderr}")
        
        # Clean up the temporary file
        os.remove(script_path)
        
        if result.returncode != 0:
            return f"Error running Claude command: {result.stderr}"
        
        return "Claude command executed successfully"
    except Exception as e:
        return f"Error running Claude command: {str(e)}"

def handle_coding_task(query, debug=False):
    """
    Main function to handle coding-related tasks using Claude Code.
    
    Args:
        query (str): The user's input query
        debug (bool): Whether to print debug information
        
    Returns:
        tuple: (is_complete, summary, actions_log) similar to the run function
    """
    print("🔍 Detected coding-related query, using Claude Code")
    
    actions_log = []
    
    # Check if query has the claude: prefix and extract it
    if query.lower().startswith('claude:'):
        # Extract the entire input after "claude:"
        claude_input = query[7:].strip()
    else:
        claude_input = query
    
    # Check for directory specification pattern: "in <directory>: <prompt>"
    directory_match = re.match(r'in\s+([^:]+):\s*(.*)', claude_input)
    
    if directory_match:
        # Extract directory and the actual prompt
        directory = directory_match.group(1).strip()
        prompt = directory_match.group(2).strip()
        result = run_claude_command(prompt, directory=directory, debug=debug)
        print(f"Running Claude in directory: {directory}")
        actions_log.append(f"✅ Executing in directory: {directory}")
    else:
        # No directory specified, run normally
        prompt = claude_input
        result = run_claude_command(prompt, debug=debug)
    
    actions_log.append(f"✅ Using Claude Code for task: {prompt}")
    actions_log.append(f"✅ {result}")
    
    return True, result, "\n".join(actions_log) 