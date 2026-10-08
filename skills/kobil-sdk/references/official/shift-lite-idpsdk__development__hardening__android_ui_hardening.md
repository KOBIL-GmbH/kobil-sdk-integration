> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/hardening/android_ui_hardening> on 2026-09-28. Converted to Markdown; wording unchanged.

# UI Hardening (Android)

### Integration

The UI Hardening feature, which is newly added, comes as a separate file named uihardening\*.aar alongside the SDK library.

1. Begin by copying the library files into your project.

   > We recommend placing the uihardening\*.aar file inside the 'artifacts/libs' directory, similar to [**other libraries**](shift-lite-idpsdk__project-setup__android-project_setup.md#dependencies) as mentioned [**here**](shift-lite-idpsdk__project-setup__android-project_setup.md#dependencies).
2. Next, specify the path to these library files in the **dependencyResolutionManagement** section of your project's **settings.gradle** file.

```
dependencyResolutionManagement {
...
repositories {
...
flatDir {
dirs 'artifacts/libs'
}
...
}
}
```

3. Now, you can add the library as a dependency in your `:app:build.gradle` file.

```
// For Java:
debugImplementation (':uihardening-debug@aar') {
transitive = true
}
releaseImplementation (':uihardening-release@aar') {
transitive = true
}
// For Kotlin:
debugImplementation (':uihardening-debug@aar') {
exclude group: 'org.jetbrains.kotlin', module: 'kotlin-stdlib-jdk7'
transitive = true
}
releaseImplementation (':uihardening-release@aar') {
exclude group: 'org.jetbrains.kotlin', module: 'kotlin-stdlib-jdk7'
transitive = true
}
```

### Setting Logging Callbacks

```
Hardening.getInstance().viewloggingCallBack();
```

This function sets up a way for the hardening library to report events
by calling a specified function. If no function is specified, the library
will still log events to the system's logcat output. However, it is crucial to note that in release versions, a callback function **must** be set up to avoid logging unencrypted data.

### UI Hardening

```
Hardening.getInstance().hardenView(View v, Boolean b);
```

* **@v**: The View (or ViewGroup) that needs to be made more secure.  
  If a `ViewGroup` is provided, all of its child views are processed recursively.
* **@b**: Determines whether accessibility services are allowed to speak or read password fields.  
  This setting is applied globally for the entire app process.

This feature applies a set of UI-hardening measures to the UI elements of your app. Specifically, it:

1. Disables accessibility services for the affected view(s)
2. Prevents the processing of input events when a transparent overlay is placed above the UI
3. Blocks virtual or synthetic clicks (for example from screen-sharing tools, accessibility services, or automated input frameworks)
4. Disables accessibility features that could read or expose password fields

> **Important:**  
> Accessibility features (such as screen readers announcing labels) are critical for users who rely on assistive technologies.  
> Before applying this hardening, carefully consider whether accessibility should remain available for certain UI elements.  
> In many cases, only specific sensitive views or ViewGroups require hardening rather than the entire layout.

### Compose

```
Hardening.hardenComposable(Modifier modifier)
```

* **@modifier**: The original `Modifier` of the composable

This method applies UI hardening to Jetpack Compose components by **removing their semantics information**.

Since accessibility services rely on the Compose **semantics tree**, this reduces the exposure of UI content such as:

* Text values
* Labels
* Structural information

This helps protect sensitive UI elements from being read or interpreted by external services.

---

#### Effect

When applied, the modifier:

* Reduces metadata exposure to accessibility services
* Limits the ability to inspect UI structure and content
* Helps protect sensitive inputs (e.g., passwords, PINs, TANs)

---

#### Important Limitations

This behavior is **not absolute**.

* Child composables (e.g., `TextField`, `Button`) may define their own semantics
* These semantics can be reintroduced even if a parent container is hardened
* Therefore, container-level hardening alone is **not sufficient** for sensitive data

---

#### Usage Scenarios

##### 1) Direct usage on a sensitive input field (Recommended) Direct usage on a sensitive input field (Recommended)")

```
TextField(
value = password,
onValueChange = { password = it },
modifier = Hardening.hardenComposable(Modifier)
)
```

* The field does not expose semantics
* Best protection for sensitive data

---

##### 2) Input field inside a hardened container Input field inside a hardened container")

```
Box(modifier = Hardening.hardenComposable(Modifier)) {
TextField(...)
}
```

* Container reduces semantics propagation
* Child components may reintroduce semantics
* Not fully reliable

---

##### 3) Nested containers Nested containers")

```
Box(modifier = Hardening.hardenComposable(Modifier)) {
Box {
TextField(...)
}
}
```

* Same limitation applies
* Nested structure does not improve protection

---

##### 4) Multiple fields with selective hardening (Recommended) Multiple fields with selective hardening (Recommended)")

```
Column {
TextField(
value = password,
onValueChange = { password = it },
modifier = Hardening.hardenComposable(Modifier)
)
TextField(
value = username,
onValueChange = { username = it }
)
}
```

* Sensitive fields are protected
* Non-sensitive fields remain accessible

---

#### Recommendation

* Always apply hardening directly to sensitive composables
* Use container-level hardening only as an additional layer
* Do not rely solely on container hardening for security-critical inputs

---

#### Summary

`Hardening.hardenComposable(...)` reduces accessibility exposure by clearing semantics.

However, it does not guarantee complete protection when applied only at container level. Fine-grained hardening of individual UI elements is required for reliable security.

### Enable Ui Hardening

```
Hardening.getInstance().enableViewHardener();
```

Activate the UI-View hardening feature. All subsequent calls contribute to strengthening the hardening process. This feature is turned on by default.

### Disable Ui Hardening

```
Hardening.getInstance().disableViewHardener();
```

Disables the UI-View hardening. After this is done, any future actions will not add extra protection. You can use this setting for views that do not need extra security measures.

### HardenScreen

```
public void onCreate(Bundle savedInstanceState) {
Hardening.getInstance().hardenScreen(this); // to be called here
super.onCreate(savedInstanceState);
[...]
}
```

This function activates screen protection for the specified activity.  
Screen protection is applied using `FLAG_SECURE`.

* It can only be applied at the **Activity** level, not at the Fragment level.
* Once enabled, the following types of content capture are blocked:
  + Screen sharing
  + Screen recording
  + Screenshots

#### Important Notes

If your app uses a single-Activity architecture but you only want certain Fragments to be protected, you may temporarily disable the flag using:

```
getWindow().clearFlags(WindowManager.LayoutParams.FLAG_SECURE);
```

You may later re-enable protection as needed by calling `hardenScreen(...)`.

However, dynamically toggling `FLAG_SECURE` can introduce race conditions — especially when the system generates preview images for the Recents screen — potentially exposing sensitive UI content.  
This usage pattern is **not officially supported** by our API and must be tested thoroughly if adopted.

For security-critical use cases, we strongly recommend using **separate Activities** instead of toggling protection at runtime.

#### Example

```
protected void onCreate(Bundle savedInstanceState) {
Hardening.getInstance().hardenScreen(this); // call before super.onCreate()
super.onCreate(savedInstanceState);
}
```
