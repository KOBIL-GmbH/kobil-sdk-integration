> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/idpsdk/idpsdk-initialization> on 2026-09-28. Converted to Markdown; wording unchanged.

# Initialization of the IdpSdk

The IdpSdk initialization process involves setting up the necessary configurations and initializing the `IdpSdkNativeInterface`.

## Dependency (on Android)")

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

---

## Prerequisites

Ensure you have the following available before initializing:

* **tenantId**: The identifier for your IDP tenant.
* **idpUrl**: The base URL of the IDP server.
* **certificateChain**: The trusted SSL certificate as a byte array, loaded from your assets.

---

## iOS/Swift

Initializing IdpSdk (iOS/Swift)

```
class IdpHandler: NSObject {
let idpSdk: IdpSdkService
init(
certificate: Data,
baseUrl: String,
tenantId: String,
) {
self.idpSdk = .init(
tenantId: tenantId,
idpUrl: baseUrl,
certificateChain: certificate,
shouldHashPin: false
)
}
}
```

> **NOTE:** The IdpSdk must be initialized via `init` before calling any other IdpSdk method.

---

## Android/Kotlin

Initializing IdpSdk (Android/Kotlin)

```
class IdpSdkApp : Application() {
companion object {
const val TENANT_ID = "your-tenant-id"
const val IDP_URL   = "https://your-idp-server.example.com"
const val CERT_FILE = "your-certificate.crt"
}
override fun onCreate() {
super.onCreate()
val certificateChain = assets.open(CERT_FILE).use { it.readBytes() }
// initIdpSdk(tenantId, idpUrl, certificateChain, shouldHashPin)
IdpSdkNativeInterface.initIdpSdk(TENANT_ID, IDP_URL, certificateChain, false)
}
}
```

> **NOTE:** The IdpSdk must be initialized via `initIdpSdk` before calling any other IdpSdk method.

---

## Master Controller Setup

The IdpSdk relies on the MC-SDK to exchange events with the server. Before using any IdpSdk flow you must:

1. On iOS: **Set up a `KSAsyncEventReceiver`** — this is your communication channel with the Master Controller. See [Initialization of the MasterController](shift-lite-idpsdk__development__initialization.md) and [Implement MasterController interface](shift-lite-idpsdk__development__implement-interface.md) for implementation details.  
   On Android: **Set up a `SynchronousEventHandler`** — this is your communication channel with the Master Controller. See [Communication with the MasterController](shift-lite-idpsdk__development__master-controller-handler.md) for implementation details.
2. **Trigger a `StartEvent`** — this initialises the MC-SDK session and returns a `StartResultEvent` containing the `sdkState` that tells you whether activation or login is required. See [Start/Restart Event](shift-lite-idpsdk__development__start.md) for details.

> **NOTE:** MC-SDK events such as `GetAstClientDataEvent` and `SetAuthorisationCodeEvent` will fail if a `StartEvent` has not been successfully completed first.

---

## Authorization Flow

After both the IdpSdk and MC-SDK are initialised, all IdpSdk operations (activation, login, change PIN, forgot PIN) share the same three-step flow with the MC-SDK:

1. **Get AST client data** — post a `GetAstClientDataEvent` to the MC-SDK and receive a `GetAstClientDataResultEvent`. Use the result to construct an `AstClientDataInfo` object.
2. **Get authorization code** — call the relevant `IdpSdkNativeInterface` method (e.g. `getAuthorizationCode`). The SDK calls back your `IdpSdkInteractionInterface.provideCredentials` implementation to collect user credentials.
3. **Set authorization code** — post a `SetAuthorisationCodeEvent` to the MC-SDK with the received authorization code (not required for `changePin` / `forgotPin`).

See the individual flow pages for full implementation details:

* [Activation](shift-lite-idpsdk__development__idpsdk__idpsdk-activation.md)
* [Login](shift-lite-idpsdk__development__idpsdk__idpsdk-login.md)
* [Add User](shift-lite-idpsdk__development__idpsdk__idpsdk-add-user.md)
