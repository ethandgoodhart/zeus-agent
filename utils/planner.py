import requests
import json
import os

def plan(task):
    prompt = f"""
    ### GOAL: {task}
    
    Create a detailed step-by-step plan to complete this goal. Break it down into specific, concrete actions.
    
    Return your plan as a JSON object with this exact format:
    {{
        "steps": [
            ...
            ...
            ...
        ]
    }}
    
    example:
    ### GOAL: Create a new playlist in YouTube Music called "Chill" with Mac Miller songs and share it with John
    {{
        "steps": [
            "Open the YouTube Music app",
            "Click on 'Playlists' in the sidebar",
            "Click the '+' button to create a new playlist",
            "Enter 'Chill' as the playlist name",
            "Click 'Done' or press Enter to create the playlist",
            "Click on 'Search' in the sidebar",
            "Type 'Mac Miller' in the search bar",
            "Click on 'Songs' to view Mac Miller's songs",
            "Right-click on a Mac Miller song and select 'Add to Playlist'",
            "Select the 'Chill' playlist from the dropdown",
            "Repeat steps 8-10 for at least 3 more Mac Miller songs",
            "Go back to the 'Playlists' section",
            "Right-click on the 'Chill' playlist",
            "Select 'Share Playlist' or 'Copy Link'",
            "Open Messages app",
            "Search for and select 'John' as the recipient",
            "Paste the playlist link in the message field",
            "Add a message like 'Check out this new Chill playlist I made with Mac Miller songs!'",
            "Click the send button"
        ]
    }}
    
    Your steps should be specific, actionable instructions that clearly describe what needs to be done. Only include actions that are necessary to complete the goal.
    """
    
    api_key = os.environ.get("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    request_body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 1, "topK": 40, "topP": 0.95, "maxOutputTokens": 4192},
        "systemInstruction": {
            "parts": [
                {"text": """
You are Zeus, a macOS automation assistant designed to complete user tasks through precise UI interactions.

YOUR ROLE:
- You control macOS by clicking UI elements and using keyboard commands
- You can see and interact with all native and third-party applications
- Your goal is to complete tasks efficiently and thoroughly
"""}
            ]
        }
    }
    
    response = requests.post(url, json=request_body)
    data = response.json()
    candidates = data.get("candidates", [])
    text = candidates[0]["content"]["parts"][0]["text"] if candidates else ""
    
    # Extract JSON steps
    text = text.replace("```", "").strip()
    if "{" in text and "}" in text:
        text = text[text.find("{"):text.rfind("}")+1].strip()
    try:
        steps_json = json.loads(text, strict=False)
        steps = steps_json["steps"]
    except Exception as e:
        print(f"Error parsing steps JSON: {e}")
        steps = []
    return steps