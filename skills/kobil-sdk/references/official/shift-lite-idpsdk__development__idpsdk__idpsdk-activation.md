> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/idpsdk/idpsdk-activation> on 2026-09-28. Converted to Markdown; wording unchanged.

# Activation

Before proceeding with activation, users must obtain an activation code. For testing purposes this can be done via a REST API. Refer to the [User Activities API](shift-lite-idpsdk__idp__postman_usage__postman_user_activities.md) documentation for step-by-step instructions on generating this activation code.

When a `StartResultEvent` with **ACTIVATION\_REQUIRED** as `sdkState` is received in response to the `StartEvent`, users should initiate the Activation flow.

This involves calling `idpSdk.getAuthorizationCode` (iOS/Swift) or `IdpSdkNativeInterface.getAuthorizationCode` (Android/Kotlin) with the user's **username**, **activation code**, and **password** provided through the `IdpSdkInteractionInterface` callback. Follow the three-step flow in the correct sequence for a successful activation.

> **Note on Multi-Step Flows:** IDP flows can be configured with multiple steps. The `provideCredentials` callback may be invoked more than once during a single activation, with each call requesting different credential fields. For example: step 1 might request only username, step 2 might request activation code, and step 3 might request password. Your implementation must handle these multiple calls gracefully. See [provideCredentials Behaviour](shift-lite-idpsdk__development__idpsdk__idpsdk-overview.md#providecredentials-behaviour) for details.

> **Note:** In Shift Lite, activation is already a login process — a `StartLoginEvent` will not be triggered after a completed activation. Once activation completes with `StatusType.OK`, the user is both activated and logged in with a valid token set. A login will be required again after an app restart, an MC-SDK restart, or when stored tokens have been cleared — however, a restart is not a full logout: the full token set received at activation enables the [Stay Logged In](shift-lite-idpsdk__development__stay-logged-in.md) feature (`OfflineLoginEvent`), which can re-authenticate the user as long as valid tokens are still present — either silently (no authentication required) or by prompting for biometrics, depending on the configured `AuthenticationMode`. See [Login](shift-lite-idpsdk__development__idpsdk__idpsdk-login.md) for post-restart flow options (see also [Restart Event](shift-lite-idpsdk__development__start.md#restartevent) and [Logout](shift-lite-idpsdk__development__logout_digitanium+_shift.md)).

---

## IdpSdk Activation Flow Diagram

The event flow diagram illustrates the sequence of events during the activation process when using the IdpSdk directly.

![](https://www.plantuml.com/plantuml/png/VL9TRnen47o_Nx6F81r_8AgYe0kfh8Q4GkWJKhMn5x0mwvDtJQh--keuFd9SrBTRt-pCU3mFefWqxqDHOr9lVOsii3ITSLfrHkFgXTiLnTB0Q7GFImDtK6t9xa3SRg6e174DYuPuJfA3mkH0hEMA0KNotlC6l88N65TlvjVupRo-_9vFVYxDVF9uPfrMS0UpA0hVISUYLV34-eYAHxA14YEhSSDYMbrjp4dgo4xWm-ksjzcwEUwlU60lvoNW6MPS2JOwghOO0l66RiOfwJQwOVVkaKLJjWeTDSFhUCQraJLO304sfEEisvZyNrGVkOgE1dYxMuAzMFAibD0sODDyhj5I2LaeDNyreQKP9c8T5YUfYxiwnODtL2LonEenoE0JMoCs18iXlAFThNZofoQhSgHct5C9DOfynEHAQ3OEHyEZ9fFUtUQaEV5fdlLas_G7zdhIDrl5VHr8yJtGKzQSw5kBQ7Vl8P74SA3J--9jYFtoB2vHomNLBL1vf9b6HsMVyFe6_-lPLoAVkbPWK31F88gQfUdzwuzEWMOfMY876k4vRZo3s4J41R4h7eXTteT_)

---

## Implementation Examples

### iOS/Swift

Implement `IdpSdkInteractionInterface` to supply credentials when the SDK requests them. The SDK calls `provideCredentials` with the required input fields via `interactionData.inputFieldIds` — iterate over them and return a `Dictionary` with the filled values.

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

Activation Flow (iOS/Swift)

```
func activate() {
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
// userId is nil for first activation (no user enrolled yet)
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

Implement `IdpSdkInteractionInterface` to supply credentials when the SDK requests them. The SDK calls `provideCredentials` with the required input fields via `interactionData.inputFieldIds` — iterate over them and return a `HashMap` with the filled values.

> **Warning:** `provideCredentials` is called from a separate thread. Your implementation must be thread-safe; any access to shared state in this scope must be synchronized. It may also be called multiple times in multi-step flows. See [provideCredentials Behaviour](shift-lite-idpsdk__development__idpsdk__idpsdk-overview.md#providecredentials-behaviour) for details on field IDs, multi-step flows, and error propagation.

IdpSdkInteractionInterface — provideCredentials (Android/Kotlin)

```
class ActivationHandler {
companion object : IdpSdkInteractionInterface {
const val ACTIVATION_CLIENT = "KssIdpEnrollment"
// Called by the SDK from a background thread to collect user credentials.
// Must be thread-safe.
override fun provideCredentials(interactionData: IdpSdkInteractionData): IdpSdkProvideCredentialsResult {
val credentials = HashMap<String?, String?>()
for (fieldId in interactionData.inputFieldIds) {
when (fieldId) {
IdpSdkConstants.USERNAME        -> credentials[fieldId] = "<username>"
IdpSdkConstants.PASSWORD        -> credentials[fieldId] = "<password>"
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

The full three-step activation flow:

Activation Flow (Android/Kotlin)

```
fun activate() {
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
// userId is null for first activation (no user enrolled yet)
val userId: String? = null
IdpSdkNativeInterface.getAuthorizationCode(
astClientDataInfo,
ACTIVATION_CLIENT,
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
ACTIVATION_CLIENT
)
MasterController.getInstance()?.postEvent(setEvent)?.then { setResult ->
when (setResult) {
is SetAuthorisationCodeResultEvent -> {
if (setResult.status == StatusType.OK) {
Log.i(TAG, "Activation successful")
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

The following credential fields are requested by the IdpSdk during activation via `provideCredentials`:

```
IdpSdkConstants.USERNAME        — the user's username
IdpSdkConstants.PASSWORD        — the desired password
IdpSdkConstants.ACTIVATION_CODE — the one-time activation code
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
