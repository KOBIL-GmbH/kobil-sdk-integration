> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/idpsdk/idpsdk-kssidp-migration-android> on 2026-09-28. Converted to Markdown; wording unchanged.

# Migration from KSSIDP (Android/Kotlin)

This guide describes the changes required to migrate an Android/Kotlin application from the **KSSIDP wrapper** (`com.kobil.kssidp`) to the **IdpSdk** (`IdpSdkNativeInterface`).

---

## Overview of Differences

|  | KSSIDP | IdpSdk |
| --- | --- | --- |
| Initialization | `KssIdp.init(application, config)` | `IdpSdkNativeInterface.initIdpSdk(...)` |
| MC event handling | Internal — KSSIDP handles `GetAstClientDataEvent` etc. | Manual — app orchestrates all MC events |
| Credential passing | Passed upfront as `HashMap` to the method call | Provided via `provideCredentials` callback |
| Result handling | `KssIdpResultObject` via listener or lambda | `CompletableFuture<IdpSdkResult>` + `SetAuthorisationCodeResultEvent` |

---

## Initialization

### Before (KSSIDP)")

```
// Register listeners
KssIdp.setOnResultReceivedListener(this)
KssIdp.addEventListener(this)
// Build config
val kssIDPConfig = KssIdpConfig(
certificatePath = trustedSslServerCerts,
baseUrl = serverUrl,
tenantId = tenantId,
shouldHashPin = true,
shouldKssIdpHandleTms = false
)
// Initialize
KssIdp.init(application, kssIDPConfig)
```

### After (IdpSdk)")

```
class IdpSdkApp : Application() {
override fun onCreate() {
super.onCreate()
val certificateChain = assets.open(CERT_FILE).use { it.readBytes() }
IdpSdkNativeInterface.initIdpSdk(TENANT_ID, IDP_URL, certificateChain, false)
}
}
```

Key changes:

* No listener registration required.
* `certificatePath` (String) is replaced by `certificateChain` (ByteArray) loaded directly from assets.
* `baseUrl` / `serverUrl` is now passed as `idpUrl` directly to `initIdpSdk`.
* `KssIdpConfig` is removed entirely.

---

## MC Event Handler

### Before (KSSIDP)")

KSSIDP registered its own event listener via `KssIdp.addEventListener(this)` using `com.kobil.kssidp.wrapper.masterController.EventListener`. The KSSIDP wrapper internally handled `GetAstClientDataEvent`, `CreateHttpCommonRequestEvent`, and `SetAuthorisationCodeEvent` — the app only called a single method.

### After (IdpSdk)")

You handle all MC events yourself using a `SynchronousEventHandler`. See [Communication with the MasterController](shift-lite-idpsdk__development__master-controller-handler.md) for implementation details.

> **Note:** `KssIdp.addEventListener` and `KssIdp.setOnResultReceivedListener` calls should be removed. The `SynchronousEventHandler` of the MC-SDK replaces KSSIDP's event listener.

---

## Activation Flow

### Before (KSSIDP)")

```
// Pass all credentials upfront — KSSIDP handles MC events internally
KssIdp.getInstance()?.activate(
clientId = "KssIdpEnrollment",
authMode = authMode,
credentials = hashMapOf(
"username"        to username,
"password"        to password,
"activation-code" to activationCode
),
traceParent = optionalTraceParent
) { result ->
handleResult(result)
}
```

### After (IdpSdk)")

Credentials are no longer passed upfront. Instead, implement `IdpSdkInteractionInterface` and manually orchestrate the three-step flow:

```
// Step 1 — get AST client data
MasterController.getInstance()?.postEvent(GetAstClientDataEvent(TENANT_ID))?.then { result ->
val astClientDataInfo = AstClientDataInfo(
result.clientData, result.astClientId,
result.codeChallenge, result.codeChallengeMethod
)
// Step 2 — get authorization code; SDK calls provideCredentials on a background thread
IdpSdkNativeInterface.getAuthorizationCode(
astClientDataInfo,
"KssIdpEnrollment",
interactionInterface,   // IdpSdkInteractionInterface implementation
userId,                 // null if no user activated/enrolled on App client ("AstClient") yet
traceParent
)?.thenApply { idpResult ->
if (idpResult.hasError()) return@thenApply
// Step 3 — pass authorization code to MC
MasterController.getInstance()?.postEvent(
SetAuthorisationCodeEvent(TENANT_ID, AuthenticationMode.BIOMETRIC,
idpResult.authorizationCode, "KssIdpEnrollment")
)
}
}
```

Implement the credential callback:

```
// Called from a background thread — must be thread-safe.
// Any access to shared state in this scope must be synchronized.
override fun provideCredentials(interactionData: IdpSdkInteractionData): IdpSdkProvideCredentialsResult {
val credentials = HashMap<String?, String?>()
for (fieldId in interactionData.inputFieldIds) {
when (fieldId) {
IdpSdkConstants.USERNAME        -> credentials[fieldId] = username
IdpSdkConstants.PASSWORD        -> credentials[fieldId] = password
IdpSdkConstants.ACTIVATION_CODE -> credentials[fieldId] = activationCode
}
}
return IdpSdkProvideCredentialsResult(credentials)
}
```

---

## Login Flow

### Before (KSSIDP)")

```
KssIdp.getInstance()?.login(
clientId = "KssIdpLogin",
authMode = authMode,
credentials = hashMapOf(
"username" to username,
"password" to password
),
traceParent = optionalTraceParent
) { result ->
handleResult(result)
}
```

### After (IdpSdk)")

Same three-step flow as activation, using `"KssIdpLogin"` as the `clientId`. The `provideCredentials` callback will receive `USERNAME` and `PASSWORD` fields only (no `ACTIVATION_CODE`).

See [Login](shift-lite-idpsdk__development__idpsdk__idpsdk-login.md) for the full implementation.

---

## Result Handling

### Before (KSSIDP)")

```
override fun onResultReceived(result: KssIdpResultObject) {
when (result.status) {
is KssIdpStatusSuccess -> { /* success */ }
is KssIdpStatusRequestFailed -> { /* error */ }
is KssIdpStatusEventFailed -> { /* error */ }
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
val error = IdpSdkError(subsystem, errorCode, "User cancelled")
return IdpSdkProvideCredentialsResult(error)
```

---

## Dependencies

Add the IdpSdk AAR to your `build.gradle`:

```
debugImplementation(
name = "idpsdk-debug", ext = "aar",
group = "com.kobil", version = "0.7.2973720"
)
releaseImplementation(
name = "idpsdk-release", ext = "aar",
group = "com.kobil", version = "0.7.2973720"
)
```

Once migration is complete, remove the KSSIDP dependency:

```
// Remove:
implementation("com.kobil:kssidp:x.y.z")
```
