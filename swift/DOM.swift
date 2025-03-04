import Foundation
import CoreGraphics
import AppKit
import ApplicationServices

public let workspace = NSWorkspace.shared

public func getFrontApp() -> [String] {
    let frontmostAppScript = """
    tell application "System Events"
        set frontApp to first process whose frontmost is true
        set pid to unix id of frontApp
        set appName to name of frontApp
        set bundleId to bundle identifier of frontApp
        return {pid, appName, bundleId}
    end tell
    """
    
    let process = Process()
    process.launchPath = "/usr/bin/osascript"
    process.arguments = ["-e", frontmostAppScript]
    
    let outputPipe = Pipe()
    process.standardOutput = outputPipe
    
    do {
        try process.run()
        process.waitUntilExit()
        let outputData = outputPipe.fileHandleForReading.readDataToEndOfFile()
        if let scriptOutput = String(data: outputData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) {
            let components = scriptOutput.components(separatedBy: ", ")
            if components.count >= 3 {
                return [components[0], components[1], components[2]]
            }
        }
    } catch {
        print("Process error: \(error)")
    }
    
    return ["0", "Unknown", ""]
}

public func getCurrentDom() -> [Int: AXUIElement] {
    var currentDom: [Int: AXUIElement] = [:]
    let maxElements = 500//99999
    let maxChildren = 100//99999
    
    let frontAppInfo = getFrontApp()
    let pid = Int32(frontAppInfo[0]) ?? 0
    let appName = frontAppInfo[1]
    let bundleId = frontAppInfo[2]
    let appRef = AXUIElementCreateApplication(pid)
    print("getCurrentDom() - activeApp: \(appName) (\(bundleId))")

    let appFrame = NSScreen.main?.frame ?? CGRect.zero
    
    func addElementToDOM(_ element: AXUIElement, depth: Int = 0, nextId: inout Int) {
        // Don't process if maxElements reached
        if currentDom.count >= maxElements { return }
        // Skip menu items
        var roleValue: AnyObject?
        AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &roleValue)
        let role = roleValue as? String ?? ""
        if role == "AXMenuItem" || role == "AXMenuBarItem" { return }
        // Skip non-clickable elements
        var actionsArray: CFArray?
        let isClickable = AXUIElementCopyActionNames(element, &actionsArray) == .success && 
            ((actionsArray as? [String])?.contains(kAXPressAction) == true || 
             (actionsArray as? [String])?.contains(kAXPickAction) == true || 
             role == "AXTextArea" || 
             role == "AXTextField" || 
             role == "AXButton")
        // Skip element outside of screen based on dimensions
        var isVisible = true
        var position: CFTypeRef?
        var size: CFTypeRef?
        if AXUIElementCopyAttributeValue(element, kAXPositionAttribute as CFString, &position) == .success,
           AXUIElementCopyAttributeValue(element, kAXSizeAttribute as CFString, &size) == .success {
            var point = CGPoint()
            var elementSize = CGSize()
            if AXValueGetValue(position as! AXValue, AXValueType.cgPoint, &point),
               AXValueGetValue(size as! AXValue, AXValueType.cgSize, &elementSize) {
                isVisible = !(point.x < appFrame.minX || point.y < appFrame.minY || point.x > appFrame.maxX || point.y > appFrame.maxY)
                if !isVisible { return }
            }
        }
        
        if isClickable && isVisible && currentDom.count < maxElements {
            currentDom[nextId] = element
            nextId += 1
        }
        
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
    // print("Got DOM with size \(currentDom.count) elems.")

    return currentDom
}

public func domToString(some_dom: [Int: AXUIElement]) -> String {
    var context = ""
    
    // Get active app info
    let frontAppInfo = getFrontApp()
    let pid = Int32(frontAppInfo[0]) ?? 0
    let appName = frontAppInfo[1]
    let bundleId = frontAppInfo[2]
    context += "### Active app: \(appName) (\(bundleId)) pid: \(pid)\n"
    
    // Only get DOM if not our own app
    if bundleId != "dev.ethan.flow" {
        context += "#### MacOS app elements:\n"
        
        for (id, element) in some_dom.sorted(by: { $0.key < $1.key }) {
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
            
            // Check if element is clickable. Set to true for now, since right now getCurrentDom() only returns clickable elements.
            let isClickable = true

            var elementInfo = ""
            if isClickable {
                elementInfo = "[\(id)]<\(role)>"
                if !title.isEmpty { elementInfo += title }
                if !description.isEmpty { elementInfo += description }
                if !value.isEmpty { elementInfo += value }
                if !placeholder.isEmpty { elementInfo += placeholder }
                elementInfo += "</\(role)>\n"
            }
            
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