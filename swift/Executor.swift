import Foundation
import AppKit
import CoreGraphics

// Global variables for state management
private let workspace = NSWorkspace.shared
private var currentApplicationBundleId: String?
private var currentDom: [Int: AXUIElement] = [:]

private func updateDOM() {
    currentDom.removeAll()
    
    guard let app = NSWorkspace.shared.frontmostApplication,
          let windowList = CGWindowListCopyWindowInfo(.optionOnScreenOnly, kCGNullWindowID) as? [[String: Any]] else {
        return
    }
    
    let appPid = app.processIdentifier
    let axApp = AXUIElementCreateApplication(appPid)
    
    // Get all windows
    var windowsRef: CFTypeRef?
    AXUIElementCopyAttributeValue(axApp, kAXWindowsAttribute as CFString, &windowsRef)
    
    if let windows = windowsRef as? [AXUIElement] {
        var elementId = 0
        for window in windows {
            // Add window itself
            currentDom[elementId] = window
            elementId += 1
            
            // Get all UI elements in window
            var elementsRef: CFTypeRef?
            AXUIElementCopyAttributeValue(window, kAXChildrenAttribute as CFString, &elementsRef)
            
            if let elements = elementsRef as? [AXUIElement] {
                for element in elements {
                    currentDom[elementId] = element
                    elementId += 1
                }
            }
        }
    }
}

private func openApplication(bundleId: String) throws {
    guard workspace.launchApplication(withBundleIdentifier: bundleId, options: [], additionalEventParamDescriptor: nil, launchIdentifier: nil) else {
        throw NSError(domain: "Executor", code: 2, userInfo: [NSLocalizedDescriptionKey: "Failed to open application: \(bundleId)"])
    }
    currentApplicationBundleId = bundleId
    print("✅ opened application: \(bundleId)")

    // Wait for app to launch and update DOM
    Thread.sleep(forTimeInterval: 1.0)
    updateDOM()
}

private func clickElement(id: Int) throws {
    guard let element = currentDom[id] else {
        throw NSError(domain: "Executor", code: 3, userInfo: [NSLocalizedDescriptionKey: "Element not found: \(id)"])
    }

    let error = AXUIElementPerformAction(element, kAXPressAction as CFString)
    if error != .success {
        throw NSError(domain: "Executor", code: 4, userInfo: [NSLocalizedDescriptionKey: "Failed to click element: \(id)"])
    }
    
    // Get element info for success message
    var roleValue: AnyObject?
    AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &roleValue)
    let role = roleValue as? String ?? ""
    
    var titleValue: AnyObject?
    AXUIElementCopyAttributeValue(element, kAXTitleAttribute as CFString, &titleValue)
    let title = titleValue as? String ?? ""
    
    print("✅ clicked on element [\(id)]<\(role)>\(title)</\(role)>")
}

private func typeInElement(id: Int, text: String) throws {
    guard let element = currentDom[id] else {
        throw NSError(domain: "Executor", code: 5, userInfo: [NSLocalizedDescriptionKey: "Element not found: \(id)"])
    }
    
    // Focus element first
    let error = AXUIElementPerformAction(element, kAXPressAction as CFString)
    if error != .success {
        throw NSError(domain: "Executor", code: 6, userInfo: [NSLocalizedDescriptionKey: "Failed to focus element: \(id)"])
    }
    
    // Set the value directly using accessibility API
    let valueError = AXUIElementSetAttributeValue(element, kAXValueAttribute as CFString, text as CFTypeRef)
    if valueError != .success {
        // If direct value setting fails, fall back to keyboard simulation
        print("setting value failed, falling back to keyboard simulation")
        for char in text {
            let source = CGEventSource(stateID: .hidSystemState)
            
            // Convert character to virtual keycode
            let keyCode: CGKeyCode
            let flags: CGEventFlags
            
            switch char {
            case "A"..."Z":
                keyCode = CGKeyCode(char.asciiValue! - 65 + 0x00)
                flags = .maskShift
            case "a"..."z":
                keyCode = CGKeyCode(char.lowercased().first!.asciiValue! - 97 + 0x00)
                flags = []
            case "0"..."9":
                keyCode = CGKeyCode(char.asciiValue! - 48 + 0x12)
                flags = []
            case " ":
                keyCode = 0x31
                flags = []
            default:
                continue
            }
            
            let keyDown = CGEvent(keyboardEventSource: source, virtualKey: keyCode, keyDown: true)
            let keyUp = CGEvent(keyboardEventSource: source, virtualKey: keyCode, keyDown: false)
            
            keyDown?.flags = flags
            keyUp?.flags = flags
            
            keyDown?.post(tap: .cghidEventTap)
            keyUp?.post(tap: .cghidEventTap)
            
            Thread.sleep(forTimeInterval: 0.05)
        }
    }

    // Get element info for success message
    var roleValue: AnyObject?
    AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &roleValue)
    let role = roleValue as? String ?? ""
    
    print("✅ typed '\(text)' in element [\(id)]<\(role)>")
}

private func executeKeyboardCommand(_ cmdString: String) throws {
    let parts = cmdString.lowercased().split(separator: "+")
    var flags: CGEventFlags = []
    var lastKey = ""
    
    for part in parts {
        switch part {
        case "cmd": flags.insert(.maskCommand)
        case "shift": flags.insert(.maskShift)
        case "alt": flags.insert(.maskAlternate)
        case "ctrl": flags.insert(.maskControl)
        default: lastKey = String(part)
        }
    }
    
    guard let keyAscii = lastKey.first?.asciiValue else {
        throw NSError(domain: "Executor", code: 7, userInfo: [NSLocalizedDescriptionKey: "Invalid keyboard command: \(cmdString)"])
    }
    
    let source = CGEventSource(stateID: .hidSystemState)
    let keyCode = CGKeyCode(keyAscii)
    
    let keyDown = CGEvent(keyboardEventSource: source, virtualKey: keyCode, keyDown: true)
    keyDown?.flags = flags
    keyDown?.post(tap: .cghidEventTap)
    
    let keyUp = CGEvent(keyboardEventSource: source, virtualKey: keyCode, keyDown: false)
    keyUp?.flags = flags
    keyUp?.post(tap: .cghidEventTap)

    print("✅ executed keyboard command: \(cmdString)")
}

@_cdecl("openApp")
public func openApp(bundleId: UnsafePointer<CChar>) -> Bool {
    let bundleIdString = String(cString: bundleId)
    do {
        try openApplication(bundleId: bundleIdString)
        return true
    } catch {
        print("❌ Error: \(error.localizedDescription)")
        return false
    }
}

@_cdecl("clickElement")
public func clickElement(elementId: Int32) -> Bool {
    do {
        try clickElement(id: Int(elementId))
        return true
    } catch {
        print("❌ Error: \(error.localizedDescription)")
        return false
    }
}

@_cdecl("typeText")
public func typeText(elementId: Int32, text: UnsafePointer<CChar>) -> Bool {
    let textString = String(cString: text)
    do {
        try typeInElement(id: Int(elementId), text: textString)
        return true
    } catch {
        print("❌ Error: \(error.localizedDescription)")
        return false
    }
}

@_cdecl("executeCommand")
public func executeCommand(command: UnsafePointer<CChar>) -> Bool {
    let commandString = String(cString: command)
    do {
        try executeKeyboardCommand(commandString)
        return true
    } catch {
        print("❌ Error: \(error.localizedDescription)")
        return false
    }
}