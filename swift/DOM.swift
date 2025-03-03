import Foundation
import CoreGraphics
import AppKit
import ApplicationServices

public let workspace = NSWorkspace.shared

public func getCurrentDom() -> [Int: AXUIElement] {
    var currentDom: [Int: AXUIElement] = [:]
    let maxElements = 400
    let maxChildren = 50
    
    guard let activeApp = workspace.frontmostApplication else { return [:] }
    let appRef = AXUIElementCreateApplication(activeApp.processIdentifier)
    
    func addElementToDOM(_ element: AXUIElement, depth: Int = 0, nextId: inout Int) {
        // Skip menu items
        var roleValue: AnyObject?
        AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &roleValue)
        let role = roleValue as? String ?? ""
        if role == "AXMenuItem" { return }
        
        // Check if element is clickable before adding to DOM
        var actionsArray: CFArray?
        let isClickable = AXUIElementCopyActionNames(element, &actionsArray) == .success &&
            (actionsArray as? [String])?.contains(kAXPressAction) == true
        
        if isClickable && currentDom.count < maxElements {
            currentDom[nextId] = element
            nextId += 1
        }
        
        if currentDom.count >= maxElements { return }
        
        var children: AnyObject?
        let result = AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &children)
        
        if result == .success, let childElements = children as? [AXUIElement] {
            // Limit number of children to process at each level
            let childrenToProcess = childElements.prefix(maxChildren)
            for child in childrenToProcess {
                if currentDom.count >= maxElements { break }
                addElementToDOM(child, depth: depth + 1, nextId: &nextId)
            }
        }
    }
    
    var nextId = 1
    addElementToDOM(appRef, nextId: &nextId)
    
    return currentDom
}

public func getCurrentAppContext() -> String {
    var context = ""
    
    // Get active app info
    guard let activeApp = workspace.frontmostApplication else { return "No active application" }
    context += "### Active app: \(activeApp.localizedName ?? "Unknown") (\(activeApp.bundleIdentifier ?? "Unknown"))\n"
    
    // Only get DOM if not our own app
    if activeApp.bundleIdentifier != "dev.ethan.flow" {
        context += "#### MacOS app elements:\n"
        
        let currentDom = getCurrentDom()
        for (id, element) in currentDom.sorted(by: { $0.key < $1.key }) {
            var roleValue: AnyObject?
            AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &roleValue)
            let role = roleValue as? String ?? ""
            
            var titleValue: AnyObject?
            AXUIElementCopyAttributeValue(element, kAXTitleAttribute as CFString, &titleValue)
            let title = titleValue as? String ?? ""
            
            var descValue: AnyObject?
            AXUIElementCopyAttributeValue(element, kAXDescriptionAttribute as CFString, &descValue)
            let description = descValue as? String ?? ""
            
            var valueAttr: AnyObject?
            AXUIElementCopyAttributeValue(element, kAXValueAttribute as CFString, &valueAttr)
            let value = valueAttr as? String ?? ""
            
            var placeholderValue: AnyObject?
            AXUIElementCopyAttributeValue(element, kAXPlaceholderValueAttribute as CFString, &placeholderValue)
            let placeholder = placeholderValue as? String ?? ""
            
            // Check if element is clickable
            var isClickable = false
            var actionsArray: CFArray?
            if AXUIElementCopyActionNames(element, &actionsArray) == .success,
               let actions = actionsArray as? [String],
               actions.contains(kAXPressAction) {
                isClickable = true
            }
            
            var elementInfo = ""
            if isClickable {
                elementInfo = "[\(id)]<\(role)>"
            }
            
            if !title.isEmpty { elementInfo += title }
            if !description.isEmpty { elementInfo += description }
            if !value.isEmpty { elementInfo += value }
            if !placeholder.isEmpty { elementInfo += placeholder }
            elementInfo += "</\(role)>\n"
            
            context += elementInfo
        }
    }

    context += "\n### Mac app bundleids:\n"
    var uniqueBundleIds = Set<String>()    
    for app in workspace.runningApplications {
        if let bundleId = app.bundleIdentifier, !uniqueBundleIds.contains(bundleId) {
            uniqueBundleIds.insert(bundleId)
            context += "\(app.localizedName ?? ""), \(bundleId)\n"
        }
    }

    return context
}