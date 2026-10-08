> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/hardening/call-monitoring/ios_callmonitor_api_reference> on 2026-09-28. Converted to Markdown; wording unchanged.

# Call Monitor iOS API Reference

> **Licensing Notice**
>
> This feature is included in the SDK as part of the standard product baseline, but is not included in the default license scope.
> The use of Voice Call Guard in any environment requires a valid, separately purchased license.
> The availability of this functionality in the SDK does not grant any right to use it without a contractually agreed scope.
> Any use beyond the licensed scope is not permitted.
> KOBIL reserves the right to require retroactive licensing in case of unlicensed usage.
> If you are unsure whether your license includes this feature, please contact your account representative or the KOBIL sales team.

---

## Call Monitor iOS API Reference

`Call Monitor` monitors for active phone calls and enforces a configurable security policy while the app is in the foreground. It does not require any special permissions or entitlements.

---

## Security Flows

### Terminate Flow

A **Close App** button and a live countdown are displayed immediately. When the timer reaches zero — or the user taps **Close App** — the app is force-exited via `exit(0)` if the call is still active.

If the call ends before the timer expires, the dialog is dismissed automatically and the monitor resets, ready for the next call.

### Acknowledge Flow

A risk-warning dialog is displayed with no button. After a configurable delay, an **Acknowledge** button appears. The user must tap it to dismiss the dialog. The app is **never** force-exited in this flow.

If the call ends before the user acknowledges, the dialog is dismissed automatically and the monitor resets.

---

## Import

**Swift**

```
import hnb
```

**Objective-C**

```
#import <hnb/CallMonitor.h>
```

---

## API

### `startMonitoringWithTerminateIn:` (Objective-C)

```
- (void)startMonitoringWithTerminateIn:(int)seconds;
```

Starts the **terminate flow**.

| Parameter | Description |
| --- | --- |
| `seconds` | Countdown duration in seconds before force-exit. Clamped to a minimum of **1**. |

**Example:**

```
[[CallMonitor sharedInstance] startMonitoringWithTerminateIn:10];
```

---

### `startMonitoringWithAcknowledgeIn:` (Objective-C)

```
- (void)startMonitoringWithAcknowledgeIn:(int)seconds;
```

Starts the **acknowledge flow**.

| Parameter | Description |
| --- | --- |
| `seconds` | Delay in seconds before the Acknowledge button appears. Pass `0` for immediate. Clamped to a minimum of **0**. |

**Example:**

```
[[CallMonitor sharedInstance] startMonitoringWithAcknowledgeIn:30];
```

---

### Swift API

```
// Terminate flow — force-exit after 10 seconds
CallMonitor.sharedInstance().startMonitoring(withTerminateIn: 10)
// Acknowledge flow — show Acknowledge button after 30 seconds
CallMonitor.sharedInstance().startMonitoring(withAcknowledgeIn: 30)
// Acknowledge flow — Acknowledge button immediately visible
CallMonitor.sharedInstance().startMonitoring(withAcknowledgeIn: 0)
```

---

### `stopMonitoring`

```
[[CallMonitor sharedInstance] stopMonitoring];
```

```
CallMonitor.sharedInstance().stopMonitoring()
```

Stops monitoring for active calls and ends any active security event. If a security UI is currently visible, it will be dismissed via `callMonitorDidEndCall` on the delegate.

---

## Custom Delegate

By default, `CallMonitor` displays its own `UIAlertController`-based security UI. You can replace this entirely by setting a custom delegate that conforms to `CallMonitorDelegate`. The delegate lets you render any UI you want — a custom view controller, a sheet, an overlay — while `CallMonitor` continues to own all timing, countdown, and force-exit logic.

### Setting the Delegate

**Objective-C**

```
[[CallMonitor sharedInstance] setDelegate:self];
```

**Swift**

```
CallMonitor.sharedInstance().setDelegate(self)
```

Pass `nil` to revert to the default `UIAlertController` behavior.

> **Important:** `CallMonitor` holds a **weak reference** to the delegate. Do not pass a locally-allocated object — the delegate will be released immediately and no callbacks will fire. Store your delegate in a property with a strong lifetime (e.g. a view controller or application-level object).

---

### `CallMonitorDelegate` Protocol

All delegate methods are called on the **main thread**.

#### `callMonitorDidDetectCall(flow:initialRemaining:onUserAction:)`

Called when a phone call is detected and the security UI should be shown.

**Objective-C**

```
- (void)callMonitorDidDetectCallWithFlow:(CallMonitorFlow)flow
initialRemaining:(int)initialRemaining
onUserAction:(dispatch_block_t)onUserAction;
```

**Swift**

```
func callMonitorDidDetectCall(flow: CallMonitorFlow, initialRemaining: Int32, onUserAction: @escaping () -> Void)
```

| Parameter | Description |
| --- | --- |
| `flow` | The active security flow — `.terminate` or `.acknowledge`. |
| `initialRemaining` | Starting countdown value in seconds. `0` means the action button should be visible immediately (acknowledge flow only). |
| `onUserAction` | Call this block when the user performs the primary action (taps **Close App** in terminate, or **Acknowledge** in acknowledge). `CallMonitor` handles the resulting security logic — force-exit or dismiss. |

---

#### `callMonitorCountdownTick(_:)`

Called every second during the countdown. Use this to update the countdown label in your UI.

**Objective-C**

```
- (void)callMonitorCountdownTick:(int)remaining;
```

**Swift**

```
func callMonitorCountdownTick(_ remaining: Int32)
```

| Parameter | Description |
| --- | --- |
| `remaining` | Seconds remaining, counting down to `0`. In the acknowledge flow, `remaining == 0` is the signal to reveal the action button. |

---

#### `callMonitorDidEndCall`

Called when the call ends or when the user completes the required action. Dismiss your security UI here.

**Objective-C**

```
- (void)callMonitorDidEndCall;
```

**Swift**

```
func callMonitorDidEndCall()
```

---

### `CallMonitorFlow` Enum

```
public enum CallMonitorFlow {
case terminate   // Force-exit flow
case acknowledge // Acknowledge-only flow
}
```

---

### Delegate Example

**Swift**

```
class MySecurityHandler: CallMonitorDelegate {
func callMonitorDidDetectCall(
flow: CallMonitorFlow,
initialRemaining: Int32,
onUserAction: @escaping () -> Void
) {
// Show your custom security UI, store onUserAction to call on button tap
}
func callMonitorCountdownTick(_ remaining: Int32) {
// Update countdown label
}
func callMonitorDidEndCall() {
// Dismiss security UI
}
}
// Store in a long-lived property — CallMonitor holds a weak reference
let securityHandler = MySecurityHandler()
CallMonitor.sharedInstance().setDelegate(securityHandler)
CallMonitor.sharedInstance().startMonitoring(withAcknowledgeIn: 30)
```

---

## Call Event Callback

In addition to the security delegate, `CallMonitor` exposes a lightweight callback that fires on every call state change. This is useful for logging, analytics, or reacting to call state without implementing the full delegate protocol.

### `setCallback(_:)`

**Objective-C**

```
- (void)setCallback:(void (^)(CallEvent event))callback;
```

**Swift**

```
CallMonitor.sharedInstance().setCallback { event in
switch event {
case .ringing: print("Call ringing")
case .started: print("Call started")
case .ended:   print("Call ended")
}
}
```

Pass `nil` to remove the callback. The callback defaults to `nil`.

The callback is called on the **main thread** for every distinct call state transition. Consecutive identical events are deduplicated — the callback fires at most once per unique event until the state changes.

### `CallEvent` Enum

| Value | Description |
| --- | --- |
| `.ringing` | An incoming call is ringing or an outgoing call is dialing. |
| `.started` | A call has connected and the conversation is active. |
| `.ended` | All calls have ended. Resets deduplication state. |

> The callback and the security delegate are independent — both can be used at the same time.

---

## Localization

The library ships translations for 22 languages:

English, German, French, Spanish, Italian, Portuguese, Dutch, Russian, Polish, Turkish, Bulgarian, Czech, Danish, Greek, Finnish, Croatian, Hungarian, Norwegian, Romanian, Slovak, Swedish, Ukrainian.
Strings are resolved using a **3-bundle fallback chain**:

1. **Main bundle** (the host app) — checked first
2. framework bundle
3. Hardcoded English default

> Localization applies to the **default UIAlertController UI only**. When a custom delegate is set, all string rendering is the delegate's responsibility.

### Overriding Strings

The app can override any string by declaring the same key in its own `Localizable.strings` (or `Localizable.xcstrings` String Catalog). The main bundle is checked first, so app-level keys always take priority.

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

**Override example** (`Localizable.strings`):

```
/* app/de.lproj/Localizable.strings */
"call_monitor_alert_title" = "Sicherheitshinweis";
```

**Override example** (`Localizable.xcstrings` — Xcode 15+):

Add the key in the String Catalog UI and provide translations per language. The compiled output is identical to `.strings`.

---

## Limitations

`Call Monitor` relies on iOS's `CXCallObserver` API to observe call state. As a result, its detection scope is limited to the following call types:

* **Cellular calls** — standard GSM/LTE/5G phone calls managed by the iOS telephony stack.
* **VoIP calls** — calls that are integrated with CallKit and surfaced through the native iOS call UI (e.g. FaceTime, WhatsApp).

The following types of voice communication are **not detected** and will **not** trigger the security policy:

* Voice or video calls made inside a **web browser** (e.g. Google Meet, Microsoft Teams, or any WebRTC-based call opened in Safari or another browser).
* Calls handled entirely within a **third-party app** that does not integrate with CallKit (e.g. Zoom, Discord, and similar apps).

---
