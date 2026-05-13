import AppKit
import Foundation

class MenuBarManager {

    private weak var delegate: AppDelegate?
    private var statusItem: NSStatusItem?
    private var pollTimer: Timer?
    private var currentStatus: String = "idle"
    private var activeCallCount: Int = 0

    init(delegate: AppDelegate) {
        self.delegate = delegate
        setupStatusItem()
    }

    private func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        guard let button = statusItem?.button else { return }
        button.title = "⬤ OH"
        button.toolTip = "Open Humana"
        // Do NOT assign button.action when an NSMenu is attached — the menu consumes all clicks.
        updateButtonAppearance(status: "idle")
        buildMenu()
    }

    private func buildMenu() {
        let menu = NSMenu()

        let titleItem = NSMenuItem(title: "Open Humana", action: nil, keyEquivalent: "")
        titleItem.isEnabled = false
        menu.addItem(titleItem)

        let statusItem = NSMenuItem(title: "Status: Checking…", action: nil, keyEquivalent: "")
        statusItem.tag = 100
        statusItem.isEnabled = false
        menu.addItem(statusItem)

        let callsItem = NSMenuItem(title: "", action: nil, keyEquivalent: "")
        callsItem.tag = 101
        callsItem.isEnabled = false
        menu.addItem(callsItem)

        menu.addItem(.separator())

        let showItem = NSMenuItem(title: "Open Dashboard", action: #selector(showDashboard), keyEquivalent: "")
        showItem.target = self
        menu.addItem(showItem)

        let liveItem = NSMenuItem(title: "Live Calls", action: #selector(showLiveCalls), keyEquivalent: "")
        liveItem.target = self
        menu.addItem(liveItem)

        menu.addItem(.separator())

        let pauseItem = NSMenuItem(title: "Pause Campaign", action: #selector(toggleCampaign), keyEquivalent: "")
        pauseItem.tag = 200
        pauseItem.target = self
        pauseItem.isEnabled = false
        menu.addItem(pauseItem)

        menu.addItem(.separator())

        let quitItem = NSMenuItem(title: "Quit Open Humana", action: #selector(quitApp), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)

        self.statusItem?.menu = menu
    }

    func startPolling() {
        pollTimer?.invalidate()
        pollTimer = Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in
            self?.poll()
        }
        poll()
    }

    private func poll() {
        guard let url = URL(string: "https://app.openhumana.com/api/native/activity") else { return }
        var req = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 10)
        req.setValue("OpenHumana-macOS/1.0", forHTTPHeaderField: "User-Agent")

        // Use nativeSession — it carries the mirrored WKWebView session cookies.
        nativeSession.dataTask(with: req) { [weak self] data, response, _ in
            guard let self = self, let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }

            let status = json["campaign_status"] as? String ?? "idle"
            let calls = json["active_call_count"] as? Int ?? 0
            let transfers = json["pending_transfer_count"] as? Int ?? 0

            DispatchQueue.main.async {
                self.updateStatus(status: status, activeCalls: calls, transferCount: transfers)
            }
        }.resume()
    }

    private func updateStatus(status: String, activeCalls: Int, transferCount: Int) {
        currentStatus = status
        activeCallCount = activeCalls
        updateButtonAppearance(status: status)
        updateMenuItems(status: status, activeCalls: activeCalls)
        delegate?.updateDockBadge(transferCount)
    }

    private func updateButtonAppearance(status: String) {
        guard let button = statusItem?.button else { return }
        switch status {
        case "active":
            button.title = "⬤ OH"
            button.contentTintColor = NSColor.systemGreen
            button.toolTip = "Open Humana — Campaign Active"
        case "paused":
            button.title = "⬤ OH"
            button.contentTintColor = NSColor.systemYellow
            button.toolTip = "Open Humana — Campaign Paused"
        default:
            button.title = "⬤ OH"
            button.contentTintColor = NSColor.secondaryLabelColor
            button.toolTip = "Open Humana — Idle"
        }
    }

    private func updateMenuItems(status: String, activeCalls: Int) {
        guard let menu = statusItem?.menu else { return }

        if let statusMenuItem = menu.item(withTag: 100) {
            switch status {
            case "active": statusMenuItem.title = "🟢  Campaign: Active"
            case "paused": statusMenuItem.title = "🟡  Campaign: Paused"
            default:       statusMenuItem.title = "⚪  Campaign: Idle"
            }
        }

        if let callsMenuItem = menu.item(withTag: 101) {
            callsMenuItem.title = activeCalls > 0
                ? "   \(activeCalls) call\(activeCalls == 1 ? "" : "s") in progress"
                : "   No active calls"
        }

        if let pauseItem = menu.item(withTag: 200) {
            pauseItem.title = (status == "active") ? "Pause Campaign" : "Resume Campaign"
            pauseItem.isEnabled = (status == "active" || status == "paused")
        }
    }

    @objc private func showDashboard() {
        delegate?.navigate(to: "/dashboard")
    }

    @objc private func showLiveCalls() {
        delegate?.navigate(to: "/dashboard#live")
    }

    @objc private func toggleCampaign() {
        let endpoint = (currentStatus == "active") ? "/pause" : "/resume"
        guard let url = URL(string: "https://app.openhumana.com\(endpoint)") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("OpenHumana-macOS/1.0", forHTTPHeaderField: "User-Agent")
        // Use authenticated nativeSession for control actions too.
        nativeSession.dataTask(with: req) { [weak self] _, _, _ in
            DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
                self?.poll()
            }
        }.resume()
    }

    @objc private func quitApp() {
        NSApplication.shared.terminate(nil)
    }
}
