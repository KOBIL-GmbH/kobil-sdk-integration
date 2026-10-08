> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/introduction/mc_sdk> on 2026-09-28. Converted to Markdown; wording unchanged.

# MC SDK

To develop your KOBIL Secured app, use the MasterController Software Development Kit (MasterController SDK, MC SDK), this documentation and the included sample 'GettingStartedApps' that demonstrate the use of the MC SDK. Our SDK contains:

### Binary package of MC SDK for iOS and Android

| **Artifact** | **Remarks** |
| --- | --- |
| **MCSDK.Android.README\_xx.x.x-MCWyyy.y.md** | Android Release Notes where xxx is the package version and yyy is the MC SDK wrappper version |
| **MCSDK.iOS.README\_xx.x.x-MCWyyy.y.md** | iOS Release Notes where xxx is the package version and yyy is the MC SDK wrappper version |
| **MCSDK.Android.CHANGELOG\_xx.x.x-MCWyyy.y.md** | Android Change Logs where fixes and new features are described |
| **MCSDK.iOS.CHANGELOG\_xx.x.x-MCWyyy.y.md** | iOS Change Logs where fixes and new features are described |
| **MCSDK-iOS-xcframeworks-xx.x.xxx.b.zip** | SDK xcframework. We support iOS simulator and arm64 |
| **MCSDK-Android-libs-xx.x.xxx.b.zip** | Android Libraries. We support Android eumlator and arm64 |

### Sample applications and project files to illustrate the use of the Getting Started App

A full app that compiles and runs against our servers for testing, debugging, and understanding the SDK usage. This app can be helpful to understand how to use the SDK.

> ⚠️ Note you should take a deep look into the getting started apps and ask KOBIL support for help, so you can run and debug our getting started app to get a deeper understanding of our SDK.

| **Artifact** | **Content** |
| --- | --- |
| **MCWMP\_GettingStartedSwift\_xx.x.xxx.2157567** | Swift GettingStartedApp |
| **MCWMP\_KotlinGettingStarted\_xx.x.xxx.2157567** | Kotlin GettingStartedApp |

### SDK Documentation

This documentation instructs you about the required steps to develop a KOBIL Secured app. It explains the options of the MasterController API and describes the MasterController SDK on the whole. The steps and the settings described here are necessary to design, build, and make your app available to your customers. The file names used here are an example, you can change them.

The Master Controller uses an event based communication to the app, so the communication between the app and the Master Controller is an asynchronous API:

![](https://developer.kobil.com/assets/images/Aspose.Words.4fab05e6-4eab-4888-94a7-e1cbcf1e6ba4.001-27e870cfb975cae1b18147198135fa86.png)

### GettingStartedApps

The purpose of the GettingStartedApps is to provide details of the mechanism of the MasterController to understand how you can use the MC SDK in native or cross-platform languages. We provide source code written in iOS/Swift and Android/Kotlin, but you can also use some other languages e.g. iOS/ObjectiveC or Android/Java.

This source code is a reference implementation for the MasterController API integration. It shows

* the basic usage
* how to handle error cases that the MasterController may respond to if there is an issue
* mock-up tests: These test cases showcase the flow of the application which will allow you to understand the mechanism of the master controller and how your app should behave in any scenario. Also, it mocks up the behavior of the master controller that gives us easy access to check the correct feature/flow implementation.

> ⚠️ The integrated tests mockup our MC SDK and simulate several errors cases. There, you can verify if your error handling is complete inside your app.

The classes and methods used for the integration in that app limit in part its functionalities. For this reason, the source code of the example app should not be used as basis for the integration of the MasterController API into your production app. Use exclusively the interfaces described in this document.

### Developing your own application

[The overview](https://developer.kobil.com/docs/mcsdk-docs/digitanium/development/api_overview) at the beginning of the Development part of this documentation aims at giving you a quick overview which parts of the API you absolutely must implement for a working application, which parts we recommend as very helpful for debugging issues and supporting end users, and which parts you may or may not need, depending on your use case.
