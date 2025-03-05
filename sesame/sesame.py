from dotenv import load_dotenv; load_dotenv()
from elevenlabs import generate
import os
import elevenlabs; elevenlabs.set_api_key(os.getenv("ELEVENLABS_API_KEY"))
import soundfile as sf
import sounddevice as sd
import io

# Device verification
devices = sd.query_devices()
if not any (d['name'] == 'BlackHole 2ch'
for d in devices):
  raise RuntimeError("Blackhole 2ch device not found")

prompt = "Pretend like you are reading a harry potter book and start reading the first chapter."

# Play audio through BlackHole 2ch
audio = generate(text=prompt, voice="UgBBYS2sOqTuMpoF3BR0", model="eleven_flash_v2_5")
data, samplerate = sf.read(io.BytesIO(audio))
sd.play(data, samplerate, device="BlackHole 2ch")
sd.wait() #wait until audio is done
