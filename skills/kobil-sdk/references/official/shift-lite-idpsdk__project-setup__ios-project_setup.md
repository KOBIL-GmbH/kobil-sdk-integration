> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/project-setup/ios-project_setup> on 2026-09-28. Converted to Markdown; wording unchanged.

# iOS

### Provided Frameworks

In this section, we will learn about the integration of the Master Controller SDK into a sample iOS application.

The MC SDK comes with the following frameworks, which are all required for proper functioning (except "kssidp.xcframework" and KSTrustedWebView.xcframework ):

**KSMasterController.xcframework (Debug and Release)**
Contains all the classes of the Master Controller (MC) API for iOS, facilitating the use of MC functionalities in iOS applications. There is no difference between the debug and release apart from the ability of debugging native code (c / c++) with debug build configuration.

**hnb.xcframework (hardening-ios):**
Provides security mechanisms to protect the native code and secure the application against various threats.
Debug: Enables app startup in iOS Simulator and allows debugging with the iOS Debugger.
Release: Intended for distribution to end users, without debugger support.

**KSTrustedWebView.xcframework**
A software stack that adds additional security to WebView inside a KOBIL Secured App. It includes features like SSL/TLS certificate pinning for enhanced security.

**kssidp.xcframework**
Built on top of the MasterController SDK, this framework facilitates activation, login, change password, and forgot password flows. It simplifies these processes by allowing applications to maintain their native interfaces while handling these operations without direct communication with the IDP.

> Do **NOT** use the debug build configuration libraries for release/production purposes.

> Our libraries are delivered and tested in specific combinations in QA.
> We strongly recommend using the exact combination of libraries delivered to avoid compatibility issues.
> Avoid mixing libraries from different release packages to streamline troubleshooting and ensure compatibility with our tested configurations.

**Note**: KSSIDP is specifically for Shift environments, not for Digitanium/Digitanium+.

## Integrating MCSDK with Swift Package Manager

You can integrate **MCSDK** into your project using **Swift Package Manager (SPM)**. Since MCSDK is provided as a compiled SDK (`.xcframework`), you’ll need to follow a few extra steps compared to a source-only package.

---

### 1. Create a Wrapper Module

Because the SDK is precompiled, it’s a good practice to create a **wrapper target**. This wrapper provides a clean, public interface for your application code while encapsulating direct access to the binary frameworks.

MCSDK Wrapper

```
import KSMasterController
public final class MCSDKPackage {
public private(set) var text = "Hello, World!"
private var masterController: (any KSAsyncEventReceiver & KSEcoModulInterface & KSEventSource)?
public init() {}
/// Initializes the master controller
public func createMasterController() {
masterController = KSMasterControllerFactory.getMasterController(withParmeter: "", andConsumer: self)
}
/// Example: sending a simple information event
public func sendEvent() {
let event = KSMGetInformationEvent()
masterController?.receive(event, withCompletionHandler: { resultEvent in
print("Received \(resultEvent)")
})
}
/// Example: sending a start event with configuration data
public func sendStartEvent(
astServerBackend: String,
mcConfigString: String,
certData: Data,
sdkConfig: Data
) {
let startEvent = KSMStartEventEx(
serverBackend: astServerBackend,
ssmsAppConfiguration: loadSsmsAppConfiguration(sdkConfig: sdkConfig),
mcConfig: mcConfigString,
certificateChain: certData,
configurationData: KSMConfigurationData(category: "", tagName: "")
)
masterController?.receive(startEvent, withCompletionHandler: { resultEvent in
print("Received \(resultEvent)")
})
}
private func loadSsmsAppConfiguration(sdkConfig: Data) -> KSMSsmsAppConfiguration {
let version = KSMVersion(majorVersion: 12, minorVersion: 0, build: 0)
return KSMSsmsAppConfiguration(
locale: "de",
version: version,
name: "clientBackend",
sdkconfig: sdkConfig
)
}
}
extension MCSDKPackage: KSAsyncEventReceiver {
func sendEvent2MasterController(
event: KSMEvent,
withCompletionHandler completionBlock: ((KsEvent?) -> Void)? = nil
) {
// implement if needed
}
public func receive(
_ event: KsEvent,
withCompletionHandler completionBlock: ((KsEvent?) -> Void)? = nil
) {
// handle received events here
}
}
```

---

### 2. Define the Package Manifest

Next, define your `Package.swift` manifest. This declares your wrapper target and links it against the MCSDK binary frameworks:

Package.swift

```
import PackageDescription
let package = Package(
name: "MCSDKPackage",
products: [
.library(
name: "MCSDKPackage",
targets: ["MCSDKPackage"]
)
],
targets: [
.target(
name: "MCSDKPackage",
dependencies: [
.target(name: "KSMasterController"),
.target(name: "hnb")
]
),
.binaryTarget(
name: "KSMasterController",
path: "Sources/MCSDKPackage/KSMasterController.xcframework"
),
.binaryTarget(
name: "hnb",
path: "Sources/MCSDKPackage/hnb.xcframework"
)
]
)
```

This setup tells SPM that your wrapper depends on two precompiled `.xcframework` targets: **KSMasterController** and **hnb**.

---

### 3. Handle Debug vs. Release Frameworks

MCSDK typically ships with both **Debug** and **Release** builds of the frameworks. Since SPM does not natively support switching binaries per build configuration, you’ll need a workaround.

The recommended approach is to add a **Run Script Phase** in your Xcode project that:

1. Detects the current build configuration (`Debug` or `Release`).
2. Copies the appropriate `.xcframework` versions into the `Sources/MCSDKPackage` folder.
3. Ensures that the correct binaries are included at build time.

This script can be as simple as:

```
echo "Switching MCSDK frameworks depending on configuration..."
destinationFolder=${PROJECT_DIR}/../MCSDKPackage/Sources/MCSDKPackage/
if [ $CONFIGURATION = "Debug" ]; then
sourceFolder="${PROJECT_DIR}/../MCSDKPackage/Sources/Debug"
echo "copy from ${sourceFolder} to ${destinationFolder}"
cp -R -f -v "${sourceFolder}/KSMasterController.xcframework" ${destinationFolder}
cp -R -f -v "${sourceFolder}/hnb.xcframework" ${destinationFolder}
else
sourceFolder="${PROJECT_DIR}/../MCSDKPackage/Sources/Release"
echo "copy from ${sourceFolder} to ${destinationFolder}"
cp -R -f -v "${sourceFolder}/KSMasterController.xcframework" ${destinationFolder}
cp -R -f -v "${sourceFolder}/hnb.xcframework" ${destinationFolder}
fi
```

With this in place, whenever you build in Debug or Release, the correct frameworks are automatically swapped in.

### Step-by-step Instruction

1. Create a new Xcode project and select "Single View App".
   ![](https://developer.kobil.com/assets/images/createProject-c2dd2876c679bace5917cda727b4ed35.png)
2. The project name chosen for this document is "MCSDKGettingStartedSwift". However, you can choose another name.
   ![](https://developer.kobil.com/assets/images/projectOptions-05a92753dd1b2fc420e14f455952017c.png)
3. Select the project file and choose target "MCSDKGettingStartedSwift" and Click on the '+' button in the section Embedded Binaries and Select the 'Add Other...' option in the opening section.
   ![](https://developer.kobil.com/assets/images/howToAddFrameworks-ca7fbe33fa8571a664f688d3b9c93b8e.png)
4. Choose MasterController and Harden the XC-framework in the finder.
   ![](https://developer.kobil.com/assets/images/kssidpPath-03c94f97dc0dd50ece16f78ef4ffed22.png)
   Apple defines XCFrameworks as a distributable binary package created by Xcode that contains variants of a framework or library so that it can be used on multiple platforms (iOS, macOS, tvOS, and watchOS), including Simulator builds. An XCFramework can be either static or dynamic and can include headers.
   'We have also provided our MasterController and Hardening framework as an XCFramework.'
5. 'Embedded Binaries' and 'Linked Frameworks and Libraries' sections should look like below. "KSMasterController.xcframework", "hnb.xcframework", kssidp.framework. and "KSTrustedWebview.xcframework" in 'Linked Frameworks and Libraries' are automatically added. There is no need for extra effort to add the frameworks in that section.
   ![](https://developer.kobil.com/assets/images/frameworksAdded-788bf37f356c02c90e54cdde9a54386a.png)
6. You can also give support to multiple servers in your application by simply adding the SDK configuration file of that server. You can add this server configuration file like this.
   ![](https://developer.kobil.com/assets/images/selectServer-156cc3bf564b3c9d5bdad0a8df2d828c.png)

You can switch your server in the currently running application also, for that you have to first delete all users of the existing server and then select a server on which you want to switch.

To activate users on different servers, please navigate to the corresponding server.

### Initial Steps

1. Ensure you have all the necessary assets and frameworks ready to proceed with the MasterController SDK:

   * MasterController SDK framework for both debug and release modes.
   * GettingStartedApps and MC configuration files.
2. Follow these steps to set up communication with the MasterController framework:

   * Add the MasterController framework to your project using artifacts.
   * Use the MasterControllerAdaptor class for communicating with the Master Controller. To start actual communication, initialize its components in the AppDelegate.
3. Register your app version in the Security Server.

### Further Information

The MasterController and Hardening come in two different variants: one in the debug folder and the other in the release folder. Refer to the table below to understand the differences and choose the appropriate MasterController Hardening for your situation:

| Debug | Release |
| --- | --- |
| KOBIL App Security is disabled, allowing iOS debugger attachment and using dummy values for KOBIL App Security | KOBIL App Security is enabled, prohibiting iOS debugger attachment |
| Some MasterController logs are written to the Xcode console | MasterController logs are not written to the Xcode console; only encrypted log files are available |
| This variant is not recommended for productive usage; a notification is displayed on startup Do Not Release |  |

### Simulator Support

Running a release version of the Hardening framework on a simulator is prevented by the security features of our framework. However, developers may want to run components or tests of their app on the simulator in release mode. To simplify this, we provide a "dummy" release version of our framework for the simulator, which is essentially a copy of the debug version. Note that the timing differences between release and debug versions are even more pronounced in this scenario. While the simulator can aid in app development and debugging, it is not a substitute for testing on a real device.
Additionally, if the SDK relies on the Secure Enclave, attempting to run it on a simulator will always fail. In such cases, testing and debugging must be conducted on a real device.

### Backup of iPhone and iPad

For security purposes, KOBIL App Security's device binding parameter is not stored in iCloud or local computer backups. Consequently, after restoring a backup, the user will lose activation and must reactivate the app. Therefore, the MCSDK does not support the backup/restore process. When a user makes a backup, the MCSDK prevents the iOS system from backing up a database file. Otherwise, restoration would result in an undefined state where the device binding parameter is missing, but the app still believes it is activated. Developers need not take any action, as this process occurs automatically.
