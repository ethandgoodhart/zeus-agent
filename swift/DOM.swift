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

public struct DOMElement {
    let id: Int
    let isClickable: Bool
    let clickableId: Int?
    let parent: AXUIElement?
    let uielem: AXUIElement
    let role: String
    var children: [Int]
    var depth: Int
}

public func getCurrentDom() -> [Int: DOMElement] {
    var currentDom: [Int: DOMElement] = [:]
    let maxElements = 500
    let maxChildren = 100
    
    let frontAppInfo = getFrontApp()
    let pid = Int32(frontAppInfo[0]) ?? 0
    let appRef = AXUIElementCreateApplication(pid)
    print("getCurrentDom() -> \(frontAppInfo[1]) (\(frontAppInfo[2]))")

    let appFrame = NSScreen.main?.frame ?? CGRect.zero
    
    func addElementToDOM(_ element: AXUIElement, depth: Int = 0, nextId: inout Int, nextClickableId: inout Int, parentId: Int? = nil) -> Int? {
        if currentDom.count >= maxElements { return nil }
        
        // Get role
        var roleValue: AnyObject?
        AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &roleValue)
        let role = roleValue as? String ?? ""
        
        // Skip menu items
        if role == "AXMenuItem" || role == "AXMenuBarItem" { return nil }
        
        // Check visibility
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
                if !isVisible { return nil }
            }
        }
        
        // Check if clickable
        var actionsArray: CFArray?
        let isClickable = AXUIElementCopyActionNames(element, &actionsArray) == .success && 
            ((actionsArray as? [String])?.contains(kAXPressAction) == true || 
             (actionsArray as? [String])?.contains(kAXPickAction) == true || 
             role == "AXTextArea" || 
             role == "AXTextField" || 
             role == "AXButton")
        
        // Get parent element
        var parentElement: AXUIElement? = nil
        var parentRef: CFTypeRef?
        if AXUIElementCopyAttributeValue(element, kAXParentAttribute as CFString, &parentRef) == .success {
            parentElement = (parentRef as! AXUIElement)
        }
        
        let currentId = nextId
        nextId += 1
        
        // Assign clickable ID if the element is clickable
        let clickableId = isClickable ? nextClickableId : nil
        if isClickable {
            nextClickableId += 1
        }
        
        currentDom[currentId] = DOMElement(
            id: currentId,
            isClickable: isClickable,
            clickableId: clickableId,
            parent: parentElement,
            uielem: element,
            role: role,
            children: [],
            depth: depth
        )
        
        // Process children
        var children: AnyObject?
        let result = AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &children)
        
        if result == .success, let childElements = children as? [AXUIElement] {
            let childrenToProcess = childElements.prefix(maxChildren)
            for child in childrenToProcess {
                if currentDom.count >= maxElements { break }
                if let childId = addElementToDOM(child, depth: depth + 1, nextId: &nextId, nextClickableId: &nextClickableId, parentId: currentId) {
                    currentDom[currentId]?.children.append(childId)
                }
            }
        }
        
        return currentId
    }
    
    var nextId = 1
    var nextClickableId = 1
    _ = addElementToDOM(appRef, nextId: &nextId, nextClickableId: &nextClickableId)
    return currentDom
}
public func getElementInfo(element: DOMElement) -> String {
    var elementInfo = ""
    
    // Only process clickable elements
    if element.isClickable, let clickableId = element.clickableId {
        // Get the normalized element role
        let role = element.role //.replacingOccurrences(of: "AX", with: "")
        elementInfo = "[\(clickableId)]<\(role)>"
        
        // Add attributes
        var titleValue: AnyObject?
        AXUIElementCopyAttributeValue(element.uielem, kAXTitleAttribute as CFString, &titleValue)
        let title = titleValue as? String ?? ""
        if !title.isEmpty {
            elementInfo += title
        }
        
        var descValue: AnyObject?
        AXUIElementCopyAttributeValue(element.uielem, kAXDescriptionAttribute as CFString, &descValue)
        let description = descValue as? String ?? ""
        if !description.isEmpty {
            elementInfo += description
        }
        
        var valueAttr: AnyObject?
        AXUIElementCopyAttributeValue(element.uielem, kAXValueAttribute as CFString, &valueAttr)
        let value = valueAttr as? String ?? ""
        if !value.isEmpty {
            elementInfo += value
        }
        
        var placeholderValue: AnyObject?
        AXUIElementCopyAttributeValue(element.uielem, kAXPlaceholderValueAttribute as CFString, &placeholderValue)
        let placeholder = placeholderValue as? String ?? ""
        if !placeholder.isEmpty {
            elementInfo += placeholder
        }
        
        // Get text content
        var textValue: AnyObject?
        AXUIElementCopyAttributeValue(element.uielem, kAXTextAttribute as CFString, &textValue)
        let text = textValue as? String ?? ""
        if !text.isEmpty {
            elementInfo += text
        }

        // var domClassListRef: CFTypeRef?
        // AXUIElementCopyAttributeValue(element.uielem, "AXDOMClassList" as CFString, &domClassListRef)
        // let classList = domClassListRef as? [String] ?? []
        // if !classList.isEmpty {
        //     emmetNotation += "." + classList.joined(separator: ".")
        // }

        // Check if this is an empty AXGroup element
        if role == "AXGroup" && title.isEmpty && description.isEmpty && value.isEmpty && placeholder.isEmpty && text.isEmpty {
            return ""
        }

        elementInfo += "</\(role)>"
    }

    return elementInfo
}

public func domToString(some_dom: [Int: DOMElement]) -> String {
    var context = ""
    
    // Get active app info
    let frontAppInfo = getFrontApp()
    let appName = frontAppInfo[1]
    let bundleId = frontAppInfo[2]
    context += "### Active app: \(appName) (\(bundleId))\n"
    
    context += "#### MacOS app elements:\n"
    
    // Only collect clickable elements
    let clickableElements = some_dom.values.filter { $0.isClickable }.sorted { $0.clickableId ?? 0 < $1.clickableId ?? 0 }
    
    for element in clickableElements {
        let info = getElementInfo(element: element)
        if !info.isEmpty {
            context += info + "\n"
        }
    }
    
    context += "\n\n### Active app bundleids:\n"
    var uniqueBundleIds = Set<String>()    
    for app in workspace.runningApplications {
        if let bundleId = app.bundleIdentifier, !uniqueBundleIds.contains(bundleId) {
            uniqueBundleIds.insert(bundleId)
            context += "\(app.localizedName ?? ""), \(bundleId)\n"
        }
    }

    return context
}