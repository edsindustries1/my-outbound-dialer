import AppKit
import UserNotifications

class AppDelegate: NSObject, NSApplicationDelegate {

    var menuBarManager: MenuBarManager?
    var notificationManager: NotificationManager?
    weak var webViewWrapper: WebViewWrapper?

    func applicationDidFinishLaunching(_ notification: Notification) {
        menuBarManager = MenuBarManager(delegate: self)
        notificationManager = NotificationManager(delegate: self)

        // Seed URLSession cookie storage from any WKWebView cookies persisted on disk,
        // then start polling (so the first poll is authenticated if already logged in).
        WebViewWrapper.shared.syncCookiesToSharedStorage {
            DispatchQueue.main.async {
                self.menuBarManager?.startPolling()
            }
        }

        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, _ in
            if granted {
                DispatchQueue.main.async {
                    self.notificationManager?.startPolling()
                }
            }
        }

        if let window = NSApplication.shared.windows.first {
            window.title = "Open Humana"
            window.setFrameAutosaveName("MainWindow")
            window.center()
        }
    }

    func applicationDidBecomeActive(_ notification: Notification) {
        // Clear dock badge whenever user switches to the app.
        updateDockBadge(0)
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
        NSApplication.shared.activate(ignoringOtherApps: true)
        NSApplication.shared.windows.first?.makeKeyAndOrderFront(nil)
        webViewWrapper?.navigate(to: path)
    }

    func showMainWindow() {
        NSApplication.shared.activate(ignoringOtherApps: true)
        NSApplication.shared.windows.first?.makeKeyAndOrderFront(nil)
    }

    func updateDockBadge(_ count: Int) {
        DispatchQueue.main.async {
            NSApp.dockTile.badgeLabel = count > 0 ? "\(count)" : nil
        }
    }
}
