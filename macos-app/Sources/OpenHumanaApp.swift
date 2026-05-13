import SwiftUI

@main
struct OpenHumanaApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        WindowGroup {
            ContentView()
                .frame(minWidth: 1024, minHeight: 768)
                .onAppear {
                    NSWindow.allowsAutomaticWindowTabbing = false
                }
        }
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified)
        .commands {
            CommandGroup(replacing: .newItem) {}
            CommandMenu("Navigate") {
                Button("Dashboard") {
                    appDelegate.navigate(to: "/dashboard")
                }
                .keyboardShortcut("1", modifiers: .command)

                Button("Campaigns") {
                    appDelegate.navigate(to: "/dashboard#campaigns")
                }
                .keyboardShortcut("2", modifiers: .command)

                Button("Live Calls") {
                    appDelegate.navigate(to: "/dashboard#live")
                }
                .keyboardShortcut("3", modifiers: .command)

                Button("Reports") {
                    appDelegate.navigate(to: "/dashboard#reports")
                }
                .keyboardShortcut("4", modifiers: .command)
            }
            CommandGroup(after: .appInfo) {
                Button("Reload") {
                    appDelegate.reloadWebView()
                }
                .keyboardShortcut("r", modifiers: .command)
            }
        }
    }
}
