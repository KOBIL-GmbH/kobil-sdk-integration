> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/push-notification/push-content> on 2026-09-28. Converted to Markdown; wording unchanged.

# Push Content

### iOS/Swift (without Flutter apps)")

This is part of the content of a push notification sent to the app, when using 'APN' Push Token prefix:

```
{
"aps": {
"alert": {
"title-loc-key or title": "<key or LocalizedTitle>",
"loc-key or message": "<key or LocalizedBody>"
},
"sound": "default",
"content-available": 1
},
"category": "<e.g. chat, payment>",
"to": {
"userId": "<The recipients user this push notification is sent to. Pseudonym in UUID format>",
"tenantId": "<The recipients user this push notification is sent to.>"
},
"messageId": "...",
}
```

### Android/Kotlin (also Huawei)")

This is part of the content of a push notification sent to the app, when using 'FCM' or 'HPK' Push Token prefix:

```
{
"data": {
"title_loc_key": "<key or localizedTitle>",
"message": "<key or localizedBody>",
"sound": "default",
"category": "<e.g. chat, payment>",
"to": {
"userId": "<The recipients user this push notification is sent to. Pseudonym in UUID format>",
"tenantId": "<The recipients user this push notification is sent to>",
},
"messageId": "...",
}
}
```

> **Note**: Note that we only send data messages and no notification messages meaning the FCM SDK / HMS sdk will not handle the push message automatically.
> The push message needs to be handled by the app in the onMessageReceived() method of the FirebaseMessagingService / HmsMessageService.
> See [FCM-docs](https://firebase.google.com/docs/cloud-messaging/concept-options#data_messages) and [HMS-docs](https://developer.huawei.com/consumer/en/doc/development/HMSCore-Guides/funtion-description-0000001050148080#section45143010280)

### Flutter (for all platforms)")

This is part of the content of a push notification sent to the app, when using 'FCMF' Push Token prefix:

```
{
"notification": {
"title_loc_key or title": "<key or localizedTitle>",
"body_loc_key or message": "<key or localizedBody>",
"sound" : "default",
},
"data": {
"title_loc_key": "<key or localizedTitle>",
"message": "<key or localizedBody>",
"sound": "default",
"category": "<e.g. chat, payment>",
"to": {
"userId": "<The recipients user this push notification is sent to. Pseudonym in UUID format>",
"tenantId": "<The recipients user this push notification is sent to>",
},
"messageId": "...",
}
}
```
