import Foundation
import AppKit
import CoreGraphics

// Global variables for state management
private let workspace = NSWorkspace.shared
private var currentApplicationBundleId: String?
private var dom: [Int: AXUIElement] = [:]

private func openApplication(bundleId: String) throws {
    guard let appURL = NSWorkspace.shared.urlForApplication(withBundleIdentifier: bundleId) else {
        throw NSError(domain: "Executor", code: 2, userInfo: [NSLocalizedDescriptionKey: "Application not found: \(bundleId)"])
    }
    
    NSWorkspace.shared.openApplication(at: appURL, configuration: NSWorkspace.OpenConfiguration())
    currentApplicationBundleId = bundleId
    print("✅ opened application: \(bundleId)")
    Thread.sleep(forTimeInterval: 0.5)
}

private func clickElement(id: Int) throws {
    guard let element = dom[id] else {
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

    Thread.sleep(forTimeInterval: 0.5)
}

// MARK: - C Interface
@_cdecl("get_dom_str") // refreshes DOM, returns it as a String
public func get_dom_str() -> UnsafeMutablePointer<CChar> {
    if currentApplicationBundleId == nil { currentApplicationBundleId = workspace.frontmostApplication?.bundleIdentifier }
    dom = getCurrentDom()
    print("✅ DOM refreshed successfully")
    let domString = getCurrentAppContext()
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
        try clickElement(id: Int(elementId))
        return true
    } catch {
        print("❌ Error: \(error.localizedDescription)")
        return false
    }
}