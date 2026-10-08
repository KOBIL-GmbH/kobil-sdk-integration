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
   iOS: embed the frameworks with `sdk_ios_project_integrate` before the first build that
   runs SDK code (linked but not embedded builds, then crashes at launch with "Library not
   loaded"); see SKILL.md step 3.
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

## Local toolchain preflight before long builds (2026-09-29 validation round)

Verify the local toolchain completely BEFORE starting a long build or device
run; an unsupported or half-installed toolchain must be a precise preflight
finding, never a mid-build surprise. `sdk_plan` returns these checks as
`local_build_preflight`. Never mutate shared toolchains (SDK/NDK installs,
global Xcode settings) automatically — report the finding and let the owner fix
the shared installation.

- Android NDK: check the selected NDK version is COMPLETELY installed
  (`source.properties` and toolchain binaries present), not merely listed.
  VAL-06: a half-installed NDK 26.3 was only discovered mid-build; the build
  then succeeded with the locally installed NDK 27.2.12479018. That is a local
  workaround, not vendor qualification of the SDK/NDK combination — record it
  as such and keep the vendor-supported combination question open.
- Compiler/toolchain versions: confirm the installed compiler versions are
  supported by the delivered SDK artifacts before building.
- iOS deployment target: validate the app/Pods deployment target against the
  installed Xcode's minimum before compiling. VAL-07: the Flutter Runner/Pods
  target had to be raised to iOS 15 for Xcode 27; this surfaced during
  compilation instead of preflight.
- Signing and device readiness: signing identity/provisioning resolved and the
  selected physical device visible and authorized before a device build.
- Disk space: enough free space for build products and result bundles.

Physical-device tests remain distinct from simulator tests; a passing simulator
build/run does not discharge any physical preflight item.

## Deployment and physical signing gates

Run the [deployment and artifact gates](deployment-preflight.md) before activation,
explicit-auth TMS and physical iOS installation. Use actual configuration and
built artifacts, explicit customer choices and observed token-holder metadata;
a sample configuration or project signing setting is not sufficient evidence.

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
  followed by setSeverityLevel(.info) instead (runtime-verified fallback,
  iOS MCSDK 15.16.803.3089231, 2026-09-29). Qualify logger and diagnostic
  APIs against the exact shipped BINARY, not only headers, and keep a runtime
  smoke test for logger initialization; see "Error capture and redaction" below.

Preferred method (user decision, 2026-09-29): trusted WebView enrollment and
interactive login with SignedJWT token-based returning login
(useTokenBasedLogin=true, SE-signed JWT OfflineLogin), protected by device
biometrics/face recognition — iOS biometric mode; Android BIOMETRIC_STRONG with
no device-credential fallback. PIN/password/no-auth are documented alternatives,
not defaults. On Android the user-authentication policy is bound at Keystore key
creation and cannot be changed on existing keys: decide the mode BEFORE the
key-creating activation step; a later change requires discarding keys and a
fresh activation with a new activation code.

This is the preferred target path, not proof of the grant used by a particular
OfflineLogin. Require the effective `maverick.jwtSignKeySecurityPolicy`, a
non-password auth mode and sanitized jwt-bearer diagnostics or equivalent issuer
evidence before claiming SignedJWT. `useTokenBasedLogin=true`, a successful
OfflineLogin result, a fresh `iat` or a biometric prompt alone is insufficient.

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
- Swift navigation decisions: inspect the delivered delegate's return semantics.
  Cancel/intercept only the verified authorization redirect; do not cancel every
  callback described as external. Ordinary navigation allowed by the existing
  trust/URL policy must remain navigable. A blank page is not proof of TLS failure.
  Parse query or fragment response fields only as required by the selected,
  verified journey. Do not generalize fragment handling to other flows, broaden
  the redirect allowlist, or bypass exact endpoint/state validation.
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

## Error capture and redaction (2026-09-29 validation round)

Qualified tuple: Android MCSDK 15.16.3088426 / iOS MCSDK 15.16.803.3089231,
kssidpdart 0.6.0 for Flutter.

- Qualify logger/diagnostic APIs against the exact shipped binary, not headers:
  the iOS 15.16 header declares `+getLogSinkWithLogLevel:` but the binary does
  not implement it (unrecognized-selector crash at first use). The verified
  fallback is `getLogSink()` then `setSeverityLevel(.info)`. Keep a runtime
  smoke test for logger initialization.
- Redaction invariant (Swift evidence, VAL round): a redactor matching generic
  `code=` fields erased the numeric error evidence together with the secrets.
  Keep the numeric SDK status/errorCode/type under a distinct key such as
  `errorCode` OUTSIDE the redaction boundary; the sanitized description must
  also survive redaction.
- Dart: the inline `(?i)` flag is invalid in `RegExp` and throws
  `FormatException` at construction — a sanitizer that throws swallows the SDK
  error it should report. Use `RegExp(pattern, caseSensitive: false)` and
  EXECUTE every sanitizer in tests against representative errors and
  secret-bearing inputs.
- Capture Warning/RuntimeError/FatalError AND failed result events,
  ConnectionManagerError and WebView error channels BEFORE cleanup/teardown;
  teardown must not destroy the only failure evidence.
- UI automation must filter credential-bearing fields (passwords, activation
  codes, OTP inputs) before emitting output. Raw evidence stays private; never
  log plaintext credentials or authorization URLs.

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

Never blank-fail the trusted WebView (VAL-36): a pinning failure must never end
in a silent blank page. Wire the load-failure delegate methods and
`onURLBlocked`/KS_CERTIFICATE_ERROR callbacks to a visible in-app diagnostic
view replacing the WebView content — numeric error code, phase and a sanitized
hint, no URLs, hostnames, tokens or secrets. A blank page must be impossible in
the reference integration; tests force a trust failure and assert the error
surface exists. Surfacing the error never means weakening validation.

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

## iOS trusted WebView certificate bytes (verified 2026-10-06)

For KSTrustedWebView 9.7.3000479, pass the approved PEM file bytes unchanged:
`configuration.certsDataForValidation = [try Data(contentsOf: approvedPEMURL)]`.
A PEM bundle can contain multiple approved roots. Do not base64-decode it into
DER for this property. This is the WebView contract, not a universal rule for
other SDK Start, Security.framework, Android or Flutter APIs.

An actual iOS simulator test with secureBrowsing and hostname checks enabled
verified: authentic X2 PEM passes; the SAME X2 converted to DER fails; X1-only
PEM fails for the observed iOS X2 chain; X1+X2 PEM passes. Choose authentic,
approved roots for the actual deployment, not a hard-coded CA or downloaded
leaf certificate. GettingStarted reads the PEM file bytes without conversion.

SecTrust OK plus hostname OK does not prove TWV acceptance: TWV additionally
validates its configured trust store. Capture onURLBlocked reason (1 means
KS_CERTIFICATE_ERROR), subSystem (1500000 here), errorCode (0 here) separately;
zero errorCode alone is not success. Use a bounded SDK log listener locally to
identify the failing stage without logging authorization URLs or credentials.

sdk_tls_chain_check reports asset coverage only. It accepts PEM and DER for
inspection and therefore cannot prove the bytes passed to a particular SDK API
are correct. A matching subject must also match the public key; even that does
not validate signatures, expiry, hostname or mobile trust-path construction.
Before consuming an activation code, load a read-only HTTPS page on the approved
origin through the actual trusted WebView. Check both a passing approved PEM
case and a deliberately wrong/empty trust case which must fail visibly. Keep
certificate and hostname checks enabled. Record SDK version and installed-asset
evidence; successful SDK Start is a separate checkpoint.


Cross-signed variants may have DIFFERENT certificate SHA-256 fingerprints while
sharing the SAME subject and public key (SPKI SHA-256). Do not require equal
certificate fingerprints to recognize those variants. sdk_tls_chain_check reports
matched_anchors.match=exact_certificate for the identical certificate, or
same_subject_and_key_variant when subject and SPKI match despite different
certificate fingerprints. Same subject with a different SPKI remains in
missing_anchors and all_hosts_ok is false. Neither match establishes runtime or
certificate-path validation; obtain anchors through an approved authenticated
source and verify their provenance separately.

## iOS trusted WebView navigation rules (verified 2026-10-06)

KSTrustedWebView 9.7 checks whitelist regexes against the full URL, including
its literal query (no URL decoding by the regex), and asks shouldHandleExternalUrl when an external rule matches.
Never put a bare redirect hostname such as `kobil` in urlExternalWhiteList:
it can match redirect_uri embedded inside the IDP authorization URL. Returning
false from that delegate then cancels the initial page after TLS succeeds.
Use anchored, escaped patterns: internal `^https://idp\.example(/.*)?$`;
external `^https://callback\.example/OpenIdRedirectUri([?#].*)?$`, derived
from the approved deployment endpoints. Do not use a global wildcard.
Still validate scheme/host/effective port/path/state in the callback handler.
Test that the initial authorization URL with its encoded redirect_uri does NOT
match the external rule, while the actual callback does; reject lookalike hosts
and callback paths. Observe a rendered page, not only successful TLS.

## iOS: the Start result arrives in the completion handler (verified 2026-10-08)

Observed in a unit test of an Xcode agent run: the code sent `KSMStartEventEx` with `withCompletionHandler: nil` and resumed its
continuation only in the consumer's `receive(_:withCompletionHandler:)`. The SDK log showed `Set Result ... StartResult(47) ...
status=Ok`, `returnedFuture gots event 47`, then `send event(KSMStartActivationUserIdAndCodeOnlyEvent) to (<consumer>)` and
no further log line: the StartResult was handed to the (nil) completion handler, not to the consumer, so `RunAllTests` ran for more than
eight minutes. With `withCompletionHandler: { reply in ... }` feeding the same dispatch as the consumer events, the earlier
simulator run passed all six gates. A fresh install answers Start with `sdk_state=ActivationRequired`, which is the expected result.
The harmless warning `Class VersionInfo is implemented in both kssidp.framework and KSMasterController.framework` also appears in
the test log. Give each XCTest an explicit timeout so a lost event fails the test instead of blocking the run.
`nil` is only for events without a result event (result none or Acknowledge, for example Cancel, DisplayConfirmation, StartTransaction, ProvidePIN, GetStateEvent, tracing): see SKILL.md, section "When the completion handler may be nil".
