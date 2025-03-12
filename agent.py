from dotenv import load_dotenv; load_dotenv()
import utils.__applist__ as __applist__
import utils.executor as executor
import utils.narrator as narrator
import utils.planner as planner
import subprocess
import requests
import json
import os
import time
import re
import claude_code  # Import the Claude Code module

executor = executor.Executor()
print("\033[92mZeus - superagent running...\033[0m\n")
system_prompt = """You are Zeus, a macOS automation assistant designed to complete user tasks through precise UI interactions.

YOUR ROLE:
- You control macOS by clicking UI elements and using keyboard commands
- You can see and interact with all native and third-party applications
- Your goal is to complete tasks efficiently and thoroughly
- You maintain detailed state awareness throughout multi-step tasks

STATE MANAGEMENT:
- Always evaluate the success of previous actions
- Maintain a detailed memory of completed steps and progress
- Set clear next goals for each action sequence
- Track progress numerically when tasks involve multiple similar steps (e.g., "3 out of 5 emails processed")

CRITICAL RULES:
1. NEVER open an app that's already open
2. END your action sequence immediately after any operation that might trigger a popup or dialog
3. USE the wait action as little as possible
4. Use keyboard shortcuts only when you are confident the action will be successful
5. ALWAYS provide detailed state information with every response

WORKFLOW:
1. STARTING:
- If no app is open (active app is "NO_APP"), first open the appropriate app:
{
    "current_state": {
        "evaluation_previous_goal": "Not started yet",
        "memory": "Task just started, need to open the required application first",
        "next_goal": "Open the application needed for this task"
    },
    "actions": [
        {"open_app": {"bundle_id": "com.appropriate.app"}}
    ]
}

2. FOLLOWING THE PLAN:
- Generate a short sequence of actions for the next step in the plan
- Don't try to complete the entire task at once
- Adapt to what you see on screen while following the general plan
- Example for "Click on 'Playlists' in the sidebar":
{
    "current_state": {
        "evaluation_previous_goal": "Success - Application opened successfully",
        "memory": "App is now open and ready for interaction. Next we need to navigate to Playlists",
        "next_goal": "Click on Playlists in the sidebar to access playlist management"
    },
    "actions": [
        {"click_element": {"id": 42}}
    ]
}

3. COMPLETING THE TASK:
- Only call finish() when the entire task is complete
- If the goal has already been completed:
{
    "current_state": {
        "evaluation_previous_goal": "Success - Task has been completed successfully",
        "memory": "All steps of the task have been completed successfully: [summarize what was done]",
        "next_goal": "No further actions needed"
    },
    "actions": [
        {"finish": {}}
    ]
}

COMMON APP BUNDLE IDs:
- Safari: "com.apple.Safari"
- Messages: "com.apple.MobileSMS"
- Mail: "com.apple.mail"
- Calendar: "com.apple.iCal"
- Photos: "com.apple.Photos"
- Notes: "com.apple.Notes" (when making a new note, type text into title first, then press enter twice, then enter body text)
- Chess: "com.apple.Chess" (play as White until you get checkmate. If it's the beginning of the game, open with Nf3. click on only white pieces, then destination square to move. PLAY WHATEVER THE BEST VALID MOVE IS BASED ON THE BOARD, AND HOW CHESS PIECES WORK.  wait 5s for black to move. repeat until checkmate)
- iMovie: "com.apple.iMovie"
- Canary Mail: "io.canarymail.mac"
- YouTube Music: "com.apple.Safari.WebApp.B08FDE55-585A-4141-916F-7F3C6DEA7B8C" (pause button means song is playing)
"""

def format_prompt(dom_string, past_actions, plan_steps, task):
    prompt = dom_string + "\n"
    prompt += """
### ACTIONS AVAILABLE
1. open_app(bundle_id) - Open app
2. click_element(id) - Click on element
3. type_in_element(id, text) - Type text into element
4. hotkey(keys) - Execute keyboard shortcuts as a list of keys, e.g. ["cmd", "s"] or ["enter"]
5. wait(seconds) - Wait for a number of seconds (less is better)
6. finish() - Only call in final block after executing all actions, when the entire task has been successfully completed

### INPUT FORMAT: MacOS app elements
[ID_NUMBER]<ELEM_TYPE>content inside</ELEM_TYPE> eg. [14]<AXButton>Click me</AXButton> -> reference using only the ID, 14

### RESPONSE FORMAT: You must ALWAYS respond with valid JSON in this exact format:
example:
{
    "current_state": {
        "evaluation_previous_goal": "Success|Failed|Unknown - Analyze the current elements and the image to check if the previous goals/actions are successful like intended by the task. Mention if something unexpected happened. Shortly state why/why not",
        "memory": "Description of what has been done and what you need to remember. Be very specific. Count here ALWAYS how many times you have done something and how many remain. E.g. 0 out of 10 websites analyzed. Continue with abc and xyz",
        "next_goal": "What needs to be done with the next immediate action"
    },
    "actions": [
        {"open_app": {"bundle_id": "bundle.id.forapp"}},
        {"click_element": {"id": 1}},
        {"wait": {"seconds": 1}},
        {"type_in_element": {"id": 7, "text": "new text"}},
        {"hotkey": {"keys": ["cmd", "t"]}}
    ]
}
if the goal is already completed, then based on the page respond only with:
{
    "current_state": {
        "evaluation_previous_goal": "Success - Task has been completed successfully",
        "memory": "All steps of the task have been completed successfully",
        "next_goal": "No further actions needed"
    },
    "actions": [
        {"finish": {}}
    ]
}

### GOAL: """ + task + """
### GENERAL STEPS: """ + "\n".join([f"{i+1}. {step}" for i, step in enumerate(plan_steps)]) + """
### ACTIONS TAKEN SO FAR:\n"""
    
    if not past_actions:
        prompt += "none\n\n"
    else:
        for i, action in enumerate(past_actions):
            prompt += f"{i + 1}. {action}\n\n"

    prompt += """Respond with the next actions to take, including your current state analysis. Only call finish() if the task was already completed, based on the page."""
    return prompt
def get_actions_from_llm(prompt):
    api_key = os.environ.get("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    request_body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 1, "topK": 40, "topP": 0.95, "maxOutputTokens": 4192},
        "systemInstruction": {
            "parts": [
                {"text": system_prompt}
            ]
        }
    }
    
    response = requests.post(url, json=request_body)
    data = response.json()
    candidates = data.get("candidates", [])
    text = candidates[0]["content"]["parts"][0]["text"] if candidates else ""
    
    # Clean response
    if "```json" in text:
        text = text.split("```json", 1)[1]
    text = text.replace("```", "").strip()
    if "{" in text and "}" in text:
        start_idx = text.find("{")
        end_idx = text.rfind("}") + 1
        text = text[start_idx:end_idx].strip()

    try:
        response_json = json.loads(text, strict=False) # allows \t and other chars which could cause issues
        actions = response_json.get("actions", [])
        current_state = response_json.get("current_state", {
            "evaluation_previous_goal": "Unknown",
            "memory": "No memory available",
            "next_goal": "No goal specified"
        })
    except Exception as e:
        print(f"Error parsing JSON: {e}, text: {text}")
        actions = []
        current_state = {
            "evaluation_previous_goal": "Unknown",
            "memory": "No memory available",
            "next_goal": "No goal specified"
        }
    
    return actions, current_state
def execute_actions(past_actions, actions):
    updated_actions = past_actions.copy()
    task_completed = False
    
    for action in actions:
        if "open_app" in action:
            bundle_id = action["open_app"]["bundle_id"]
            result = executor.open_app(bundle_id)
            status = "✅" if result else "❌ [FAILED]"
            updated_actions.append(f"{status} Opened app: {bundle_id}")
        elif "click_element" in action:
            element_id = action["click_element"]["id"]
            result = executor.click_element(element_id)
            status = "✅" if result else "❌ [FAILED]"
            updated_actions.append(f"{status} Clicked element: {element_id}")
        elif "type_in_element" in action:
            element_id = action["type_in_element"]["id"]
            text = action["type_in_element"]["text"]
            result = executor.type_in_element(element_id, text)
            status = "✅" if result else "❌ [FAILED]"
            updated_actions.append(f"{status} Typed text: {text} into element: {element_id}")
        elif "hotkey" in action:
            keys = action["hotkey"]["keys"]
            result = executor.hotkey(keys)
            status = "✅" if result else "❌ [FAILED]"
            updated_actions.append(f"{status} Pressed keys: {keys}")
        elif "wait" in action:
            seconds = action["wait"]["seconds"]
            result = executor.wait(seconds)
            status = "✅" if result else "❌ [FAILED]"
            updated_actions.append(f"{status} Waited {seconds} sec")
        elif "finish" in action:
            task_completed = True
            updated_actions.append("Task completed")
    
    return [task_completed, updated_actions]

def get_initial_dom_str():
    dom_str = "### Active app: NO_APP\n"
    try:
        app_list = subprocess.check_output(["osascript", "-e", 'tell application "System Events" to get name of every process whose background only is false']).decode().strip()
        bundle_ids = subprocess.check_output(["osascript", "-e", 'tell application "System Events" to get bundle identifier of every process whose background only is false']).decode().strip()
        app_names = app_list.split(", ")
        app_bundle_ids = bundle_ids.split(", ")        
        dom_str += "\n### Mac app bundleids:\n"
        for app_name, bundle_id in zip(app_names, app_bundle_ids):
            if bundle_id:
                dom_str += f"{app_name}, {bundle_id}\n"
    except Exception as e:
        print(f"Error getting app list: {e}")
    return dom_str
initial = get_initial_dom_str()

def run(task, debug=False, speak=True, use_maya=False):
    max_iterations = 20
    is_task_complete = False
    past_actions = []
    dom_str = initial
    plan_steps = planner.plan(task)
    print(f"✅ Planned {len(plan_steps)} general steps to accomplish the goal.")
    
    # Initialize state tracking
    current_state = {
        "evaluation_previous_goal": "Not started",
        "memory": "Task just started",
        "next_goal": plan_steps[0] if plan_steps else "No specific steps planned"
    }

    # No need to call announce_task_plan - we're sending the command directly to Maya

    for iteration in range(max_iterations):
        prompt = format_prompt(dom_str, past_actions, plan_steps, task)
        actions, new_state = get_actions_from_llm(prompt)
        
        # Update state information
        current_state = new_state
        
        if debug: print("json_actions =", actions, "\n", "current_state =", current_state, "\n")    
        
        # Only use regular narrator for narration
        if speak:
            narrator.async_narrate(actions)
        
        # Print state information
        print(f"📝 State Analysis: {current_state['evaluation_previous_goal']}")
        print(f"🧠 Memory: {current_state['memory']}")
        print(f"🎯 Next Goal: {current_state['next_goal']}")
        
        is_task_complete, past_actions = execute_actions(past_actions, actions)
        if is_task_complete: break
        dom_str = executor.get_dom_str()
        print("---------------")
    
    # Print final task summary
    if is_task_complete:
        print("\n✨ Task Completed Successfully ✨")
        print(f"📋 Final State: {current_state['evaluation_previous_goal']}")
        print(f"📝 Summary: {current_state['memory']}")
    else:
        print("\n⚠️ Maximum iterations reached without task completion")
        print(f"📋 Current State: {current_state['evaluation_previous_goal']}")
        print(f"📝 Progress: {current_state['memory']}")
        print(f"🔄 Next Step: {current_state['next_goal']}")
        
    return is_task_complete, current_state['memory'], "\n".join(past_actions)

# Function that can be called by external scripts like discord-bot.py
def execute_command(command, use_narrator=True, use_maya=True):
    """
    Execute a command with optional narrator and Maya integration.
    
    Args:
        command: The command to execute
        use_narrator: Whether to use the narrator for audio feedback
        use_maya: Whether to use Maya for voice interaction
        
    Returns:
        Tuple of (is_complete, summary, actions_log)
    """
    print(f"Executing command: {command}")
    print("---------------")
    
    # Check if this is a direct Claude command with prefix
    if command.lower().startswith('claude:'):
        # Handle the command with Claude Code
        is_complete, summary, actions_log = claude_code.handle_coding_task(command, debug=True)
        print(f"\n{'✨ Task Completed Successfully ✨' if is_complete else '⚠️ Task could not be completed'}")
        print(f"📝 Claude Code Status: {summary}")
        return is_complete, summary, actions_log
    
    # Check if this is a coding-related query that should use Claude Code
    elif claude_code.is_coding_query(command):
        # Provide a tip about using the claude: prefix for future use
        print("\033[33mDetected code or Claude-specific query.\033[0m")
        print("\033[33mTip: You can also prefix with 'claude:' for direct Claude access.\033[0m")
        
        # Handle the coding task with Claude Code
        is_complete, summary, actions_log = claude_code.handle_coding_task(command, debug=True)
        print(f"\n{'✨ Task Completed Successfully ✨' if is_complete else '⚠️ Task could not be completed'}")
        print(f"📝 Claude Code Status: {summary}")
        return is_complete, summary, actions_log
    
    # For non-coding tasks, continue with the normal workflow
    # Initialize Maya if needed and not already running
    if use_maya:
        from agent_maya import maya_agent
        
        # Check if Maya is initialized
        if not hasattr(maya_agent, 'is_initialized') or not maya_agent.is_initialized:
            print("🌐 Initializing Maya voice agent...")
            greeting_event = maya_agent.start()
            maya_agent.wait_for_initial_greeting(timeout=60)
        
        # Send the command to Maya
        maya_agent.process_command(command)
        # Give Maya some time to process and respond
        time.sleep(2)
    
    # Run the command
    is_complete, summary, actions_log = run(command, debug=False, speak=use_narrator, use_maya=False)
    
    # Have Maya announce completion if enabled
    if use_maya:
        from agent_maya import maya_agent
        if is_complete:
            maya_agent.say("The command has been executed successfully. Zeus is awaiting further commands.")
        else:
            maya_agent.say("I wasn't able to complete the command fully. Zeus is awaiting further commands.")
    
    return is_complete, summary, actions_log

if __name__ == "__main__":
    try:
        # Initialize Maya if enabled
        use_maya = False
          # Set this to your preferred default
        
        if use_maya:
            import time
            from agent_maya import maya_agent
            print("🌐 Initializing Maya voice agent...")
            
            # Start Maya and get the event that will be set when the initial greeting is complete
            greeting_event = maya_agent.start()
            
            # Wait for the initial greeting to complete
            if not maya_agent.wait_for_initial_greeting(timeout=60):
                print("⚠️ Continuing without waiting for Maya's initial greeting")
        
        while True:
            user_input = input("✈️ Enter command: "); print("---------------")
            
            # Use the execute_command function which now handles Claude Code integration
            execute_command(user_input, use_narrator=False, use_maya=use_maya)
            
            print("\n---------------")
    except KeyboardInterrupt:
        print("\nShutting down...")
        # Stop Maya agent if it was started
        if use_maya:
            try:
                from agent_maya import maya_agent
                maya_agent.stop()
            except Exception as e:
                print(f"Error stopping Maya: {e}")