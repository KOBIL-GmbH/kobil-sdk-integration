> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/delete-user> on 2026-09-28. Converted to Markdown; wording unchanged.

# Delete User

As Master Controller provides the functionality to add multiple users, it also provides the mechanism to delete them. For deletion, there must be one or more activated users on your device. Deletion of a user uses the events described in the [**delete user events list**](shift-lite-idpsdk__mcsdk-api__ast_event_list.md#delete-user).
Note that the delete user process can only be performed if the user to be deleted is not logged in. The application needs to trigger a **DeleteUserEvent**. For details of the deletion process, see this event flow:

> **NOTE:** Passing `UserIdentifier("", "")` to `DeleteUserEvent` will delete all users on Digitanium/SSMS-based environments, but will do nothing on SHIFT.

### **DeleteUser event flow-diagram**

![](https://www.plantuml.com/plantuml/png/hP51ImD138NlyojoQ_TWVy0Uf58h5BL2YxUz33lPRN1siYJPYlzUfYfTsge87aDUllTuSNCrBpPqqRcRlezKUoDES7KDZruDPS79X6D4AM4iCA6sHL6eqZOJbdjCvavlCcTqLPv1GL1xJa7XbMpt1TkW3l4JwNmqe0O6HG5I46mfCp30z5Gyow87KfkHhjcMNMzlqwA0AjrYH4Dupf0gJNlXFGLABVW3U1Km6JM40erm1xP3YAG6tC2fIV5xKHzksUo_QZaIBtLpSGjgtWQ5cWFcuYPFzvEpw8iIDgZ71pfCmQtP428sviQrROUwHjMiWCI6Vp9FR1S3ZCSI5ZkiNxu1DYo08YmGlFaVSjvvYXYECG_IEQOmTF4T)

### iOS/Swift

For Swift you can trigger that by this snippet:

Triggering DeleteUserEvent (Swift)

```
static func performDeleteUser(traceParent: String? = nil, deleteRequest: DeleteUserRequest, completion: @escaping (ActionResult) -> Void) {
let userIdentifier = KsUserIdentifier(tenantId: deleteRequest.tenant, userId: deleteRequest.userId)
let event = KSMDeleteUserEvent(userIdentifier: userIdentifier)
if let traceParent {
let state = event.traceContext.traceState
event.traceContext = .init(traceParent: traceParent, traceState: state)
}
let time = CallTimer(event: event)
MasterControllerAdapter.sharedInstance.masterController?.receive(event, withCompletionHandler: { resultEvent in
let duration = time.stop()
if let deleteUserResult = resultEvent as? KSMDeleteUserResultEvent {
let eventResult = handleDeleteStatus(status: deleteUserResult.status, duration: duration)
let actionResult = ActionResult(title: "deleteUserModel.status.title".localized(table: localizedTable),
success: eventResult.success,
error: eventResult.errorText?.localized(table: localizedTable),
duration: duration,
event: resultEvent)
EventLogObject(actionResult: actionResult,
component: "\(self)")
completion(actionResult)
}
})
}
```

### Android/Kotlin

Triggering DeleteUserEvent (Kotlin)

```
fun triggerDeleteUserEvent(userIdentifier: UserIdentifier) {
synchronousEventHandler.postEvent(DeleteUserEvent(userIdentifier))?.then {
// handle result
}
}
```

### All Platforms

As a response to **DeleteUserEvent**, the Master Controller sends a [**DeleteUserResultEvent**](shift-lite-idpsdk__mcsdk-api__ast_event_list.md#delete-user) with appropriate status, sdkState, and an array of `UserDetails` containing the remaining users.

> ⚠️ **Deprecated:** The array of `UserIdentifier` in `DeleteUserResultEvent` is deprecated and will be removed in a **2026** major release. Use the array of `UserDetails` instead. For details on the `UserDetails` type, see [Start/Restart Event](shift-lite-idpsdk__development__start.md#userdetails-in-result-events).
