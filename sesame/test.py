from playwright.sync_api import Playwright, sync_playwright, expect
import os
import time

def start_sesame(playwright: Playwright):
    # Launch browser with audio congif
    browser = playwright.chromium.launch(
        headless=False, 
        ignore_default_args=["--mute-audio"],
        args=[
            "--no-sandbox", 
            "--allow-file-access-from-files", 
            "--use-fake-ui-for-media-stream",
            # Specify BlackHole 2ch as the audio source
            "--use-file-for-fake-audio-capture=BlackHole 2ch"
        ]
    )
    
    # Set up context with permissions
    context = browser.new_context()
    context.grant_permissions(permissions=["microphone"])
    
    # Create page and navigate
    page = context.new_page()
    page.goto("https://www.sesame.com/research/crossing_the_uncanny_valley_of_voice#demo")
    
    # Wait for page to load. Don't really need this though.
    # time.sleep(1)
    
    # Injection of JavaScript ensures BlackHole 2ch is selected
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
                        }
                    }
                    
                    return await originalGetUserMedia.call(navigator.mediaDevices, constraints);
                } catch (e) {
                    console.error('Error overriding getUserMedia:', e);
                    return await originalGetUserMedia.call(navigator.mediaDevices, constraints);
                }
            };
        }
    }""")
    
    # Click Maya button
    try:
        page.click("[data-testid='maya-button']")
    except:
        print("Couldn't find maya-button, continuing anyway")
    
    # Pause for debugging/viewing
    page.pause()
    
    # Clean up
    context.close()
    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        start_sesame(playwright)
