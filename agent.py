from dotenv import load_dotenv; load_dotenv()
import utils.__applist__ as __applist__
import utils.executor as executor
import utils.narrator as narrator
import subprocess
import requests
import json
import os

executor = executor.Executor()
print("\033[92mZeus - agent running...\033[0m\n")
system_prompt = """You are Zeus, a macOS automation assistant designed to complete user tasks through precise UI interactions.

YOUR ROLE:
- You control macOS by clicking UI elements and using keyboard commands
- You can see and interact with all native and third-party applications
- Your goal is to complete tasks efficiently and thoroughly

CORE PRINCIPLES:
1. ANALYZE FIRST: Always examine the current screen before acting
2. BE EFFICIENT: Choose the most direct path to complete tasks
3. BE METHODICAL: Break complex tasks into clear steps
4. BE THOROUGH: Complete the entire task, not just part of it

CRITICAL RULES:
1. ALWAYS click a text field BEFORE typing in it
2. NEVER open an app that's already open
3. END your action sequence immediately after any operation that might trigger a popup or dialog
4. USE the wait action as little as possible
5. use keyboard shortcuts only when you are confident the action will be successful

EXACT WORKFLOW:
1. STARTING A TASK:
- If no app is open (active app is "NO_APP"), first open the appropriate app:
{
    "actions": [
        {"open_app": {"bundle_id": "com.appropriate.app"}}
    ]
}
    
2. EXECUTING THE TASK:
  - Observe the interface carefully
  - Plan your approach based on what you see
  - Execute actions in a logical sequence
  - If you get stuck, try alternative approaches to complete the task

3. COMPLETING THE TASK:
  - Only call finish() after the ENTIRE task is complete
  - Verify completion by examining the final screen state
  - If the task has already been completed, use the finish action:
{
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
- Notes: "com.apple.Notes" (when making a new note, type text into title then press enter and enter body text)
- Chrome: "com.google.Chrome"
- iMovie: "com.apple.iMovie"
- Canary Mail: "io.canarymail.mac"
- YouTube Music: "com.apple.Safari.WebApp.B08FDE55-585A-4141-916F-7F3C6DEA7B8C" (pause button means song is playing)
"""

def format_prompt(dom_string, past_actions, task):
    prompt = dom_string + "\n"
    
    prompt += "### ACTIONS TAKEN SO FAR:\n"
    if not past_actions:
        prompt += "none"
    else:
        for i, action in enumerate(past_actions):
            prompt += f"{i + 1}. {action}\n"
    prompt += "\n"
    
    prompt += """
### ACTIONS AVAILABLE
1. open_app(bundle_id) - Open app
2. click_element(id) - Click on element
3. type(text) - Type text at current cursor position
4. hotkey(keys) - Execute keyboard shortcuts as a list of keys, e.g. ["cmd", "s"] or ["enter"]
5. wait(seconds) - Wait for a number of seconds (less is better)
6. finish() - Only call in final block after executing all actions, when the entire task has been successfully completed

### INPUT FORMAT: MacOS UI Elements in DOM-like Structure
The UI structure is presented in a hierarchical format:

1. **INTERACTABLE ELEMENTS**
   - ⚠️ **CRITICAL**: You can ONLY interact with elements that have an [ID=...] attribute
   - ⚠️ **CRITICAL**: Only elements with numeric IDs (e.g., [ID=42]) can be clicked or manipulated

2. **ELEMENT HIERARCHY**
   - Elements follow a parent > child relationship structure
   - Example: "Window > Button > Text" shows nesting and relationships

3. **ELEMENT PROPERTIES**
   - Elements have descriptive attributes: role, title, etc.
   - Example: role=button, title="Click me"

4. **SELECTION GUIDELINES**
   - ❌ NEVER attempt to interact with elements without an [ID=...] attribute
   - ✅ Prioritize elements with clear, descriptive attributes over empty/generic elements
   - ✅ Choose elements whose purpose is clearly indicated by their attributes

### RESPONSE FORMAT: You must ALWAYS respond with valid JSON in this exact format:
example:
{
    "actions": [
        {"open_app": {"bundle_id": "bundle.id.forapp"}},
        {"click_element": {"id": 1}},
        {"wait": {"seconds": 1}},
        {"type": {"text": "new text"}},
        {"hotkey": {"keys": ["cmd", "r"]}}
    ]
}
if the task is already completed, then based on the page respond only with:
{
    "actions": [
        {"finish": {}}
    ]
}

### CURRENT TASK: """ + task + """

Respond with the next actions to take. Only call finish() if the task was already completed, based on the page.
    """
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
    
    try:
        action_json = json.loads(text, strict=False) # allows \t and other chars which could cause issues
        actions = action_json.get("actions", [])
    except Exception as e:
        print(f"Error parsing JSON: {e}, text: {text}")
        actions = []
    
    return actions
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
        elif "type" in action:
            text = action["type"]["text"]
            result = executor.type(text)
            status = "✅" if result else "❌ [FAILED]"
            updated_actions.append(f"{status} Typed text: {text}")
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

def run(task, debug=False, speak=True): # avg. ~$0.002/run
    max_iterations = 10
    is_task_complete = False
    past_actions = []
    dom_str = initial

    for _ in range(max_iterations):
        prompt = format_prompt(dom_str, past_actions, task)
        actions = get_actions_from_llm(prompt)
        if debug: print("prompt: ", prompt)
        if debug: print("json_actions =", actions, "\n")
        if speak: narrator.async_narrate(actions)
        is_task_complete, past_actions = execute_actions(past_actions, actions)
        if is_task_complete: break
        dom_str = executor.get_dom_str()
        print("---------------")
        
    return "\n".join(past_actions)

if __name__ == "__main__":
    while True:
        user_input = input("✈️ Enter command: "); print("---------------")
        run(user_input, debug=False, speak=False)
        print("Task completed successfully\n")
        # import time; time.sleep(2); print(format_prompt(executor.get_dom_str(), [], "sample task")); break #dom debugging