import Foundation
import CoreGraphics
import AppKit
import ApplicationServices

// Global variables for state management
private let workspace = NSWorkspace.shared
private var currentApplicationBundleId: String?
private var currentDom: [Int: AXUIElement] = [:]

// MARK: - Private Methods - Context & DOM
public func getCurrentAppContext() -> String {
    var context = ""
    
    // Get active app info
    context += "### Active app: \(currentApplicationBundleId ?? "None")\n"
    
    // Only get DOM if not our own app
    if currentApplicationBundleId != "dev.ethan.flow" {
        context += "#### MacOS app elements:\n"
        getCurrentDom()
        
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

public func getCurrentDom() {
    currentDom.removeAll()
    
    guard let activeApp = workspace.frontmostApplication else { return }
    let appRef = AXUIElementCreateApplication(activeApp.processIdentifier)
    
    func addElementToDOM(_ element: AXUIElement, depth: Int = 0, nextId: inout Int) {
        // Check if element is clickable before adding to DOM
        var actionsArray: CFArray?
        let isClickable = AXUIElementCopyActionNames(element, &actionsArray) == .success &&
            (actionsArray as? [String])?.contains(kAXPressAction) == true
        
        if isClickable {
            currentDom[nextId] = element
            nextId += 1
        }
        
        var children: AnyObject?
        let result = AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &children)
        
        if result == .success, let childElements = children as? [AXUIElement] {
            for child in childElements {
                addElementToDOM(child, depth: depth + 1, nextId: &nextId)
            }
        }
    }
    
    var nextId = 1
    addElementToDOM(appRef, nextId: &nextId)
}