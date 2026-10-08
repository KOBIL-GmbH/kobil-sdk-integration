> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/start> on 2026-09-28. Converted to Markdown; wording unchanged.

# Start/Restart Event

Start Event is the initial event we need to trigger when our app starts communicating with the Master Controller. This event informs us whether the user needs to activate or log in. Additionally, it handles some configuration tasks in the background. When triggering this event, we must provide certain configuration-related information. You can find relevant details about this event [**here**](shift-lite-idpsdk__mcsdk-api__base_event.md).

In the start event, you must provide values for APP\_NAME and the app version. While you do not necessarily have to use the values provided in the samples, it is essential to configure these values in the security server. Refer to [**Add App in Security Server**](shift-lite-idpsdk__prerequisites__app-lifecycle__add-app__add_app.md) for instructions on adding a new app in your Security Server. Similarly, refer to [**Register App Version**](shift-lite-idpsdk__prerequisites__app-lifecycle__register-app-version__register_app_version.md) for registering a new app version.

Also, you must provide the language you expect to be used in [**transactions**](shift-lite-idpsdk__development__transaction.md) sent to this instance of your app. This must be a language tag as described in RFC 3066 with additional requirement:

* In KOBIL Digitanium and KOBIL Digitanium+, only two-letter primary subtags are allowed, e.g. "de" or "en" As for configuring the translation templates on the server side, see the full documentation of the ASM module available via <https://developer.kobil.com/docs/ssms-docs/ssmsgui/modules/asm-module/overview>.
* In KOBIL Shift Lite a region subtag is allowed in addition to the primary subtag (e.g. "de-DE", "de-CH", "en-GB", or "en-US"), localization templates are maintained as described in <https://developer.kobil.com/api/ast#tag/Localization>. Note that more specialized tags match more general language specifications, i.e. if the app asks for "de-DE" and the server has only "de" available, then that translation is used. However, in the opposite direction this does not work, i.e. if the app asks for "de" and the server has "de-CH" and "de-DE", then neither does match and you fall back to the default translation which might be e.g. "en".

Which language tags actually work depends on localization templates on the server side. If a suitable language is not found, transactions automatically fall back to using the translations that have been marked as the default language on the server side. In general, it is a good idea to keep the translations on the server side general, i.e. make sure to have a translation for the base language (e.g. "de"). However, we expect that most of the time there is some coordination between people developing the app and people maintaining the translation on the server side, so you should know, which languages are available and which tags to use to choose them.

### UserDetails in Result Events

The `StartResultEvent`, `RestartResultEvent`, `StartLoginEvent`, and `DeleteUserResultEvent` include an array of `UserDetails` containing information about activated users on the device.

The `UserDetails` type consists of:

| Field | Type | Description |
| --- | --- | --- |
| `userIdentifier` | UserIdentifier | The user's identifier (tenantId, userId). |
| `displayUsername` | String | The user's display username. |
| `displayEmail` | String | The user's display email. |

* `displayUsername` and `displayEmail` are updated during `SetAuthorizationCode` and `OfflineLogin` event handling (activation/login).
* `displayUsername` and `displayEmail` may be empty if the server backend is set to `ssms` or if no activation/login has been performed with this version of the SDK.

> ⚠️ **Deprecated:** The array of `UserIdentifier` parameter in `StartResultEvent`, `RestartResultEvent`, `StartLoginEvent`, and `DeleteUserResultEvent` is deprecated and will be removed in a **2026** major release. Use the array of `UserDetails` instead.

### StartLoginEvent

If you have already activated users/accounts on the device, you will receive the `StartLoginEvent` after the successful initialization of the SDK or MasterController. The `StartLoginEvent` is an information event meant to inform you that the SDK is ready for performing a login.

> **Important StartLoginEvent behavior:**
>
> * `StartLoginEvent` will **NOT** be triggered on the first app start when no user is activated yet.
> * It will **only** be triggered after a start/restart if a user is already activated.
> * Using **KOBIL Shift Lite**, it will **NOT** be triggered right after activation, because activation is already a login process — there is no point in a `StartLoginEvent` after a completed login.

#### **Start event flow-diagram**

The following diagram illustrates the Start Event and its result:

![](https://www.plantuml.com/plantuml/png/dP2zRiCm30PtFSKtjaDVm4CHmpKA0qc3Accd08LWCOuGXJ94Edtz8Z-3xIv5z-CTIRCGTLc7KpIcxFiOMgSXCPwUiNAYbAl4cbECb0kC0SsXwoWBDfVv-aoisF53OhWHTPK_chdgeX_9YbyjP98-iHTy1prWnzUA9HdYhJLTTgf3WUf0xH7YZnjrIaXxZ0Iu6OoBYh2VK9PapY48bklNvktBrkyVZQrVve-QN6B9XqojaeScB5CN6D9c8ZOKXVvIAwjjyrbkc_M_acMhuNp__htBtXYp8FR3AVu0)

#### iOS/Swift

For Swift, you can use the following snippet to trigger the Start Event.

**Note:**
The Swift code utilizes helper classes available in the sample app's code to read the configuration files and directly pass their content to the MasterController:

Triggering Start Event (Swift)

```
func startMaster(startRequest: StartRequest, assetBundle: AssetBundle? = nil, completion: @escaping (ActionResult) -> Void) {
GlobalConstats.appVersion = startRequest.appVersion
GlobalConstats.appName = startRequest.appName
let startHelper = StartHelper(assetBundle: assetBundle)
let startEvent = KSMStartEventEx(serverBackend: (GlobalConstats.mcConfig?.astServerBackend)!,
ssmsAppConfiguration: startHelper.appConfig,
mcConfig: startHelper.mcConfigString,
certificateChain: startHelper.certData,
configurationData: startHelper.configurationData)
startEvent.traceContext =   OtelTraceHandler.shared.getTraceContext(traceName: "StartEventSpan")
let timer = CallTimer(event: startEvent)
MasterControllerAdapter.sharedInstance.sendEvent2MasterController(event: startEvent) { event in
let neededTime = timer.stop()
if let startResultEvent = event as? KSMStartResultEvent {
if startResultEvent.status == .KSMOK {
completion(ActionResult(title: "Start", success: true, error: nil, duration: neededTime, event: event))
} else {
print("Start failed")
completion(ActionResult(title: "Start",
success: false,
error: "Failed with Status \(startResultEvent.status.rawValue)",
duration: neededTime, event: event))
}
} else {
print("unexpected Event")
completion(ActionResult(title: "Start",
success: false,
error: "unexpected Event",
duration: neededTime, event: event))
}
OtelTraceHandler.shared.complete(traceName: "StartEventSpan")
}
}
```

Start Helper (Swift)

```
struct StartRequest: Encodable {
var appName, appVersion: String
}
struct StartHelper {
let certData: Data
let appConfig: KSMSsmsAppConfiguration
let mcConfigString: String
let configurationData: KSMConfigurationData
init(assetBundle: AssetBundle? = nil) {
let server = assetBundle ?? MultiAssets.current
let bundlePath = server.getPath()
GlobalConstats.appConfig = AssetHelper.sharedInstance.getAppConfigMap(path: bundlePath, namespace: nil)
let dataSdkConfig = AssetHelper.sharedInstance.getSdkConfigData(path: bundlePath, namespace: nil)
mcConfigString = AssetHelper.sharedInstance.getMcConfigJsonString(path: bundlePath, namespace: nil)
GlobalConstats.mcConfig = McConfigMappable(jsonString: mcConfigString)
var versionStrings = GlobalConstats.appVersion.split(separator: ".")
if versionStrings.count < 3 {
versionStrings = ["0", "0", "1"]
}
let major = Int32(Int(versionStrings[0])!)
let minor = Int32(Int(versionStrings[1])!)
let build = Int32(Int(versionStrings[2])!)
GlobalConstats.appVersion = "\(major).\(minor).\(build)"
certData = AssetHelper.sharedInstance.getCertificateData(path: bundlePath,
namespace: nil,
name: (GlobalConstats.appConfig?.iam?.trustedSslServerCerts?.first) ?? "")
let version = KSMVersion(majorVersion: major, minorVersion: minor, build: build)
appConfig = KSMSsmsAppConfiguration(locale: "de",
version: version,
name: GlobalConstats.appName,
sdkconfig: dataSdkConfig)
configurationData = KSMConfigurationData(category: "", tagName: "")
}
}
```

#### Android/Kotlin

Triggering Start Event (Kotlin)

```
fun triggerStartEvent() {
// Step 1: Create a basic StartEvent
val startEvent = StartEvent(
LOCALE, // you can use Locale.getDefault().language
AppVersion(
BuildConfig.VERSION_MAJOR,
BuildConfig.VERSION_MINOR,
BuildConfig.VERSION_BUILD
),
APP_NAME,
Utils.getAssetAsString("${MC_CONFIG_FILE_NAME}"),
certificateChain,
Utils.getAssetAsString("${SDK_CONFIG_FILE_NAME}")?.toByteArray()
)
// Step 2: Send event using your MC instance and handle response
synchronousEventHandler.postEvent(startEvent)?.then { resultEvent ->
when (resultEvent) {
is StartResultEvent -> {
if (resultEvent.sdkState == SdkState.ACTIVATION_REQUIRED) {
// perform activation
} else if (resultEvent.sdkState == SdkState.LOGIN_REQUIRED) {
// perform login
}
}
else -> {
// handle unexpected case
}
}
}
}
```

> ***NOTE:*** You must have an assets folder with correct config files in your project folder, in order to send the correct configuration to SSMS. [**Read more in the MC Configuration files Overview**](shift-lite-idpsdk__prerequisites__mc-config-files__mc_configuration_files_overview.md)

### RestartEvent

In certain situations, you may need to restart the SDK, such as when **logging out** in KOBIL Digitanium or KOBIL Digitanium+ / KOBIL Shift Lite. Additionally, the SDK itself might initiate a restart, for instance, if it encounters a RuntimeErrorEvent.
Because most of the configuration can be retained from the previous startup of the Master Controller, we require fewer parameters compared to the Start Event. However, you still need to provide values for APP\_NAME and the app version.

> **IMPORTANT:**
> When calling RestartEvent, developers must wait for RestartResultEvent before proceeding to use any MC features. Attempting to use the SDK before initialization (StartEvent) has completed will result in errors, and the same applies for re-initialization (RestartEvent).
> ⚠️ In certain cases, such as a RuntimeError, the SDK may trigger a RestartEvent. Ensure that your app can respond to a RestartResultEvent at any time!

#### **Restart event flow-diagram**

The following diagram illustrates the Restart Event and its reply:

![](https://www.plantuml.com/plantuml/png/dT1DQiCm40NWlKxnBj0BU55YN5CCIKFLjAj04DB44L4aCpDEhr-Q7uZJHKltRxutCsOcwbZ7GpAc7eOKlTDOCXuUiN2Yn4t9oYKbuWgtWS9OD52EVKyii7HosYDbDVUJtzhDRFM31fCC9GV1PzGTrld2MP8nNT39TbCG5PeT-JqaxD_KAQ5iCI5mDenBYhZzBOSec2-VkvUDRL_VEzi-tVzcSesb49cyKe0Mp4iVCyGpKJQKXFxILZUhxgDUTSj_LTPUu_4SlFRcOCoCSXWFwGi0)

#### iOS/Swift

For Swift, you can use the following snippet to trigger the Restart Event.

Triggering Restart Event (Swift)

```
func restartMaster(assetBundle: AssetBundle? = nil, completion: @escaping (ActionResult) -> Void) {
let startHelper = StartHelper(assetBundle: assetBundle)
let restart = KSMRestartEventEx(serverBackend: (GlobalConstats.mcConfig?.astServerBackend)!,
ssmsAppConfiguration: startHelper.appConfig,
mcConfig: startHelper.mcConfigString,
certificateChain: startHelper.certData)
let traceContext = TraceContext(traceParent: GlobalConstats.uuid, traceState: "restartEvent")
restart.traceContext = traceContext
let time = CallTimer(event: restart)
MasterControllerAdapter.sharedInstance.sendEvent2MasterController(event: restart) { event in
let duration = time.stop()
if let result = event as? KSMRestartResultEvent {
if result.status == .KSMOK {
completion(ActionResult(title: "Restart",
success: true,
error: nil,
duration: duration,
event: result))
} else {
print("Start failed")
completion(ActionResult(title: "Restart",
success: false,
error: "Failed with Status \(result.status)",
duration: duration,
event: result))
}
}
}
OtelTraceHandler.shared.complete(traceName: "RestartEventSpan")
}
```

#### Android/Kotlin

In Kotlin you can trigger RestartEvent like that:

Triggering Restart Event (Kotlin)

```
fun triggerRestartEvent() {
// Step 1: Create a basic RestartEvent
val restartEvent = RestartEvent(
LOCALE, // you can use Locale.getDefault().language
AppVersion(
BuildConfig.VERSION_MAJOR,
BuildConfig.VERSION_MINOR,
BuildConfig.VERSION_BUILD
),
APP_NAME
)
// Step 2: Send event using your MC instance and handle response
synchronousEventHandler.postEvent(restartEvent)?.then { resultEvent ->
when (resultEvent) {
is RestartResultEvent -> {
if (resultEvent.sdkState == SdkState.ACTIVATION_REQUIRED) {
// perform activation
} else if (resultEvent.sdkState == SdkState.LOGIN_REQUIRED) {
// perform login
}
}
else -> {
// handle unexpected case
}
}
}
}
```

#### Flutter

Triggering StartEvent (Flutter)

```
// Step 1: Create a basic StartEvent
final version = VersionT()
..buildNo = 100
..majorVersion = 1
..minorVersion = 0
..ssmsVersionString = "1.0.0";
final startEvent = StartEventT()
..locale = "en"
..version = version
..appName = "MyApp"
..mcConfig = "{}"
..certificateChain = Uint8List(0)
..sdkconfig = Uint8List(0)
..iamCertificateChain = Uint8List(0);
// Step 2: Send event using your mcApi instance and handle response
final response = await mcApi.send(startEvent);
response.fold(
(error) => print("❌ Error: $error"),
(result) {
if (result is StartResultEventT) {
print("✅ SDK State: ${result.sdkState}");
if (result.sdkState == SdkState.activationRequired) {
print("🔐 Activation needed");
} else if (result.sdkState == SdkState.loginRequired) {
print("👤 Login needed");
}
}
},
);
```

## Automated Restart Scenarios

The MC-SDK will automatically trigger a **RestartEvent** in certain situations. Understanding these scenarios is important for proper error handling and application flow:

### **Successful App Registration**

When an app successfully completes registration with **Digitanium/Digitanium+**, an automatic restart is triggered.
The **`ActivationResultEvent`** will be sent before the **`RestartEvent`** and allows for checking if **`status=APP_REGISTERED`**.

> **Note:** Unlike **Digitanium/Digitanium+**, in **Shift Lite** solutions, there is **no automatic restart** upon app registration.

### **RuntimeErrorEvent Leading to Automated Restart**

A **`RuntimeErrorEvent`** will **always** lead to an automated restart by the MC-SDK. This event is received whenever an error occurs with `errorType=GOT_ALERT_FROM_AST`.

> ⚠️ **Recommended approach:** Handle the **`RuntimeErrorEvent`** directly as it arrives first in the event sequence. There's no need to wait for your original event result (e.g., **LoginResultEvent**) or the automated restart, since the **RuntimeErrorEvent** already contains the same **errorCode** and all necessary details about the failure.

**Common scenarios triggering RuntimeErrorEvent:**

* **User is locked** - Account locked for various reasons.
* **Too many failed login attempts from a particular device** - Device locked when retry counter is exceeded.
* **Unauthorized registration attempt** - User not allowed to register the app but tries to do so.
* **App integrity failure** - Digest of the app version does not match the database record.

Handling RuntimeErrorEvent

```
override fun executeEvent(event: EventFrameworkEvent?) {
when (event) {
is RuntimeErrorEvent -> {
logError("RuntimeError: ${event.errorType} - ${event.errorDescription}")
// MC-SDK will automatically trigger restart after this event
showRestartMessage()
}
// ... other event handling
}
}
```

### **ServerConnectionEvent Leading to Automated Restart**

**`ServerConnectionEvent`** can trigger automated restarts based on connection state:

#### **CONNECTION\_LOST → Retry → Restart**

1. When `ConnectionState.CONNECTION_LOST` is received
2. MC tries to reconnect automatically
3. If reconnection fails → `ConnectionState.NOT_REACHABLE` is received
4. **Automated restart is triggered**

#### **DISCONNECTED → Immediate Restart**

* When `ConnectionState.DISCONNECTED` is received
* **Restart is triggered immediately**

Handling ServerConnectionEvent

```
override fun executeEvent(event: EventFrameworkEvent?) {
when (event) {
is ServerConnectionEvent -> {
when (event.connectionState) {
ConnectionState.CONNECTION_LOST -> {
showConnectionLostMessage()
// MC will attempt to reconnect
}
ConnectionState.NOT_REACHABLE -> {
// This follows CONNECTION_LOST after failed reconnection
// MC will trigger automated restart
}
ConnectionState.DISCONNECTED -> {
// MC will trigger immediate automated restart
}
}
}
// ... other event handling
}
}
```

### **Best Practices for Automated Restart Handling**

1. **Implement `executeEvent` of the SynchronousEventHandler globally** - Ensure your app can receive and handle restart events from anywhere
2. **Clear user session data** - Clean up before restart, if necessary
3. **Save application state** - Preserve user progress when possible
4. **Provide user feedback** - Inform users about the restart and reason
5. **Handle gracefully** - Ensure smooth transition back to appropriate screens after restart

> **⚠️ Important:** Automated restarts are critical error recovery mechanisms. Your app should handle these events gracefully and guide users through the appropriate flow (activation, login, etc.) based on the post-restart state.
