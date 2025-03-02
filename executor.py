import subprocess, os, ctypes
from typing import Optional

class Executor:
    def __init__(self):
        try:
            subprocess.run(["swiftc", "-emit-library", "swift/Executor.swift", "-o", "libexecutor.dylib"], check=True, capture_output=True)
            self.lib = ctypes.CDLL("./libexecutor.dylib")
            self.lib.openApp.argtypes, self.lib.openApp.restype = [ctypes.c_char_p], ctypes.c_bool
            self.lib.clickElement.argtypes, self.lib.clickElement.restype = [ctypes.c_int32], ctypes.c_bool
            self.lib.typeText.argtypes, self.lib.typeText.restype = [ctypes.c_int32, ctypes.c_char_p], ctypes.c_bool
            self.lib.executeCommand.argtypes, self.lib.executeCommand.restype = [ctypes.c_char_p], ctypes.c_bool
        except Exception as e: print(f"Failed to initialize Executor: {e}"); raise
    
    def open_app(self, bundle_id: str) -> bool: return self.lib.openApp(bundle_id.encode('utf-8'))
    def click_element(self, element_id: int) -> bool: return self.lib.clickElement(ctypes.c_int32(element_id))
    def type_text(self, element_id: int, text: str) -> bool: return self.lib.typeText(ctypes.c_int32(element_id), text.encode('utf-8'))
    def execute_command(self, command: str) -> bool: return self.lib.executeCommand(command.encode('utf-8'))
    
    def __del__(self): 
        try:
            if os.path.exists("libexecutor.dylib"): os.remove("libexecutor.dylib")
        except: pass
