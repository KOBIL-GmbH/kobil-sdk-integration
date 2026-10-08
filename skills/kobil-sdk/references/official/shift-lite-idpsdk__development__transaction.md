> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/transaction> on 2026-09-28. Converted to Markdown; wording unchanged.

# Transaction

A Transaction is a message sent to a user's app when they are logged in to Security Service. To handle situations when the app is not running or in the background, a push notification is sent to inform the user.

The app can be in one of four states when you receive a Transaction:

![](https://www.plantuml.com/plantuml/png/bP3D2i8m48JlUOh1n-YfyUP5nJv1R88DjflGtIX5V7THYyOVYjvsXXdcOqiMqqlgMiLYn66cOmG5GP-8FErcC8nbaEeQSrOzpm9-LHLO9sxW6Un8OCYYCMHRPx4Tm0EBwruwccmVl9tkwHXp74_Ocdg_wqCYUmDQqFnXg5py3lNQ-XahvzfaBz8nZX8d1MIfevSc986fnHySs37xGEDVzSsixfx2kpFDOsBydFgsyxxovyPPbOviwjeB)

There are mainly two types of transactions:

* **Wire Transfer** (without authentication confirmation)
* **Wire Transfer - free text** (with and without authentication confirmation)

One more type of transaction is Send Message which is mainly used to display some message in the application and does not require any pin confirmation. Below is the diagram to understand the Transaction event categorization:

![](https://developer.kobil.com/assets/images/transaction_categories-33bcc79b376991488b074580a9a136c8.png)

A user will receive transactions only if they are logged into the application. Furthermore, a user can receive transaction requests irrespective of the screen they are on.
The Transaction flow involves a specific [**set of events**](shift-lite-idpsdk__mcsdk-api__ast_event_list.md#transaction), and always starts with a [**TriggerBannerEvent**](shift-lite-idpsdk__mcsdk-api__individual_events.md#triggerbannerevent) sent by the MC-SDK.

Note that the server side is expected to select a localization of the texts sent to the app based on the language information that was provided in the [**StartEvent**](shift-lite-idpsdk__development__start.md).

## **Transaction Event Flow Diagram**

The following diagram shows the event flow in detail.

![](https://www.plantuml.com/plantuml/png/lPNFRjGm4CRlVeevWjI-049LeO2qGeMgjEAIYuadcv6IiR4dNLRgmoFRoQwZJSjMBDnsOtl-VFFpvyiWsilGTqhfJe0QkFEQWww5B0C582OXBMYWyRQ7YlkLGHQIBMZdm61lmLalkbFgdNCTrJeTVNiErpe8-YlBuctNeNzpy0N4qtgDFi1T_l5UCwF_-80iKF6cHGOD0Tb0Zo7eDOBre47cDLQyhz8oI8kxadPD7OHttZwGmNWwVxxREln0mNLwUpqcqt7rHre5sJgSjtX-iT1YkM7NtRSeyZnsAaAf0qNEByeG2v9v3Cwo2R0XQQ7YXR1GiTYfGI1khEzpHMd1v1C7pSpoZkgEUwCEkmcaCCK4GkqH-QXm-0lhGPBeJscIQso8ARHfbFDapjiQGmoWsSJoUah_uiwbef2DKb-i87XQjwBKc1Ac6PUyDvtTAFMH3R0LLEhnyN67qD4CbG4hrW5E1L0HUAHduSf6jT8XD8aGEmWuOl3uSy1mIkAkB3SqWdMReuzb7G62ynYG9IoYj1zkcjG8ti8ilvCV1zYWdxNxt2IVa-k5MXrYNGI_eQGBUJGdrYUgK_6ap_qAR9CAF_PgBbAtfwtYcmps3MNINkb6q4F5o8AUU9qzDkfiFJpeZaoA_VeKUErpts8OkYpQMJJv1e9e6KBq_A-Vp_AjPzWWjD7effeglb_z1yxdBXkJ5s_KV0ob1R_GW0TdT2GhE-7zAYaUMhkPfl1afgFkozENvO_87BA_8DZkAO-vWiEQ6aAJl312Mt5TR8Q8i3U9jFaRKBJupoOxOosFTT9unAvYsq1PyDywnAVK8PhdqzgcxFzisHBMADaIudk81bhqasDU8fkXxtu3)
> **NOTE**: After triggering the StartTransactionEvent, the App is expected to only handle the transaction.
> Using events that are not related to the transaction will result in InvalidStateEvent on Digitanium
> and may result in InvalidStateEvent on Shift environments (astServerBackend == maverick), with the exception of the following events:
> SetProperty, GetProperty, SetPushToken, SetDeviceName, ExchangeIamToken, SetLocales, ProvideNonce, DeleteIamTokenByAudience.

## **Transaction Sequence Diagram**

For a better understanding of this decisive flow, here is a diagram that additionally shows the interaction of the various screens in our demo application:

![](https://www.plantuml.com/plantuml/png/bLJ1Rjim3BthAuZsqW1Tccsd-32qInkaW3CKbO5TSj4i9Y5gKvuajylGZnzaExKS91rwCwJ7n_SUHLyxhwoloq88zqHSAQjASFYxHixnnbhpacqfVs9q3hv646jgrhcnZ1Q-JAABKlqfqJcrGKT_4JvF9aU8botYfg0DGuxiqGfHAUiffqgnXpCPPCdS8l8PA0TImlbqEfzFfqDSQZR44IuzWLkO4YFOuWGiiugToZsPc3GxWLugvz7E37jhYW9j0rxEu7mocKwdSo42qxFo25BstykPa18-VOFbB876vzqpiXVBMJYKiZjidFLLgUogKYaqniGQdRTc5pxJDzwckk6zg1tQ-rjGhA4Y7dLzKjc17j7LHIlXmlZgCi198tjQ4zhnU3mUTRmBcVHw5WCPQIyZbKAemWEj8KeJo04nUL8UDQojAM75vNtJn-z0LHLeB0rKndfLY4xaGYQGMTfiq7vNp6XRcRxdpNOLZiHYc6VKjuss5tJ81PKrpwJHmOhRuy1uIwugrAvxfc6gA_xLt8BVLNZORmYFfnaC7Bczw5OaWUvZr0URoOu-amdejXOYn_kIEFwiZp-J0bcB7yOZMDfilUZwmzvDF9LrOLx47MjWur6ylhv-DAcORCNAGHpJaMUmOjyoeuONybjJ-_0gmOO_WpiIsypmccofGlLZ2se3FXROGIO7GVmasxbVenrqVoU6qz9Fw8vA7gYHJ1RrG7e_ttYk7LMW7PZBtXxRGpk1X_rcLyH9W5z27gKKnfA0URhA5UTON7agqTH-l_YXRKyKRx_pojSknlrd1l4YtlFQZFwV-8cuUuz7MiOBTL9LR-E3MKJpcXEJsw8Unl7kdebhP5sNnJy0)

As an app developer you can trigger a transaction by following [the instructions](shift-lite-idpsdk__testing__tms__test_tms.md).

## Implementation Examples

### iOS/Swift

Here are two code snippets for Swift:

Transaction (Swift)

```
func receive(_ event: KsEvent, withCompletionHandler completionBlock: ((KsEvent?) -> Void)? = nil) {
if let triggerBannerEvent = event as? KSMTriggerBannerEvent {
handleTriggerBanner(triggerBanner: triggerBannerEvent)
} else if let displayConfirmationRequestEvent = event as? KSMDisplayConfirmationRequestEvent {
handleDisplayConfirmationRequestEvent(displayConfirmationRequestEvent: displayConfirmationRequestEvent)
} else if let displayConfirmationResultEvent = event as? KSMDisplayConfirmationResultEvent {
handleDisplayConfirmationResultEvent(displayConfirmationResultEvent: displayConfirmationResultEvent)
} else if let transactionFinished = event as? KSMTransactionFinishedEvent {
handleTransactionFinished(transactionFinished: transactionFinished)
}
}
func handleTriggerBanner(triggerBanner: KSMTriggerBannerEvent) {
if triggerBanner.bannerType == .transaction {
let transactionInfo = TransactionInfo(timer: Int(triggerBanner.timer), payload: triggerBanner.payload)
if delegate != nil {
OtelTraceHandler.shared.start(traceName: kTransactionSpanName)
delegate?.transactionAvailable(transactionInfo: transactionInfo)
}
}
}
func handleTransactionFinished(transactionFinished: KSMTransactionFinishedEvent) {
let duration = timer?.stop()
let actionResult = ActionResult(title: "transactionModel.title".localized(table: localizeTable),
success: true, error: nil, duration: duration, event: nil)
EventLogObject(actionResult: actionResult,
component: localizeTable)
OtelTraceHandler.shared.complete(traceName: kTransactionSpanName)
if confirmBlock != nil {
confirmBlock!(actionResult)
confirmBlock = nil
}
}
func handleDisplayConfirmationRequestEvent(displayConfirmationRequestEvent: KSMDisplayConfirmationRequestEvent) {
let data = TransactionData(time: Int(displayConfirmationRequestEvent.timerValue),
transactionText: displayConfirmationRequestEvent.transactionInformation)
if startBlock != nil {
startBlock!(data)
startBlock = nil
}
}
func confirmTransaction (confirmation: TransactionConfirmation, completion: @escaping (ActionResult) -> Void) {
let displayConfirmationName = "DisplayConfirmation"
OtelTraceHandler.shared.addSubTrace(traceName: kTransactionSpanName, subTraceName: displayConfirmationName)
let traceParent = OtelTraceHandler.shared.getTraceParent(traceName: displayConfirmationName)
let event = KSMDisplayConfirmationEvent(confirmationType: confirmation.confirmationType,
andTransactionInformation: confirmation.transactionInformation)
let traceState = event.traceContext.traceState
event.traceContext = .init(traceParent: traceParent, traceState: traceState)
confirmBlock = completion
MasterControllerAdapter.sharedInstance.masterController?.receive(event)
OtelTraceHandler.shared.complete(traceName: displayConfirmationName)
}
func handleDisplayConfirmationResultEvent(displayConfirmationResultEvent: KSMDisplayConfirmationResultEvent) {
let duration = timer?.interval()
let actionResult = ActionResult(title: "transactionModel.title".localized(table: localizeTable),
success: true,
error: nil,
duration: duration,
event: nil)
EventLogObject(actionResult: actionResult,
component: localizeTable)
}
```

After receiving [**TriggerBannerEvent**](shift-lite-idpsdk__mcsdk-api__individual_events.md#triggerbannerevent), the UI will trigger a **StartTransactionEvent** or a **StartDisplayMessageEvent** depending on the received BannerType.

Trigger-Events-As-Per Transaction Event received (Swift)

```
if KSMTriggerBannerEvent.bannerType == .transaction{
masterControllerAdapter.sendEvent2MasterController(
KSMStartTransactionEvent(), withCompletionHandler: nil)
}else {
masterControllerAdapter.sendEvent2MasterController(
KSMStartDisplayMessageEvent(), withCompletionHandler: nil)
}
```

### Android/Kotlin

Below is the code sample to handle transaction events in Kotlin:

Handling Transaction Events (Kotlin)

```
override fun executeEvent(event: EventFrameworkEvent?) {
when (eventFrameworkEvent) {
is TriggerBannerEvent -> {
when (eventFrameworkEvent.bannerType) {
BannerType.TRANSACTION -> {
// trigger StartTransactionEvent
}
BannerType.DISPLAY_MESSAGE -> {
// trigger StartDisplayMessageEvent
}
}
}
is TransactionPinRequiredRequestEvent -> {
}
is DisplayConfirmationRequestEvent -> {
}
is DisplayConfirmationResultEvent -> {
}
is DisplayMessageEvent -> {
}
is TransactionEndEvent -> {
when (eventFrameworkEvent.status) {
StatusType.OK -> {}
StatusType.USER_CANCEL -> {}
StatusType.NOT_REACHABLE -> {}
StatusType.USER_CONFIRMATION_TIMEOUT -> {}
else -> {}
}
}
is ProvidePinResultEvent -> {
when (eventFrameworkEvent.status) {
StatusType.OK -> {}
StatusType.USER_CANCEL -> {}
StatusType.NOT_REACHABLE -> {}
StatusType.USER_CONFIRMATION_TIMEOUT -> {}
else -> {}
}
}
}
}
```

### Flutter/Dart

Below is the code sample to handle transaction events in Flutter:

Handling Transaction Events (Flutter/Dart)

```
class TransactionEventReceiver extends McWrapperApiEventReceiver {
@override
void onReceive(Object event) {
if (event is TriggerBannerEventT) {
_handleTriggerBannerEvent(event);
} else if (event is TransactionPinRequiredRequestEventT) {
_handleTransactionPinRequired(event);
} else if (event is DisplayConfirmationRequestEventT) {
_handleDisplayConfirmationRequest(event);
} else if (event is DisplayMessageEventT) {
_handleDisplayMessage(event);
} else if (event is TransactionEndEventT) {
_handleTransactionEnd(event);
}
}
void _handleTriggerBannerEvent(TriggerBannerEventT event) {
print("📱 Transaction triggered: ${event.bannerType}");
switch (event.bannerType) {
case BannerType.transaction:
case BannerType.pushReceived:
_triggerStartTransactionEvent();
break;
case BannerType.displayMessage:
_triggerStartDisplayMessageEvent();
break;
default:
print("❓ Unknown banner type: ${event.bannerType}");
}
}
void _handleTransactionPinRequired(TransactionPinRequiredRequestEventT event) {
print("🔐 PIN required for transaction");
print("   Timer value: ${event.timerValue}");
// Navigate to PIN input screen
// Handle the timer value for PIN timeout
}
void _handleDisplayConfirmationRequest(DisplayConfirmationRequestEventT event) {
print("✅ Display confirmation request");
print("   Transaction info: ${event.transactionInformation ?? 'No info'}");
print("   Timer value: ${event.timerValue}");
// Show transaction confirmation screen
}
void _handleDisplayMessage(DisplayMessageEventT event) {
print("💬 Display message event");
print("   Message: ${event.messageInformation ?? 'No message'}");
// Show message screen or popup
}
void _handleTransactionEnd(TransactionEndEventT event) {
print("🏁 Transaction ended with status: ${event.status}");
switch (event.status) {
case StatusType.ok:
print("✅ Transaction successful");
break;
case StatusType.userCancel:
print("❌ Transaction cancelled by user");
break;
case StatusType.userConfirmationTimeout:
print("⏰ Transaction timed out");
break;
default:
print("💥 Transaction failed: ${event.status}");
}
}
Future<void> _triggerStartTransactionEvent() async {
try {
final mcApi = locator<McWrapperApi>();
final startTransactionEvent = StartTransactionEventT();
final response = await mcApi.send(startTransactionEvent);
response.fold(
(error) => print("❌ Start transaction error: $error"),
(result) => print("✅ Start transaction sent successfully"),
);
} catch (e) {
print("❌ Exception in start transaction: $e");
}
}
Future<void> _triggerStartDisplayMessageEvent() async {
try {
final mcApi = locator<McWrapperApi>();
final startDisplayMessageEvent = StartDisplayMessageEventT();
final response = await mcApi.send(startDisplayMessageEvent);
response.fold(
(error) => print("❌ Start display message error: $error"),
(result) => print("✅ Start display message sent successfully"),
);
} catch (e) {
print("❌ Exception in start display message: $e");
}
}
}
```
