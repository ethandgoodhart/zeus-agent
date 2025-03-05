from dotenv import load_dotenv; load_dotenv()
import utils.__applist__ as __applist__
import utils.executor as executor
import utils.narrator as narrator
import utils.planner as planner
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

CRITICAL RULES:
1. NEVER open an app that's already open
2. END your action sequence immediately after any operation that might trigger a popup or dialog
3. USE the wait action as little as possible
4. Use keyboard shortcuts only when you are confident the action will be successful

WORKFLOW:
1. STARTING:
- If no app is open (active app is "NO_APP"), first open the appropriate app:
{
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
    "actions": [
        {"click_element": {"id": 42}}
    ]
}

3. COMPLETING THE TASK:
- Only call finish() when the entire task is complete
- If the goal has already been completed:
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
- Notes: "com.apple.Notes" (when making a new note, type text into title first, then press enter twice, then enter body text)
- Chrome: "com.google.Chrome"
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

    prompt += """Respond with the next actions to take. Only call finish() if the task was already completed, based on the page."""
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

def run(task, debug=False, speak=True): # avg. ~$0.002/run
    max_iterations = 10
    is_task_complete = False
    past_actions = []
    dom_str = initial
    plan_steps = planner.plan(task)
    print(f"✅ Planned {len(plan_steps)} general steps to accomplish the goal.")

    for _ in range(max_iterations):
        prompt = format_prompt(dom_str, past_actions, plan_steps, task)
        actions = get_actions_from_llm(prompt)
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