> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/push-notification/push-localization> on 2026-09-28. Converted to Markdown; wording unchanged.

# Push Localization

For receiving localized push notification titles and body messages, there are two different ways:

1. **Server side Localization:** The server sends already localized values inside the push notification. While in the case of [**transactions**](shift-lite-idpsdk__development__transaction.md) our app actively fetches the text, transmitting locale information in the request, here the server simply pushes texts to the device without first receiving a request. Thus, it is challenging to select the correct locale. To alleviate this issue, the app can store a set of preferred locales on the server side by sending a SetLocales event. Then, the service sending the push message can look up the preferred locales, check which locales it supports, and select a corresponding localization. Note, however, that this option may still lead to incorrect localization when the server side does not know the current locale of the current smartphone, e.g., when a user has multiple devices with different locales.
2. **App side Localization:** The server sends keys inside the push notification that the app needs to translate with its own localized files. This option concentrates all app localization resources on the app side.

We recommend localizing push notifications on the app side.

[**Look here**](shift-lite-idpsdk__development__push-notification__push-content.md) for more information about push content.

### Server side Localization

#### **SetLocales event flow-diagram**

This diagram shows the internal workings of setting the locales for push functionality.

![](https://www.plantuml.com/plantuml/png/PSmn3i8m34RXFQVm1Ng13gWLOeC5JX2rLedasf7z1wwFAfO8zlU-D0Moe-sIqbohb2MZcD9mebiEi9zDuIR2Fb8VmCksiGSz65TRid1SNgn8lzj1TUFuvv9pLDCrw5tmxBmxHnDyrJInhcsN3m00)

We recommend calling the SetLocalesEvent after you receive the SetPushTokenResultEvent.

#### iOS/Swift

This shows how to set locales on the server.

SetLocales

```
func setLocales(locales: [String]) async -> ActionResult {
let localesEvent = KSMSetLocalesEvent(locales: locales)
let actionResult = await sendStatusReusultRequest(event: localesEvent)
EventLogObject(actionResult: actionResult, component: localizedTable)
return actionResult
}
```

For further documentation, you can check the Apple developer documentation: <https://developer.apple.com/library/archive/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/CreatingtheNotificationPayload.html>

#### Android/Kotlin

SetLocales

```
fun triggerSetLocalesEvent(){
val setLocales = SetLocalesEvent(listOf("de","en"))
synchronousEventHandler?.postEvent(setLocales)?.then {
logDebug("received Result: $it", "triggerSetLocales")
}
}
```

### App side Localization

To localize push content, you can use the app's normal localization. Therefore, the push content contains two keys that contain the key which must be present in your localized string resource files.

#### iOS/Swift

These are the referenced keys from which the values are used:

```
"title-loc-key": "RESOURCE_KEY_PUSH_NOTIFICATION_TITLE",
"loc-key": "RESOURCE_KEY_PUSH_NOTIFICATION_BODY"
```

For further documentation, you can check the Apple developer documentation: <https://developer.apple.com/library/archive/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/CreatingtheNotificationPayload.html>

#### Android/Kotlin

These are the referenced keys from which the values are used:

1. title-loc-key
2. message
