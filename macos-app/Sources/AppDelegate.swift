import AppKit
import UserNotifications

class AppDelegate: NSObject, NSApplicationDelegate {

    var menuBarManager: MenuBarManager?
    var notificationManager: NotificationManager?
    weak var webViewWrapper: WebViewWrapper?

    func applicationDidFinishLaunching(_ notification: Notification) {
        menuBarManager = MenuBarManager(delegate: self)
        notificationManager = NotificationManager(delegate: self)

        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, _ in
            if granted {
                DispatchQueue.main.async {
                    self.notificationManager?.startPolling()
                }
            }
        }

        menuBarManager?.startPolling()

        if let window = NSApplication.shared.windows.first {
            window.title = "Open Humana"
            window.setFrameAutosaveName("MainWindow")
            window.center()
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return false
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag {
            NSApplication.shared.windows.first?.makeKeyAndOrderFront(nil)
        }
        return true
    }

    func reloadWebView() {
        webViewWrapper?.reload()
    }

    func navigate(to path: String) {
        NSApplication.shared.windows.first?.makeKeyAndOrderFront(nil)
        webViewWrapper?.navigate(to: path)
    }

    func showMainWindow() {
        NSApplication.shared.activate(ignoringOtherApps: true)
        NSApplication.shared.windows.first?.makeKeyAndOrderFront(nil)
    }

    func updateDockBadge(_ count: Int) {
        DispatchQueue.main.async {
            if count > 0 {
                NSApp.dockTile.badgeLabel = "\(count)"
            } else {
                NSApp.dockTile.badgeLabel = nil
            }
        }
    }
}
