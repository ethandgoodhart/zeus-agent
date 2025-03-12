from dotenv import load_dotenv; load_dotenv()
import os
import threading
import time
import json
import requests
import io
import soundfile as sf
import sounddevice as sd
from playwright.sync_api import sync_playwright

class MayaVoiceAgent:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.voice_thread = None
        self.is_running = False
        self.message_queue = []
        self.lock = threading.Lock()
        self.initial_greeting_complete = False
        self.initial_greeting_event = threading.Event()
    
    def start(self):
        """Start the Maya voice agent in a separate thread"""
        if self.voice_thread is not None and self.voice_thread.is_alive():
            print("Maya voice agent is already running")
            return self.initial_greeting_event
            
        self.is_running = True
        self.initial_greeting_complete = False
        self.initial_greeting_event.clear()
        
        # Initialize the browser first
        self._initialize_browser()
        
        # Then start the voice thread
        self.voice_thread = threading.Thread(target=self._process_message_queue)
        self.voice_thread.daemon = True
        self.voice_thread.start()
        
        # Queue the initial greeting
        self.say("Pretend like you are Zeus, a computer agent that is executing user commands. Introduce yourself and when you receive a command explain how you will fulfill it.", is_initial_greeting=True)


        
        print("✅ Maya voice agent started")
        return self.initial_greeting_event
    
    def _initialize_browser(self):
        """Initialize the browser and Maya interface"""
        try:
            print("🌐 Starting Maya session...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=False)
            self.context = self.browser.new_context()
            self.page = self.context.new_page()
            
            # Navigate to Sesame website
            print("🌐 Navigating to Sesame website...")
            self.page.goto("https://www.sesame.com/research/crossing_the_uncanny_valley_of_voice#demo")
            self.page.wait_for_load_state("networkidle")
            
            # Grant microphone permissions
            self.context.grant_permissions(['microphone'])
            
            # Configure audio settings to use BlackHole
            print("⚙️ Configuring audio settings...")
            self.page.evaluate("""() => {
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
            has_blackhole = self.page.evaluate("""() => {
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
                self.browser.close()
                return False
            
            # Target the Maya button
            maya_button_selector = "[data-testid='maya-button']"
            
            try:
                maya_button = self.page.locator(maya_button_selector)
                if maya_button.count() > 0:
                    print("🎯 Found Maya button! Clicking now...")
                    maya_button.first.click()
                    
                    # Give Maya time to initialize
                    time.sleep(7)
                    print("✅ Maya initialized and ready")
                    return True
                else:
                    print("❌ Couldn't find the Maya button.")
                    return False
            except Exception as e:
                print(f"❌ Error: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Error initializing browser: {e}")
            return False
    
    def _process_message_queue(self):
        """Process messages in the queue"""
        try:
            while self.is_running:
                message = None
                is_greeting = False
                
                # Check if there's a message in the queue
                with self.lock:
                    if self.message_queue:
                        message, is_greeting = self.message_queue.pop(0)
                
                if message:
                    try:
                        # Generate and play audio through BlackHole
                        print(f"🎙️ Maya speaking: '{message}'")
                        self._play_audio_through_maya(message)
                        
                        # If this was the initial greeting, signal that it's complete
                        if is_greeting:
                            print("✅ Initial greeting completed")
                            self.initial_greeting_complete = True
                            self.initial_greeting_event.set()
                            
                    except Exception as e:
                        print(f"❌ Error speaking through Maya: {e}")
                        # If there was an error with the initial greeting, still signal completion
                        if is_greeting:
                            self.initial_greeting_complete = True
                            self.initial_greeting_event.set()
                
                # Sleep to prevent high CPU usage
                time.sleep(0.5)
                
        except Exception as e:
            print(f"❌ Error in Maya voice thread: {e}")
            # Ensure the event is set even if there's an error
            if not self.initial_greeting_complete:
                self.initial_greeting_event.set()
    
    def _play_audio_through_maya(self, text):
        """Generate audio with ElevenLabs and play it through BlackHole to Maya"""
        try:
            # Check if BlackHole is available
            devices = sd.query_devices()
            blackhole_found = False
            
            for d in devices:
                if 'BlackHole 2ch' in str(d['name']):
                    blackhole_found = True
                    break
            
            if not blackhole_found:
                raise RuntimeError("❌ BlackHole 2ch device not found. Please ensure it's properly installed")
            
            print(f"🎙️ Generating audio for: '{text[:50]}...'")
            
            # Get audio from ElevenLabs
            url = f"https://api.elevenlabs.io/v1/text-to-speech/NYC9WEgkq1u4jiqBseQ9"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": os.getenv("ELEVENLABS_API_KEY")
            }
            data = {
                "text": text,
                "model_id": "eleven_flash_v2_5",
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
            print(f"⏳ Audio playing for approximately {duration:.1f} seconds...")
            
            # Wait for audio to finish playing plus a buffer for Maya to respond
            time.sleep(duration + 3)
            
            print("✅ Audio playback completed")
            return True
            
        except Exception as e:
            print(f"❌ Error playing audio through Maya: {e}")
            return False
    
    def say(self, message, is_initial_greeting=False):
        """Add a message to the queue to be spoken by Maya"""
        with self.lock:
            self.message_queue.append((message, is_initial_greeting))
        print(f"🗣️ Queued for Maya: '{message}'")
    
    def wait_for_initial_greeting(self, timeout=60):
        """Wait until the initial greeting has been spoken and Maya has responded"""
        print(f"⏳ Waiting for Maya to complete initial greeting (timeout: {timeout}s)...")
        result = self.initial_greeting_event.wait(timeout)
        if result:
            print("✅ Maya has completed the initial greeting")
        else:
            print("⚠️ Timeout waiting for Maya to complete initial greeting")
        return result
    
    def process_command(self, command):
        """Send the user's command directly to Maya"""
        self.say(command)
    
    def stop(self):
        """Stop the Maya voice agent"""
        self.is_running = False
        if self.voice_thread and self.voice_thread.is_alive():
            self.voice_thread.join(timeout=5)
            
        # Close the browser
        if self.browser:
            try:
                self.browser.close()
            except:
                pass
            
        # Stop the playwright
        if self.playwright:
            try:
                self.playwright.stop()
            except:
                pass
                
        print("✅ Maya voice agent stopped")

# Global instance that can be imported by agent.py
maya_agent = MayaVoiceAgent()

# For testing
if __name__ == "__main__":
    agent = MayaVoiceAgent()
    event = agent.start()
    
    # Wait for the initial greeting to complete
    agent.wait_for_initial_greeting()
    
    # Test sending a command
    agent.process_command("Make me a new note with a list of famous chess players")
    time.sleep(10)
    
    agent.stop() 