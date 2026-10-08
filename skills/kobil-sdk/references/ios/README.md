# iOS reference implementation: activation, login, logout with MCSDK + KSSIDP

Verified 2026-09-16/17 on an iPhone 15 Pro (iOS 26.6.1) with MCSDK iOS 15.16.803.3089231
debug XCFrameworks, a Maverick/AST backend with `useTokenBasedLogin: true`, and a KSSIDP
activation flow. First activation, relaunch to login required, login and logout all passed
with SDK result OK. The email-code variant (`email-code/`) passed the same loop on
2026-09-26. Copy the files of one variant into a fresh SwiftUI app; they are the shortest
known path that works. Every comment in them records a device failure, so read them before
changing anything.

The official IdpSdk pages describe an iOS `IdpSdkService` / `IdpSdkNativeInterface`; the
delivered iOS 15.16 frameworks expose `KssIdp` / `KssIdpWrapper` (kssidp.framework) instead,
and these files follow the delivered headers. The event sequence is the same:
`GetAstClientDataEvent`, authorization code from the IDP, `SetAuthorisationCodeEvent`.

Logout sends `KSMClearIamTokenCacheEvent` before `KSMRestartEvent`, as the official Logout page
requires for Shift Lite. That step was added on 2026-09-28 from the documentation: it compiles
in every variant but has not yet been run on a device. Check after logout that relaunching
lands on the login screen rather than logging in silently.

## Pick one activation variant first

Run `sdk_idp_journeys`. It decides which files you copy; never mix the two sessions. Take
the first row that matches, top to bottom: kssidp comes first even when the realm also has
`email_code` clients.

| The realm lists | Use for end users | Copy these files |
|---|---|---|
| clients tagged `login_standard` (KOBIL's official native standards; kssidp current, bddk deprecated) | **Login-standards variant**: administrator issues user, activation code and (kssidp) a temporary password; see [login-standards.md](../login-standards.md) | `login-standards/MasterControllerSession.swift`, `login-standards/KssidpFormFlow.swift`, `login-standards/IdpErrorText.swift`, `HeadlessIdpFlow.swift`, `IdpActivation.swift`, `LoginView.swift`, `TransactionCenter.swift`, `App-Bridging-Header.h` |
| `email_code` clients (KOBIL's self-service email journeys) | **Email-code variant**: the user types an email, the IDP emails a code, no admin-issued code or password | `email-code/MasterControllerSession.swift`, `email-code/EmailCodeActivationView.swift`, `HeadlessIdpFlow.swift`, `IdpActivation.swift`, `LoginView.swift`, `TransactionCenter.swift`, `App-Bridging-Header.h` |
| only `activation` clients | **Activation-code variant**: an administrator issues a one-time code with `sdk_activation_code_set` | `MasterControllerSession.swift`, `IdpActivation.swift`, `ActivationView.swift`, `LoginView.swift`, `MasterControllerStatusView.swift`, `App-Bridging-Header.h` |
| neither | Create an activation-code flow and client (`sdk_activation_flow_ensure`, `sdk_activation_client_ensure`), then the activation-code variant | as above |

For a whole app, [reference-app-design.md](../reference-app-design.md) suggests a screen flow,
tabs and layout; build the screens yourself on top of the variant's files.

The email-code session also ends with an "SDK requests" section (`SdkResultRouter`,
`signData`, `storeUserData`, `userData`, and the internal `awaitResult`, `post`, `loggedInUser` and `certificateChain`)
plus a one-line hook at the top of `receive`. The signing feature and `sdk-requests/` need
both. Transactions (TMS), document signing and display messages are
wired only in the email-code session: the six TMS cases of `MasterControllerEvent`, their mapping, `transactions`,
`sendToController` and `transactions.endSession()` on logout. With the activation-code variant,
port exactly those parts from `email-code/MasterControllerSession.swift` and add
`TransactionCenter.swift`. Chat messaging does not exist in the iOS MCSDK; see
[TMS](../tms.md#chat-is-not-in-the-ios-mcsdk).

The files sit next to this README. A client that cannot read them from disk gets each one
from `sdk_docs(section="ios/<path>")`, for example `ios/email-code/MasterControllerSession.swift`;
when the result has `next_offset`, call again with `offset=next_offset` until it is absent,
and join the parts exactly.

When `email_code` and activation-code clients exist but no login standard, the email-code
variant is the end-user path; the activation-code journey stays for test users an
administrator provisions. A realm with a kssidp login standard always uses the
login-standards variant. Returning login is the same in both
variants: the one-page login client through KSSIDP with `acr_values=1`.

| File | Role |
|---|---|
| `MasterControllerSession.swift` | Activation-code variant. Owns the MasterController: start event, state machine, activation, login, logout, the authorisation URL builder, the 40 s deadline on IDP exchanges, diagnostics |
| `email-code/MasterControllerSession.swift` | Email-code variant of the same class (same name, drop-in replacement): runs first activation with `HeadlessIdpFlow`, hands the code over with `KSMSetAuthorisationCodeEvent`, reads token claims (name, email) and `KSMGetInformationEvent`, keeps a session event log |
| `IdpActivation.swift` | Drives KSSIDP: fills the classic HTML form or the headless JSON envelope, forwards the authorisation code, reports the nested result. Both variants use it for login |
| `HeadlessIdpFlow.swift` | Email-code and login-standards variants: runs the IDP's multi-page headless-v2 journeys natively, because KSSIDP cannot, and provides the HTTP transport and HTML reader `KssidpFormFlow` uses |
| `login-standards/MasterControllerSession.swift` | Login-standards variant: the email-code session plus `LoginStandard` (`.kssidp` or `.bddk`, PER APP), enrollment with user ID, code, temporary password and new password, sign-in with `X-KOBIL-ASTUSERID`, plain error text |
| `login-standards/KssidpFormFlow.swift` | Posts the three kssidp enrollment pages natively; KssIdp fills only the first and drops the rest silently |
| `login-standards/IdpErrorText.swift` | Turns kobil-lite error pages (513_4042, 513_4041, 513_4036, wrong code or password) into one plain sentence |
| `ActivationView.swift` | Activation-code variant: collects user id and one-time code (no password field; the login password comes from `sdk_activation_password_set`) |
| `email-code/EmailCodeActivationView.swift` | Email-code variant: draws every server-sent page natively (fields, OTP, resend timer, notices, journey-switch buttons). Present it as a sheet while the phase is `.activationRequired` |
| `LoginView.swift` | Email + password login of an activated user (all variants; for a login standard relabel the field "User ID" and drop the email keyboard) |
| `MasterControllerStatusView.swift` | Activation-code variant: shows the SDK state and hosts the views plus the logout button; put it in your root view. With the email-code variant, route on `session.phase` in your own root view instead |
| `TransactionCenter.swift` | Email-code variant (the session creates it): transaction confirmations, document signing and display messages. Parses the SDK's `{text, external, data}` envelope, answers each confirmation once (OK or CANCEL, with the original information), ends it at the SDK's timer, keeps history and a message inbox per user (call `load(for:)` after sign-in and `reset()` on sign-out, in the root view where the wallet and profile photo are loaded; without `load(for:)` nothing is saved). UI-free: present `pending` as a sheet with two full-size buttons, list `history` and `inbox`. Verified on device for accept, decline, signature and display message, 2026-09-26. It also answers PIN or token requests (`secretRequest`, `provideSecret`, `cancelSecret`); that part is compiled only |
| `ui/Theme.swift` | Colours, fonts, `AvatarView(name:size:image:)`, `SettingsRow`, primary/secondary buttons. The signing and profile views use it |
| `ui/ApprovalSheet.swift` | The TMS approval sheet (transaction, signature request, display message, result) for `TransactionCenter.pending` / `lastFinished`; present it as a full-screen cover while logged in |
| `signing/*.swift` | In-app PDF signing: hand signature, SDK user-data store, PDF signer, documents list and signing screen. See [signing.md](../signing.md) |
| `profile/*.swift` | Profile photo: per-user local store, picker, camera, circular crop. See [profile-photo.md](../profile-photo.md) |
| `sdk-requests/SdkFlows.swift` | Email-code session extension: change PIN, add/reactivate/delete users, offline/token/anonymous login, workspace, nonce, properties, REST endpoints, tracing, SSMS OTP, app-initiated transactions, update, HTTP through the SDK, upload |
| `sdk-requests/SdkStatusMonitor.swift` | `@Observable` connection, SSE, busy, chat, migration and IDP-login-required state; `SdkStatusMonitor.shared.start()` before the session starts |
| `ui/TransactionSecretSheet.swift` | Asks for the SDK PIN or a token when a transaction needs one (`TransactionCenter.secretRequest`); present it as a sheet |
| `ui/DeviceSecurityView.swift` | "Device and security" settings: status, device name, users, Face ID sign-in on/off, change PIN, update, licences |
| `tests/SdkFeatureTests.swift` | Swift Testing tests for the PIN/token answer and the helpers |
| `sdk-requests/SdkFeatureRequests.swift` | Email-code session extension: typed async calls for SDK state, user list, device info and name, licences, locales, authentication mode, push token and push verification, IAM tokens, decrypt, global data store, update check. See [sdk-features.md](../sdk-features.md) |
| `platform/SecureWebView.swift` | SwiftUI host for `KsTrustedWebView` with host allow-lists and certificate pinning; implements all 15 required delegate methods |
| `platform/BiometricSignIn.swift` | "Sign in with Face ID": keeps the IDP password in the Keychain behind Face ID after a password login and replays it; no backend change (sdk-features.md, "Face ID sign-in") |
| `platform/CallGuard.swift` | `.callGuard()` view modifier: hnb `CallMonitor` scam-call warning on sensitive screens |
| `platform/PushRegistration.swift` | APNs registration (`PushAppDelegate`) and `.sendsPushToken(to:)`, which sends SetPushToken after every login (official Push Token page); needs the Push Notifications capability. Compiled; delivery not device-verified |
| `wallet/*.swift` | Saved cards (last four digits, network, expiry, name; never the number or security code) in the Keychain per user, a wallet screen, an add-card form, card art, and `.walletPaymentCard(wallet)` which puts "Pay with" on the approval sheet. See [wallet.md](../wallet.md) |
| `tests/SigningAndPhotoTests.swift` | Swift Testing unit tests for `signing/` and `profile/` |
| `App-Bridging-Header.h` | The imports the Swift code needs. `sdk_ios_project_integrate` already writes the same content as `<Target>-Bridging-Header.h`; copy this file only when integrating by hand |

The reference views are deliberately plain. Restyle them freely, but keep their state
handling: which session call each button makes, when a form is re-shown, and that a
failure message stays on screen above the form.

## Project setup (Xcode 27)

Steps 1 and 2 are one tool call; the manual route below them is the fallback.

- `sdk_ios_project_integrate(project_path, target_name)` does everything: when the local
  store is empty it imports the SDK delivery bundled with this MCP (`sdk-delivery/`, verified
  against the shipped `.sha512` files), then copies the debug framework set next to the
  target's sources, writes `<Target>-Bridging-Header.h`, and edits `project.pbxproj` exactly
  as the verified app has it (Embed & Sign, bridging-header setting, version). Verified
  twice on a fresh Xcode 27 project: headless `xcodebuild` for iOS succeeded with all four
  frameworks embedded. Build once afterwards, then add code.
- `sdk_artifacts_notes("ios")` shows the delivered changelog; `sdk_artifacts_list` shows the
  store; `sdk_artifacts_import` / `sdk_artifacts_install` exist for a delivery that arrived
  elsewhere. Nothing is ever downloaded.

1. Manual fallback for frameworks: take `KSMasterController`, `hnb`, `kssidp` and
   `KSTrustedWebView` from the **debug** set of the delivered zip while developing (the
   release set refuses the debugger). Drag them onto the app folder, copy, tick the app
   target only, then set all four to **Embed & Sign**. A pre-ticked test target is the usual
   mistake.
2. Manual fallback for the bridging header: add `App-Bridging-Header.h` and set Build
   Settings → Swift Compiler → Objective-C Bridging Header to its path.
3. Bundle resources: the trusted root PEM (from `sdk_trusted_certificate_write`, which
   also proves every backend host chains to it), `sdk_config.jwt` (from `sdk_config_write`
   with that PEM) and `mc_config.json` (from `sdk_mc_config` with `output_path`, naming
   that PEM file). Check Build Phases → Copy Bundle Resources lists all three; Xcode skips
   unfamiliar extensions.
4. The app version in General must equal the version registered with
   `sdk_app_version_ensure`, and so must `appVersion` in `MasterControllerSession.swift`.
   Supported destinations: iPhone and iPad only. The delivered XCFrameworks have no macOS or
   visionOS slices, so `sdk_ios_project_integrate` sets `SUPPORTED_PLATFORMS` to
   `iphoneos iphonesimulator`, `TARGETED_DEVICE_FAMILY` to `1,2` and turns Mac Catalyst and
   "Designed for iPhone" off (an Xcode 27 template adds Mac and Vision). By hand, set the same.
   Pass `usage_descriptions` for the Face ID, camera and photo-library texts the features
   need; the tool adds only keys that are missing. Xcode reloads the project after the tool
   edits it and cancels a build that is running; build again afterwards.
5. Build once before writing code. A green build proves the frameworks link.

Compiler settings the reference files need: `SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor`
(the Xcode 26+ default for new app targets). Swift 5 and Swift 6 language modes both work,
in Debug and Release; the plugin's test suite type-checks every variant with the features
in both. Previews are inside `#if DEBUG`; keep new ones there, because they use DEBUG-only
sample data and a Release build fails otherwise.

The **debug** frameworks are for development only. They show a "PUBLIC HARDENING — DO !NOT!
RELEASE" alert at start, and their log prints the plaintext of display messages and
transaction texts. Ship with the release set (it refuses a debugger) and never share a debug
console log from a customer's device.

## What to change per app

The session files stop the build with `#error` until `appName` and `tenantId` are filled in:
set them to the app you registered with `sdk_app_ensure` and the tenant `sdk_backend_status`
reports, then delete the `#error` line. Search the sources for `PER APP` and `PER REALM`: the AST app name, the tenant, the app
version, the login client id and, in the email-code variant, the three journey client ids
(find all of them with `sdk_idp_journeys`; names differ per realm), the certificate file
name, and the `Logger` subsystem. Everything else is the SDK contract.

## The contract these files implement

- Start: `KSMStartEventEx` with the mc_config text, the sdk_config JWT, and the same
  certificate bytes passed as `certificateChain`, `iamCertificateChain` and
  `smartScreenCertificateChain`. The event receiver is registered before the start event so
  fatal errors are not lost.
- Activation and login are the same three-step exchange: `KSMGetAstClientDataEvent` →
  KSSIDP `initiateConnection` with an authorisation URL the app builds (client_id,
  redirect_uri, response_type=code, scope=openid, response_mode=form_post, nonce, the PKCE
  challenge from the client data, and `acr_values=1`; never on the email-code journeys) and explicit `X-KOBIL-ASTCLIENTDATA` /
  `X-KOBIL-ASTCLIENTID` headers → KSSIDP posts `SetAuthorisationCodeEvent` itself.
- Activation-code variant: activation uses the client named in `mc_config.json` (the one
  bound to the flow that consumes an activation code). Email-code variant: activation names
  the journey's own client in the URL and in `KSMSetAuthorisationCodeEvent`, so `mc_config.json`
  `iam.clientId` names the **login** client: the SDK exchanges the session tokens as
  `iam.clientId` (explicit-authentication TMS, `KSMExchangeIamTokenEvent`), and Keycloak lets a
  public client exchange only tokens it holds itself; any other client gets 403 "Client is not
  the holder of the token" (device-verified 2026-09-27; see tms.md). Both: login overrides the
  client id with the realm's subsequent-login client. Logout clears the IAM token cache, then sends `KSMRestartEvent`; nothing else is sent until its result.
- `KssIdp.isMultiflow = false` and `dataSource` set, for both the classic HTML activation
  form and the headless JSON envelope. The app fills the JSON itself.
- A rejected credential is answered by the IDP with a page KSSIDP cannot parse and drops
  silently; the session's deadline turns that into a visible failure after 40 s.

## Provisioning order with the MCP

For **email-code activation** (the realm lists `email_code` clients) stop after
`sdk_mc_config` and `sdk_idp_theme_check`: no activation user, password or code is issued.
The order below is the **activation-code** journey.

`sdk_ios_project_integrate` (once per project; imports the bundled delivery on first use;
then build) → `sdk_backend_verify` → `sdk_app_get` / `sdk_app_versions` (see what exists and
read a registration user to reuse) → `sdk_app_ensure` with THIS app's own name (never an app
found in the list, unless the user names it) →
`sdk_app_version_ensure` →
`sdk_trusted_certificate_write` → `sdk_config_write` → `sdk_idp_journeys` → `sdk_mc_config`
(client id = an activation client the journeys tool reported, or the one
`sdk_activation_client_ensure` created; `output_path` set) → `sdk_activation_user_ensure` →
`sdk_activation_password_set` → `sdk_activation_code_set` → `sdk_idp_theme_check` on the
login client → device test. Codes are one-time; the login password is the one the tool
returned, never something typed on the activation screen.

## Simulator and device

Use the simulator for layout and visual checks: SDK Start reaches `ActivationRequired` there.
Activation and login are verified on physical devices only; a simulator activation once
failed with "Failed to get DM crypto key" after the backend had already consumed the
activation credential (see `../platforms.md`). Run the first activation on a device, and do
not spend a one-time code or an end user's email journey on a simulator.

## Verification on the device

The tester types the user id, the one-time code and, for login, the email and password on
the phone. Hand them over in chat and wait; do not write them into a UI test or any file,
and do not try to drive the SDK's screens with automation.

Read the console for `SetAuthorisationCodeResult` with `status=Ok`, then relaunch and expect
`sdk_state=LoginRequired` with one user, then login `SetAuthorisationCodeResult status=Ok`,
then `RestartResult status=Ok` after logout. If the console goes quiet, run
`sdk_activation_user_status` for the test user: it is the reliable record. See `../activation-login-findings.md` for the
defects behind each rule.

## Second fresh-app verification (2026-09-17)

A second SwiftUI app built from these sources by Xcode's own agent, provisioned entirely
through the MCP (app, version, signed config, mc_config, certificate, user, password, code),
passed the full loop on an iPhone 15 Pro (iOS 26.6.1): Start OK / ActivationRequired, first
activation `SetAuthorisationCodeResult Ok`, relaunch to LoginRequired with one user, login Ok
against the subsequent-login client, logout back to the login screen. Backend record on both
sides: activation code consumed plus a session for the activation client, then a session for
the login client, zero failed logins.

Lessons from that run, now built in:

- `sdk_ios_project_integrate` sets the deployment target on every native target when asked;
  an Xcode 27 template puts 27.0 on the test targets too, and the device shows as
  "Incompatible" for the scheme until all of them are lowered.
- The activation screen has no password field; the login password comes from
  `sdk_activation_password_set`.
- A failed activation keeps its message on screen with the form beneath it for the retry.
- `KSMGetInformationEvent` after login answers `GetInformationResult Ok` with the SDK
  version and the logged-in user; a good source for an in-app status card.
- Do not drive the SDK's screens with XCUITest on a physical device: the runner needs a
  free app slot on a free developer profile, event synthesis needs iOS 27, and one-time
  codes must never sit in test sources. The tester types; the console and
  `sdk_activation_user_status` verify.

## Email-code activation (self-service journeys), verified 2026-09-26

Use this instead of the activation-code journey when the realm activates devices with
KOBIL's self-service journeys: the user types an email, the IDP emails a code, and a new or reset
password is chosen on the way. `sdk_idp_journeys` lists such clients under `email_code`. No
backend change and no admin-issued password or activation code is needed. Verified on an
iPhone 15 Pro (iOS 26.6.1), MCSDK iOS 15.16, from a fresh install: registration journey →
the IDP's "log in" button → forgot password → emailed code → new password → activated, then
relaunch to LoginRequired, login, logout.

KSSIDP drops the second page of these flows, so the app runs them with `HeadlessIdpFlow.swift`.
The wiring in `MasterControllerSession` is small:

1. Send `KSMGetAstClientDataEvent` as for any activation. On its result build the
   authorisation URL for the chosen `email_code` client **without** `acr_values` (these flows
   activate the AST client inside the verify-identity step; the bypass is not needed).
2. Create `HeadlessHttpTransport(controller:certificate:)` with the trusted certificate bytes
   and `HeadlessIdpFlow(transport:redirectUri:headers:)` with `Accept-Language`,
   `X-KOBIL-ASTCLIENTDATA` and `X-KOBIL-ASTCLIENTID` (26 zeros before activation). The
   redirect URI is `iam.redirectUri` from `mc_config.json`.
3. Forward every `KSMCreateHttpCommonRequestResultEvent` the global receiver sees to
   `transport.deliver(HeadlessHttpResponse(event))`; the SDK may answer there instead of in
   the send's completion handler.
4. `try await flow.start(authorizationUrl:)`, then `flow.submit(form, values:, …)` for each
   page. Each returns `.form(HeadlessForm, message)` to draw natively or
   `.authorisationCode(code)`.
5. On `.authorisationCode` send `KSMSetAuthorisationCodeEvent(tenantId:, authenticationMode:
   .no, authorisationCode:, clientId: <the journey's client>)`. On
   `KSMSetAuthorisationCodeResultEvent` status Ok the SDK is already logged in: show the
   logged-in screen, do not ask the user to relaunch.

Draw the page from `HeadlessForm`: text, password and OTP fields, validation, the resend
timer (`resendCodeModel`), and buttons. The OTP page posts only the OTP key. The two resends:

```swift
// New code on the OTP page: the current values, flagged on the OTP key.
try await flow.submit(form, values: values, resendKey: otpKey)
// A "resendEmail" button: only the user identity, flagged, with that action.
try await flow.submit(form, values: values, action: "resendEmail",
                      resendKey: "userIdentity", onlyKeys: ["userIdentity"])
```

A page can carry a notice (`HeadlessPageMessage`, from `<p id="error-msg">`) with buttons; the app switches
journey on their `action`: `login`, `registration`, `forgotPassword` start that journey again
with fresh AST client data, `ok`/`retry` dismiss the notice. The registration journey answers
an email that already has an account with such a notice and a `login` button; a
`forgotPassword` field on the login page leads to the password reset. Map each action to the
realm's client from `sdk_idp_journeys`; never hard-code another realm's names.

The same actions also arrive outside a notice: as page buttons (`HeadlessForm.buttons`,
from `formDisplayButtons`) and as a field's `actionButton`. Render every button whose
`action` names a journey and switch on it; `submit` and `resendEmail` are the only other
page actions. The wiring above is already implemented in `email-code/MasterControllerSession.swift` and
`email-code/EmailCodeActivationView.swift`, copied from the device-verified app; copy those
instead of writing it again. The top-level `MasterControllerSession.swift` and
`ActivationView.swift` are the activation-code variant only.

### The logged-in user's name and email

After an Ok login or activating `SetAuthorisationCodeResult`, send
`KSMGetIamAccessTokenClaimsEvent()`; `KSMGetIamAccessTokenClaimsResultEvent` carries
`status` and `claims` (claim name → stringified value). The SDK may also push
`KSMLoginTokenClaimsAvailableEvent` with the same `claims` at login. Read `name` (or
`given_name` + `family_name`) and `email`; log claim names only, never values. Clear them
on logout. Seen on screen by the tester on 2026-09-26 (MCSDK iOS 15.16, email-code
realm); the console capture of that run was lost, so the exact claim set is not recorded.
