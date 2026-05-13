# Open Humana — Mac App Store Setup Guide

Complete step-by-step instructions for building and submitting the macOS app to the Mac App Store.

---

## Prerequisites

- macOS 13.0 Ventura or later (for development machine)
- Xcode 15 or later (free from Mac App Store)
- Apple Developer Program account (you already have this)
- The source files in this `macos-app/` folder

---

## Phase 1 — Apple Developer Portal Setup (do this first, ~30 minutes)

### 1.1 Create the Bundle ID

1. Go to [developer.apple.com](https://developer.apple.com) → Certificates, IDs & Profiles → Identifiers
2. Click **+** → **App IDs** → **App**
3. Fill in:
   - **Description:** Open Humana Desktop
   - **Bundle ID:** `com.openhumana.desktop` (Explicit)
4. Enable capabilities: **Push Notifications**, **App Sandbox**
5. Click **Continue** → **Register**

### 1.2 Create Distribution Certificates

You need two certificates for Mac App Store:

**Mac App Distribution certificate:**
1. Certificates → **+** → **Mac App Distribution**
2. Follow the CSR instructions (Keychain Access → Certificate Assistant → Request a Certificate)
3. Download and double-click to install in Keychain

**Mac Installer Distribution certificate:**
1. Certificates → **+** → **Mac Installer Distribution**
2. Same CSR process
3. Download and install in Keychain

### 1.3 Create Provisioning Profile

1. Profiles → **+** → **Mac App Store** → **Mac App Store**
2. Select Bundle ID: `com.openhumana.desktop`
3. Select the Mac App Distribution certificate
4. Name it: `Open Humana Mac App Store`
5. Download and double-click to install

---

## Phase 2 — Create the Xcode Project (30 minutes)

### 2.1 Create the Project

1. Open Xcode → **File → New → Project**
2. Choose **macOS → App**
3. Fill in:
   - **Product Name:** Open Humana
   - **Team:** Select your Apple Developer team
   - **Organization Identifier:** `com.openhumana`
   - **Bundle Identifier:** `com.openhumana.desktop` (auto-filled)
   - **Interface:** SwiftUI
   - **Language:** Swift
4. **Uncheck** "Include Tests"
5. Save to a folder of your choice

### 2.2 Add Source Files

Delete the auto-generated `ContentView.swift` (move to Trash).
Drag all `.swift` files from `macos-app/Sources/` into the Xcode project:
- `OpenHumanaApp.swift`
- `AppDelegate.swift`
- `ContentView.swift`
- `WebViewWrapper.swift`
- `MenuBarManager.swift`
- `NotificationManager.swift`

When prompted: check **"Copy items if needed"**, target **Open Humana**.

### 2.3 Replace Info.plist

1. In Xcode's project navigator, right-click the existing `Info.plist` → **Show in Finder**
2. Replace its contents with the contents of `macos-app/Info.plist`

### 2.4 Set Entitlements

1. Click the project in the navigator → Select the **Open Humana** target
2. Click the **Signing & Capabilities** tab
3. Click **+ Capability** → add **App Sandbox**
4. Under App Sandbox, enable:
   - ✅ **Network → Outgoing Connections (Client)**
   - ✅ **File Access → User Selected File → Read Only**
5. Click **+ Capability** → add **Push Notifications**

Xcode generates an `.entitlements` file. Replace its contents with the contents of `macos-app/OpenHumana.entitlements`.

### 2.5 Add App Icon

1. In the project navigator, click **Assets.xcassets** → **AppIcon**
2. You need 10 PNG files in the sizes listed in `Assets.xcassets/AppIcon.appiconset/Contents.json`

**Easiest way to generate them:**
- Go to [appicon.co](https://www.appicon.co)
- Upload your Open Humana logo (square, 1024×1024 recommended)
- Select **macOS**
- Download and drag the resulting files into the AppIcon set in Xcode

### 2.6 Configure Signing

1. **Signing & Capabilities** tab
2. Uncheck **Automatically manage signing**
3. Set **Provisioning Profile** to the one you downloaded: `Open Humana Mac App Store`
4. Set **Signing Certificate** to **Mac App Distribution**

---

## Phase 3 — Build Settings

1. Project → Target **Open Humana** → **Build Settings**
2. Search for **"Deployment Target"** → Set **macOS Deployment Target** to `13.0`
3. Search for **"User Script Sandboxing"** → Set to `NO` (required for WKWebView JavaScript injection)
4. Search for **"Enable Hardened Runtime"** → Set to `YES`
5. In **Product → Scheme → Edit Scheme → Run**, set **Build Configuration** to `Release` for final archive

---

## Phase 4 — Test the App

1. Select **My Mac** as the run destination (top of Xcode)
2. Press **⌘R** to build and run
3. Verify:
   - App opens and loads `app.openhumana.com/login`
   - Login works and session persists after quitting/reopening
   - Menu bar icon appears with correct status color
   - Clicking the menu bar icon opens the dashboard
   - CSV file picker opens native dialog when uploading contacts
   - Desktop notification fires when a live transfer is active
   - External links (e.g., links to `openhumana.com`) open in Safari
   - Cmd+1/2/3/4 navigate to correct sections

---

## Phase 5 — App Store Connect Setup

### 5.1 Create the App Record

1. Go to [appstoreconnect.apple.com](https://appstoreconnect.apple.com)
2. **My Apps** → **+** → **New App**
3. Fill in:
   - **Platforms:** macOS
   - **Name:** Open Humana
   - **Primary Language:** English (U.S.)
   - **Bundle ID:** `com.openhumana.desktop`
   - **SKU:** `openhumana-desktop-v1`
4. Click **Create**

### 5.2 Fill in the Listing

Paste the content from `macos-app/AppStore_Listing.md` into the corresponding fields.

### 5.3 Screenshots

Required sizes:
- **MacBook (1280×800):** minimum 3, maximum 10
- **5K iMac (2560×1600):** minimum 3, maximum 10 (optional but recommended)

**How to take screenshots:**
1. In Xcode, select **iPhone 15 Pro Max** simulator and change to **My Mac** → set window size to 1280×800
2. Run the app → use **File → Take Screenshot** (Cmd+Shift+4 in the simulator window)
3. Show: dashboard with active campaign, live calls panel, campaign wizard step 2, reports/analytics

### 5.4 Pricing

Set to **Free** (revenue comes from the web subscription, not the app store).

---

## Phase 6 — Archive and Submit

### 6.1 Archive

1. In Xcode, make sure destination is **Any Mac**
2. **Product → Archive** (takes 1–2 minutes)
3. **Window → Organizer** opens automatically

### 6.2 Validate

1. In Organizer, select your archive → **Validate App**
2. Select **App Store Connect** → **Next**
3. Choose your distribution certificate and provisioning profile
4. Fix any validation errors before proceeding (common: missing icon sizes, entitlement mismatches)

### 6.3 Upload

1. **Distribute App** → **App Store Connect** → **Upload**
2. Wait for processing (10–30 minutes) — you'll get an email from Apple

### 6.4 Submit for Review

1. In App Store Connect, go to your app → **macOS App** tab
2. Under **Build**, click **+** and select your uploaded build
3. Fill in **"What's New in This Version":** `Initial release — AI Sales Dialer for Mac.`
4. Set **App Review Information:**
   - **Notes:** "This app loads our dashboard at app.openhumana.com and adds native macOS features: desktop notifications for live call transfers, a menu bar status indicator, and a native macOS CSV file picker for campaign contact uploads. A demo account is available — email: demo@openhumana.com / password: Demo1234 (create before submission)."
   - Create the demo account first so reviewers can log in.
5. Click **Submit for Review**

Apple typically reviews in **1–3 business days**.

---

## Phase 7 — After Approval

1. In App Store Connect, set release to **"Release This Version"**
2. Add **"Download on the Mac App Store"** badge to `openhumana.com` — download official badge assets from [developer.apple.com/app-store/marketing/guidelines](https://developer.apple.com/app-store/marketing/guidelines/)
3. Update `templates/landing.html` with the Mac App Store link badge

---

## Common App Review Rejection Reasons (and how you've addressed them)

| Rejection Reason | How This App Addresses It |
|---|---|
| Guideline 4.2 — Thin wrapper | Native menu bar, desktop notifications, native CSV file picker are meaningful native features |
| Missing keyboard shortcuts | Cmd+1–4 for navigation, Cmd+R reload, standard Edit menu |
| No About box | NSApp.orderFrontStandardAboutPanel triggered from Help menu |
| Privacy policy missing | Linked to openhumana.com/privacy in App Store Connect |
| No demo account for review | Create demo@openhumana.com before submitting |
| App crashes on launch | Test on a fresh macOS user account before submission |

---

## Version Updates (after initial release)

1. In Xcode, bump **CFBundleShortVersionString** (e.g., `1.0.1`) and **CFBundleVersion** (e.g., `2`)
2. Archive → Upload → Submit
3. Backend changes on Railway deploy automatically — no resubmission needed for backend-only changes
