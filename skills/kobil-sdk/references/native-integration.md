# Native integration handoff

This first-priority pack covers classic MCSDK with KSSIDP on Kotlin/Android and
Swift/iOS. Select a platform and read all eight `sdk_knowledge_get` topics before
building a fresh app. Examples are small functions to integrate into the app;
they do not provide a complete UI, controller lifecycle or customer configuration.
Their exact artifact validation is returned with each example. Standalone IDPSDK,
Flutter and SSMS require separate bindings; do not translate these calls blindly.

## From backend selection to a runnable app

1. Call `sdk_service_catalog` and confirm the three knowledge tools are present.
   If missing, update both MCP and skill to the same tested commit/release and
   restart the MCP/session. An older installed package is not upgraded by Git.
2. Validate the configured connection with `sdk_backend_status` and check referenced
   credential availability with `sdk_credential_status`. Keep administrator
   credentials in the backend provider, never in app assets. Follow the bundled
   [credential guide](../../../docs/credentials.md) for native stores/age transfer.
3. Read `sdk_app_get` and `sdk_app_versions`; prefer a suitable existing record.
   If creation is needed within the user's task, use `sdk_app_ensure` and
   `sdk_app_version_ensure` with explicit platform/version, registration user and
   integrity policy. Read back the resulting record. The registration user is
   distinct from the user who will activate this device.
4. Request the signed configuration via `sdk_config_write`, using the selected
   trusted certificates. Package the JWT together with the delivery's matching
   app/MC configuration and referenced certificates. Preserve signed content.
   Verify assets in the built APK/app bundle, not only in the source tree.
5. Select the existing native-compatible IDP client and exact field mappings.
   Use user search/read operations to select a dedicated test user. Create one
   only if needed and authorized by the test task. Generate an activation code
   using `sdk_idp_activation_code_generate` for the selected user UUID when the
   deployment supports that credential type. Never replace codes automatically
   after an uncertain timeout. Registration metadata is not an activation code.
6. Integrate the `setup`, `lifecycle` and `diagnostics` recipes first. Register
   listeners before initialization, retain controller/wrapper references and
   inspect result status/state. Install required native framework/AAR dependencies.
   Keep app console messages separate from SDK Warning/RuntimeError/FatalError.
7. Implement `activation`, `login` and `multi_step`. Pass the explicit client,
   requested credentials, user-selection headers and callback/delegate. Use actual
   SDK result status and state to drive UI. The supplied helpers are dispatch
   functions, not proof of successful authentication. Never default to SuperApp
   Login V2 for native Android/iOS.
8. Integrate `tms` with one event owner (app or KSSIDP), according to the selected
   architecture. For authorized test transactions use `sdk_tms_trigger`, retain
   its transaction ID, and compare `sdk_tms_status`/`sdk_tms_result` with the SDK
   terminal result. Show the transaction information and actual approve/reject
   choice; confirmation acknowledgement alone is not completion.
9. Implement `logs` with the actual SDK log directory, archive validation and
   platform sharing. Android needs a scoped FileProvider definition and temporary
   read grant. iOS needs a share sheet presented on the main thread; on iPad set
   its popover anchor. Keep encrypted SDK logs intact and clean temporary archives
   after sharing according to app policy.

## User acceptance

Retrieve `sdk_integration_checklist` for each topic and retain observed results.
Check cold start, activation, login after restart, multi-step continuation/cancel,
wrong/expired input, TMS approve/reject/timeout, all three error categories and
shareable SDK logs. Record platform, exact mobile SDK, app/backend version and
result. Stop at an unexplained error and show the original error fields plus
pending operation; do not claim success from a build, token or empty callback.

Compilation, synthetic diagnostics and the successful registration/activation/cold
returning-login path are recorded for MCSDK 15.16 on two physical devices. Read the
per-platform runtime_acceptance scope. Other checklist cases remain to be tested.
For iOS, package AND explicitly pass the IAM certificate chain at Start; packaging
alone did not initialize it in the tested SDK.
