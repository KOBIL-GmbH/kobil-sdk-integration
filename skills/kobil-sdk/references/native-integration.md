# Native integration handoff

This first-priority pack covers classic MCSDK with KSSIDP on Kotlin/Android and
Swift/iOS. Select a platform and read the eight integration topics plus `automated_testing` through `sdk_knowledge_get` before
building a fresh app. Examples are small functions to integrate into the app;
they do not provide a complete UI, controller lifecycle or customer configuration.
Their exact artifact validation is returned with each example. Standalone IDPSDK,
Flutter and SSMS require separate bindings; do not translate these calls blindly.

## From backend selection to a runnable app

1. Call `sdk_service_catalog` and confirm the three knowledge tools are present.
   If missing, update both MCP and skill to the same tested commit/release and
   restart the MCP/session. An older installed package is not upgraded by Git.
2. Validate the configured connection with `sdk_backend_status` and check referenced
   credential availability with `sdk_credential_status`. Keep administrator
   credentials in the backend provider, never in app assets. Follow the bundled
   [credential guide](../../../docs/credentials.md) for native stores/age transfer.
3. Read `sdk_app_get` and `sdk_app_versions`; prefer a suitable existing record.
   If creation is needed within the user's task, use `sdk_app_ensure` and
   `sdk_app_version_ensure` with explicit platform/version, registration user and
   integrity policy. Read back the resulting record. The registration user is
   distinct from the user who will activate this device.
4. Request the signed configuration via `sdk_config_write`, using the selected
   trusted certificates. Package the JWT together with the delivery's matching
   app/MC configuration and referenced certificates. Preserve signed content.
   Verify assets in the built APK/app bundle, not only in the source tree.
5. Select the existing native-compatible IDP client and exact field mappings.
   Use user search/read operations to select a dedicated test user. Create one
   only if needed and authorized by the test task. Generate an activation code
   using `sdk_idp_activation_code_generate` for the selected user UUID when the
   deployment supports that credential type. Never replace codes automatically
   after an uncertain timeout. Registration metadata is not an activation code.
6. Integrate the `setup`, `lifecycle` and `diagnostics` recipes first. Register
   listeners before initialization, retain controller/wrapper references and
   inspect result status/state. Install required native framework/AAR dependencies.
   Keep app console messages separate from SDK Warning/RuntimeError/FatalError.
7. Implement `activation`, `login` and `multi_step`. Pass the explicit client,
   requested credentials, user-selection headers and callback/delegate. Use actual
   SDK result status and state to drive UI. The supplied helpers are dispatch
   functions, not proof of successful authentication. Never default to SuperApp
   Login V2 for native Android/iOS.
8. Integrate `tms` with one event owner (app or KSSIDP), according to the selected
   architecture. For authorized test transactions use `sdk_tms_trigger`, retain
   its transaction ID, and compare `sdk_tms_status`/`sdk_tms_result` with the SDK
   terminal result. Show the transaction information and actual approve/reject
   choice; confirmation acknowledgement alone is not completion.
9. Implement `logs` with the actual SDK log directory, archive validation and
   platform sharing. Android needs a scoped FileProvider definition and temporary
   read grant. iOS needs a share sheet presented on the main thread; on iPad set
   its popover anchor. Keep encrypted SDK logs intact and clean temporary archives
   after sharing according to app policy.

## Release-qualified configuration and errors (15.16, verified 2026-09-29)

Qualified tuple: Android MCSDK 15.16.3088426, iOS MCSDK 15.16.803.3089231
(2026-09-29 validation round). Configuration templates (mc_config/app_config)
ship in the delivery's GettingStarted asset ZIPs, not in the framework or
xcframework archive; sdk_artifact_info flags missing templates. The delivered
mc_config for this tuple contains useScp, useTokenBasedLogin, useSmartScreen,
astServerBackend, iam {clientId, serverUrl (origin only), redirectUri,
trustedSslServerCerts} and maverick {mTLS, mKex, useSEKeyForSigningTransactions}.
Fill values from the selected deployment; other releases need their own
qualification.

Runtime-verified error knowledge for this tuple:

- 800000133 FatalError ScpParameterError "Tag is empty, but category not": the
  SDK configuration category/tag is NOT the TMS notification category. Leaving
  both empty is correct for deployments without that configuration.
- 800000015 SCP_ERROR_CANNOT_READ_APP_CONFIG: a warning at Start; Start can
  still succeed. Whether app_config is required for a given deployment remains
  partially unverified — preserve the warning and investigate, do not assert
  either semantic.
- 800000279 "Signed jwt together with mkex or SE for signing transactions is
  not supported yet": SignedJWT login with maverick.mKex=true or
  useSEKeyForSigningTransactions=true is rejected. The tested known-good
  SignedJWT combination used both false; this is a tested combination, not a
  universal default.
- iOS 15.16 binary lacks the header-declared +getLogSinkWithLogLevel: selector
  (unrecognized selector at runtime despite a clean build). Use getLogSink()
  followed by setSeverityLevel instead (runtime-verified fallback; broader
  logging diagnostics remain a separate E05 work item).

Preferred method (user decision, 2026-09-29): trusted WebView enrollment and
interactive login with SignedJWT token-based returning login
(useTokenBasedLogin=true, SE-signed JWT OfflineLogin), protected by device
biometrics/face recognition — iOS biometric mode; Android BIOMETRIC_STRONG with
no device-credential fallback. PIN/password/no-auth are documented alternatives,
not defaults. On Android the user-authentication policy is bound at Keystore key
creation and cannot be changed on existing keys: decide the mode BEFORE the
key-creating activation step; a later change requires discarding keys and a
fresh activation with a new activation code.

## Native trusted WebView callback contract (verified 2026-09-29)

Record the callback contract from the ACTUAL delivered interfaces (javap/bytecode
on Android, `xcrun swift-synthesize-interface` on iOS); never code against assumed
or older signatures — a signature mismatch silently fails to override.

- Android (TWV Proxy 20.1 with MCSDK 15.16.3088426): the delivered `TWVClient`
  only calls `sendOpenIdRedirectUriCode` from
  `shouldOverrideUrlLoading(WebView, String)` and `onReceivedSslError`. Android
  WebView does NOT invoke `shouldOverrideUrlLoading` for POST-initiated
  navigations, so the redirect after the enrollment POST is never delivered:
  activation stalls while the activation code is consumed. Verified fix: a
  `TWVClient` subclass intercepts the registered redirect URI in
  `shouldInterceptRequest`/`shouldOverrideUrlLoading` before any network request,
  matching the delivered nullable parameter signatures exactly. The second attempt
  returned SetAuthorisationCodeResult OK/error 0 on a physical device.
- iOS (KSTrustedWebView 9.7.3000479 with MCSDK 15.16.803.3089231): ALL
  `KsTrustedWebViewDelegate` methods are required — the 15.16 header declares no
  `@optional` methods. Implement every one.
- Redirect validation on both platforms: exact scheme, host, effective port
  (explicit or scheme default) and path plus the state parameter; deliver the
  authorization code exactly once, ignore duplicate callbacks, then hand it to
  SetAuthorisationCode with the same client/tenant and authentication mode.
- Never diagnose an enrollment HTTP 406 from the status alone; inspect sanitized
  header propagation first (Flutter evidence: comma-joined ASTCLIENTDATA →
  513/4002 "Invalid AST Client ID"; the SDK ASTCLIENTID including the null ULID
  must be forwarded unchanged).
- Before any retry, read back the backend fixture (`sdk_idp_user_credentials_list`,
  `sdk_ast_find_client`): a stalled or failed enrollment can consume the
  activation code and create a password credential or partial AST client.

## Mobile certificate-chain coverage and pinning diagnostics (verified 2026-09-29)

SDK Start trust (mc_config `iam.trustedSslServerCerts`; for iOS also pass the IAM
chain explicitly at Start) is separate from the trusted WebView trust
(`KsTrustedWebViewConfiguration.certsDataForValidation`). Configure and verify
both independently, matching each API's DER/PEM contract; never disable
certificate or hostname verification.

The mobile TLS client may build a DIFFERENT chain than desktop verification.
Verified on iOS simulator and physical device (2026-09-29, MCSDK
15.16.803.3089231, KSTrustedWebView 9.7.3000479): TWV runs SecTrust, which
succeeds, then pins against the chain iOS built — for a Let's Encrypt chain iOS
ends at the self-signed system root ISRG Root X2, not X1 via the cross-sign.
Pinning X1 alone gives `onURLBlocked` reason 1 (KS_CERTIFICATE_ERROR), subsystem
1500000 and the log line "servercert validation endresult failed". Fix: pin the
authentic X2 (from the system root store, fingerprint-checked) alongside X1.
Derive approved trust anchors from the chains actually negotiated by the mobile
clients per platform and environment; never hard-code one CA for all
environments, and never weaken pinning to make a page load.

Diagnostics: `KsTrustedWebView.setLogListener` plus a temporary
`KsTwvLog.setLogLevel(debug)` shows the per-certificate validation steps; lower
the level again after diagnosis. The Android trusted-proxy full-URL allowlist
matching fix is already part of this pack (see the Flutter WebView reference); it
is a separate failure mode from chain coverage.

Candidate tooling (not adopted): branch feature/AK-539-ios-tooling-review commit
773afbe carries a TLS-chain reader/root-certificate writer that saves the IDP
host's verified root and checks every configured backend host against it. It fits
this repo's connection-file schema, but it selects only the root of the chain the
LOCAL (desktop) trust store verified — exactly the single-chain assumption this
section corrects — and would have produced X1-only pinning here. Adopt it only
after extending it to enumerate mobile-negotiated roots (or accept multiple
anchors) with the caveats above.

## User acceptance

Retrieve `sdk_integration_checklist` for each topic and retain observed results.
Check cold start, activation, login after restart, multi-step continuation/cancel,
wrong/expired input, TMS approve/reject/timeout, all three error categories and
shareable SDK logs. Record platform, exact mobile SDK, app/backend version and
result. Stop at an unexplained error and show the original error fields plus
pending operation; do not claim success from a build, token or empty callback.

Compilation, synthetic diagnostics and the successful registration/activation/cold
returning-login path are recorded for MCSDK 15.16 on two physical devices. Read the
per-platform runtime_acceptance scope. Other checklist cases remain to be tested.
For iOS, package AND explicitly pass the IAM certificate chain at Start; packaging
alone did not initialize it in the tested SDK.
