import subprocess
import os

def list_installed_apps():
    # """Generate a list of 20 prompts I should try for my AI agent based on the currently installed apps on my mac.
    # Format should be APPNAME - "PROMPT", eg. Spotify - "Play some songs by Led Zepplin".
    # Apps:"""
    app_info = []
    for directory in ['/Applications', os.path.expanduser('~/Applications'), '/System/Applications']:
        if os.path.exists(directory):
            for item in os.listdir(directory):
                if item.endswith('.app'):
                    app_name = item.replace('.app', '')
                    app_path = os.path.join(directory, item)
                    icon_path = os.path.join(app_path, 'Contents', 'Resources', 'AppIcon.icns')
                    if not os.path.exists(icon_path):
                        resources_dir = os.path.join(app_path, 'Contents', 'Resources')
                        if os.path.exists(resources_dir):
                            icns_files = [f for f in os.listdir(resources_dir) if f.endswith('.icns')]
                            icon_path = os.path.join(resources_dir, icns_files[0]) if icns_files else "No icon found"
                        else:
                            icon_path = "No icon found"
                    try:
                        result = subprocess.run(['mdls', '-name', 'kMDItemCFBundleIdentifier', '-r', app_path], 
                                               capture_output=True, text=True, check=False)
                        bundle_id = result.stdout.strip() or "Unknown"
                        app_info.append([app_name, bundle_id, icon_path])
                    except Exception:
                        app_info.append([app_name, "Unknown", icon_path])
    return "\n".join(f"- {' | '.join(app[:2])}" for app in sorted(app_info))

if __name__ == "__main__":
    print(list_installed_apps())