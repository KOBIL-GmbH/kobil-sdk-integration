# MCSDK overview: how it works and what it can do

Read this first when a developer asks what the SDK is, how it works, or whether it can do
something. It says what is tested and links to the page with the details and the code.

## How it works

- The **MasterController (MC)** is the SDK's core. The app never calls it directly: it sends
  **events** (`KSM…Event`) and receives events back, one listener for the whole app. The
  reference `MasterControllerSession.swift` wraps this into `async` calls and a `phase` the
  UI routes on.
- **Start:** the app starts the MC with its app name and version. The MC answers with the
  SDK state: activation required, login required, or logged in.
- **Activation (once per device and user):** binds a key on the device to a user. On iOS,
  **KSSIDP** runs the IDP page the realm defines (kssidp standard, emailed code or an
  administrator's activation code). After it the device holds its own credentials.
- **Login (every session):** the user's password (or Face ID releasing the saved password)
  goes through the IDP; the MC then holds a session and tokens.
- **Backend:** **AST** knows the app, its versions and the devices; the **IDP** holds users,
  clients and login pages; **TMS** sends transactions (payment approval, signature
  requests) and messages to the logged-in device over a live connection.
- **Logout** clears the user's cached IAM tokens (`KSMClearIamTokenCacheEvent`) and restarts
  the SDK; without the clear, Shift Lite logs the user in again from the cache. The device
  stays activated. Deleting the last user deactivates the device.

## What it can do (iOS, MCSDK 15.16)

✅ tested on a device · 🟡 compiled, never run · ❌ not possible in 15.16 · ⚙️ needs a backend
feature a normal realm may not have

| Capability | Status | Details |
|---|---|---|
| First activation (kssidp, emailed code, activation code) | ✅ | [ios/README.md](ios/README.md), [login-standards.md](login-standards.md) |
| Login, logout, Face ID sign-in (app-side) | ✅ | [ios/README.md](ios/README.md), [sdk-features.md](sdk-features.md) |
| Transaction approval (payments) | ✅ foreground | [tms.md](tms.md) |
| Signature requests and in-app PDF signing | ✅ | [signing.md](signing.md), [tms.md](tms.md) |
| Display messages from the provider | ✅ receive only | [tms.md](tms.md) |
| SDK state, users on the device, logged-in user, licences | ✅ | [sdk-features.md](sdk-features.md) |
| Token for your own backend (IAM exchange) | ✅ | [sdk-features.md](sdk-features.md) |
| Trusted web view for your portal | ✅ | [sdk-features.md](sdk-features.md) |
| Saved cards, "Pay with" on a payment | 🟡 app-side, compiled; no SDK card API | [wallet.md](wallet.md) |
| Profile photo | see page | [profile-photo.md](profile-photo.md) |
| Change PIN, add / switch / reactivate users, offline and token login | 🟡 | [sdk-features.md](sdk-features.md) |
| Transactions that ask for a PIN or token | 🟡 | [sdk-features.md](sdk-features.md) |
| Push notifications | 🟡 app side; APNs and backend setup are the customer's | [sdk-features.md](sdk-features.md), [tms.md](tms.md) |
| Scam-call warning, locales | 🟡 | [sdk-features.md](sdk-features.md) |
| SSMS OTP, verify push content, app update check, device name | ⚙️ SSMS | [sdk-features.md](sdk-features.md) |
| Sending chat messages | ❌ not in the iOS SDK | [tms.md](tms.md#chat-is-not-in-the-ios-mcsdk) |
| Muting chats, multipart upload | ❌ missing from the binary; upload as JSON instead | [sdk-features.md](sdk-features.md) |
| SDK log export | see page | [log-export.md](log-export.md) |
| Android, Flutter | requirements only, no reference code | [platforms.md](platforms.md) |

Say the status when you answer. Never present 🟡 as working; ask for a device test.

## Common questions

| Question | Where |
|---|---|
| "How do I start a new app?" | [SKILL.md](../SKILL.md) workflow, then [ios/README.md](ios/README.md) |
| "Which activation should I use?" | `sdk_idp_journeys`; the order is in the workflow |
| "Can I do X?" / "How do I add X?" | the request table in [sdk-features.md](sdk-features.md) |
| "Why does activation or login fail?" | [activation-login-findings.md](activation-login-findings.md), `sdk_activation_user_status` |
| "How do I test a payment or a signature?" | `sdk_tms_trigger`, `sdk_tms_result`, or all kinds at once with `sdk_tms_test_sequence` ([tms.md](tms.md)) |
| "Can the app keep cards / a wallet?" | [wallet.md](wallet.md): app-side, no card number stored, no money moved |
| "Where do the SDK files come from?" | [sdk-delivery.md](sdk-delivery.md) |
| "What changed in 15.16?" | [release-review-15.16.md](release-review-15.16.md) |
| "How should it look?" | [reference-app-design.md](reference-app-design.md), [design-system.md](design-system.md) (ideas, not rules) |
