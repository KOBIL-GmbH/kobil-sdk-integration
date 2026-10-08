> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/get-sdk-info> on 2026-09-28. Converted to Markdown; wording unchanged.

# Get SDK Information

The `GetInformationEvent` is used to obtain SDK and user information. It can be triggered at any time, even when no user is activated or logged in — in that case, the result will only contain non-user-related information (e.g., `sdkVersion`, `appName`, `locale`). You can find SDK Information related events [**here**](https://developer.kobil.com/docs/mcsdk-docs/digitanium/mcsdk-api/base_event).

> **Note:** For retrieving device-specific information (deviceId, deviceName) on SSMS-based environments (KOBIL Digitanium / KOBIL Digitanium+), see [Set/Get Device Information](shift-lite-idpsdk__development__set-device-name.md).

### GetInformationResultEvent

The `GetInformationResultEvent` provides the following fields:

| Field | Type | Description |
| --- | --- | --- |
| `sdkVersion` | String | The version of the MC-SDK. |
| `serialNumber` | String | The serial number of the device registration. |
| `locale` | String | The locale configured during the StartEvent. |
| `version` | AppVersion | The app version provided during the StartEvent. |
| `appName` | String | The app name provided during the StartEvent. |
| `appConfig` | String | The app configuration string. |
| `loggedInUserIdentifier` | UserIdentifier | The identifier of the currently logged-in user. |
| `iamConfigurationData` | IamConfigurationData | IAM configuration data from the server. |
| `encryptionCertificate` | byte[] | The encryption certificate. |
| `signerCertificate` | byte[] | The signer certificate. |
| `authenticationCertificate` | byte[] | The authentication certificate. |

### **GetInformation event flow-diagram**

Here is the event flow diagram to show the details of how this works:

![](https://www.plantuml.com/plantuml/png/fP6_Ri903CRtUufl1Abz0OQA2Yg4MfQYRbckEIUSTF55jWzUlqgeIahL1LRB_lxyx9PgNgnqoRddla-nzXOpu_49Ewz6iifiabCYMM2wO1BRbaIn7-vVZiI6YcUPuITRe_ZSNKiDyXEnnHyl26cVEIXEqGweU7Hv9otfx5NnB51F72At6E8SQBWfoHvGSSfjP6WjH8migDZN5e_VcSxZKqm9dmGzv1FFdVF941jyA0cYGgYDGoOAg7X3XYqtMRfHuaPIRqEg7rA-CH8G6ydGeIZ9TWtF0Nta-v6DPXDW5qijTKsgJKauSwhua3lwXyjjLJTa4rvZWBiR_TQyghPRePTyZ84K-_KhucLpP5h6jrw6S-U8WriIXzAbBm00)

### iOS/Swift

For Swift, the following snippet can be used to trigger the event, where the response can be processed in the completion handler:

Triggering GetInformationEvent (Swift)

```
func handleGetInformation(completion: @escaping (KSMGetInformationResultEvent?) -> Void) {
let event = KSMGetInformationEvent()
let timer = CallTimer(event: event)
MasterControllerAdapter.sharedInstance.sendEvent2MasterController(event: event) { resultEvent in
let duration = timer.stop()
if let informationResult = resultEvent as? KSMGetInformationResultEvent {
let actionResult = ActionResult(title: "GetInformation",
success: true,
error: nil,
duration: duration,
event: resultEvent)
EventLogObject(actionResult: actionResult, component: "GetInformation")
completion(informationResult)
} else {
let actionResult = ActionResult(title: "GetInformation",
success: false,
error: "Unexpected event",
duration: duration,
event: resultEvent)
EventLogObject(actionResult: actionResult, component: "GetInformation")
completion(nil)
}
}
}
```

### Android/Kotlin

Triggering GetInformationEvent (Kotlin)

```
fun triggerGetInformationEvent() {
synchronousEventHandler.postEvent(GetInformationEvent())?.then {
// handle result
}
}
```
