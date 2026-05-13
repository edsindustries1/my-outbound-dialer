import Foundation
import UserNotifications
import AppKit

class NotificationManager: NSObject, UNUserNotificationCenterDelegate {

    private weak var delegate: AppDelegate?
    private var pollTimer: Timer?
    private var lastSeenTransferKey: String?
    private var lastNotificationTime: Date?

    init(delegate: AppDelegate) {
        self.delegate = delegate
        super.init()
        UNUserNotificationCenter.current().delegate = self
        registerNotificationCategories()
    }

    private func registerNotificationCategories() {
        let openAction = UNNotificationAction(
            identifier: "OPEN_LIVE",
            title: "View Live Calls",
            options: [.foreground]
        )
        let category = UNNotificationCategory(
            identifier: "LIVE_TRANSFER",
            actions: [openAction],
            intentIdentifiers: [],
            options: []
        )
        UNUserNotificationCenter.current().setNotificationCategories([category])
    }

    func startPolling() {
        pollTimer?.invalidate()
        pollTimer = Timer.scheduledTimer(withTimeInterval: 15, repeats: true) { [weak self] _ in
            self?.poll()
        }
        poll()
    }

    private func poll() {
        guard let url = URL(string: "https://app.openhumana.com/api/native/activity") else { return }
        var req = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 10)
        req.setValue("OpenHumana-macOS/1.0", forHTTPHeaderField: "User-Agent")

        // Use nativeSession — carries mirrored WKWebView session cookies.
        nativeSession.dataTask(with: req) { [weak self] data, _, _ in
            guard let self = self, let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }

            let transferCount = json["pending_transfer_count"] as? Int ?? 0
            guard transferCount > 0,
                  let lastTransfer = json["last_transfer"] as? [String: Any] else { return }

            let name = lastTransfer["contact_name"] as? String ?? "Someone"
            let number = lastTransfer["number"] as? String ?? ""
            // Deduplicate by contact number + name
            let key = "\(name)|\(number)"

            let cooldownExpired = self.lastNotificationTime.map {
                Date().timeIntervalSince($0) > 30
            } ?? true

            guard self.lastSeenTransferKey != key || cooldownExpired else { return }

            self.lastSeenTransferKey = key
            self.lastNotificationTime = Date()

            DispatchQueue.main.async {
                self.fireTransferNotification(contactName: name, count: transferCount)
            }
        }.resume()
    }

    private func fireTransferNotification(contactName: String, count: Int) {
        let content = UNMutableNotificationContent()
        content.title = "Live Transfer — Pick Up Now"
        content.body = count == 1
            ? "\(contactName) answered. Transfer your reps in."
            : "\(contactName) answered (+\(count - 1) more). Transfers waiting."
        content.sound = .default
        content.categoryIdentifier = "LIVE_TRANSFER"

        let request = UNNotificationRequest(
            identifier: UUID().uuidString,
            content: content,
            trigger: nil
        )
        UNUserNotificationCenter.current().add(request, withCompletionHandler: nil)
    }

    // MARK: - UNUserNotificationCenterDelegate

    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                 didReceive response: UNNotificationResponse,
                                 withCompletionHandler completionHandler: @escaping () -> Void) {
        switch response.actionIdentifier {
        case "OPEN_LIVE", UNNotificationDefaultActionIdentifier:
            delegate?.navigate(to: "/dashboard#live")
        default:
            break
        }
        completionHandler()
    }

    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                 willPresent notification: UNNotification,
                                 withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        if #available(macOS 12.0, *) {
            completionHandler([.banner, .sound, .badge])
        } else {
            completionHandler([.alert, .sound, .badge])
        }
    }
}
