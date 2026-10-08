> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/set-device-name> on 2026-09-28. Converted to Markdown; wording unchanged.

# Set/Get Device Information

The `GetDeviceInformationEvent` retrieves device-specific information as stored on the server, and the `SetDeviceNameEvent` allows updating the device name. See [**Set**](shift-lite-idpsdk__mcsdk-api__ast_event_list.md#device-name) / [**Get**](shift-lite-idpsdk__mcsdk-api__ast_event_list.md#device-information) for the event reference.

> **Note:** `GetDeviceInformationEvent` is only available on SSMS-based environments (KOBIL Digitanium / KOBIL Digitanium+) and requires an activated user on the device.

### GetDeviceInformationResultEvent

The `GetDeviceInformationResultEvent` provides the following fields:

| Field | Type | Description |
| --- | --- | --- |
| `deviceId` | String | The device identifier as registered on the server. |
| `deviceName` | String | The device name as registered on the server. |

### iOS/Swift

For Swift, you can use the following code snippets, where the completion handler handles the response to the event:

Triggering GetDeviceInformation Event(Swift)

```
static func getDeviceInformation(request: DeviceInfoRequest, completion: @escaping (ActionResult, DeviceInfo?) -> Void) {
let userIdentifier = KsUserIdentifier(tenantId: request.tenant, userId: request.user)
let event = KSMGetDeviceInformationEvent(userIdentifier: userIdentifier)
let timer = CallTimer(event: event)
MasterControllerAdapter.sharedInstance.sendEvent2MasterController(event: event) { resultEvent in
let duration = timer.stop()
if let informationResult = resultEvent as? KSMGetDeviceInformationResultEvent {
let actionResult = ActionResult(title: "deviceInformationModel.title".localized(table: localizedTable),
success: true,
error: nil,
duration: duration,
event: resultEvent)
let info = DeviceInfo(id: informationResult.deviceId,
name: informationResult.deviceName)
EventLogObject(actionResult: actionResult,
component: localizedTable)
completion(actionResult, info)
} else {
let actionResult = ActionResult(title: "deviceInformationModel.title".localized(table: localizedTable),
success: false,
error: "deviceInformationModel.status.unexpectedEvent".localized(table: localizedTable),
duration: duration,
event: event)
EventLogObject(actionResult: actionResult,
component: localizedTable)
completion(actionResult, nil)
}
}
}
```

Triggering SetDeviceName Event(Swift)

```
static func performSetDeviceName() async -> ActionResult {
return await withCheckedContinuation { continuation in
let event = KSMSetDeviceNameEvent(deviceName: deviceName)
let timer = CallTimer(event: event)
MasterControllerAdapter.sharedInstance.sendEvent2MasterController(event: event) { resultEvent in
let duration = timer.stop()
let title = "deviceNameModel.title".localized(table: localizedTable)
var errorText: String?
var success = false
if let deviceNameResult = resultEvent as? KSMSetDeviceNameResultEvent {
let status = handleDeviceNameStatus(status: deviceNameResult.status)
success = status.success
errorText = status.errorText?.localized(table: localizedTable)
} else if resultEvent is KSMInvalidStateEvent {
errorText = "deviceNameModel.event.invalidStateEvent".localized(table: localizedTable)
} else {
errorText = "deviceNameModel.event.unexpectedEvent".localized(table: localizedTable)
}
let actionResult = ActionResult(title: title,
success: success,
error: errorText,
duration: duration,
event: resultEvent)
EventLogObject(actionResult: actionResult,
component: "\(self)")
continuation.resume(returning: actionResult)
}
}
}
```

### Android/Kotlin

Triggering GetDeviceInformation Event(Kotlin)

```
fun triggerGetDeviceInformationEvent(userId: String, tenantId: String) {
val getDeviceInformationEvent =
GetDeviceInformationEvent(UserIdentifier(tenantId, userId))
synchronousEventHandler.postEvent(getDeviceInformationEvent)?.then {
// handle result
}
}
```

Triggering SetDeviceName Event(Kotlin)

```
fun triggerSetDeviceNameEvent(deviceName: String) {
val setDeviceNameEvent = SetDeviceNameEvent(deviceName)
synchronousEventHandler.postEvent(setDeviceNameEvent)?.then {
// handle result
}
}
```

Handling SetDeviceNameResult Event

```
override fun executeEvent(event: EventFrameworkEvent?) {
when (eventFrameworkEvent) {
is SetDeviceNameResultEvent -> {
when (eventFrameworkEvent.status) {
StatusType.OK -> {
}
StatusType.NOT_UNIQUE -> {
}
StatusType.NOT_REACHABLE -> {
}
else -> {
}
}
}
}
}
```
