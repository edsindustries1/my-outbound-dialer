import WebKit
import AppKit
import UniformTypeIdentifiers

/// Shared URLSession that mirrors cookies from the WKWebView cookie store.
/// MenuBarManager and NotificationManager must use this session for authenticated requests.
let nativeSession: URLSession = {
    let config = URLSessionConfiguration.default
    config.httpCookieStorage = HTTPCookieStorage.shared
    config.httpCookieAcceptPolicy = .always
    config.httpShouldSetCookies = true
    return URLSession(configuration: config)
}()

class WebViewWrapper: NSObject, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler, WKHTTPCookieStoreObserver {

    static let shared = WebViewWrapper()

    let webView: WKWebView
    private let baseURL = "https://app.openhumana.com"

    override init() {
        let config = WKWebViewConfiguration()

        let prefs = WKWebpagePreferences()
        prefs.allowsContentJavaScript = true
        config.defaultWebpagePreferences = prefs

        config.websiteDataStore = .default()

        config.applicationNameForUserAgent = "OpenHumana-macOS/1.0"

        let contentController = WKUserContentController()

        let filePickerScript = WKUserScript(
            source: """
            (function() {
                document.addEventListener('click', function(e) {
                    var el = e.target;
                    while (el) {
                        if (el.tagName === 'INPUT' && el.type === 'file' &&
                            (el.accept === '.csv' || el.accept === 'text/csv' || el.accept === '')) {
                            e.preventDefault();
                            e.stopPropagation();
                            window.webkit.messageHandlers.filePicker.postMessage({
                                inputId: el.id || '',
                                inputName: el.name || ''
                            });
                            return false;
                        }
                        el = el.parentElement;
                    }
                }, true);
            })();
            """,
            injectionTime: .atDocumentEnd,
            forMainFrameOnly: false
        )
        contentController.addUserScript(filePickerScript)
        config.userContentController = contentController

        webView = WKWebView(frame: .zero, configuration: config)
        webView.allowsMagnification = true
        webView.allowsBackForwardNavigationGestures = true

        super.init()

        webView.navigationDelegate = self
        webView.uiDelegate = self
        contentController.add(self, name: "filePicker")

        // Observe WKWebView cookie changes and mirror them into HTTPCookieStorage.shared
        // so that nativeSession (used by MenuBarManager / NotificationManager) stays authenticated.
        config.websiteDataStore.httpCookieStore.add(self)

        load(path: "/login")
    }

    // MARK: - Cookie synchronization

    func cookiesDidChange(in cookieStore: WKHTTPCookieStore) {
        cookieStore.getAllCookies { cookies in
            for cookie in cookies {
                HTTPCookieStorage.shared.setCookie(cookie)
            }
        }
    }

    /// Call once on startup to seed HTTPCookieStorage.shared from any persisted WKWebView cookies.
    func syncCookiesToSharedStorage(completion: (() -> Void)? = nil) {
        webView.configuration.websiteDataStore.httpCookieStore.getAllCookies { cookies in
            for cookie in cookies {
                HTTPCookieStorage.shared.setCookie(cookie)
            }
            completion?()
        }
    }

    // MARK: - Navigation helpers

    func load(path: String) {
        guard let url = URL(string: baseURL + path) else { return }
        let req = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData)
        webView.load(req)
    }

    func reload() {
        webView.reload()
    }

    func navigate(to path: String) {
        guard let url = URL(string: baseURL + path) else { return }
        let currentHost = webView.url?.host ?? ""
        if currentHost.contains("openhumana.com") {
            webView.load(URLRequest(url: url))
        } else {
            load(path: path)
        }
    }

    // MARK: - Native file picker (WKScriptMessageHandler)

    func userContentController(_ userContentController: WKUserContentController,
                                didReceive message: WKScriptMessage) {
        guard message.name == "filePicker" else { return }

        let info = message.body as? [String: String] ?? [:]
        let inputId = info["inputId"] ?? ""

        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            let panel = NSOpenPanel()
            panel.allowsMultipleSelection = false
            panel.canChooseDirectories = false
            panel.canChooseFiles = true
            panel.title = "Select Contacts CSV"
            panel.message = "Choose a CSV file with your contacts list"
            panel.prompt = "Select"

            if #available(macOS 11.0, *) {
                panel.allowedContentTypes = [UTType.commaSeparatedText, UTType.plainText]
            } else {
                panel.allowedFileTypes = ["csv", "txt"]
            }

            guard let window = NSApplication.shared.keyWindow else { return }
            panel.beginSheetModal(for: window) { [weak self] response in
                guard response == .OK, let fileURL = panel.url else { return }
                self?.injectFileIntoInput(fileURL: fileURL, inputId: inputId)
            }
        }
    }

    private func injectFileIntoInput(fileURL: URL, inputId: String) {
        guard let data = try? Data(contentsOf: fileURL) else { return }
        let base64 = data.base64EncodedString()
        let fileName = fileURL.lastPathComponent
        let mimeType = "text/csv"

        let js = """
        (function() {
            var b64 = '\(base64)';
            var byteChars = atob(b64);
            var bytes = new Uint8Array(byteChars.length);
            for (var i = 0; i < byteChars.length; i++) {
                bytes[i] = byteChars.charCodeAt(i);
            }
            var blob = new Blob([bytes], {type: '\(mimeType)'});
            var file = new File([blob], '\(fileName)', {type: '\(mimeType)'});
            var dt = new DataTransfer();
            dt.items.add(file);
            var selector = '\(inputId.isEmpty ? "input[type=file]" : "#\(inputId)")';
            var input = document.querySelector(selector);
            if (input) {
                Object.defineProperty(input, 'files', {
                    value: dt.files,
                    writable: false,
                });
                input.dispatchEvent(new Event('change', {bubbles: true}));
                input.dispatchEvent(new Event('input', {bubbles: true}));
            }
        })();
        """
        webView.evaluateJavaScript(js, completionHandler: nil)
    }

    // MARK: - WKNavigationDelegate

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else {
            decisionHandler(.allow)
            return
        }

        let host = url.host ?? ""

        if host.hasSuffix("openhumana.com") || host.isEmpty {
            decisionHandler(.allow)
            return
        }

        if navigationAction.navigationType == .linkActivated {
            NSWorkspace.shared.open(url)
            decisionHandler(.cancel)
            return
        }

        decisionHandler(.allow)
    }

    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url = navigationAction.request.url {
            let host = url.host ?? ""
            if host.hasSuffix("openhumana.com") {
                webView.load(navigationAction.request)
            } else {
                NSWorkspace.shared.open(url)
            }
        }
        return nil
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        webView.evaluateJavaScript(
            "document.body.dataset.nativeApp = 'macos';",
            completionHandler: nil
        )
        // Re-sync cookies on every page load (catches login, logout, session refresh)
        syncCookiesToSharedStorage()
    }

    // MARK: - WKUIDelegate

    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        let alert = NSAlert()
        alert.messageText = "Open Humana"
        alert.informativeText = message
        alert.alertStyle = .informational
        alert.addButton(withTitle: "OK")
        alert.runModal()
        completionHandler()
    }

    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let alert = NSAlert()
        alert.messageText = "Open Humana"
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.addButton(withTitle: "OK")
        alert.addButton(withTitle: "Cancel")
        completionHandler(alert.runModal() == .alertFirstButtonReturn)
    }
}
