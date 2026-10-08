> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/push-notification/push-token> on 2026-09-28. Converted to Markdown; wording unchanged.

# Push Token

For receiving push notifications, we need to set the app device push token via MC using SetPushTokenEvent. [**This table**](shift-lite-idpsdk__mcsdk-api__ast_event_list.md#push-token) shows the list of events that are used to set the app device push token.

We use different Push Notification providers depending on the client platform, so the app has to use the correct prefix:

| Client platform | Push Notification provider | Push Token prefix |
| --- | --- | --- |
| Android (without Flutter apps) | Google's Firebase Cloud Messaging (FCM) | FCM: |
| Flutter on Android, Flutter on iOS | Google's Firebase Cloud Messaging (FCM) | FCMF: |
| Huawei | Huawei Push Kit (HPK) | HPK: |
| iOS (without Flutter apps) | Apple Push Notification service (APNs) | APN: |

## **SetPushToken Event Flow Diagram**

This diagram shows the internal workings of the set app device push token functionality.

![](https://www.plantuml.com/plantuml/png/PSmn2W9134RXVawH2tY1BMH5B0LHIvl13Rk3sMH8_j7hYzWCsh_tZO7iQAkajAjLoZsZcD9cIySSOD-Rmas4VQ0-W9TvPW-wC4ujbgizM0zFLgJVyODrw_0datDKqodeLR3GJNlppD44NpcDh5DRvGq0)
> In order to keep the push token up to date on the server at all times, you could call the SetPushTokenEvent after every successful login.
> Alternatively, to reduce unnecessary communication with your server, you could store a hash of your token,
> and with each login, compare it with the hash of the current token returned by your Push Notification provider before deciding whether to trigger SetPushTokenEvent.

## **Push Notifications with TMS Flow Diagram**

The event flow diagram illustrates the sequence of events during the Push Notification and TMS process for KOBIL products.

![](https://www.plantuml.com/plantuml/png/VLBBSeCm3Bpp5JhrrX_Wq0afEMJoOZ3JksCKeW5iuaVw-nqRXX1ASfLMgzsLLiPoRLtRH0NP1cDOSrcJh23fEiYSkS9HMRgGu9QKX0ye3WmOtXnAWP0IhpHlesYOyaEVNv1aHnD3ZXKPYnekIaFdp3NoTTz_e6D8yKu2mQeQvOpcyCtINGmChHTI14Ie-URkjDxksIR_sUIJLJtDf3VXIKGjrM-3POMWmu0EfXwSKrqlqKjMcJiReUcCxxqEi2v4oSS5BKexetrojvLaYLlqsS-z3VjHbY0dXnhNqudr2Vka6xfZB-yPF8B-2VRF4Lw1o_8DmUBTzggYLxS8WhsTnSbCAu76X5-3Q8MoT6tp1m00)

## Implementation Examples

### iOS/Swift

There are a few steps you have to implement for getting your app device push token:

1. Register your app for RemoteNotifications. You can add this to your AppDelegate

AppDelegate

```
func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions:
[UIApplication.LaunchOptionsKey: Any]?) -> Bool {
registerForPushNotifications(application: application)
}
```

RegisterForRemoteNotifications

```
func registerForPushNotifications(application: UIApplication){
if #available(iOS 10.0, *){
UNUserNotificationCenter.current().delegate = self
UNUserNotificationCenter.current().requestAuthorization(
options: [.badge, .sound, .alert], completionHandler: { (granted, error) in
DispatchQueue.main.async {
UIApplication.shared.registerForRemoteNotifications()
}
})
}
else {
let notificationSettings = UIUserNotificationSettings(types:
[.badge, .sound, .alert], categories: nil)
application.registerUserNotificationSettings(notificationSettings)
}
}
```

You must save the app device token with the prefix "APN:". If you do not provide any prefix the master controller will append "GCM:", and this will lead to an error and the application will not receive the push notification. So, it is important to save the app device token with the server type which you are using for push notification. Here we are using APNS, so we have added "APN:" as a prefix.

RegisterForRemoteNotificationsWithDeviceToken

```
func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
AppDelegateLog(title: "AppDelegate",
action: "didRegisterForRemoteNotification",
logLevel: .trace,
component: "AppDelegate")
let deviceTokenString = deviceToken.reduce("", {$0 + String(format: "%02X", $1)})
if deviceTokenString.isEmpty == false {
appCoordinator.setPushToken(pushToken: "APN:\(deviceTokenString)")
print("Token received")
}
}
```

Also, do not forget to add the push notification in signing capabilities as shown in the below screenshot

![](https://developer.kobil.com/assets/images/Aspose.Words.c5ff49bf-0412-4fd6-9e0f-40984ea08b5f.008-4cec63d5e8819f0a8f33bd4c1a37d67d.png)

After getting the app device token, save it for later use. Once you receive LoginResultEvent and its status is OK, trigger the setPushToken event.

SetPushToken

```
static func performSetPushToken() async -> ActionResult {
return await withCheckedContinuation { continuation in
let setPushTokenEvent = KSMSetPushTokenEvent(pushToken: pushToken)
let timer = CallTimer(event: setPushTokenEvent)
MasterControllerAdapter.sharedInstance.sendEvent2MasterController(event: setPushTokenEvent) { resultEvent in
let duration = timer.stop()
let title = "pushModel.title".localized(table: localizedTable)
var errorText: String?
var success = false
if let pushTokenResult = resultEvent as? KSMSetPushTokenResultEvent {
let status = handlePushTokenResultStatus(status: pushTokenResult.status)
success = status.success
errorText = status.errorText?.localized(table: localizedTable)
} else if resultEvent is KSMInvalidStateEvent {
errorText = "pushModel.event.invalidStateEvent".localized(table: localizedTable)
} else {
errorText = "pushModel.event.unexpectedEvent".localized(table: localizedTable)
}
let actionResult = ActionResult(title: title,
success: success,
error: errorText,
duration: duration,
event: resultEvent)
continuation.resume(returning: actionResult)
OtelTraceHandler.shared.complete(traceName: "PushTokenSpan")
}
}
}
```

### Android/Kotlin (also Huawei)")

To generate an app device push token using FCM, you need to have certain configurations. Google provides a good [**description**](https://firebase.google.com/docs/cloud-messaging/android/client) where you can find all the FCM configuration-related steps.

To generate an app device push token using Huawei Push Kit (HPK), you need to have certain configurations. Huawei provides a detailed [**description**](https://developer.huawei.com/consumer/en/codelab/HMSPreparation/index.html#0) where you can find all the HMS configuration-related steps.

Once you obtain the app device push token using either FCM or HMS, you need to send it to MC using SetPushTokenEvent. As a result of this event, you will receive SetPushTokenResultEvent.

```
fun triggerSetPushToken(pushToken: String) {
synchronousEventHandler.postEvent(SetPushTokenEvent(pushToken))?.then {
when (resultEvent) {
is SetPushTokenResultEvent -> {
// handle result
// NOTE: this is a good place to trigger SetLocalesEvent
}
else -> {
}
}
}
}
```

### Flutter/Dart

For Flutter applications, we use Firebase Cloud Messaging (FCM) for both Android and iOS platforms. The token must be prefixed with "FCMF:" to indicate it's from a Flutter FCM implementation.

NotificationService Setup (Flutter/Dart)

```
// Call this after successful login
Future<void> setupPushNotifications() async {
// Initialize Firebase Messaging
final fcm = FirebaseMessaging.instance;
// Request permission (especially important for iOS)
final settings = await fcm.requestPermission(
alert: true,
badge: true,
sound: true,
);
if (settings.authorizationStatus == AuthorizationStatus.authorized) {
// Get the FCM token
final token = await fcm.getToken();
if (token != null) {
// Add FCMF prefix for Flutter FCM
final pushToken = 'FCMF:$token';
// Send token to MC after successful login
await sendPushTokenToMC(pushToken);
}
} else {
print('❌ User declined push notification permission');
}
}
Future<void> sendPushTokenToMC(String pushToken) async {
try {
// Create SetPushTokenEvent
final setPushTokenEvent = SetPushTokenEventT()
..pushToken = pushToken;
// Get your McWrapperApi instance
final mcApi = locator<McWrapperApi>();
// Send the event
final response = await mcApi.send(setPushTokenEvent);
response.fold(
(error) => print("❌ Push token error: $error"),
(result) => print("✅ Push token sent successfully"),
);
} catch (e) {
print("❌ Exception setting push token: $e");
}
}
```
