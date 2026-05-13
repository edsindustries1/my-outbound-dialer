import Foundation
import UserNotifications
import AppKit

class NotificationManager: NSObject, UNUserNotificationCenterDelegate {

    private weak var delegate: AppDelegate?
    private var pollTimer: Timer?
    private var lastSeenTransferNumber: String?
    private var lastNotificationTime: Date?

    init(delegate: AppDelegate) {
        self.delegate = delegate
        super.init()
        UNUserNotificationCenter.current().delegate = self
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

        URLSession.shared.dataTask(with: req) { [weak self] data, _, _ in
            guard let self = self, let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }

            let transferCount = json["pending_transfer_count"] as? Int ?? 0
            if let lastTransfer = json["last_transfer"] as? [String: Any] {
                let number = lastTransfer["contact_name"] as? String ?? ""
                let name = lastTransfer["contact_name"] as? String ?? "Someone"

                let shouldNotify = self.lastSeenTransferNumber != number
                    && (self.lastNotificationTime == nil ||
                        Date().timeIntervalSince(self.lastNotificationTime!) > 30)

                if transferCount > 0 && shouldNotify {
                    self.lastSeenTransferNumber = number
                    self.lastNotificationTime = Date()
                    DispatchQueue.main.async {
                        self.fireTransferNotification(contactName: name, count: transferCount)
                    }
                }
            }
        }.resume()
    }

    private func fireTransferNotification(contactName: String, count: Int) {
        let content = UNMutableNotificationContent()
        content.title = "Live Transfer — Pick Up Now"
        if count == 1 {
            content.body = "\(contactName) answered. Transfer your reps in."
        } else {
            content.body = "\(contactName) answered (+\(count - 1) more). Transfer waiting."
        }
        content.sound = .default
        content.categoryIdentifier = "LIVE_TRANSFER"

        let openAction = UNNotificationAction(identifier: "OPEN_LIVE", title: "View Live Calls",
                                              options: [.foreground])
        let category = UNNotificationCategory(identifier: "LIVE_TRANSFER",
                                              actions: [openAction],
                                              intentIdentifiers: [],
                                              options: [])
        UNUserNotificationCenter.current().setNotificationCategories([category])

        let request = UNNotificationRequest(identifier: UUID().uuidString,
                                            content: content,
                                            trigger: nil)
        UNUserNotificationCenter.current().add(request, withCompletionHandler: nil)
    }

    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                 didReceive response: UNNotificationResponse,
                                 withCompletionHandler completionHandler: @escaping () -> Void) {
        if response.actionIdentifier == "OPEN_LIVE" ||
           response.actionIdentifier == UNNotificationDefaultActionIdentifier {
            delegate?.navigate(to: "/dashboard#live")
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
