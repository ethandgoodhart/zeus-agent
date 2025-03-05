import Foundation
import AppKit
import CoreGraphics

// Global variables for state management
private var dom: [Int: DOMElement] = [:]

private func openApplication(bundleId: String) throws {
    guard let appURL = workspace.urlForApplication(withBundleIdentifier: bundleId) else {
        throw NSError(domain: "Executor", code: 2, userInfo: [NSLocalizedDescriptionKey: "Application not found: \(bundleId)"])
    }
    
    // Check if the app is already running
    let isAppAlreadyRunning = workspace.runningApplications.contains { app in
        app.bundleIdentifier == bundleId
    }
    
    workspace.openApplication(at: appURL, configuration: NSWorkspace.OpenConfiguration())
    print("✅ opened application: \(bundleId)")
    
    // Wait for 0.5s if app was already running, 3s if newly opened
    let waitTime = isAppAlreadyRunning ? 0.5 : 3.0
    print("waiting for \(waitTime)s")
    Thread.sleep(forTimeInterval: waitTime)
}

let appFrame = NSScreen.main?.frame ?? CGRect.zero
private func clickElement(clickableId: Int) throws {
    // Find the element with the matching clickableId
    guard let element = dom.values.first(where: { $0.clickableId == clickableId }) else {
        throw NSError(domain: "Executor", code: 3, userInfo: [NSLocalizedDescriptionKey: "Clickable element not found: \(clickableId)"])
    }

    // Get element info for success message
    let elementInfo = getElementInfo(element: element)

    // Get the frame of the element
    var position: AnyObject?
    var size: AnyObject?    
    if AXUIElementCopyAttributeValue(element.uielem, kAXPositionAttribute as CFString, &position) == .success,
       AXUIElementCopyAttributeValue(element.uielem, kAXSizeAttribute as CFString, &size) == .success {
        var point = CGPoint()
        var elementSize = CGSize()
        if AXValueGetValue(position as! AXValue, AXValueType.cgPoint, &point),
           AXValueGetValue(size as! AXValue, AXValueType.cgSize, &elementSize) {
            let centerX = point.x + elementSize.width / 2
            let centerY = point.y + elementSize.height / 2
            
            // Check if the element is off-screen
            if centerX < appFrame.minX || centerY < appFrame.minY || 
               centerX > appFrame.maxX || centerY > appFrame.maxY {
                // Element is off-screen, use AXPress action instead
                AXUIElementPerformAction(element.uielem, kAXPressAction as CFString)
                print("✅ clicked on clickableId=\(clickableId) using (AXPress) with info \(elementInfo)")
            } else {
                // Element is on-screen, use mouse events
                let mouseDown = CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, mouseCursorPosition: CGPoint(x: centerX, y: centerY), mouseButton: .left)
                let mouseUp = CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp, mouseCursorPosition: CGPoint(x: centerX, y: centerY), mouseButton: .left)
                mouseDown?.post(tap: .cghidEventTap)
                mouseUp?.post(tap: .cghidEventTap)
                print("✅ clicked on clickableId=\(clickableId) using (coords) with info \(elementInfo)")
            }
        } else {
            throw NSError(domain: "Executor", code: 4, userInfo: [NSLocalizedDescriptionKey: "Failed to get position and size for element with info= \(elementInfo)"])
        }
    } else {
        throw NSError(domain: "Executor", code: 4, userInfo: [NSLocalizedDescriptionKey: "Failed to get position and size for element with info= \(elementInfo)"])
    }
    Thread.sleep(forTimeInterval: 0.3)
}

// MARK: - C Interface
@_cdecl("get_dom_str") // refreshes DOM, returns it as a String
public func get_dom_str() -> UnsafeMutablePointer<CChar> {
    dom = getCurrentDom()
    let domString = domToString(some_dom: dom)
    let cString = strdup(domString)
    return cString!
}
// executor actions
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
        try clickElement(clickableId: Int(elementId))
        return true
    } catch {
        print("❌ Error: \(error.localizedDescription)")
        return false
    }
}