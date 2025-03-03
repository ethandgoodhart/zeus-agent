from dotenv import load_dotenv; load_dotenv()
import utils.__applist__ as __applist__
import utils.executor as executor
import requests
import json
import os

executor = executor.Executor()
dom_str = executor.get_dom_str()
print("\033[92mFlow - agent running...\033[0m\n")

def generate_prompt(context, task):
    prompt = context + "\n"
    
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
    3. type_in_element(id, text) - Type text into element
    4. keyboard_command(command) - Execute keyboard command on mac eg. cmd+s or enter or cmd+shift+r
    5. wait(seconds) - Wait for a number of seconds
    5. finish() - Only call in final block after executing all actions, when the entire task has been successfully completed
    
    ### INPUT FORMAT: MacOS app elements
    [ID_NUMBER]<ELEM_TYPE>content inside</ELEM_TYPE> eg. [14]<AXButton>Click me</AXButton> -> reference using only the ID, 14

    ### RESPONSE FORMAT: You must ALWAYS respond with valid JSON in this exact format:
    example:
    {
        "actions": [
            {"open_app": {"bundle_id": "bundle.id.forapp"}},
            {"click_element": {"id": 1}},
            {"wait": {"seconds": 1}},
            {"type_in_element": {"id": 2, "text": "new text"}},
            {"keyboard_command": {"command": "cmd+r"}}
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
                You are Flow, an expert automation agent specializing in macOS application control and automation. Your purpose is to generate precise, efficient action sequences that help users interact with macOS applications through accessibility controls and keyboard commands.
                
                If previous actions is empty, the first and only action should be to open the best app to complete the task in (eg. Spotify to play music, or Messages to send a text):
                {
                    "actions": [
                        {"open_app": {"bundle_id": "app_to_open_bundle_id"}}
                    ] //no more actions after
                }

                After opening the app, generate actions to successfully complete the task.
                """}
            ]
        }
    }
    
    response = requests.post(url, json=request_body)
    data = response.json()
    candidates = data.get("candidates", [])
    text = candidates[0]["content"]["parts"][0]["text"] if candidates else ""
    
    # Clean response if needed
    text = text.replace("```json", "").replace("```", "")
    
    action_json = json.loads(text)
    actions = action_json.get("actions", [])
    
    return actions
def execute_actions(actions):
    global is_task_complete, past_actions
    
    for action in actions:
        if "open_app" in action:
            bundle_id = action["open_app"]["bundle_id"]
            executor.open_app(bundle_id)
            past_actions.append(f"Opened app: {bundle_id}")
        elif "click_element" in action:
            element_id = action["click_element"]["id"]
            executor.click_element(element_id)
            past_actions.append(f"Clicked element: {element_id}")
        elif "type_in_element" in action:
            element_id = action["type_in_element"]["id"]
            text = action["type_in_element"]["text"]
            executor.click_element(element_id)
            executor.type(text)
            past_actions.append(f"Typed '{text}' in element: {element_id}")
        elif "keyboard_command" in action:
            command = action["keyboard_command"]["command"]
            keys = command.split("+")
            executor.hotkey(keys)
            past_actions.append(f"Executed keyboard command: {command}")
        elif "wait" in action:
            seconds = action["wait"]["seconds"]
            executor.wait(seconds)
            past_actions.append(f"Waited for {seconds} seconds")
        elif "finish" in action:
            is_task_complete = True
            past_actions.append("Task completed")
            break

while True:
    user_input = input("✈️ Enter command: ")

    past_actions = []
    is_task_complete = False
    
    while not is_task_complete:
        prompt = generate_prompt(dom_str, user_input)
        actions = get_actions_from_llm(prompt)
        execute_actions(actions)
        dom_str = executor.get_dom_str()

    print("✅ Task completed successfully")