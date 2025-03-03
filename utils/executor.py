import subprocess, os, ctypes
from typing import Optional, List
import pyperclip
import pyautogui
import time

class Executor:
    def __init__(self):
        try:
            # Compile the Swift code to a dynamic library
            result = subprocess.run(["swiftc", "-emit-library", "swift/Executor.swift", "swift/DOM.swift", "-o", "libexecutor.dylib"], check=True)            
            if result.returncode != 0:
                print(f"Swift compilation error: {result.stderr}")
                raise Exception(f"Swift compilation failed with code {result.returncode}")
            # Code sign the library with entitlements
            subprocess.run(["codesign", "-s", "-", "--entitlements", "swift/Executor.entitlements", "libexecutor.dylib"], check=True)
            self.lib = ctypes.CDLL("./libexecutor.dylib")

            self.lib.openApp.argtypes, self.lib.openApp.restype = [ctypes.c_char_p], ctypes.c_bool
            self.lib.clickElement.argtypes, self.lib.clickElement.restype = [ctypes.c_int32], ctypes.c_bool
            self.lib.get_dom_str.restype = ctypes.c_char_p
        except Exception as e: print(f"Failed to initialize Executor: {e}"); raise
    
    def open_app(self, bundle_id: str) -> bool:
        return self.lib.openApp(bundle_id.encode('utf-8'))
    def click_element(self, element_id: int) -> bool:
        return self.lib.clickElement(ctypes.c_int32(element_id))
    def type(self, text: str) -> bool:
        pyautogui.write(text)
        print("✅ typed text:", text)
        return True
    def hotkey(self, keys: List[str]) -> bool:
        pyautogui.hotkey(*keys)
        print("✅ pressed keys:", keys)
        return True
    
    def wait(self, seconds: float) -> bool:
        time.sleep(seconds)
        print(f"✅ waited {seconds} sec")
        return True
    def get_dom_str(self) -> str:
        result = self.lib.get_dom_str()
        dom_str = result.decode('utf-8') if result else ""
        return dom_str
    
    def __del__(self): 
        try:
            if os.path.exists("libexecutor.dylib"): os.remove("libexecutor.dylib")
        except: pass
