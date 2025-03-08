from dotenv import load_dotenv; load_dotenv()
import os
import io
import time
import threading
from playwright.sync_api import Playwright, sync_playwright
import soundfile as sf
import sounddevice as sd
import requests

def generate_and_play_audio(text, voice_id="UgBBYS2sOqTuMpoF3BR0", model_id="eleven_turbo_v2"):
    """Generate audio with ElevenLabs and play it through BlackHole 2ch"""
    devices = sd.query_devices()
    blackhole_found = False
    
    for d in devices:
        if 'BlackHole 2ch' in str(d['name']):
            blackhole_found = True
            break
    
    if not blackhole_found:
        raise RuntimeError("❌ BlackHole 2ch device not found. Please ensure it's properly installed")
    
    print(f"🎙️ Generating audio for: '{text[:50]}...'")
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": os.getenv("ELEVENLABS_API_KEY")
    }
    data = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    
    print("📡 Sending request to ElevenLabs API...")
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"API call failed with status code {response.status_code}: {response.text}")
    
    print("✅ Received audio from ElevenLabs")
    audio_bytes = response.content
    
    data, samplerate = sf.read(io.BytesIO(audio_bytes))
    
    print("🔊 Playing audio through BlackHole 2ch...")
    sd.play(data, samplerate, device="BlackHole 2ch")
    
    duration = len(data) / samplerate
    return duration

def start_sesame_with_maya(playwright: Playwright, prompt):
    """Start Sesame and configure it to use BlackHole as input for Maya"""
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    print("🌐 Navigating to Sesame website...")
    page.goto("https://www.sesame.com/research/crossing_the_uncanny_valley_of_voice#demo")
    page.wait_for_load_state("networkidle")

    context.grant_permissions(['microphone'])
    
    print("⚙️ Configuring audio settings...")
    page.evaluate("""() => {
        if (navigator.mediaDevices) {
            // Store the original methods
            const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices;
            const originalGetUserMedia = navigator.mediaDevices.getUserMedia;
            
            // Override enumerateDevices to prioritize BlackHole 2ch
            navigator.mediaDevices.enumerateDevices = async () => {
                const devices = await originalEnumerateDevices.call(navigator.mediaDevices);
                
                // Find BlackHole device
                const blackHoleDevice = devices.find(device => 
                    device.kind === 'audioinput' && device.label.includes('BlackHole 2ch')
                );
                
                if (blackHoleDevice) {
                    // Move BlackHole to the first position for audioinput devices
                    const filteredDevices = devices.filter(device => 
                        device.kind !== 'audioinput' || !device.label.includes('BlackHole 2ch')
                    );
                    
                    return [blackHoleDevice, ...filteredDevices];
                }
                
                return devices;
            };
            
            // Override getUserMedia to always select BlackHole 2ch
            navigator.mediaDevices.getUserMedia = async (constraints) => {
                try {
                    // If audio constraints exist
                    if (constraints && constraints.audio) {
                        // Get all audio devices
                        const devices = await originalEnumerateDevices.call(navigator.mediaDevices);
                        const blackHoleDevice = devices.find(device => 
                            device.kind === 'audioinput' && device.label.includes('BlackHole 2ch')
                        );
                        
                        if (blackHoleDevice) {
                            // Force selection of BlackHole 2ch
                            if (typeof constraints.audio === 'boolean') {
                                constraints.audio = { deviceId: { exact: blackHoleDevice.deviceId } };
                            } else {
                                constraints.audio.deviceId = { exact: blackHoleDevice.deviceId };
                            }
                            console.log('Successfully set BlackHole 2ch as the audio input device');
                        } else {
                            console.error('BlackHole 2ch device not found');
                        }
                    }
                    
                    return await originalGetUserMedia.call(navigator.mediaDevices, constraints);
                } catch (e) {
                    console.error('Error overriding getUserMedia:', e);
                    return await originalGetUserMedia.call(navigator.mediaDevices, constraints);
                }
            };
            
            console.log('Audio device selection overrides installed');
        } else {
            console.error('navigator.mediaDevices not available');
        }
    }""")
    
    # Verify BlackHole 2ch is available
    has_blackhole = page.evaluate("""() => {
        return navigator.mediaDevices.enumerateDevices()
            .then(devices => {
                const blackHoleDevice = devices.find(device => 
                    device.kind === 'audioinput' && device.label.includes('BlackHole 2ch')
                );
                return !!blackHoleDevice;
            })
            .catch(err => {
                console.error('Error checking for BlackHole device:', err);
                return false;
            });
    }""")
    
    if has_blackhole:
        print("✅ BlackHole 2ch device found and set as default microphone")
    else:
        print("❌ BlackHole 2ch device not found in browser. Please ensure it's properly installed")
        browser.close()
        return
    
    # Target the Maya button
    maya_button_selector = "[data-testid='maya-button']"
    
    try:
        maya_button = page.locator(maya_button_selector)
        if maya_button.count() > 0:
            print("🎯 Found Maya button! Clicking now...")
            maya_button.first.click()
            
            # Now play audio through BlackHole
            time.sleep(2)  # Give Maya time to initialize
            
            # Generate and play audio in a separate thread
            audio_duration = generate_and_play_audio(prompt)
            
            # Wait for audio to finish playing
            print(f"⏳ Audio playing for approximately {audio_duration:.1f} seconds...")
            time.sleep(audio_duration + 1)  # Add 1 second buffer
            
            print("✅ Audio playback completed")
        else:
            print("❌ Couldn't find the Maya button.")
    except Exception as e:
        print(f"❌ Error: {e}")


    input("Press Enter to close the browser...")
    browser.close()

if __name__ == "__main__":

    default_prompt = "Pretend like you are reading a harry potter book and start reading the first chapter."
    
    user_prompt = input("Enter your prompt (or press Enter for default): ")
    prompt = user_prompt if user_prompt.strip() else default_prompt
    
    with sync_playwright() as playwright:
        start_sesame_with_maya(playwright, prompt)