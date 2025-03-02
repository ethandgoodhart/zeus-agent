import subprocess
import os

def get_current():
    try:
        subprocess.run(["swiftc", "swift/DOM.swift", "-o", "DOMRunner"], check=True, capture_output=True)
        result = subprocess.run(["./DOMRunner"], check=True, capture_output=True, text=True)
        print(result.stdout)
        os.remove("DOMRunner")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}\nSTDERR: {e.stderr}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    get_current()
