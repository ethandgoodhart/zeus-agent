from playwright.sync_api import Playwright, sync_playwright
import time

def start_sesame(playwright: Playwright):
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    
    # Navigate to the page
    page.goto("https://www.sesame.com/research/crossing_the_uncanny_valley_of_voice#demo")
    page.wait_for_load_state("networkidle")
    
    context.grant_permissions(['microphone'])
    
    
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
        print("❌ BlackHole 2ch device not found. Please ensure it's properly installed")
    # Target the button using the test ID
    maya_button_selector = "[data-testid='maya-button']"
    
    try:
        maya_button = page.locator(maya_button_selector)
        if maya_button.count() > 0:
            print("Found Maya button! Clicking now...")
            maya_button.first.click()
        else:
            print("Couldn't find the Maya button.")
    except Exception as e:
        print(f"Error clicking Maya button: {e}")

    page.pause()  # Pause execution to inspect the page
    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        start_sesame(playwright)