import SwiftUI
import WebKit

struct ContentView: View {
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        WebViewRepresentable()
            .ignoresSafeArea()
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Color(NSColor.windowBackgroundColor))
    }
}

struct WebViewRepresentable: NSViewRepresentable {
    func makeNSView(context: Context) -> WKWebView {
        let wrapper = WebViewWrapper.shared
        if let appDelegate = NSApplication.shared.delegate as? AppDelegate {
            appDelegate.webViewWrapper = wrapper
        }
        return wrapper.webView
    }

    func updateNSView(_ nsView: WKWebView, context: Context) {}
}
