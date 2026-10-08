> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/enable-authentication-mode> on 2026-09-28. Converted to Markdown; wording unchanged.

# Enable Authentication Mode

**Event Name:** EnableAuthenticationModeEvent

**Description:**
The EnableAuthenticationModeEvent is triggered when a user wants to change the authentication mode without the need to perform a login again. This event enhances the user experience by streamlining the process of switching authentication modes within the MC SDK.

**Usage:**
To utilize the EnableAuthenticationModeEvent, developers need to create to this event within their application's codebase. When the authentication mode needs to be changed, simply trigger this event to seamlessly transition to the desired mode without requiring the user to log in again.

**Code Changes:**

**Swift:**

```
func enable(mode: KSMAuthenticationMode, completion: ((KSMEventStatusType) -> Void)? = nil) {
let event = KSMEnableAuthenticationModeEvent(authenticationMode: mode)
MasterControllerAdapter.sharedInstance.sendEvent2MasterController(event: event) { [weak self] receivedEvent in
guard let self = self, let result = receivedEvent as? KSMStatusResultEvent else { return }
if result.status == .KSMOK {
self.updateCurrent(mode: mode)
}
DispatchQueue.main.async {
completion?(result.status)
}
}
}
```

**Kotlin:**

```
val enableAuthenticationEvent = EnableAuthenticationModeEvent(AuthenticationMode.PASSWORD)
MasterControllerAdapter.getInstance()?.postEvent(enableAuthenticationEvent)?.then { resultEvent ->
when (resultEvent) {
is StatusResultEvent -> {
val status = (resultEvent as StatusResultEvent).status
}
else -> {
...
}
}
}
```

**Note:** Ensure to call function with desired `AuthenticationMode` with the actual implementation specific to your application's requirements.

With the EnableAuthenticationModeEvent, users can seamlessly switch between authentication modes within your application, enhancing the overall user experience and reducing friction associated with authentication mode changes.
