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
