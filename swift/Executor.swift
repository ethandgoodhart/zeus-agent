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
    
    dom = getCurrentDom()
}

private func clickElement(clickableId: Int) throws {
    // Find the element with the matching clickableId
    guard let element = dom.values.first(where: { $0.clickableId == clickableId }) else {
        throw NSError(domain: "Executor", code: 3, userInfo: [NSLocalizedDescriptionKey: "Clickable element not found: \(clickableId)"])
    }

    let error = AXUIElementPerformAction(element.uielem, kAXPressAction as CFString)
    if error != .success {
        throw NSError(domain: "Executor", code: 4, userInfo: [NSLocalizedDescriptionKey: "Failed to click element with clickableId: \(clickableId), info: \(getElementInfo(element: element))"])
    }
    
    // Get element info for success message
    let elementInfo = getElementInfo(element: element)
    print("✅ clicked on clickableId=\(clickableId) with info \(elementInfo)")

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