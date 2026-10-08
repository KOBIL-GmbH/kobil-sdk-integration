> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/suspend_resume> on 2026-09-28. Converted to Markdown; wording unchanged.

# Suspend and Resume

> 📋 **Deprecation Notice:** Starting with MC-SDK releases 16.x, calling suspend/resume will no longer be necessary. The SDK will handle app lifecycle events internally. The functions will be deprecated and become no-ops, so no app changes are required at that time.

The MC SDK provides **suspend** and **resume** methods that must be called when your app transitions between background and foreground states.

Due to built-in protection mechanisms, the MC SDK does not allow applications to enter the background without explicit notification. Therefore, your app must call **suspend** before going to the background to prevent SDK termination. When returning to the foreground, your app must call **resume**.

> ⚠️ **Critical:** Always call suspend and resume within the appropriate OS lifecycle events.
> **On app startup, call the SDK's resume method before any other SDK operations!**

### iOS/Swift

For iOS, call **`suspend()`** in **`applicationDidEnterBackground()`** and **`resume()`** in **`applicationWillEnterForeground()`**:

Handling Suspend and resume (Swift)

```
extension AppDelegate {
...
func applicationDidEnterBackground(_ application: UIApplication) {
MasterControllerAdapter.sharedInstance.masterController?.suspend()
}
func applicationWillEnterForeground(_ application: UIApplication) {
MasterControllerAdapter.sharedInstance.masterController?.resume()
}
...
}
```

### Android/Kotlin

For Android, call **`suspendMasterController()`** in **`onStop()`** and **`resumeMasterController()`** in **`onStart()`** lifecycle methods. Both methods are available in the **SynchronousEventHandler** class.

**⚠️ Avoid [ProcessLifecycleOwner](https://developer.android.com/reference/androidx/lifecycle/ProcessLifecycleOwner):** ProcessLifecycleOwner introduces delays that can cause timing issues with the MC SDK's time-sensitive suspend/resume operations.

Instead, use the activity lifecycle directly with **`onStop()`** and **`onStart()`**.

**Important:** Only call **`suspendMasterController()`** when the app is actually going to the background. Use **ActivityManager.RunningAppProcessInfo** to verify the app's foreground state and avoid suspending the MC SDK during activity transitions.

**Note:** In rare cases, the system may not allow sufficient time for **`suspendMasterController()`** to complete (e.g., when the user force-kills the app during suspension). Despite this limitation, activity lifecycle methods provide more precise timing control than ProcessLifecycleOwner.

**Optimization:** We recommend using **`suspendMasterController()`** over **RestartEvent** in **`onStop()`** as it requires less time to complete. If you must trigger a **RestartEvent** in **`onStop()`**, skip calling suspend as the restart serves as a logout operation, making suspend unnecessary. Additionally, there might not be sufficient time to complete both operations anyway.

Here's a helper function to check if your app is in the foreground before calling **`suspendMasterController()`**:

Helper function to check if app is in foreground

```
fun isAppOnForeground(context: Context): Boolean {
val activityManager = context.getSystemService(ACTIVITY_SERVICE) as ActivityManager
val appProcesses = activityManager.runningAppProcesses ?: return false
val packageName = context.packageName
for (appProcess in appProcesses) {
if (appProcess.importance == RunningAppProcessInfo.IMPORTANCE_FOREGROUND && appProcess.processName == packageName) {
return true
}
}
return false
}
```

### Flutter/Dart

For Flutter, call **`suspend()`** when the app goes to the background and **`resume()`** when returning to the foreground. Use **`WidgetsBindingObserver`** to monitor app lifecycle changes:

Triggering suspend/resume (Flutter)

```
@override
Future<void> didChangeAppLifecycleState(AppLifecycleState state) async {
switch (state) {
case AppLifecycleState.resumed:
mcApi.resume();
break;
case AppLifecycleState.paused:
mcApi.suspend();
break;
case AppLifecycleState.detached:
mcApi.stop();
break;
default:
break;
}
}
```
