from playwright.sync_api import Playwright, sync_playwright, expect
import os
import time

def start_sesame(playwright: Playwright):
    browser = playwright.chromium.launch(
        headless=False, 
        ignore_default_args=["--mute-audio"],
        args=["--no-sandbox", '--allow-file-access-from-files', "--use-fake-ui-for-media-stream"]
    )
    context = browser.new_context()
    context.grant_permissions(permissions=["microphone"])
    page = context.new_page()
    
    # Navigate to the Sesame demo page
    page.goto("https://www.sesame.com/research/crossing_the_uncanny_valley_of_voice#demo")
    
    # Inject JavaScript to make BlackHole 2ch the only available microphone option
    page.evaluate("""() => {
        if (navigator.mediaDevices) {
            // Override enumerateDevices to only show BlackHole 2ch
            const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices;
            navigator.mediaDevices.enumerateDevices = async () => {
                const devices = await originalEnumerateDevices();
                // Filter to only include BlackHole 2ch for audio input
                return devices.filter(device => 
                    device.kind !== 'audioinput' || device.label.includes('BlackHole 2ch')
                );
            };
            
            // Override getUserMedia to always use BlackHole 2ch
            const originalGetUserMedia = navigator.mediaDevices.getUserMedia;
            navigator.mediaDevices.getUserMedia = async (constraints) => {
                if (constraints.audio) {
                    constraints.audio = { deviceId: { exact: 'BlackHole 2ch' } };
                }
                return await originalGetUserMedia(constraints);
            };
        }
    }""")
    
    time.sleep(1)
    page.click("[data-testid='maya-button']")
    page.pause()
    context.close()
    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        start_sesame(playwright)