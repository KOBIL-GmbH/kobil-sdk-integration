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
