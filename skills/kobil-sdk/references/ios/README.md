# iOS reference implementation: activation, login, logout with MCSDK + KSSIDP

Verified 2026-09-16/17 on an iPhone 15 Pro (iOS 26.6.1) with MCSDK iOS 15.16.803.3089231
debug XCFrameworks, a Maverick/AST backend with `useTokenBasedLogin: true`, and a KSSIDP
activation flow. First activation, relaunch to login required, login and logout all passed
with SDK result OK. Copy these files into a fresh SwiftUI app; they are the shortest known
path that works. Every comment in them records a device failure, so read them before
changing anything.

| File | Role |
|---|---|
| `MasterControllerSession.swift` | Owns the MasterController: start event, state machine, activation, login, logout, the authorisation URL builder, the 40 s deadline on IDP exchanges, diagnostics |
| `IdpActivation.swift` | Drives KSSIDP for activation and login: fills the classic HTML form or the headless JSON envelope, forwards the authorisation code, reports the nested result |
| `ActivationView.swift` | Collects user id, one-time code and a password (the password is not sent to the IDP by this flow) |
| `LoginView.swift` | Email + password login of an activated user |
| `MasterControllerStatusView.swift` | Shows the SDK state and hosts the two views plus the logout button; put it in your root view |
| `App-Bridging-Header.h` | The four imports the Swift code needs |

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
   `sdk_app_version_ensure`. Supported destinations: iPhone and iPad only.
5. Build once before writing code. A green build proves the frameworks link.

## What to change per app

Search the sources for `PER APP` and `PER REALM`: the AST app name, the tenant, the login
client id (find the realm's login and activation clients with `sdk_idp_journeys`; names
differ per realm), the certificate file name, and the `Logger` subsystem. Everything else is
the SDK contract.

## The contract these files implement

- Start: `KSMStartEventEx` with the mc_config text, the sdk_config JWT, and the same
  certificate bytes passed as `certificateChain`, `iamCertificateChain` and
  `smartScreenCertificateChain`. The event receiver is registered before the start event so
  fatal errors are not lost.
- Activation and login are the same three-step exchange: `KSMGetAstClientDataEvent` →
  KSSIDP `initiateConnection` with an authorisation URL the app builds (client_id,
  redirect_uri, response_type=code, scope=openid, response_mode=form_post, nonce, the PKCE
  challenge from the client data, and `acr_values=1`) and explicit `X-KOBIL-ASTCLIENTDATA` /
  `X-KOBIL-ASTCLIENTID` headers → KSSIDP posts `SetAuthorisationCodeEvent` itself.
- Activation uses the client named in `mc_config.json` (the one bound to the flow that
  consumes an activation code). Login overrides the client id with the realm's
  subsequent-login client. Logout is `KSMRestartEvent`; nothing is sent until its result.
- `KssIdp.isMultiflow = false` and `dataSource` set, for both the classic HTML activation
  form and the headless JSON envelope. The app fills the JSON itself.
- A rejected credential is answered by the IDP with a page KSSIDP cannot parse and drops
  silently; the session's deadline turns that into a visible failure after 40 s.

## Provisioning order with the MCP

`sdk_ios_project_integrate` (once per project; imports the bundled delivery on first use;
then build) → `sdk_backend_verify` → `sdk_app_ensure` → `sdk_app_version_ensure` →
`sdk_trusted_certificate_write` → `sdk_config_write` → `sdk_idp_journeys` → `sdk_mc_config`
(client id = an activation client the journeys tool reported, or the one
`sdk_activation_client_ensure` created; `output_path` set) → `sdk_activation_user_ensure` →
`sdk_activation_password_set` → `sdk_activation_code_set` → `sdk_idp_theme_check` on the
login client → device test. Codes are one-time; the login password is the one the tool
returned, never something typed on the activation screen.

## Verification on the device

The tester types the user id, the one-time code and, for login, the email and password on
the phone. Hand them over in chat and wait; do not write them into a UI test or any file,
and do not try to drive the SDK's screens with automation.

Read the console for `SetAuthorisationCodeResult` with `status=Ok`, then relaunch and expect
`sdk_state=LoginRequired` with one user, then login `SetAuthorisationCodeResult status=Ok`,
then `RestartResult status=Ok` after logout. If the console goes quiet, run
`sdk_activation_user_status` for the test user: it is the reliable record. See `../activation-login-findings.md` for the
defects behind each rule.

## Second fresh-app verification (2026-09-17, KOBILVault)

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
