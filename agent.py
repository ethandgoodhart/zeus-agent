from dotenv import load_dotenv; load_dotenv()
import utils.__applist__ as __applist__
import utils.executor as executor
import utils.narrator as narrator
import subprocess
import requests
import json
import os

executor = executor.Executor()
print("\033[92mFlow - agent running...\033[0m\n")

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
5. wait(seconds) - Wait for a number of seconds
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
        {"type": {"text": "new text"}},
        {"hotkey": {"keys": ["cmd", "r"]}}
    ]
}
after confirming that the entire task has been successfully completed
{
    "actions": [
        {"finish": {}}
    ]
}

### CURRENT TASK: """ + task + """

Respond with the next actions to take. Only call finish() after another iteration where you have confirmed that the entire task has been successfully completed.
    """
    return prompt
def get_actions_from_llm(prompt):
    api_key = os.environ.get("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    request_body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 1, "topK": 40, "topP": 0.95, "maxOutputTokens": 8192},
        "systemInstruction": {
            "parts": [
                {"text": """
                You are Flow, an expert automation agent for macOS with deep knowledge of all native and popular third-party applications. Your goal is to complete user tasks with minimal, precise actions using accessibility controls and keyboard commands.

                GUIDELINES:
                - Always analyze the current state before deciding actions
                - Choose the most direct path to complete tasks
                - Prefer keyboard shortcuts over clicking when efficient
                - Break complex tasks into logical sequences
                - Wait appropriate times between actions that need processing
                - If the app is already open and loaded, don't open it again

                WORKFLOW:
                1. ONLY IF active app is NO_APP, on the first response, you should open the most appropriate app:
                   {
                     "actions": [
                       {"open_app": {"bundle_id": "com.appropriate.app"}}
                     ]
                   }
                2. After app is open, observe the interface and plan your approach
                3. Execute precise action sequences to complete the task
                4. Verify completion before calling finish()

                COMMON BUNDLE IDs:
                - Safari: "com.apple.Safari"
                - Messages: "com.apple.MobileSMS"
                - Mail: "com.apple.mail"
                - YouTube Music: "com.apple.Safari.WebApp.B08FDE55-585A-4141-916F-7F3C6DEA7B8C"
                - Calendar: "com.apple.iCal"
                - Photos: "com.apple.Photos"
                - Canary Mail: "io.canarymail.mac"
                - Notes: "com.apple.Notes"
                - Chrome: "com.google.Chrome"

                Remember: Efficiency and precision are key. Use the minimum actions needed to complete the task successfully.
                """}
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
    
    action_json = json.loads(text)
    actions = action_json.get("actions", [])
    
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

def run(task, debug=False, speak=True):
    max_iterations = 6
    is_task_complete = False
    past_actions = []
    dom_str = initial

    for _ in range(max_iterations):
        prompt = format_prompt(dom_str, past_actions, task)
        actions = get_actions_from_llm(prompt)
        if debug: print("prompt: ", prompt)#print("json_actions =", actions, "\n");
        if speak: narrator.async_narrate(actions)
        is_task_complete, past_actions = execute_actions(past_actions, actions)
        if is_task_complete: break
        dom_str = executor.get_dom_str()

if __name__ == "__main__":
    while True:
        user_input = input("✈️ Enter command: "); print("---------------")
        run(user_input, debug=False, speak=False)
        print("Task completed successfully\n")
        # import time; time.sleep(2); print(format_prompt(executor.get_dom_str(), [], "sample task")); break #dom debugging