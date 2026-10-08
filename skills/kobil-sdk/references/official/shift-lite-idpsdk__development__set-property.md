> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/set-property> on 2026-09-28. Converted to Markdown; wording unchanged.

# Set and Get Properties

Once logged in to the application, you can store and retrieve a limited amount of user or device specific information by using [**Set PropertyEvent**](shift-lite-idpsdk__mcsdk-api__ast_event_list.md#set-property) and [**GetPropertyEvent**](shift-lite-idpsdk__mcsdk-api__ast_event_list.md#get-property). Aside from having a key and a value which specify the name of the property and the value, our properties have some additional components:

* First, our properties have an [**owner**](shift-lite-idpsdk__mcsdk-api__set-property__property_owner_type.md) which defines the owner of the property, i.e. whether is a property of a specific device, a specific user, or a user group.
* Next, they have a specific [**type**](shift-lite-idpsdk__mcsdk-api__set-property__property_type.md), e.g. integer, boolean, string, or others. This type needs to be taken into account when interpreting the bytes representing the value.
* Finally, there are a couple of [**flags**](shift-lite-idpsdk__mcsdk-api__set-property__property_flags.md), which specify specific details of the behaviour, most commonly used are the flags for the access and the cache policies.

The flows for setting and getting properties involve the events detailed in the respective tables.

### **SetProperty event flow-diagram**

Here is the event flow diagram to show the details of how this works:

![](https://www.plantuml.com/plantuml/png/PSsn3i8m38JXFK_X4GPUe0CgGeoL4Ami4J4bKcf7PwU8jqTqgc2__xlGcqTucqe8XrfBlaVFAhJRqn3D6KSLXvR2w6WzSEHnP1XTsS_Gol3tQMRnyDjzhLNP_S44jggIZ5xPdslmmjQAB-nDDiEHAdJEYOtCepUZA8aOK52MXs9Q7hOXz2ofJUK3)

### **GetProperty event flow-diagram**

Here is the event flow diagram to show the details of how this works:

![](https://www.plantuml.com/plantuml/png/PSwn2i903CRn_PuYeq9z0GTHH9m4SUvozD9wa2P7agluzjAw51q3t_z7mj4ygjUHGZYLGhcBdeLXTu1RD4Sz2xiA4UeUrWFNF0oe1bVqkqf1zVTbGlRmsytMgjp_mQ1eHJWPlB8_r-03hP8lRCkRsncAofGJ6fX7hzQqt3ggYaBcNdJy_hR9FSp0z-fZ9apRPIiw4uiDKwIA3VYxO0EH4_GK1_k9hNOTOiAq3U68dEf87m00)

### iOS/Swift

For Swift, you can use the following code snippets, where the completion handler handles the response to the event:

Triggering SetProperty Event(Swift)

```
static func performSetProperty(setPropertyRequest: SetPropertyRequest, completion: @escaping (ActionResult) -> Void) {
let event = KSMSetPropertyEvent(propertyKey: setPropertyRequest.key,
withPropertyData: setPropertyRequest.data,
with: setPropertyRequest.type.getKOBILValue(),
with: setPropertyRequest.owner.getKOBILValue(),
withPropertyTtl: setPropertyRequest.ttl,
withPropertyFlags: setPropertyRequest.flags)
let time = CallTimer(event: event)
MasterControllerAdapter.sharedInstance.masterController?.receive(event, withCompletionHandler: { event in
let duration = time.stop()
if let resultEvent = event as? KSMSetPropertyResultEvent {
let result = handleSetPropertyStatus(status: resultEvent.status)
let actionResult = ActionResult(title: "propertyModel.set.title".localized(table: localizedTable),
success: result.success,
error: result.errorText?.localized(table: localizedTable),
duration: duration,
event: resultEvent)
EventLogObject(actionResult: actionResult,
component: "\(self)")
completion(actionResult)
}
})
}
```

Triggering GetProperty Event(Swift)

```
static func performGetProperty(propertyRequest: GetPropertyRequest) async -> (actionResult: ActionResult, getProperty: GetProperty?) {
return await withCheckedContinuation { continuation in
let event = KSMGetPropertyEvent(propertyKey: propertyRequest.key, with: propertyRequest.owner.getKOBILValue())
let time = CallTimer(event: event)
MasterControllerAdapter.sharedInstance.masterController?.receive(event, withCompletionHandler: { event in
let duration = time.stop()
if let resultEvent = event as? KSMGetPropertyResultEvent {
let result = handleGetPropertyStatus(status: resultEvent.status)
let actionResult = ActionResult(title: "propertyModel.get.title".localized(table: localizedTable),
success: result.success,
error: result.errorText?.localized(table: localizedTable),
duration: duration,
event: resultEvent)
if result.success {
let property = GetProperty(data: resultEvent.propertyData,
type: resultEvent.propertyType.getAppEnum(),
ttl: resultEvent.propertyTtl,
flags: resultEvent.propertyFlags)
EventLogObject(actionResult: actionResult,
component: "\(self)")
continuation.resume(returning: (actionResult, property))
} else {
EventLogObject(actionResult: actionResult,
component: "\(self)")
continuation.resume(returning: (actionResult, nil))
}
}
})
}
}
```

### Android/Kotlin

Triggering SetProperty Event(Kotlin)

```
fun triggerSetPropertyEvent(
propertyKey: String, propertyOwnerType: PropertyOwnerType,
propertyData: ByteArray, propertyType: PropertyType, ttl: Int, flags: Int) {
val setPropertyEvent = SetPropertyEvent(
propertyKey, propertyData, propertyType, propertyOwnerType, ttl, flags)
synchronousEventHandler.postEvent(setPropertyEvent)?.then { resultEvent ->
// handle result
}
}
```

Triggering GetProperty Event(Kotlin)

```
fun triggerGetPropertyEvent(
propertyKey: String, propertyOwnerType: PropertyOwnerType) {
val getPropertyEvent = GetPropertyEvent(propertyKey, propertyOwnerType)
synchronousEventHandler.postEvent(getPropertyEvent)?.then { resultEvent ->
// handle result
}
}
```
