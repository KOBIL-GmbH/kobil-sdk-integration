> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/api_overview> on 2026-09-28. Converted to Markdown; wording unchanged.

# Overview

As already mentioned in the [Introduction](introduction__mc_sdk.md#sdk-documentation), the Master Controller uses event-based communication with the app. In the following sections, we describe the setup of the framework for sending and receiving events, and then the most important events and how to send or process them.

There are a few things that you absolutely MUST implement on your way to a working app. Here is a short list of these decisive sections:

* [**Bridging-Header (iOS/Swift)**](shift-lite-idpsdk__development__bridging-header.md): Without such a header, you typically lack easy access to some of the functionality of the MC SDK.
* [**Initialization of the MasterController (iOS/Swift)**](shift-lite-idpsdk__development__initialization.md) and
* [**Implement MasterController interface (iOS/Swift)**](shift-lite-idpsdk__development__implement-interface.md): The first step needed to establish a connection between your Swift app on iOS and the MC SDK.
* [**Initialization of the MasterController (Android/Kotlin)**](shift-lite-idpsdk__development__master-controller-handler.md): The first step needed to establish a connection between your Kotlin app on Android and the MC SDK.
* [**Start Event**](shift-lite-idpsdk__development__start.md): The first event that you need to send to the MC SDK using the connection established in the previous step.
* **Activation, Login, ...** in one of the server environments ([**KOBIL Digitanium**](https://developer.kobil.com/docs/mcsdk-docs/digitanium/development/ssms-activation),
  [**KOBIL Digitanium+**](https://developer.kobil.com/docs/mcsdk-docs/digitanium-plus/development/iam-activation), [**KOBIL Shift Lite-TWV**](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-twv/development/twv_event_flow/shift-activation) or [**KOBIL Shift Lite-KssIdp**](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-kssidp/development/kssidp_event_flow/shift-activation)) is bound to be the
  most important reason why you are using the MC SDK, so depending on which environment you use, you obviously need to
  activate your user accordingly and/or log in to the environment.
* Handling [**Suspend and Resume**](shift-lite-idpsdk__development__suspend_resume.md) properly is especially important in our environment, as the protection mechanisms implemented in the MC SDK tend to lead to crashes if your app is suspended or resumed without properly notifying the MC SDK about this change of state.
* Finally, be prepared to handle the [**invalid state event**](shift-lite-idpsdk__development__invalid-state.md) in reply to any event you send. While this typically occurs during development when improperly using the MC SDK (so handling it right from the beginning should simplify your life...), it also might happen occasionally in "real life", e.g. when something went wrong on the server side or with your internet connection.

Now, on to some things that you do not have to implement to get a working app, but which you really SHOULD implement - either to simplify your own life or the life of the end users:

* We strongly recommend implementing the needed functions to [**enable tracing**](shift-lite-idpsdk__development__enable_tracing.md) as this greatly simplifies everyone's life when something goes wrong or when you need support.
* Similarly, support for [**exporting logs**](shift-lite-idpsdk__development__export-logs.md) is very helpful when something goes wrong.
* In the KOBIL Digitanium environment, users need a PIN to authenticate to the server, so implementing [**Reactivation (Forgot PIN)**](https://developer.kobil.com/docs/mcsdk-docs/digitanium/development/reactivation) will be very helpful in real life.
* While we do not specifically recommend forcing end users to regularly change their PIN, giving them at least the option to [**change their PIN**](https://developer.kobil.com/docs/mcsdk-docs/digitanium/development/change-pin) is recommended.

Finally, the following points CAN be implemented if you need/want them and can be safely omitted if you do not need the corresponding feature:

* In KOBIL Digitanium and KOBIL Digitanium+, it is possible to manage multiple users/accounts from the same instance
  of your app. If you want to use that feature, you can implement the functionality to **add users** (either
  [**in Digitanium**](https://developer.kobil.com/docs/mcsdk-docs/digitanium/development/add-user) or
  [**in Digitanium+**](https://developer.kobil.com/docs/mcsdk-docs/digitanium-plus/development/add-user-digitanium+)) and to [**delete users**](shift-lite-idpsdk__development__delete-user.md).
* You can use our [transaction mechanism](shift-lite-idpsdk__development__transaction.md) to send arbitrary messages to end users and optionally require them to confirm the message. This is useful, e.g., for financial transactions.
* You may also use [**push notifications**](shift-lite-idpsdk__development__push-notification__push-token.md) to reach your users even when the app is suspended.
* Your users might use multiple devices to access the same account. In such scenarios, setting a specific device name and getting information about a device as described in [**Set/Get Device Information**](shift-lite-idpsdk__development__set-device-name.md) may be helpful to identify which device is currently used.
* [**Get SDK Information**](shift-lite-idpsdk__development__get-sdk-info.md) allows you to collect some details about the SDK version that your app is using. Once you have multiple versions or even multiple apps using different SDK versions, using this event can be helpful to understand which version of the SDK is being used where.
* Finally, there is a whole bunch of events that are used much more rarely or that are even considered outdated, for a full list see the section [Master Controller API](shift-lite-idpsdk__mcsdk-api__base_event.md).
