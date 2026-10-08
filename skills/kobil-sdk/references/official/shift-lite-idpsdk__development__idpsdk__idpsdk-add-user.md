> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/idpsdk/idpsdk-add-user> on 2026-09-28. Converted to Markdown; wording unchanged.

# Add User

Adding a user is not a distinct flow — it is the [Activation](shift-lite-idpsdk__development__idpsdk__idpsdk-activation.md) flow performed when at least one user is already enrolled on the device. You can identify this situation by the `sdkState` in the `StartResultEvent`: when another user is already activated, the state will be **LOGIN\_REQUIRED** rather than **ACTIVATION\_REQUIRED**. Performing an activation in this state enrolls an additional user.

Before proceeding, you must obtain an activation code for the new user. Refer to the [User Activities API](shift-lite-idpsdk__idp__postman_usage__postman_user_activities.md) documentation for step-by-step instructions on generating this activation code for testing purposes.

---

## IdpSdk Add User Flow Diagram

The event flow diagram illustrates the sequence of events during the add user process when using the IdpSdk directly.

![](https://www.plantuml.com/plantuml/png/VLBBRkCm3BpxAtXC0ES7YaNHmaqBOUjjcY2t00jMOc8X2cb8TDBThr_OUTLniJTH8cT6mtb8Yb6RNSXgZEgjhv4LbgPNbaMlDAvUk6sMBGrC9lUmD707HKLs2ybj5ufA86jOjC1pIarGcEw9DLynlBwzc5-_vzFtfPbFdy2l0LcqeWXDeWW-0OP8wFu0MlLxL79dchA0EvX9KdWXVKnQ14-iJwZOeO-K65cD6sTbSTKrfrGBkmG7hzLWyYYlcr_no5xkSy1pct4vM75KL1W2yOPkofAq4ZVkco6SD3PMeSTcU2tdlgE7RI-601lInqOhYVulgXSknD48RsTpi1T9dfLYwv6mQOzhj9Ht9hQl6j7I32EnZhCJrKLT7MNl7HMH7B5w36dq1Qqb6uF543xGRbSy_Qp9QkgW6NUKGuqf7IIw_BmZBpnfFHdyRKxQH3xLim7jqVsHlTuCnHQogmCfVWHwRhI9zEFOSPozXqX9mfvE-yLR4uVXMLoiJfUkVe3o3gOKH_aGyBg3_-NiEv8lMSimA9XdI8hQf3RrRpzx0Pf5iKGELE1LDfuXsKZ4815I9GSWZX82kMuhAIDssGEnQtRX7m00)

---

## Implementation Examples

### iOS/Swift

Adding a user reuses the same `IdpSdkHandler` pattern as activation. The SDK calls `provideCredentials` with the required input fields via `interactionData.inputFieldIds` — iterate over them and return a `Dictionary` with the filled values.

> **Warning:** `provideCredentials` is called from a separate thread. Your implementation must be thread-safe; any access to shared state in this scope must be synchronized. It may also be called multiple times in multi-step flows. See [provideCredentials Behaviour](shift-lite-idpsdk__development__idpsdk__idpsdk-overview.md#providecredentials-behaviour) for details on field IDs, multi-step flows, and error propagation.

IdpSdkInteractionInterface — provideCredentials (iOS/Swift)

```
extension IdpHandler: IdpSdkInteractionInterface {
/// Provides credentials when requested by the IDP SDK interaction flow.
///
/// - Parameter interactionData: Additional interaction context provided by the IDP SDK.
/// - Returns: Sample credential container.
func provideCredentials(_ interactionData: IdpSdkInteractionData) -> IdpSdkProvideCredentialsResult {
// To cancel the flow and propagate an error, create the error and return it:
//   let error: IdpSdkError = .init(subsystem, errorCode, , errorDescription)
//   return .init(error: error)
.init(credentials: ["username"       : username,
"password"       : password,
"activation-code": activationCode]
)
}
}
```

The full three-step activation flow:

Add User Flow (iOS/Swift)

```
func addUser() {
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
}
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
// userId must be the already enrolled user's userId, so the SDK can
// assicuate the new enrollment with the existing device binding.
await withCheckedContinuation { continuation in
idpSdk.getAuthorizationCode(
withAstClientData: astClientDataInfo,
clientId: clientId,
interactionInterface: self,
userId: userId,
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
/// Submits the authorization code to MCSDK.
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

### Android/Kotlin

Adding a user reuses the same `IdpSdkInteractionInterface` pattern as activation. The SDK calls `provideCredentials` with the required input fields via `interactionData.inputFieldIds` — iterate over them and return a `HashMap` with the filled values.

> **Warning:** `provideCredentials` is called from a separate thread. Your implementation must be thread-safe; any access to shared state in this scope must be synchronized. It may also be called multiple times in multi-step flows. See [provideCredentials Behaviour](shift-lite-idpsdk__development__idpsdk__idpsdk-overview.md#providecredentials-behaviour) for details on field IDs, multi-step flows, and error propagation.

IdpSdkInteractionInterface — provideCredentials for Add User (Kotlin)

```
class AddUserHandler {
companion object : IdpSdkInteractionInterface {
const val ENROLLMENT_CLIENT = "KssIdpEnrollment"
// Called by the SDK from a background thread to collect new user's credentials.
// Must be thread-safe.
override fun provideCredentials(interactionData: IdpSdkInteractionData): IdpSdkProvideCredentialsResult {
val credentials = HashMap<String?, String?>()
for (fieldId in interactionData.inputFieldIds) {
when (fieldId) {
IdpSdkConstants.USERNAME        -> credentials[fieldId] = "<new-username>"
IdpSdkConstants.PASSWORD        -> credentials[fieldId] = "<new-password>"
IdpSdkConstants.ACTIVATION_CODE -> credentials[fieldId] = "<activation-code>"
}
}
// To cancel the flow and propagate an error, return:
// IdpSdkProvideCredentialsResult(IdpSdkError(subsystem, errorCode, errorDescription))
return IdpSdkProvideCredentialsResult(credentials)
}
}
}
```

The full three-step add user flow:

Add User Flow (Android/Kotlin)

```
fun addUser() {
// Step 1 — get AST client data from the MC-SDK
val getAstClientDataEvent = GetAstClientDataEvent(IdpSdkApp.TENANT_ID)
MasterController.getInstance()?.postEvent(getAstClientDataEvent)?.then { resultEvent ->
when (resultEvent) {
is GetAstClientDataResultEvent -> {
if (resultEvent.status != StatusType.OK) {
Log.e(TAG, "GetAstClientData failed: ${resultEvent.errorDescription}")
return@then
}
// Step 2 — get authorization code from the IdpSdk
val astClientDataInfo = AstClientDataInfo(
resultEvent.clientData,
resultEvent.astClientId,
resultEvent.codeChallenge,
resultEvent.codeChallengeMethod
)
// Pass the existing enrolled user's userId so the SDK can associate
// the new enrollment with the existing device binding.
// Pass null if this is the very first user on the device.
val userId: String? = StartRestartHandler.getFirstUserId()
IdpSdkNativeInterface.getAuthorizationCode(
astClientDataInfo,
ENROLLMENT_CLIENT,
this,       // IdpSdkInteractionInterface — provideCredentials called here
userId,
traceParent // optional W3C-compliant trace parent, or null
)?.thenApply { idpSdkResult ->
if (idpSdkResult.hasError()) {
Log.e(TAG, "getAuthorizationCode failed: ${idpSdkResult.idpSdkError}")
return@thenApply
}
// Step 3 — pass the authorization code to the MC-SDK
val authorizationCode = idpSdkResult.authorizationCode
val setEvent = SetAuthorisationCodeEvent(
IdpSdkApp.TENANT_ID,
AuthenticationMode.BIOMETRIC,
authorizationCode,
ENROLLMENT_CLIENT
)
MasterController.getInstance()?.postEvent(setEvent)?.then { setResult ->
when (setResult) {
is SetAuthorisationCodeResultEvent -> {
if (setResult.status == StatusType.OK) {
Log.i(TAG, "Add user successful")
} else {
Log.e(TAG, "SetAuthorisationCode failed: ${setResult.errorDescription}")
}
}
else -> error("Unexpected result for SetAuthorisationCodeEvent")
}
}
}
}
else -> error("Unexpected result for GetAstClientDataEvent")
}
}
}
```

---

## Request Parameters

The following credential fields are requested by the IdpSdk during add user via `provideCredentials`:

```
IdpSdkConstants.USERNAME        — the new user's username
IdpSdkConstants.PASSWORD        — the new user's desired password
IdpSdkConstants.ACTIVATION_CODE — the one-time activation code for the new user
```

The `clientId` passed to `getAuthorizationCode` is provided by the KOBIL IDP services (e.g. `KssIdpEnrollment`).

---

## Important Notes

> For more information about MC-SDK event usage during IdpSdk flows, please refer to [GetAstClientData](shift-lite-idpsdk__mcsdk-api__ast_event_list.md) and [SetAuthorisationCode](shift-lite-idpsdk__mcsdk-api__ast_event_list.md#ast-client-management).

## Response Handling (iOS/Swift)")

`IdpSdkService`'s `getAuthorizationCode` returns an `IdpSdkResult`. Check its `hasError()` function before accessing its member `authorizationCode`.

In response to the `KSMSetAuthorisationCodeEvent`, the MC-SDK sends a `KSMSetAuthorisationCodeResultEvent` with the appropriate **status**.

## Response Handling (Android/Kotlin)")

`IdpSdkNativeInterface.getAuthorizationCode` returns a `CompletableFuture<IdpSdkResult>`. Check `idpSdkResult.hasError()` before accessing `idpSdkResult.authorizationCode`.

In response to the `SetAuthorisationCodeEvent`, the MC-SDK sends a `SetAuthorisationCodeResultEvent` with the appropriate **status**.
