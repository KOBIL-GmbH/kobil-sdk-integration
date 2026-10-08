> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/master-controller-handler> on 2026-09-28. Converted to Markdown; wording unchanged.

# Communication with the MasterController (Android/Kotlin and Flutter)

We communicate with the Master Controller by sending and receiving events. We do this through the **SynchronousEventHandler**.

## Android/Kotlin Implementation

We mainly use three methods of the **SynchronousEventHandler** to communicate with the Master Controller:

1. **`postEvent(event: EventFrameworkEvent)`:** This method sends an event to the Master Controller. We use it when we expect a result event after triggering an event on the Master Controller side. By implementing the **`then{}`** block on **`postEvent()`**, we can retrieve and handle the result event. The **`postEvent()`** method returns a **Future** object, and its **`get()`** method returns an **EventFrameworkEvent**, which is the superclass of all events.
2. **`forwardEvent(event: EventFrameworkEvent)`:** Similar to **`postEvent()`**, this method sends events to the Master Controller. However, it operates as a "Fire and Forget" mechanism, meaning it does not expect a result event for the triggered event. We use this method when no result event is expected; however, using **`postEvent()`** in such cases works just as well. [Here you can find the events table.](shift-lite-idpsdk__mcsdk-api__ast_event_list.md)
3. **`executeEvent(eventFrameworkEvent: EventFrameworkEvent?)`:** This method receives events from the Master Controller. You should override it to make your app react to events/result events coming from the MC.

> We suggest that you override executeEvent in some kind of global observer in your app to ensure you can always react to a [**RestartEvent**](shift-lite-idpsdk__development__start.md) sent by the MC.

> ⚠️ **Important:** Instantiate your `SynchronousEventHandler(Context)` implementation as early as possible in the app lifecycle (e.g., in your `Application.onCreate`).

example override of executeEvent

```
override fun executeEvent(event: EventFrameworkEvent?) {
when (event) {
is RestartResultEvent -> {
when (event.sdkState) {
SdkState.ACTIVATION_REQUIRED -> {
// go to activation screen...
}
SdkState.LOGIN_REQUIRED -> {
// go to login screen...
}
else -> {
// unexpected...
}
}
}
// ...
}
}
```

---

### Non-Blocking Asynchronous Handling with `then{}` Block

The recommended approach for handling postEvent results is using the **`then{}`** block, which allows you to handle the result event asynchronously **without blocking** the calling thread.

#### **Basic `then{}` Usage**

```
synchronousEventHandler.postEvent(restartEvent)?.then { resultEvent ->
when (resultEvent) {
is RestartResultEvent -> {
// Handle restart result
when (resultEvent.sdkState) {
SdkState.ACTIVATION_REQUIRED -> {
// Navigate to activation screen
}
SdkState.LOGIN_REQUIRED -> {
// Navigate to login screen
}
SdkState.LOGGED_IN -> {
// Navigate to main screen
}
}
}
// Handle other result types...
}
}
// This code executes immediately without waiting for the result
println("Event sent, continuing with other operations...")
```

> **Advantage:** Code execution continues immediately after sending the event, without waiting for the result. The `then{}` block executes asynchronously when the result is received.

#### **Key Benefits of `then{}` Block**

* **Non-blocking**: UI remains responsive while waiting for results
* **Asynchronous**: Result handling happens when the response arrives
* **Thread-safe**: Callbacks execute on appropriate threads
* **Clean code**: Avoids complex threading and callback management
* **Error handling**: Easy to implement try-catch blocks within the callback

> **Best Practice:** Use `then{}` block for most postEvent operations to maintain responsive UI and clean asynchronous code flow. Reserve blocking methods (`get()`, `waitResult()`, `waitResultFor()`) for special cases where synchronous behavior is required.

---

### MC-Future Methods for Synchronous Handling

The **Future** object returned by `postEvent()` provides several methods for blocking operations:

#### **`get()`** - Block Until Future Resolved

```
val future = synchronousEventHandler.postEvent(event)
val resultEvent = future.get() // Blocks until future is resolved
// Handle the result event
```

> **⚠️ IMPORTANT:** The `get()` method **blocks the calling thread** until the future is resolved. Use carefully to avoid blocking the UI thread.

#### **`waitResult()`** - Block Until Future Resolved (No Return)

```
val future = synchronousEventHandler.postEvent(event)
future.waitResult() // Blocks until future is resolved (no return value)
// Future is now resolved
```

#### **`waitResultFor(milliseconds)`** - Block with Timeout

```
val future = synchronousEventHandler.postEvent(event)
val status = future.waitResultFor(5000) // Wait max 5 seconds
when (status) {
Status.READY -> {
// Future resolved within timeout
val resultEvent = future.get()
// Handle result
}
Status.TIMEOUT -> {
// Future did not resolve within timeout period
// Handle timeout case
}
}
```

#### Usage Examples with Blocking Operations

```
// Example 1: Direct blocking call
fun performSynchronousLogin(userIdentifier: UserIdentifier): LoginResultEvent {
val loginEvent = LoginEvent(userIdentifier)
val resultEvent = synchronousEventHandler.postEvent(loginEvent)?.get() // Blocks here
return resultEvent as LoginResultEvent
}
// Example 2: Blocking with timeout
fun performLoginWithTimeout(userIdentifier: UserIdentifier): LoginResultEvent? {
val loginEvent = LoginEvent(userIdentifier)
val future = synchronousEventHandler.postEvent(loginEvent)
val status = future?.waitResultFor(10000) // Wait max 10 seconds
return if (status == Status.READY) {
future.get() as LoginResultEvent
} else {
null // Timeout occurred
}
}
```

> **⚠️ Threading Warning:** These blocking methods will block the calling thread. Avoid using them on the main/UI thread, as this will freeze the user interface. If you need to use these methods, ensure they are only called in background threads or coroutines.

---

## Flutter/Dart Implementation

For Flutter, we use a helper class called **McWrapperHandler** in our demo app. The McWrapperHandler class serves as a wrapper around the **McWrapperApi** and provides methods for communicating with the Master Controller.

### Key Features of McWrapperHandler:

1. **Singleton Pattern:** Ensures a single instance throughout the app lifecycle
2. **Event Sending:** Uses the `send()` method to communicate with the Master Controller
3. **Event Receiving:** Implements `McWrapperApiEventReceiver` to handle incoming events
4. **Observer Pattern:** Allows multiple observers to listen for Master Controller events
5. **Lifecycle Management:** Provides start, stop, suspend, and resume functionality

McWrapperHandler Structure (Flutter/Dart)

```
class McWrapperHandler extends McWrapperApiEventReceiver {
late McWrapperApi _mcWrapperApi;
static final McWrapperHandler _instance = McWrapperHandler._internal();
List<McWrapperApiEventReceiver> receivers = [];
McWrapperApi get api => _mcWrapperApi;
factory McWrapperHandler() {
return _instance;
}
}
```

### Flutter/Dart Usage Examples

#### Getting Instance and Initialization

Getting McWrapperHandler Instance (Flutter/Dart)

```
// Get the singleton instance
final mcHandler = McWrapperHandler();
// Or get from service locator (see below for further details)
// final mcHandler = locator<McWrapperHandler>();
// Initialize the wrapper
await mcHandler.initializerMethod();
```

#### Sending Events to the Master Controller

Sending Events (Flutter/Dart)

```
Future<void> sendEventToMC() async {
try {
// Create your event
final startEvent = StartEventT();
// Send event and handle response
final response = await mcHandler.send(startEvent);
response.fold(
(error) {
print("❌ Error sending event: $error");
},
(result) {
print("✅ Event sent successfully: $result");
// Handle the result event
},
);
} catch (e) {
print("❌ Exception: $e");
}
}
```

#### Adding Event Observers

Adding Event Observer (Flutter/Dart)

```
class MyEventReceiver extends McWrapperApiEventReceiver {
@override
void onReceive(Object event) {
print("📥 Received event: ${event.runtimeType}");
// Handle specific event types
if (event is TriggerBannerEventT) {
handleTransactionEvent(event);
} else if (event is StartResultEventT) {
handleStartResult(event);
}
}
void handleTransactionEvent(TriggerBannerEventT event) {
// Handle transaction events
}
void handleStartResult(StartResultEventT event) {
// Handle start result events
}
}
// Add the observer
void setupEventHandling() {
final mcHandler = locator<McWrapperHandler>();
final eventReceiver = MyEventReceiver();
mcHandler.addObserver(eventReceiver);
}
```

#### Removing Event Observers

Removing Event Observer (Flutter/Dart)

```
void cleanupEventHandling() {
final mcHandler = locator<McWrapperHandler>();
final eventReceiver = myEventReceiverInstance;
mcHandler.removeObserver(eventReceiver);
}
```

#### Lifecycle Management

Lifecycle Management (Flutter/Dart)

```
class MyApp extends StatefulWidget with WidgetsBindingObserver {
@override
void didChangeAppLifecycleState(AppLifecycleState state) {
final mcHandler = locator<McWrapperHandler>();
switch (state) {
case AppLifecycleState.resumed:
mcHandler.resumeWrapper();
break;
case AppLifecycleState.paused:
mcHandler.suspendWrapper();
break;
case AppLifecycleState.detached:
mcHandler.stopWrapper();
break;
default:
break;
}
}
}
```

### Flutter Service Locator Integration

In Flutter, we use a **service locator** (GetIt) to manage dependencies and provide global access to the McWrapperHandler instance. This approach offers several benefits:

* **Singleton Management**: Ensures only one instance of McWrapperHandler exists throughout the app
* **Global Access**: Any part of the app can access the handler without passing it through constructors
* **Dependency Injection**: Simplifies testing by allowing easy substitution of mock implementations
* **Lifecycle Management**: Centralized control over when services are created and destroyed
* **Decoupling**: Reduces dependencies between classes by providing a central registry

Service Locator Setup (Flutter/Dart)

```
GetIt locator = GetIt.instance;
Future<void> setupDependencies() async {
// Initialize McWrapperHandler
final mcHandler = McWrapperHandler();
await mcHandler.initializerMethod();
// Register in service locator as singleton
locator.registerSingleton<McWrapperHandler>(mcHandler);
// Add observers for transaction handling
final transactionReceiver = TransactionEventReceiver();
mcHandler.addObserver(transactionReceiver);
locator.registerLazySingleton(() => transactionReceiver);
}
// Access from anywhere in the app
void useFromAnywhereInApp() {
final mcHandler = locator<McWrapperHandler>();
// Use the handler...
}
```

## Event Handling with KSSIDP (Android)")

If you are using KSSIDP in your project, there are two approaches for receiving events from the Master Controller:

### Using KSSIDP's EventListener

If you are using KSSIDP via `com.kobil.kssidp.wrapper.masterController.EventListener`, make sure your `onEventReceived` implementation handles the relevant events. You must also register your listener:

```
KssIdp.addEventListener(yourEventListenerImpl)
```

### Using the MC Wrapper Directly

If you are using the MC wrapper directly via `com.kobil.wrapper.SynchronousEventHandler`, make sure your `executeEvent` override handles the relevant events (as described [above](#androidkotlin-implementation)).

## Important Notes

> **NOTE:**
>
> * Always remove observers when they are no longer needed to prevent memory leaks
> * Handle app lifecycle events to properly suspend/resume the wrapper
