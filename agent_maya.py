from dotenv import load_dotenv; load_dotenv()
import os
import threading
import asyncio
import time
import json
import requests
import io
import soundfile as sf
import sounddevice as sd
from playwright.async_api import async_playwright

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
        self.is_initialized = False
        self.loop = None  # Store the event loop
        self.ready_for_audio = False  # Flag to indicate when we're ready to send audio
    
    def start(self):
        """Start the Maya voice agent in a separate thread"""
        if self.voice_thread is not None and self.voice_thread.is_alive():
            print("Maya voice agent is already running")
            return self.initial_greeting_event
            
        self.is_running = True
        self.initial_greeting_complete = False
        self.initial_greeting_event.clear()
        self.is_initialized = False
        self.ready_for_audio = False
        
        # Create a new event loop for the thread
        self.loop = asyncio.new_event_loop()
        
        # Start the voice thread
        self.voice_thread = threading.Thread(target=self._run_async_loop)
        self.voice_thread.daemon = True
        self.voice_thread.start()
        
        # Wait for browser initialization before queuing the greeting
        # We'll queue the greeting after initialization is complete
        
        print("✅ Maya voice agent started")
        return self.initial_greeting_event
    
    def _run_async_loop(self):
        """Run the async event loop in a separate thread"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._initialize_and_process())
    
    async def _initialize_and_process(self):
        """Initialize browser and process messages asynchronously"""
        try:
            # Initialize the browser with audio completely disabled
            success = await self._initialize_browser()
            
            if success:
                # Now that initialization is complete, queue the initial greeting
                self.ready_for_audio = True
                print("🔊 Ready to send audio to Maya")
                
                # Queue the initial greeting
                self.say("Pretend like you are Zeus, a computer agent that is executing user commands. Introduce yourself and don't talk until you receive further commands", is_initial_greeting=True)
            
            # Process messages
            while self.is_running:
                message = None
                is_greeting = False
                
                # Check if there's a message in the queue
                with self.lock:
                    if self.message_queue and self.ready_for_audio:
                        message, is_greeting = self.message_queue.pop(0)
                
                if message and self.ready_for_audio:
                    try:
                        # Generate and play audio through BlackHole
                        print(f"🎙️ Maya speaking: '{message}'")
                        await self._play_audio_through_maya(message)
                        
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
                await asyncio.sleep(0.5)
                
        except Exception as e:
            print(f"❌ Error in Maya voice thread: {e}")
            # Ensure the event is set even if there's an error
            if not self.initial_greeting_complete:
                self.initial_greeting_event.set()
        finally:
            # Clean up resources
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
    
    async def _initialize_browser(self):
        """Initialize the browser and Maya interface asynchronously with audio completely disabled"""
        try:
            print("🌐 Starting Maya session...")
            self.playwright = await async_playwright().start()
            
            # Launch browser with audio muted
            self.browser = await self.playwright.chromium.launch(
                headless=False,
                args=["--mute-audio"]  # Start with audio completely muted
            )
            
            # Create context with permissions but no audio
            self.context = await self.browser.new_context(
                permissions=['microphone'],
                # Disable audio completely
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            
            # Create page
            self.page = await self.context.new_page()
            
            # Mute the page before navigating
            await self.page.evaluate("""() => {
                // Disable all audio
                HTMLMediaElement.prototype.play = async function() { return; };
                HTMLAudioElement.prototype.play = async function() { return; };
                
                // Disable speech synthesis
                if (window.speechSynthesis) {
                    window.speechSynthesis.speak = function() { return; };
                }
                
                console.log('All audio and speech disabled');
            }""")
            
            # Navigate to Sesame website
            print("🌐 Navigating to Sesame website...")
            await self.page.goto("https://www.sesame.com/research/crossing_the_uncanny_valley_of_voice#demo")
            await self.page.wait_for_load_state("networkidle")
            
            # Disable all audio again after page load
            await self.page.evaluate("""() => {
                // Disable all audio elements
                const audioElements = document.querySelectorAll('audio, video');
                audioElements.forEach(el => {
                    el.muted = true;
                    el.volume = 0;
                    el.pause();
                    
                    // Override play method
                    const originalPlay = el.play;
                    el.play = function() {
                        this.muted = true;
                        this.volume = 0;
                        return originalPlay.apply(this);
                    };
                });
                
                // Disable speech synthesis
                if (window.speechSynthesis) {
                    window.speechSynthesis.speak = function() { return; };
                }
                
                // Disable getUserMedia
                if (navigator.mediaDevices) {
                    const originalGetUserMedia = navigator.mediaDevices.getUserMedia;
                    navigator.mediaDevices.getUserMedia = async (constraints) => {
                        // If audio is requested, modify the constraints
                        if (constraints && constraints.audio) {
                            // Store original constraints
                            window.originalAudioConstraints = constraints.audio;
                            
                            // Disable audio initially
                            constraints.audio = false;
                        }
                        return await originalGetUserMedia(constraints);
                    };
                }
                
                console.log('All audio and speech disabled after page load');
            }""")
            
            # Configure audio settings to use BlackHole (but keep it disabled for now)
            print("⚙️ Configuring audio settings...")
            await self.page.evaluate("""() => {
                if (navigator.mediaDevices) {
                    // Store the original methods
                    window.originalEnumerateDevices = navigator.mediaDevices.enumerateDevices;
                    window.originalGetUserMedia = navigator.mediaDevices.getUserMedia;
                    
                    // Override enumerateDevices to prioritize BlackHole 2ch
                    navigator.mediaDevices.enumerateDevices = async () => {
                        const devices = await window.originalEnumerateDevices.call(navigator.mediaDevices);
                        
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
                    
                    // Override getUserMedia but keep it disabled for now
                    navigator.mediaDevices.getUserMedia = async (constraints) => {
                        // Disable audio initially
                        let modifiedConstraints = {...constraints};
                        if (modifiedConstraints.audio) {
                            // Store original audio constraints
                            window.originalAudioConstraints = modifiedConstraints.audio;
                            // Disable audio
                            modifiedConstraints.audio = false;
                        }
                        
                        // Call original with modified constraints
                        return await window.originalGetUserMedia.call(navigator.mediaDevices, modifiedConstraints);
                    };
                    
                    console.log('Audio configuration set up but disabled');
                } else {
                    console.error('navigator.mediaDevices not available');
                }
            }""")
            
            # Target the Maya button
            maya_button_selector = "[data-testid='maya-button']"
            
            try:
                maya_button = self.page.locator(maya_button_selector)
                if await maya_button.count() > 0:
                    print("🎯 Found Maya button! Clicking now...")
                    await maya_button.first.click()
                    
                    # Give Maya time to initialize
                    await asyncio.sleep(7)
                    print("✅ Maya initialized and ready")
                    
                    # Now prepare the audio system but keep it disabled until we're ready
                    await self._prepare_audio_system()
                    
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
    
    async def _prepare_audio_system(self):
        """Prepare the audio system but keep it disabled until we're ready"""
        try:
            # Configure the audio system to use BlackHole but keep it disabled
            await self.page.evaluate("""() => {
                // Prepare to enable audio later
                window.enableAudio = function() {
                    // Enable audio elements
                    const audioElements = document.querySelectorAll('audio, video');
                    audioElements.forEach(el => {
                        el.muted = false;
                        el.volume = 1;
                    });
                    
                    // Restore getUserMedia
                    if (navigator.mediaDevices && window.originalGetUserMedia) {
                        navigator.mediaDevices.getUserMedia = async (constraints) => {
                            let modifiedConstraints = {...constraints};
                            
                            // If audio is requested, use BlackHole
                            if (modifiedConstraints.audio) {
                                // Get all audio devices
                                const devices = await window.originalEnumerateDevices.call(navigator.mediaDevices);
                                const blackHoleDevice = devices.find(device => 
                                    device.kind === 'audioinput' && device.label.includes('BlackHole 2ch')
                                );
                                
                                if (blackHoleDevice) {
                                    // Force selection of BlackHole 2ch
                                    if (typeof modifiedConstraints.audio === 'boolean') {
                                        modifiedConstraints.audio = { deviceId: { exact: blackHoleDevice.deviceId } };
                                    } else {
                                        modifiedConstraints.audio.deviceId = { exact: blackHoleDevice.deviceId };
                                    }
                                    console.log('Successfully set BlackHole 2ch as the audio input device');
                                }
                            }
                            
                            return await window.originalGetUserMedia.call(navigator.mediaDevices, modifiedConstraints);
                        };
                    }
                    
                    console.log('Audio system enabled');
                    return true;
                };
                
                console.log('Audio system prepared but still disabled');
            }""")
            
            print("🔇 Audio system prepared but disabled")
            return True
        except Exception as e:
            print(f"❌ Error preparing audio system: {e}")
            return False
    
    async def _enable_audio(self):
        """Enable the audio system when we're ready to use it"""
        try:
            # Call the enableAudio function we defined earlier
            result = await self.page.evaluate("window.enableAudio()")
            
            if result:
                print("🔊 Audio system enabled")
                return True
            else:
                print("❌ Failed to enable audio system")
                return False
        except Exception as e:
            print(f"❌ Error enabling audio system: {e}")
            return False
    
    async def _play_audio_through_maya(self, text):
        """Generate audio with ElevenLabs and play it through BlackHole to Maya"""
        try:
            # Enable audio if not already enabled
            if not self.ready_for_audio:
                await self._enable_audio()
                self.ready_for_audio = True
            
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
            # Use requests in a non-blocking way
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(url, json=data, headers=headers)
            )
            
            if response.status_code != 200:
                raise Exception(f"API call failed with status code {response.status_code}: {response.text}")
            
            print("✅ Received audio from ElevenLabs")
            audio_bytes = response.content
            
            # Process audio in a non-blocking way
            data, samplerate = await loop.run_in_executor(
                None,
                lambda: sf.read(io.BytesIO(audio_bytes))
            )
            
            print("🔊 Playing audio through BlackHole 2ch...")
            # Play audio (this is blocking but we'll run it in a separate thread)
            await loop.run_in_executor(
                None,
                lambda: sd.play(data, samplerate, device="BlackHole 2ch")
            )
            
            duration = len(data) / samplerate
            print(f"⏳ Audio playing for approximately {duration:.1f} seconds...")
            
            # Wait for audio to finish playing plus a buffer for Maya to respond
            await asyncio.sleep(duration + 3)
            
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
            self.is_initialized = True
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
        
        # The browser and playwright will be closed in the finally block of _initialize_and_process
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