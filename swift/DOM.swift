import Foundation
import AppKit
import ApplicationServices

func getDomList() -> String {
    var domOutput = ""
    guard let activeApp = NSWorkspace.shared.frontmostApplication else { return "No active app" }
    
    let appRef = AXUIElementCreateApplication(activeApp.processIdentifier)
    let bundleId = activeApp.bundleIdentifier ?? "unknown"
    domOutput += "App: \(activeApp.localizedName ?? "Unknown") (\(bundleId))\n"
    
    func processElement(_ element: AXUIElement, depth: Int = 0) {
        let indent = String(repeating: "  ", count: depth)
        
        var roleValue: AnyObject?
        AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &roleValue)
        let role = roleValue as? String ?? "unknown"
        
        var titleValue: AnyObject?
        AXUIElementCopyAttributeValue(element, kAXTitleAttribute as CFString, &titleValue)
        let title = titleValue as? String ?? ""
        
        var valueAttr: AnyObject?
        AXUIElementCopyAttributeValue(element, kAXValueAttribute as CFString, &valueAttr)
        let value = valueAttr as? String ?? ""
        
        var actionsArray: CFArray?
        let isClickable = AXUIElementCopyActionNames(element, &actionsArray) == .success && 
                         (actionsArray as? [String])?.contains(kAXPressAction) == true
        
        domOutput += "\(indent)[\(role)] \(title) \(value) \(isClickable ? "[clickable]" : "")\n"
        
        var children: AnyObject?
        let result = AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &children)
        
        if result == .success, let childElements = children as? [AXUIElement] {
            for child in childElements {
                processElement(child, depth: depth + 1)
            }
        }
    }
    
    var children: AnyObject?
    let result = AXUIElementCopyAttributeValue(appRef, kAXChildrenAttribute as CFString, &children)
    
    if result == .success, let childElements = children as? [AXUIElement] {
        for child in childElements {
            processElement(child)
        }
    }
    
    return domOutput
}

print(getDomList())