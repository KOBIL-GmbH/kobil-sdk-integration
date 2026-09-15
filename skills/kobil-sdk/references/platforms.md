# Platform integration requirements

These are implementation requirements, not verified app templates. Read the
selected SDK release's actual APIs and platform prerequisites before coding.

| Target | Resolve and verify |
|---|---|
| Kotlin / Android | Package ID, Gradle dependencies, native ABIs, startup/events, signing and device binding |
| Swift / iOS | Bundle ID, SDK frameworks, Xcode target resources, delegates, signing and entitlements |
| Flutter / Android | Dart wrapper plus compatible Android native artifacts, runner and device lifecycle |
| Flutter / iOS | Dart wrapper plus compatible iOS native artifacts, resources, runner and signing |

For Flutter, native SDK support does not guarantee a Dart binding. Verify exported
wrapper APIs and event types rather than translating Kotlin/Swift names into
invented Dart calls. Initialize once outside widget rebuilds, handle events and
fatal errors, and connect lifecycle operations according to the SDK contract.
If the SDK needs filesystem paths, an asset key is not a substitute: follow its
asset-to-storage setup. Inspect release/debug artifact differences independently.

For activation/login, resolve the backend realm/client and configured flow,
register or reuse the app and platform version, obtain signed SDK configuration
and trusted certificates, and provide the required test user/activation method.
The JWT is only part of configuration. Credential/session ownership and PIN
processing depend on the SDK family; do not mix contracts between SDKs.

Acceptance: successful initialization, first activation, backend/device state,
login after restart, errors, cancellation and interrupted connectivity. Test
fresh and existing apps separately. Flutter requires separate Android and iOS evidence. Desktop app targets are
excluded from the external-customer scope. Missing test hosts and unavailable
SDK artifacts for the in-scope targets remain explicit blockers.

## Verified Android activation and login

Verified tuple: fresh Kotlin debug app, KSSIDP 1.7.0 / MC 188.1.2937039,
Pixel 8, Android API36, arm64. Activation and returning login passed. The API35
arm64 emulator passed startup/key exchange; its complete flow remains unverified.
This evidence does not establish support for every OS/device/SDK combination.

### Reusable workflow

1. Prefer an appropriate existing AST app/version and its registration user.
   A fresh client app can reuse backend registration. For a new backend record,
   explicitly select an existing tenant user; any existing user may be selected
   by the deployment owner. This API stores registerUserId on the version.
   Verify readback and keep the registration and activation-user roles separate.
2. Request a backend-signed JWT containing astUrl, the deployment service map
   (including astLogin) and trusted TLS certificates. Never modify a signed JWT.
   Package it with app_config.json, mc_config.json and every referenced certificate
   under app/src/main/assets. Compare packaged APK asset bytes, including exact
   certificate subdirectory paths.
3. Resolve manifest merges and native preload metadata from the supplied AARs.
   The tested bundle required the Material resource dependency. Do not drop SDK
   providers or preload libraries to make a build pass. Pass the required
   Application context and register SDK error-event listeners before Start.
4. Resolve authentication mode, backend password policy and hashing contract
   independently. This selected integration used explicit AuthenticationMode.NO
   and hashPin=false with a backend password. NO does not remove that password
   requirement. Do not choose SDK PIN mode because an input field is named PIN:
   the inspected implementation requires jwtSignKeySecurityPolicy for that mode.
5. Use restricted native file logging for this tested tuple; retain the separate
   Warning/RuntimeError/FatalError event listener. The selected StartEncryption
   implementation accepts a directory and creates ks.log inside it. Confirm
   useful log records are actually written; file/header creation alone is not
   sufficient evidence of log capture. Verify the contract for other releases.
6. Target the intended device explicitly with adb when multiple devices exist.
   Install and launch, then wait for StartResult OK / ACTIVATION_REQUIRED and
   StartActivationUserIdAndCodeOnlyEvent before the first activation. Supply a
   valid activation method and policy-compliant credentials through private input.
7. Require KSSIDP SUCCESS and SetAuthorisationCodeResultEvent OK for activation.
   Preserve app data, force-stop/relaunch, and check StartResult OK / LOGIN_REQUIRED
   with the activated user and StartLoginEvent. Resolve userId and the required
   AST-user header from the SDK user list; do not substitute the Keycloak UUID.
   Submit returning login and require its own SUCCESS / OK result.

### Observed errors and corrections

| Evidence | Correction or diagnostic action |
|---|---|
| Native startup error 801000008; JWT payload invalid | Include astUrl in the signing request and obtain a newly signed JWT. |
| 800000271, REST module not initialised; astLogin absent | Include the authorized service map; both key-exchange result events then returned OK. |
| Native SIGSEGV during GetAstClientData with Java Log.RegisterCallback | Replacing the optional callback with native file logging avoided the crash on Pixel. Exact JNI cause remains unproven; keep error-event listeners. |
| HTTP200/request SUCCESS but application error580/0017 | Read the explanation: this test password lacked uppercase characters. Respect the realm policy; HTTP success is not activation success. |
| SetAuthorisationCodeResult NOT_SUPPORTED/code0 | The test incorrectly selected PIN without its signing-key policy. Use the selected deployment's documented authentication mode. |
| Failed SDK handoff after successful backend enrollment | The activation code may already be consumed and a password created. Inspect partial state; do not blindly replay, reset accounts or keep issuing codes. |

A failed result can omit useful numeric information, and a native crash may
prevent FatalErrorEvent delivery entirely. Preserve restricted SDK and Android
crash evidence, report the last successful operation, and ask for help when no
supported correction is clear.

### Acceptance evidence and limits

The physical test passed activation (SUCCESS / OK), persisted one user through
force-stop/relaunch (LOGIN_REQUIRED), and passed returning login (SUCCESS / OK)
with the same successful identity. App data and backend security settings were
preserved. AST notification categories were resolved separately from the sample
application's category label. Test identity provisioning still used a local
backend helper; this is not yet fully self-contained MCP onboarding.

Swift/iOS, Flutter Android/iOS, existing-app integration, and all
remaining SDK features require their own evidence. This milestone does not close
the full-feature scope.
