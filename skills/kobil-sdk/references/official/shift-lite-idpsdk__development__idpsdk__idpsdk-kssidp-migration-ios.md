> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/idpsdk/idpsdk-kssidp-migration-ios> on 2026-09-28. Converted to Markdown; wording unchanged.

# Migration from KSSIDP (iOS/Swift)

This guide describes the changes required to migrate an iOS/Swift application from the **KSSIDP wrapper** to the **IdpSdk**`.

---

## Overview of Differences

|  | KSSIDP | IdpSdk |
| --- | --- | --- |
| Initialization | let kssidp: KssIdpWrapper = .init(config: KssIdpConfig) |  |

```
let idpSdk: IdpSdkService = .init(...)
|
```

| MC event handling | Internal — KSSIDP handles `GetAstClientDataEvent` etc. | Manual — app orchestrates all MC events |
| Credential passing | Passed upfront as `Dictionary` to the method call | Provided via `provideCredentials` callback |
| Result handling | Completion block processing `ResultObject` and `KssIdpResultObject` via code block | Completion block processing `IdpSdkResult` |
| Thread safety | Managed by KSSIDP | `provideCredentials` is called on a background thread — implementation must be thread-safe |

---

## Initialization

### Before (KSSIDP)")

```
// Build config
let idpConfig = KssIdpConfig(certificatePath: certificatePath,
baseUrl: baseUrl,
tenantId: tenantId,
masterController: masterController,
shouldKssIdpHandleTms: false,
shouldHashPin: true)
// Initialize
let kssIdp = KssIdpWrapper(config: idpConfig)
```

### After (IdpSdk)")

```
class IdpHandler: NSObject {
let idpSdk: IdpSdkService
/// Master Controller instance used to send and receive MC-SDK events.
let masterController: MCSDK
/// Wrapper around the IDP SDK responsible for requesting the authorization code.
let idpSdk: IdpSdkService
/// Logger used to display progress and results on screen.
let screenLogger: ScreenLogger
init(
masterController: MCSDK,
screenLogger: ScreenLogger,
certificate: Data,
baseUrl: String,
tenantId: String,
) {
self.masterController = masterController
self.screenLogger = screenLogger
self.idpSdk = .init(
tenantId: tenantId,
idpUrl: baseUrl,
certificateChain: certificate,
shouldHashPin: false
)
self.tenantId = tenantId
}
}
```

Key changes:

* `certificatePath` (String) is replaced by `certificateChain` (ByteArray) loaded directly from assets.
* `baseUrl` is now passed as `idpUrl` directly to `initIdpSdk`.
* `KssIdpConfig` is removed entirely.

---

## Activation Flow

### Before (KSSIDP)")

```
// Pass all credentials upfront — KSSIDP handles MC events internally
kssIdp.activate(clientId: "KssIdpEnrollment",
authMode: authMode,
credentials: ["username"       : username,
"password"       : password,
"activation-code": activationCode],
parentSpan: parentSpan) { _, newResultObject in
self.handleNewResult(newResultObject: newResultObject)
}
```

### After (IdpSdk)")

Credentials are no longer passed upfront. Instead, implement `IdpSdkInteractionInterface` and manually orchestrate the three-step flow:

```
// Step 1 — get AST client data
let astClientData = await getAstClientData(tenantId: tenantId)
// Step 2 — get authorization code; SDK calls provideCredentials on a background thread
let authorizationCode = await getAuthorizationCode(
clientId: clientId,
astClientDataInfo: .init(astClientData: astClientData)
)
// Step 3 — pass authorization code to MC-SDK
let authorizationCodeResult = await setAuthorizationCode(
tenantId: tenantId,
authCode: authorizationCode,
authMode: .no,
clientId: clientId
)
// Step 4 - Handle the Result
handle(authorizationCodeResult)
...
// Functions implementing the steps
/// Requests AST client data required to obtain an authorization code.
///
/// - Parameter tenantId: Tenant identifier used to build the `KSMGetAstClientDataEvent`.
/// - Returns: `KSMGetAstClientDataResultEvent` containing AST client data and challenge information.
func getAstClientData(tenantId: String) async -> KSMGetAstClientDataResultEvent {
let event = KSMGetAstClientDataEvent(tenantId: tenantId)
let result = await masterController.receive(event) as! KSMGetAstClientDataResultEvent
return result
}
/// Requests an authorization code from the IDP SDK.
///
/// - Parameters:
///   - clientId: Client identifier used in the IDP authorization request.
///   - astClientDataInfo: AST client data required by the IDP SDK to build the request.
/// - Returns: Authorization code returned by the IDP SDK, or an empty string if no code is provided.
func getAuthorizationCode(clientId: String, astClientDataInfo: AstClientDataInfo) async -> String {
await withCheckedContinuation { continuation in
idpSdk.getAuthorizationCode(
withAstClientData: astClientDataInfo,
clientId: clientId,
interactionInterface: self,
userId: nil,
traceParent: ""
) { result in
if let code = result.authorizationCode {
continuation.resume(returning: code)
} else {
continuation.resume(returning: "")
}
}
}
}
/// Submits the authorization code to MC-SDK.
///
/// - Parameters:
///   - tenantId: Tenant identifier used to build the `KSMSetAuthorisationCodeEvent`.
///   - authCode: Authorization code received from the IDP SDK.
///   - authMode: Authentication mode used when submitting the authorization code.
///   - clientId: Client identifier associated with the authorization request.
/// - Returns: `KSMSetAuthorisationCodeResultEvent` describing the outcome of the operation.
func setAuthorizationCode(
tenantId: String,
authCode: String,
authMode: KSMAuthenticationMode,
clientId: String
) async -> KSMSetAuthorisationCodeResultEvent {
let event = KSMSetAuthorisationCodeEvent(
tenantId: tenantId,
authenticationMode: authMode,
authorisationCode: authCode,
clientId: clientId
)
let result = await masterController.receive(event) as! KSMSetAuthorisationCodeResultEvent
return result
}
```

Implement the credential callback:

```
// Called from a background thread — must be thread-safe.
// Any access to shared state in this scope must be synchronized.
extension IdpHandler: IdpSdkInteractionInterface {
/// Provides credentials when requested by the IDP SDK interaction flow.
///
/// - Parameter interactionData: Additional interaction context provided by the IDP SDK.
/// - Returns: Credential container built from `credentials`.
func provideCredentials(_ interactionData: IdpSdkInteractionData) -> IdpSdkProvideCredentialsResult {
.init(credentials: ["username"       : username,
"password"       : password,
"activation-code": activationCode]
)
}
}
```

---

## Login Flow

### Before (KSSIDP)")

```
kssIdp.login(clientId: "KssIdpLogin",
authMode: authMode,
credentials: ["username"       : username,
"password"       : password,
"activation-code": activationCode],
parentSpan: parentSpan) { _, newResultObject in
self.handleNewResult(newResultObject: newResultObject)
}
```

### After (IdpSdk)")

Same three-step flow as activation, using `"KssIdpLogin"` as the `clientId`. The `provideCredentials` callback will receive `USERNAME` and `PASSWORD` fields only (no `ACTIVATION_CODE`).

See [Login](shift-lite-idpsdk__development__idpsdk__idpsdk-login.md) for the full implementation.

---

## Result Handling

### Before (KSSIDP)")

```
/// Example handler processing the result of `KSMSetAuthorisationCodeEvent`.
///
/// - Parameter result: Result event returned by MC-SDK after submitting the authorization code.
func handle(_ result: KSMSetAuthorisationCodeResultEvent) {
if result.status == .KSMOK {
/* success */
} else {
/* error */
}
}
```

### After (IdpSdk)")

Results come from two places:

1. **`IdpSdkResult`** from `getAuthorizationCode` — check `idpResult.hasError()` / `idpResult.idpSdkError`.
2. **`SetAuthorisationCodeResultEvent`** from the MC-SDK — check `result.status == StatusType.OK`.

---

## Cancelling a Flow

### Before (KSSIDP)")

Not applicable — the flow was handled internally.

### After (IdpSdk)")

Return an error from `provideCredentials` to cancel the flow:

```
let error: IdpSdkError = .init(subsystem, errorCode, "User cancelled")
return .init(error: error)
```
