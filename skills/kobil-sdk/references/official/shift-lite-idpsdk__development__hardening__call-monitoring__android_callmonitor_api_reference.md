> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/hardening/call-monitoring/android_callmonitor_api_reference> on 2026-09-28. Converted to Markdown; wording unchanged.

# Call Monitor Android API Reference

> **Licensing Notice**
>
> This feature is included in the SDK as part of the standard product baseline, but is not included in the default license scope.
> The use of Voice Call Guard in any environment requires a valid, separately purchased license.
> The availability of this functionality in the SDK does not grant any right to use it beyond the contractually agreed scope.
> Any use beyond the licensed scope is not permitted.
> KOBIL reserves the right to require retroactive licensing in case of unlicensed usage.
> If you are unsure whether your license includes this feature, please contact your account representative or the KOBIL sales team.

---

## Call Monitor Android API Reference

`Call Monitor` monitors for active phone calls and enforces a configurable security policy while the app is in the foreground. It does **not** require `READ_PHONE_STATE` permission.

---

## Security Flows

### Terminate Flow

A countdown dialog is displayed. When the timer reaches zero — or the user taps **Close App** — the app is force-exited via `System.exit(0)` if the call is still active.

If the call ends before the timer expires, the dialog is dismissed automatically and the monitor resets, ready for the next call.

### Acknowledge Flow

A risk-warning dialog is displayed. After a configurable delay, an **Acknowledge** button appears. The user must tap it to dismiss the dialog. The app is **never** force-exited in this flow.

If the call ends before the user acknowledges, the dialog is dismissed automatically and the monitor resets.

---

## Import

**Kotlin**

```
import com.kobil.hardening.core.callmonitor.*
```

**Java**

```
import com.kobil.hardening.core.callmonitor.*;
```

---

## API

### `startMonitoring` (Kotlin)

```
CallMonitor.startMonitoring(
activity: Activity,
callback: CallMonitorCallback? = null,  // optional — fires on every call state change
withTerminateIn: Int? = null,           // seconds before force-exit
withAcknowledgeIn: Int? = null          // seconds before Acknowledge button appears
)
```

At most **one** of `withTerminateIn` or `withAcknowledgeIn` may be provided. Omit both for callback-only monitoring with no security UI.

**Examples:**

```
// Terminate flow — force-exit after 10 seconds
CallMonitor.startMonitoring(this, withTerminateIn = 10)
// Acknowledge flow — show Acknowledge button after 30 seconds
CallMonitor.startMonitoring(this, withAcknowledgeIn = 30)
// Acknowledge flow — Acknowledge button immediately visible
CallMonitor.startMonitoring(this, withAcknowledgeIn = 0)
// Callback only — no security UI, just call state events
CallMonitor.startMonitoring(this, callback = { event -> Log.d("App", "Call event: $event") })
// Both — security flow + event callback
CallMonitor.startMonitoring(this, callback = { event -> ... }, withTerminateIn = 10)
```

---

### `startMonitoringWithTerminateIn` (Java)

```
CallMonitor.startMonitoringWithTerminateIn(Activity activity, int seconds)
CallMonitor.startMonitoringWithTerminateIn(Activity activity, int seconds, CallMonitorCallback callback)
```

Starts the **terminate flow**.

| Parameter | Description |
| --- | --- |
| `activity` | The current Activity. |
| `seconds` | Countdown before force-exit. Minimum 1. |
| `callback` | Optional. Notified on every call state change. |

**Example:**

```
CallMonitor.startMonitoringWithTerminateIn(this, 10);
// With callback
CallMonitor.startMonitoringWithTerminateIn(this, 10, event -> Log.d("App", "Event: " + event));
```

---

### `startMonitoringWithAcknowledgeIn` (Java)

```
CallMonitor.startMonitoringWithAcknowledgeIn(Activity activity, int seconds)
CallMonitor.startMonitoringWithAcknowledgeIn(Activity activity, int seconds, CallMonitorCallback callback)
```

Starts the **acknowledge flow**.

| Parameter | Description |
| --- | --- |
| `activity` | The current Activity. |
| `seconds` | Delay before Acknowledge button appears. `0` for immediate. |
| `callback` | Optional. Notified on every call state change. |

**Example:**

```
CallMonitor.startMonitoringWithAcknowledgeIn(this, 30);
// With callback
CallMonitor.startMonitoringWithAcknowledgeIn(this, 30, event -> Log.d("App", "Event: " + event));
```

---

### `stopMonitoring`

**Kotlin**

```
CallMonitor.stopMonitoring()
```

**Java**

```
CallMonitor.stopMonitoring();
```

Stops monitoring, cancels any running countdown, and dismisses the dialog if visible.

---

## Custom Delegate

By default, `CallMonitor` displays its own `AlertDialog`-based security UI. You can replace this entirely by setting a custom delegate that implements `CallMonitorDelegate`. The delegate lets you show any UI — a custom dialog, an overlay, or any view — while `CallMonitor` continues to own all timing, countdown, and force-exit logic.

### `setDelegate`

**Kotlin**

```
CallMonitor.setDelegate(myDelegate)  // call before startMonitoring
```

**Java**

```
CallMonitor.setDelegate(myDelegate);
```

Pass `null` to revert to the default `AlertDialog` behavior.

> **Important:** Call `setDelegate` **before** `startMonitoring`. The delegate is stored internally and used for the lifetime of a monitoring session.

---

### `CallMonitorDelegate` Interface

All methods are called on the **main thread**.

#### `onCallDetected`

Called when a phone call is detected and the security UI should be shown.

**Kotlin**

```
fun onCallDetected(context: Context, flow: CallFlow, initialRemaining: Int, onUserAction: Runnable)
```

**Java**

```
void onCallDetected(Context context, CallFlow flow, int initialRemaining, Runnable onUserAction);
```

| Parameter | Description |
| --- | --- |
| `context` | The current foreground `Activity` context, used to create dialogs and resolve string resources. Falls back to `Application` context if no Activity is available at detection time. |
| `flow` | The active security flow — `CallFlow.TERMINATE` or `CallFlow.ACKNOWLEDGE`. |
| `initialRemaining` | Starting countdown value in seconds. `0` means the action button should be visible immediately (acknowledge flow only). |
| `onUserAction` | Call this when the user performs the primary action — **Close App** in terminate flow, or **Acknowledge** in acknowledge flow. `CallMonitor` handles the resulting security logic (force-exit or dismiss). |

---

#### `onCountdownTick`

Called every second during the countdown. Use this to update a countdown label in your UI.

**Kotlin**

```
fun onCountdownTick(remaining: Int)
```

**Java**

```
void onCountdownTick(int remaining);
```

| Parameter | Description |
| --- | --- |
| `remaining` | Seconds remaining, counting down to `0`. In the acknowledge flow, `remaining == 0` is the signal to reveal the action button. |

---

#### `onCallEnded`

Called when the call ends or when the user completes the required action. Dismiss your security UI here.

**Kotlin**

```
fun onCallEnded()
```

**Java**

```
void onCallEnded();
```

---

### `CallFlow` Enum

```
enum class CallFlow {
TERMINATE,   // Force-exit flow — exits if call is still active when timer reaches zero
ACKNOWLEDGE  // Acknowledge-only flow — never force-exits
}
```

---

### Delegate Example

**Kotlin**

```
class MySecurityDelegate : CallMonitorDelegate {
private var dialog: AlertDialog? = null
override fun onCallDetected(context: Context, flow: CallFlow, initialRemaining: Int, onUserAction: Runnable) {
val builder = AlertDialog.Builder(context).setCancelable(false)
when (flow) {
CallFlow.TERMINATE ->
builder.setTitle("Security Warning")
.setMessage("App will close in $initialRemaining seconds.")
.setPositiveButton("Close App") { _, _ -> onUserAction.run() }
CallFlow.ACKNOWLEDGE ->
builder.setTitle("Security Warning")
.setMessage("A call is active. Please acknowledge to continue.")
.apply {
if (initialRemaining == 0)
setPositiveButton("Acknowledge") { _, _ -> onUserAction.run() }
}
}
dialog = builder.create().also { it.show() }
}
override fun onCountdownTick(remaining: Int) {
dialog?.setMessage("App will close in $remaining seconds.")
}
override fun onCallEnded() {
dialog?.dismiss()
dialog = null
}
}
// Wire up before starting
CallMonitor.setDelegate(MySecurityDelegate())
CallMonitor.startMonitoring(this, withTerminateIn = 10)
```

**Java**

```
CallMonitor.setDelegate(new CallMonitorDelegate() {
private AlertDialog dialog;
@Override
public void onCallDetected(Context context, CallFlow flow, int initialRemaining, Runnable onUserAction) {
AlertDialog.Builder builder = new AlertDialog.Builder(context).setCancelable(false);
if (flow == CallFlow.TERMINATE) {
builder.setTitle("Security Warning")
.setMessage("App will close in " + initialRemaining + " seconds.")
.setPositiveButton("Close App", (d, w) -> onUserAction.run());
} else {
builder.setTitle("Security Warning")
.setMessage("A call is active. Please acknowledge to continue.");
if (initialRemaining == 0) {
builder.setPositiveButton("Acknowledge", (d, w) -> onUserAction.run());
}
}
dialog = builder.create();
dialog.show();
}
@Override
public void onCountdownTick(int remaining) {
if (dialog != null) dialog.setMessage("App will close in " + remaining + " seconds.");
}
@Override
public void onCallEnded() {
if (dialog != null) { dialog.dismiss(); dialog = null; }
}
});
CallMonitor.startMonitoringWithTerminateIn(this, 10);
```

---

## Call Event Callback

In addition to the security delegate, `CallMonitor` exposes a lightweight callback that fires on every call state change. This is useful for logging, analytics, or reacting to call state without implementing the full delegate protocol.

The callback is passed directly to `startMonitoring` (or its Java equivalents). It is called on the **main thread** for every distinct call state transition. Consecutive identical events are deduplicated.

### `CallMonitorCallback`

```
fun interface CallMonitorCallback {
fun onCallEvent(event: CallEvent)
}
```

### `CallEvent` Enum

| Value | Description |
| --- | --- |
| `CALL_RINGING` | An incoming call is ringing or an outgoing call is dialing. |
| `CALL_STARTED` | A call has connected and the conversation is active. |
| `CALL_ENDED` | All calls have ended. Resets deduplication state. |

### Examples

**Kotlin — callback only (no security UI)**

```
CallMonitor.startMonitoring(this, callback = { event ->
when (event) {
CallEvent.CALL_RINGING -> Log.d("App", "Call ringing")
CallEvent.CALL_STARTED -> Log.d("App", "Call started")
CallEvent.CALL_ENDED   -> Log.d("App", "Call ended")
}
})
```

**Kotlin — callback combined with security flow**

```
CallMonitor.startMonitoring(
activity  = this,
callback  = { event -> analytics.track("call_event", event.name) },
withAcknowledgeIn = 30
)
```

**Java — callback combined with security flow**

```
CallMonitor.startMonitoringWithTerminateIn(this, 10, event -> {
Log.d("App", "Call event: " + event);
});
```

> The callback and the security delegate are independent — both can be used at the same time.

---

## Activity Parameter

The API requires an `Activity` (not `Context`). The dialog needs an Activity window token to display correctly. After the initial call, the monitor automatically tracks Activity transitions via `ActivityLifecycleCallbacks`. You only call `startMonitoring` once.

---

## Localization

The library ships translations for 22 languages:

English, German, French, Spanish, Italian, Portuguese, Dutch, Russian, Polish, Turkish, Bulgarian, Czech, Danish, Greek, Finnish, Croatian, Hungarian, Norwegian, Romanian, Slovak, Swedish, Ukrainian.

### Overriding Strings

The app can override any string by declaring the same key in its own `strings.xml`. Android resource merging prioritizes app resources over library resources.

> Localization applies to the **default AlertDialog UI only**. When a custom delegate is set, all string rendering is the delegate's responsibility.

**Available string keys:**

| Key | Default (English) | Used in |
| --- | --- | --- |
| `call_monitor_alert_title` | Security Policy | Both flows — dialog title |
| `call_monitor_alert_message` | Application access is disabled during active calls for your protection. | Terminate flow — dialog body |
| `call_monitor_alert_message_warning` | Using this application during an active call may expose sensitive information. | Acknowledge flow — dialog body |
| `call_monitor_button_close` | Close App | Terminate flow — button |
| `call_monitor_button_acknowledge` | Acknowledge | Acknowledge flow — button |
| `call_monitor_close_countdown` | App will close in %d seconds. | Terminate flow — countdown text |
| `call_monitor_acknowledge_countdown` | Acknowledge in %d seconds. | Acknowledge flow — countdown text |

> `%d` is replaced with the remaining seconds at runtime.

**Override example:**

```
<!-- app/src/main/res/values-de/strings.xml -->
<resources>
<string name="call_monitor_alert_title">Sicherheitshinweis</string>
</resources>
```

---

## Limitations

`Call Monitor` relies on Android's telephony and VoIP call-state APIs. As a result, its detection scope is limited to the following call types:

* **Cellular calls** — standard GSM/LTE/5G phone calls managed by the Android telephony stack.
* **VoIP calls** — calls registered via `ConnectionService` (i.e. apps that integrate with the Android Telecom framework and surface calls through the native dialer, e.g. WhatsApp, Telegram).

The following types of voice communication are **not detected** and will **not** trigger the security policy:

* Voice or video calls made inside a **web browser** (e.g. Google Meet, Microsoft Teams, or any WebRTC-based call opened in Chrome or another browser).
* Calls handled entirely within a **third-party app** that does not register with the Android Telecom framework (Zoom, Discord, and similar apps).

---
