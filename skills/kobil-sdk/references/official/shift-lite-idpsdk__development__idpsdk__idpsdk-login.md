> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/idpsdk/idpsdk-login> on 2026-09-28. Converted to Markdown; wording unchanged.

# Login

When a `StartResultEvent` with **LOGIN\_REQUIRED** as `sdkState` is received in response to a `StartEvent`, you should initiate the Login flow.

> **Note:** When `LOGIN_REQUIRED` is received after a restart, there are two valid approaches:
>
> * **Stay Logged In (`OfflineLoginEvent`)**: if a valid offline or authorization-grant token is stored, post an `OfflineLoginEvent` to re-authenticate without requiring credentials. See [Stay Logged In](shift-lite-idpsdk__development__stay-logged-in.md).
> * **Fresh IDP login**: perform a full login using `getAuthorizationCode` as described below.
>
> There is no way to determine in advance which will succeed — `LOGIN_REQUIRED` only confirms the user is activated on the app client, not whether valid tokens are still present. The recommended approach is to attempt `OfflineLoginEvent` first; if it returns a status other than `StatusType.OK`, fall back to a fresh IDP login using the same `AuthenticationMode`.

This involves calling `IdpSdkNativeInterface.getAuthorizationCode` and supplying the user's **username** and **password** via the `IdpSdkInteractionInterface` callback. Follow the three-step flow in the correct sequence to ensure a successful login.

> **Note on Multi-Step Flows:** IDP flows can be configured with multiple steps. The `provideCredentials` callback may be invoked more than once during a single login, with each call requesting different credential fields. For example: step 1 might request only username, step 2 might request a security question answer, and step 3 might request password. Your implementation must handle these multiple calls gracefully. See [provideCredentials Behaviour](shift-lite-idpsdk__development__idpsdk__idpsdk-overview.md#providecredentials-behaviour) for details.

---

## IdpSdk Login Flow Diagram

The event flow diagram illustrates the sequence of events during the login process when using the IdpSdk directly.

![](https://www.plantuml.com/plantuml/png/VLBBRjim4BphA_Pe0yeF14MGG75IebNZol3DGB4XrpPXQYbmbqxHho_aPsGLlMd9sPdXQ1v5CMbkGz5XKczzXwomD8EnhWQZSTt2xOfYQU3kxW6M1kwXsfBTWRZTGb49uXeMFN53aeF2R4-ivOe1HNBhUGDUmGjyVtirFturivzBqyoUpuHr1VSmZwBmIleaMWLFhC-eUE2PA36o6ZSjwkhge27f8Zk13w_RqURHo65_nHDxEIy1pp3ZIh3HKRN548WtT3FMfDlefiDdHnPDsIeCr0olunbtJAl7OWYm8NtAket9_q7raQleQ8AtkoNOYoNFIWbj3pRzvnejbP25Kd-h2ItDCH7hj3X9NTnrAUwzeogH8rQFGIQVs7gnALWCuHtjRiMptnrPbGCrOqibT2Zo4PCRFQKXpObFytoaSWnxOgydOszLRBj0Yk-1NhBcH5-EYEFk0oII6FPq-fruczcuAujBid913VjI7cZgwAWS4ruZ_r-j_YNogLe51WNp0gAeMVg6ltqRz6MUeYLoe16-nfP0R2BYWjWLZyGkj-4l)

---

## Implementation Examples

### iOS/Swift

Implement `IdpSdkInteractionInterface` to supply credentials when the SDK requests them. The SDK calls `provideCredentials` with the required input fields via `interactionData.inputFieldIds` — iterate over them and return a `HashMap` with the filled values.

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
func login() {
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
// userId must be the userId of the (existing) user that we want to log in.
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

> **NOTE:** The `userId` passed to `getAuthorizationCode` during login should be the enrolled user's identifier, obtained from the `StartResultEvent` or `RestartResultEvent` user list.

### Android/Kotlin

Implement `IdpSdkInteractionInterface` to supply credentials when the SDK requests them. The SDK calls `provideCredentials` with the required input fields via `interactionData.inputFieldIds` — iterate over them and return a `HashMap` with the filled values.

> **Warning:** `provideCredentials` is called from a separate thread. Your implementation must be thread-safe; any access to shared state in this scope must be synchronized. It may also be called multiple times in multi-step flows. See [provideCredentials Behaviour](shift-lite-idpsdk__development__idpsdk__idpsdk-overview.md#providecredentials-behaviour) for details on field IDs, multi-step flows, and error propagation.

IdpSdkInteractionInterface — provideCredentials (Kotlin)

```
class LoginHandler {
companion object : IdpSdkInteractionInterface {
const val LOGIN_CLIENT = "KssIdpLogin"
// Called by the SDK from a background thread to collect user credentials.
// Must be thread-safe.
override fun provideCredentials(interactionData: IdpSdkInteractionData): IdpSdkProvideCredentialsResult {
val credentials = HashMap<String?, String?>()
for (fieldId in interactionData.inputFieldIds) {
when (fieldId) {
IdpSdkConstants.USERNAME -> credentials[fieldId] = "<username>"
IdpSdkConstants.PASSWORD -> credentials[fieldId] = "<password>"
}
}
// To cancel the flow and propagate an error, return:
// IdpSdkProvideCredentialsResult(IdpSdkError(subsystem, errorCode, errorDescription))
return IdpSdkProvideCredentialsResult(credentials)
}
}
}
```

The full three-step login flow:

Login Flow (Android/Kotlin)

```
fun login() {
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
// userId is the identifier of the enrolled user (from StartResultEvent)
val userId: String? = StartRestartHandler.getFirstUserId()
IdpSdkNativeInterface.getAuthorizationCode(
astClientDataInfo,
LOGIN_CLIENT,
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
LOGIN_CLIENT
)
MasterController.getInstance()?.postEvent(setEvent)?.then { setResult ->
when (setResult) {
is SetAuthorisationCodeResultEvent -> {
if (setResult.status == StatusType.OK) {
Log.i(TAG, "Login successful")
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

> **NOTE:** The `userId` passed to `getAuthorizationCode` during login should be the enrolled user's identifier, obtained from the `StartResultEvent` or `RestartResultEvent` user list.

---

## Request Parameters

The following credential fields are requested by the IdpSdk during login via `provideCredentials`:

```
IdpSdkConstants.USERNAME — the user's username
IdpSdkConstants.PASSWORD — the user's password
```

The `clientId` passed to `getAuthorizationCode` is provided by the KOBIL IDP services (e.g. `KssIdpLogin`).

---

## Important Notes

> For more information about MC-SDK event usage during IdpSdk flows, please refer to [GetAstClientData](shift-lite-idpsdk__mcsdk-api__ast_event_list.md) and [SetAuthorisationCode](shift-lite-idpsdk__mcsdk-api__ast_event_list.md#ast-client-management).

## Response Handling (iOS/Swift)")

`IdpSdkNativeInterface.getAuthorizationCode` returns a `CompletableFuture<IdpSdkResult>`. Check `idpSdkResult.hasError()` before accessing `idpSdkResult.authorizationCode`.

In response to the `SetAuthorisationCodeEvent`, the MC-SDK sends a `SetAuthorisationCodeResultEvent` with the appropriate **status**.

## Response Handling (Android/Kotlin)")

`IdpSdkNativeInterface.getAuthorizationCode` returns a `CompletableFuture<IdpSdkResult>`. Check `idpSdkResult.hasError()` before accessing `idpSdkResult.authorizationCode`.

In response to the `SetAuthorisationCodeEvent`, the MC-SDK sends a `SetAuthorisationCodeResultEvent` with the appropriate **status**.
