from dotenv import load_dotenv; load_dotenv()
import threading
from elevenlabs import generate, play
import os
import elevenlabs; elevenlabs.set_api_key(os.getenv("ELEVENLABS_API_KEY"))
import io
import requests
import json
# Create a lock to prevent multiple narrations from running simultaneously
narration_lock = threading.Lock()

def async_narrate(actions):
    def narrate_thread():
        # Acquire lock to ensure only one narration happens at a time
        if not narration_lock.acquire(blocking=False):
            print("Narration already in progress, skipping")
            return
            
        try:
            # Get API key
            api_key = os.environ.get("GEMINI_API_KEY")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            
            # Create prompt for narration
            actions_text = str(actions)
            prompt = f"Pretend you're a witty, playful friend watching over someone's shoulder. In ONE short, conversational sentence, describe what this computer agent is doing: {actions_text}. Be casual, use humor, and make it sound like you're narrating a friend's actions. Keep it brief and natural - like you're chatting with a buddy. No explanations or commentary needed!"
            
            # Prepare request
            request_body = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 1, "topK": 40, "topP": 0.95, "maxOutputTokens": 1024}
            }
            
            # Get narration from Gemini
            response = requests.post(url, json=request_body)
            data = response.json()
            candidates = data.get("candidates", [])
            narration = candidates[0]["content"]["parts"][0]["text"] if candidates else ""

            audio = generate(text=narration, voice="NYC9WEgkq1u4jiqBseQ9", model="eleven_flash_v2_5")
            play(audio)  # This is blocking and will wait until audio finishes playing
        except Exception as e:
            print(f"Narration error: {e}")
        finally:
            # Always release the lock when done
            narration_lock.release()
    
    # Start narration in background thread
    threading.Thread(target=narrate_thread, daemon=True).start()