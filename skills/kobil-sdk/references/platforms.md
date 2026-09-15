# Platform integration requirements

These are implementation requirements, not verified app templates. Read the
selected SDK release's actual APIs and platform prerequisites before coding.

| Target | Resolve and verify |
|---|---|
| Kotlin / Android | Package ID, Gradle dependencies, native ABIs, startup/events, signing and device binding |
| Swift / iOS | Bundle ID, SDK frameworks, Xcode target resources, delegates, signing and entitlements |
| Flutter / Android | Dart wrapper plus compatible Android native artifacts, runner and device lifecycle |
| Flutter / iOS | Dart wrapper plus compatible iOS native artifacts, resources, runner and signing |
| Flutter / Windows | Dart/native SDK tuple, DLL loading, CMake/MSVC requirements, packaging and Windows runtime |
| Flutter / macOS | Dart/native SDK tuple, dylib/framework bundling, signing/entitlements and macOS runtime |

For Flutter, native SDK support does not guarantee a Dart binding. Verify exported
wrapper APIs and event types rather than translating Kotlin/Swift names into
invented Dart calls. Initialize once outside widget rebuilds, handle events and
fatal errors, and connect lifecycle operations according to the SDK contract.
If the SDK needs filesystem paths, an asset key is not a substitute: follow its
asset-to-storage setup. Inspect release/debug artifact differences independently.

For activation/login, resolve the backend realm/client and configured flow,
register or reuse the app and platform version, obtain signed SDK configuration
and trusted certificates, and provide the required test user/activation method.
The JWT is only part of configuration. Credential/session ownership and PIN
processing depend on the SDK family; do not mix contracts between SDKs.

Acceptance: successful initialization, first activation, backend/device state,
login after restart, errors, cancellation and interrupted connectivity. Test
fresh and existing apps separately. Flutter requires Android, iOS, Windows and
macOS evidence; a successful macOS build does not verify Windows. Missing test
hosts and unavailable SDK artifacts remain explicit blockers.

## Verified Android setup checkpoints

A fresh Kotlin Android debug project using KSSIDP 1.7.0 and separately supplied
arm64 SDK artifacts was built and launched on an Android API35 emulator. These
are build/launch findings; activation and return-login require separate evidence.

- Verify `app/src/main/assets` against the built APK's `assets/` entries, including
  JSON configuration, backend-issued JWT and each referenced public certificate.
  Compare bytes/checksums, not merely filenames. Certificate references may name
  subdirectories and must resolve exactly.
- SDK AAR manifests can conflict on the application label and native preload
  metadata. Resolve the merge explicitly using the selected SDK bundle's required
  libraries; do not discard SDK preload metadata just to make the build pass.
- This bundle required the Material dependency for resources referenced by its
  AARs. Use the selected release's dependency requirements; successful Kotlin
  compilation alone does not establish resource/link compatibility.
- Confirm installation and foreground activity/process after building. These
  prove launch only; wait for successful SDK StartResult before activation.
- AST notification categories are a separate contract from a sample application's
  category label. Use supported backend categories; do not copy the sample label
  into sdk_app_ensure without checking the backend contract.

### SDK initialization verified

MC SDK 188.1.2937039 with KSSIDP 1.7.0 reached `StartResultEvent` status `OK`,
state `ACTIVATION_REQUIRED`, zero activated users, followed by
`StartActivationUserIdAndCodeOnlyEvent` on the API35 arm64 debug emulator.
A backend-issued JWT missing `astUrl` had failed parsing with native error
801000008; requesting a new signed JWT with `astUrl` fixed startup. Verify the
actual SDK result and runtime version after provisioning, not just HTTP success
or JWT file creation. Activation and return-login are separate checkpoints.

A new MCP-issued JWT containing the deployment service map was also packaged and
verified with successful Start on this same SDK/platform tuple. Check the signed
request includes the feature endpoints even when SDK startup already succeeds;
startup alone does not exercise registration/key exchange.

### AST key exchange verified

On the same Android tuple, adding the authorized service map to the backend
signing request resolved error 800000271. Both KexKeyExchangeInternalResultEvent
and EstablishKeyExchangeResultEvent returned OK. The subsequent GetAstClientData
operation encountered a native process crash before its result; registration,
activation and return-login are therefore still unverified. A native process
crash may prevent delivery of FatalErrorEvent: retain Android crash evidence
alongside SDK events and inspect the last completed operation.

### Physical Android startup verified

The same fresh debug APK with KSSIDP 1.7.0 / MC 188.1.2937039 installed on a
Pixel 8 running Android API36 (arm64), with no prior validation-app installation.
StartResult returned OK / ACTIVATION_REQUIRED and zero users, followed by
StartActivationUserIdAndCodeOnlyEvent. Select an explicit adb serial when an
emulator and physical device are both connected. Activation remains a separate
check; successful startup does not establish support for the entire OS/SDK tuple.

### Native logging isolation on physical Android

On Pixel 8/API36 with the same SDK tuple and preserved app data, replacing the
optional Java Log.RegisterCallback sink with native Log.StartEncryption file
logging avoided the observed GetAstClientData SIGSEGV and reached the HTTP
activation stage. The exact native/JNI cause is unproven. For this tuple, use
restricted app-private native log files and retain Warning/RuntimeError/FatalError
event listeners; these are independent logging paths. The selected implementation
treats StartEncryption input as a directory and creates ks.log within it. Verify
that contract for other releases. The HTTP activation request still returned an
error, so activation and returning login remained pending at this checkpoint.
