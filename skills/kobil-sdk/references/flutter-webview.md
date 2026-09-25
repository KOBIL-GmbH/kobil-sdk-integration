# Flutter trusted WebView: activation, login and TMS

## Scope and evidence
Flutter wrapper 107.0.0 with hardening 21.0.0 was used for an Android mobile test app.
Android SDK startup, manual activation and foreground TMS approval were observed;
TMS acceptance was independently confirmed through AST status and result. The app
passed 26 unit/widget tests and Android builds. An unsigned iOS build passed before
the final environment/theme change; iOS device behavior is unverified. Returning
login can use cached or refreshed tokens: success alone does not prove a SignedJWT
grant. These observations qualify only this test tuple, not every delivery.

## Setup and activation
- Select a customer-configured connection explicitly. Keep server URLs, tenants,
  credentials and signed assets in project-local configuration, outside this recipe.
  Reuse an appropriate AST app/version and its existing registration user.
- Package the complete asset folder, referenced certificates and backend-signed
  SDK JWT. Isolate persistent SDK state per environment. Do not overwrite another
  environment's device binding when switching assets.
- This tested profile used useTokenBasedLogin=true, astServerBackend=maverick,
  AuthenticationMode.pin and maverick.jwtSignKeySecurityPolicy=
  ALLOW_VIRTUAL_SMART_CARD. This policy was explicitly selected for the test;
  it is not a universal default and must not silently replace a hardware policy.
- BDDKEnrollment/BDDKLogin can render HTML inside trusted WebView when the deployed
  clients support that contract. Inspect bindings and run sdk_native_preflight;
  passing preflight is not proof of fresh enrollment. Do not substitute SuperApp
  Login V2 or a generic browser flow that requires an already-registered device.
- Install warning/runtime/fatal listeners before Start. Gate all operations on
  successful Start/Restart and the returned state.
- GetAstClientDataEventT supplies clientData, astClientId and PKCE challenge/method.
  Preserve the wrapper's actual field spelling (107 uses codeChallange).
  Send X-KOBIL-ASTCLIENTDATA; send X-KOBIL-ASTCLIENTID only when nonzero. Fresh
  enrollment may require X-KOBIL-ASTDEVICENAME. Returning WebView login requires
  X-KOBIL-ASTUSERID from the SDK user list, not the IDP UUID. Never fabricate IDs.
- Bind authorization requests to the selected client, redirect and PKCE values;
  validate redirect and state, and consume a code only once. Pass the returned
  code to SetAuthorisationCodeEventT with that same client/tenant and the selected
  authentication mode. A successful web page is not SDK activation success.
- Require SetAuthorisationCodeResult OK. Preserve data across restart and require
  the persisted user. OfflineLoginEventT handles token reuse/refresh and eligible
  SignedJWT login internally; use trusted WebView when interactive login is needed.
- Android device credential authentication needs FlutterFragmentActivity and the
  delivered biometric bridge initialized before its lifecycle callbacks. Flat AARs
  may require an explicit androidx.biometric dependency (tested 1.2.0-alpha03).
  Device PIN entry belongs to Android system UI, not chat or app text fields.

## Mobile identity and AST registration

Android applicationId and iOS bundle identifier are mobile application identities.
AST app_name and its registered version identify backend registration records;
they are not automatically the same identifier. A new mobile bundle ID alone
neither proves an existing AST registration is incompatible nor proves it reusable.
Never recommend adopting the SuperApp mobile bundle ID just to reuse its assets.

For an authorized app integration, proceed with sdk_app_list, sdk_app_get and
sdk_app_versions without asking for another confirmation for these read-only
checks. Inspect the selected platform/version, registration user, lock state,
integrity policy, and any signing/package binding required by the supplied SDK
and deployment. If returned metadata cannot establish a required binding, identify
that exact gap; do not claim compatibility from the app name or integrity flag alone.
Reuse a suitable existing app/version and preserve its registration user and
security policy. Create new records only when none is suitable or the user requests
separate registration. Do not disable integrity to force reuse.

Do not assert that a delivered sdk_config.jwt is bound to a mobile package or AST
app/version without inspecting the documented configuration contract and applicable
claims privately. sdk_config_write in this MCP takes certificates and connection
service settings, not a mobile bundle ID or AST app_name. Obtain a fresh
backend-signed configuration when required; never edit signed JWT contents.

Preserve the user's previously selected test security policy and flow. Ask only
for an unresolved binding/policy choice or an actual blocker; do not request the
same decision repeatedly. A test selection is not a default for other customers.

## Foreground TMS
1. Handle TriggerBanner, bind its payload/trace context, and show availability.
2. On Review send StartTransaction; display the exact DisplayConfirmationRequest
   transactionInformation and remaining time.
3. Handle a transaction PIN request separately from Android's device PIN. Return
   the actual user decision and exact information through DisplayConfirmation.
4. DisplayConfirmationResult is acknowledgement only. Wait for TransactionEnd,
   inspect status/error, and compare sdk_tms_status and sdk_tms_result.
5. Prevent duplicate decisions, late results reopening cancelled UI, and SDK
   restart while a transaction is active. Test deadlines with an injected clock.

Wrapper 107's inspected StartTransaction possibleResults list was empty, leaving
its Future unresolved. Verify the actual delivery; the app-local correction
includes DisplayConfirmationRequest, TransactionPinRequiredRequest,
TransactionTokenRequiredRequest and TransactionEnd. Keep the original delivery
unchanged and do not patch an unrelated wrapper version blindly.

For this Maverick flow the SDK supplies its stored IAM token internally. Do not
export it into Dart to implement TMS. The test user needed ks-users/ast-client;
inspect the deployment's permission mapping before assigning any role.

freshness_seconds=0 requires fresh authentication; it does not disable freshness.
A synthetic test failed with status39/code516004035 and HTTP403 because its token
was older than the required time. An explicitly selected 300-second test window
then passed. Never relax a real transaction policy merely to make a test pass.

## Validation and diagnostics
Capture status, numeric error, description and report ID, without dumping event
objects or tokens. HTTP406/missing X-KOBIL-ASTCLIENTID during fresh enrollment
indicates an incompatible journey prerequisite; do not invent the header.
An AST TMS HTTP202 is submission only; a pending result may return HTTP412.
Keep activation, returning login, observed SignedJWT grant, approve/reject/timeout,
push and iOS device results separate. Never automate approval of a real transaction.

Themes change presentation, not the SDK handshake. A copied client/flow may use
its own theme while the original BDDK definitions remain unchanged. Rendering a
new theme does not prove that its authentication submission succeeds.


## Signed configuration and retained choices
Within an authorized app build, request a fresh signed SDK configuration with
sdk_config_write using the selected environment service map and verified public
TLS certificates. Do not ask the user to supply a JWT or propose trying an
unverified sample JWT when the MCP can issue one. If certificates, permissions
or services are missing, report that concrete prerequisite; never disable TLS
verification or edit a signed configuration.
Read project instructions (including CLAUDE.md when present) for previously
selected test policy before asking again. Reuse an explicit current-project
ALLOW_VIRTUAL_SMART_CARD/device-PIN decision; do not extend that test choice to
other projects. This does not authorize changing shared backend security policy.

## First-device test: trusted WebView and backend diagnostics

The delivered Flutter549 package contains wrapper106.0.0 and hardening20.1.0.
Source inspection confirms that its WebViewController.loadRequest defaults to
certPinningEnabled=false, pinnedCertificates="", and whiteList=[]. SDK Start
trust configuration is separate from this WebView proxy configuration. For the
selected trusted-WebView integration, explicitly pass the approved PEM trust
anchors, certPinningEnabled=true, and narrowly scoped full-URL allowlist patterns
derived from the deployment's approved HTTPS origins (see matching below).
Verify the certificate chain and validity first; do not hardcode a public CA for
all customers, accept invalid certificates, or weaken pinning to make a page load.
Successful SDK Start/GetAstClientData does not prove WebView TLS is configured.

Install callbacks before loadRequest. Hardening20.1 RunTimeError exposes url,
errorCode and errorDescription. Retain numeric code, sanitized description,
origin (strip URL query/fragment/userinfo), phase and timestamp. Do not replace
these with only "WebView runtime error". Catch asset-read/loadRequest exceptions,
keep the outcome visible, and guard navigation completion against duplicate error,
redirect and cancellation callbacks. Never dump authorization URLs, headers or
entire error objects. SDK and WebView diagnostic channels are separate.

Use explicit checkpoints: SDK Start -> GetAstClientData -> WebView load -> IDP
redirect/state validation -> SetAuthorisationCode -> persisted-user restart/login.
If key exchange fails before navigation with an HTTP gateway/service error,
compare a bounded read-only sdk_backend_auth_test before changing WebView settings.
A failure in that phase cannot validate or invalidate a later WebView certificate
fix. Record actual status codes and server response; only diagnose a tunnel or
origin outage from supporting evidence. Do not repeatedly retry activation or
consume more codes during a backend outage. No successful page load or activation
is claimed until the corresponding phase has been observed after recovery.

Wrapper106 also maps StartTransaction to AsyncEventInfo([]), as does the inspected
107 delivery. Avoid awaiting a Future that has no terminal response mapping.
Use the documented event receiver with a bounded transaction state machine (and
handle dispatch failures), or a reviewed app-local mapping adapter. Global events
must still drive confirmation and TransactionEnd. An unawaited call alone is not
a complete fix. Do not modify the original supplied SDK delivery.

The mc_config maverick.jwtSignKeySecurityPolicy nesting has source evidence in
MCSDK configuration tests; binary string search alone does not establish nesting
or release compatibility. Preserve the selected policy and document the supplied
release's contract. When only newer source evidence exists, say so explicitly.

Log export acceptance requires reopening the ZIP, confirming nonempty expected
SDK log entries, and testing recipient access through the platform share flow.
Showing a share sheet alone does not establish successful delivery. iOS release
framework selection, hardening prerequisites and Android packaging warnings must
be checked against the actual delivery; a debug/unsigned build proves compilation
only, not production readiness or device feature acceptance.

### Trusted WebView allowlist matching

The Android trusted proxy matches each `whiteList` entry as a regular expression against the **complete URL** (`Pattern.matcher(url).matches()`), not just its origin. A bare `https://idp.example.com` therefore rejects `/auth/...`. Build a narrowly scoped pattern from the escaped configured origin, for example `'^${RegExp.escape(idpBaseUrl)}/.*\$'` in Dart. Never use an unrestricted wildcard or disable certificate verification to work around this.

`processReceivedSslError` checks both the proxy certificate and the URL allowlist. If logs say `Proxy set up is correct` followed by `certificate verification failed`, inspect the allowlist before replacing certificates. The latter message alone does not prove a certificate-chain failure. Source: CertPinningProxy `Util.kt`, `urlWhiteListCheckOk` and `processReceivedSslError`.

### Device evidence and error channels

On Android with wrapper106.0.0/hardening20.1.0, the corrected full-URL allowlist
was tested on a physical device: key exchange returned HTTP200, the trusted proxy
reported certificate verification OK, and the enrollment page rendered. This
verifies page loading only; activation, persisted-user login, TMS and iOS runtime
were not established by this run. Earlier wrapper107 results remain separate.

An existing but empty SDK log directory does not establish that no diagnostic
output exists. Check the app's configured log destination and capture Android
logcat for the current app process; the tested debug build emitted native spdlog
there. Do not clear logs before preserving failure evidence. An empty directory
cannot satisfy SDK log-export acceptance.

Warning, RuntimeError and FatalError listeners remain required, but a failed
operation may instead report ConnectionManagerError and a failed result event.
The observed key-exchange failure was 700000036 (MaverickServerHttpError), with
server error field 755000000 and separate HTTP530/502/503 responses. Preserve
these fields separately: 755000000 alone does not identify the underlying cause.
HTTP503 with 'no healthy upstream' during a service rollout is a backend phase
failure; confirm service readiness and make a bounded retry after recovery.
Do not restart services merely because a gateway error appears.
