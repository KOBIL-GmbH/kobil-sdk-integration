# Official KOBIL MCSDK documentation (bundled copy)

These pages are the official KOBIL documentation for **Shift Lite - IdpSdk** and the
**MCSDK introduction**, copied from <https://developer.kobil.com/docs/mcsdk-docs/introduction/mc_sdk>
and its sub-pages on 2026-09-28. Each page starts with its source URL. The wording is
unchanged; only the site navigation was removed, and code blocks lost their indentation in
the conversion. Links between bundled pages point at the local copies.

How to use them:

- Search: `sdk_official_docs_search` (MCP; also searches the plugin guides, results labelled `official` or `guide`). Read a page: `sdk_docs` section `official/<file name without .md>`.
- Check a name against the delivered SDK: `sdk_api_lookup` (headers, and whether the binary exports the class).
- Answer SDK questions from these pages and cite the source URL. Our own guides
  (`../*.md`) add what was checked on devices and must not contradict these pages except in
  the cases listed below.
- Refresh: `uv run --with beautifulsoup4 --with markdownify python scripts/fetch_official_docs.py`
  in the plugin repository, then re-check the differences below.

## Known differences from the delivered iOS SDK 15.16.803.3089231

The documentation is written for the current SDK line; a delivered release can differ. What
compiles is decided by the delivered headers. Verified on 2026-09-28:

| Topic | Official documentation | Delivered iOS 15.16 | Follow |
|---|---|---|---|
| Suspend / resume | [Suspend and Resume](shift-lite-idpsdk__development__suspend_resume.md): call `suspend()` / `resume()` on background / foreground | `KsEcoModulInterface.h` marks both deprecated: "handled by MCSDK … can be safely removed"; CHANGELOG: "MCSDK now handles app state changes automatically" (SDK-828) | headers: do not call them |
| Transaction end event | [Transaction](shift-lite-idpsdk__development__transaction.md), [Individual events](shift-lite-idpsdk__mcsdk-api__individual_events.md): `TransactionEndEvent` | `KSMTransactionFinishedEvent` (`KsMacroEvents.h`); no `TransactionEndEvent` | headers |
| Authentication mode PIN | [Enumerations](shift-lite-idpsdk__mcsdk-api__enumerations.md): `NO`, `BIOMETRIC`, `PASSWORD`, `PIN` | `KSMAuthenticationMode`: `No`, `Biometric`, `Password` only | headers |
| IdpSdk on iOS | [IdpSdk pages](shift-lite-idpsdk__development__idpsdk__idpsdk-overview.md): `IdpSdkService`, `IdpSdkNativeInterface` | kssidp.framework: `KssIdp`, `KssIdpWrapper`; no `IdpSdkService` | headers; same event sequence |
| Multipart upload, muting | [HTTP common request](shift-lite-idpsdk__development__http-common-request.md) shows `multiPartContent:` with `KsHttpMultiPart` | declared in the headers, but the binary exports no `KsHttpMultiPart` or muting classes (link fails) | upload as JSON; report to KOBIL |
| IdpSdk client IDs | [IdpSdk overview](shift-lite-idpsdk__development__idpsdk__idpsdk-overview.md): defaults `KssIdpEnrollment` / `KssIdpLogin`, "may differ per tenant" | not an SDK matter; KOBIL's IDP exports use `KSSIDPWebBasedEnrollment` / `KSSIDPWebBasedLogin` | the realm's own client IDs |

## Pages

### introduction

| Page | Local copy |
|---|---|
| [KOBIL App Security](https://developer.kobil.com/docs/mcsdk-docs/introduction/kobil_app_security) | [introduction__kobil_app_security.md](introduction__kobil_app_security.md) |
| [KOBIL Solutions](https://developer.kobil.com/docs/mcsdk-docs/introduction/kobil_solutions) | [introduction__kobil_solutions.md](introduction__kobil_solutions.md) |
| [MC SDK](https://developer.kobil.com/docs/mcsdk-docs/introduction/mc_sdk) | [introduction__mc_sdk.md](introduction__mc_sdk.md) |

### anonymous_flows

| Page | Local copy |
|---|---|
| [Anonymous Enrollment](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/anonymous_flows/shift-anonymous_enrollment) | [shift-lite-idpsdk__anonymous_flows__shift-anonymous_enrollment.md](shift-lite-idpsdk__anonymous_flows__shift-anonymous_enrollment.md) |

### development

| Page | Local copy |
|---|---|
| [Overview](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/api_overview) | [shift-lite-idpsdk__development__api_overview.md](shift-lite-idpsdk__development__api_overview.md) |
| [Bridging-Header (iOS/Swift)](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/bridging-header) | [shift-lite-idpsdk__development__bridging-header.md](shift-lite-idpsdk__development__bridging-header.md) |
| [Delete User](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/delete-user) | [shift-lite-idpsdk__development__delete-user.md](shift-lite-idpsdk__development__delete-user.md) |
| [Digitanium to Shift Migration Flow](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/digitanium-shift-migration) | [shift-lite-idpsdk__development__digitanium-shift-migration.md](shift-lite-idpsdk__development__digitanium-shift-migration.md) |
| [Enable Authentication Mode](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/enable-authentication-mode) | [shift-lite-idpsdk__development__enable-authentication-mode.md](shift-lite-idpsdk__development__enable-authentication-mode.md) |
| [Enabling Tracing](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/enable_tracing) | [shift-lite-idpsdk__development__enable_tracing.md](shift-lite-idpsdk__development__enable_tracing.md) |
| [Logging](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/export-logs) | [shift-lite-idpsdk__development__export-logs.md](shift-lite-idpsdk__development__export-logs.md) |
| [Get SDK Information](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/get-sdk-info) | [shift-lite-idpsdk__development__get-sdk-info.md](shift-lite-idpsdk__development__get-sdk-info.md) |

### development/hardening

| Page | Local copy |
|---|---|
| [UI Hardening (Android)](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/hardening/android_ui_hardening) | [shift-lite-idpsdk__development__hardening__android_ui_hardening.md](shift-lite-idpsdk__development__hardening__android_ui_hardening.md) |

### development/hardening/call-monitoring

| Page | Local copy |
|---|---|
| [Call Monitor Android API Reference](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/hardening/call-monitoring/android_callmonitor_api_reference) | [shift-lite-idpsdk__development__hardening__call-monitoring__android_callmonitor_api_reference.md](shift-lite-idpsdk__development__hardening__call-monitoring__android_callmonitor_api_reference.md) |
| [Call Monitor iOS API Reference](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/hardening/call-monitoring/ios_callmonitor_api_reference) | [shift-lite-idpsdk__development__hardening__call-monitoring__ios_callmonitor_api_reference.md](shift-lite-idpsdk__development__hardening__call-monitoring__ios_callmonitor_api_reference.md) |

### development/hardening

| Page | Local copy |
|---|---|
| [Hardening Topics](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/hardening/hardening_topics) | [shift-lite-idpsdk__development__hardening__hardening_topics.md](shift-lite-idpsdk__development__hardening__hardening_topics.md) |

### development/hardening/trusted-webview

| Page | Local copy |
|---|---|
| [Trusted WebView Android API Reference](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/hardening/trusted-webview/android_trustedwebview_api_reference) | [shift-lite-idpsdk__development__hardening__trusted-webview__android_trustedwebview_api_reference.md](shift-lite-idpsdk__development__hardening__trusted-webview__android_trustedwebview_api_reference.md) |
| [Trusted WebView iOS API Reference](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/hardening/trusted-webview/ios_trustedwebview_api_reference) | [shift-lite-idpsdk__development__hardening__trusted-webview__ios_trustedwebview_api_reference.md](shift-lite-idpsdk__development__hardening__trusted-webview__ios_trustedwebview_api_reference.md) |
| [Trusted WebView](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/hardening/trusted-webview/trusted_webview_overview) | [shift-lite-idpsdk__development__hardening__trusted-webview__trusted_webview_overview.md](shift-lite-idpsdk__development__hardening__trusted-webview__trusted_webview_overview.md) |

### development

| Page | Local copy |
|---|---|
| [CreateHttpCommonRequestEvent](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/http-common-request) | [shift-lite-idpsdk__development__http-common-request.md](shift-lite-idpsdk__development__http-common-request.md) |

### development/idpsdk

| Page | Local copy |
|---|---|
| [Activation](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/idpsdk/idpsdk-activation) | [shift-lite-idpsdk__development__idpsdk__idpsdk-activation.md](shift-lite-idpsdk__development__idpsdk__idpsdk-activation.md) |
| [Add User](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/idpsdk/idpsdk-add-user) | [shift-lite-idpsdk__development__idpsdk__idpsdk-add-user.md](shift-lite-idpsdk__development__idpsdk__idpsdk-add-user.md) |
| [Initialization of the IdpSdk](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/idpsdk/idpsdk-initialization) | [shift-lite-idpsdk__development__idpsdk__idpsdk-initialization.md](shift-lite-idpsdk__development__idpsdk__idpsdk-initialization.md) |
| [Migration from KSSIDP (Android/Kotlin)](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/idpsdk/idpsdk-kssidp-migration-android) | [shift-lite-idpsdk__development__idpsdk__idpsdk-kssidp-migration-android.md](shift-lite-idpsdk__development__idpsdk__idpsdk-kssidp-migration-android.md) |
| [Migration from KSSIDP (iOS/Swift)](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/idpsdk/idpsdk-kssidp-migration-ios) | [shift-lite-idpsdk__development__idpsdk__idpsdk-kssidp-migration-ios.md](shift-lite-idpsdk__development__idpsdk__idpsdk-kssidp-migration-ios.md) |
| [Login](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/idpsdk/idpsdk-login) | [shift-lite-idpsdk__development__idpsdk__idpsdk-login.md](shift-lite-idpsdk__development__idpsdk__idpsdk-login.md) |
| [IdpSdk Overview](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/idpsdk/idpsdk-overview) | [shift-lite-idpsdk__development__idpsdk__idpsdk-overview.md](shift-lite-idpsdk__development__idpsdk__idpsdk-overview.md) |

### development

| Page | Local copy |
|---|---|
| [Implement MasterController interface (iOS/Swift)](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/implement-interface) | [shift-lite-idpsdk__development__implement-interface.md](shift-lite-idpsdk__development__implement-interface.md) |
| [Initialization of the MasterController (iOS/Swift)](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/initialization) | [shift-lite-idpsdk__development__initialization.md](shift-lite-idpsdk__development__initialization.md) |
| [Invalid state](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/invalid-state) | [shift-lite-idpsdk__development__invalid-state.md](shift-lite-idpsdk__development__invalid-state.md) |
| [Logout](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/logout_digitanium+_shift) | [shift-lite-idpsdk__development__logout_digitanium+_shift.md](shift-lite-idpsdk__development__logout_digitanium+_shift.md) |
| [Communication with the MasterController (Android/Kotlin and Flutter)](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/master-controller-handler) | [shift-lite-idpsdk__development__master-controller-handler.md](shift-lite-idpsdk__development__master-controller-handler.md) |

### development/push-notification

| Page | Local copy |
|---|---|
| [Push Content](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/push-notification/push-content) | [shift-lite-idpsdk__development__push-notification__push-content.md](shift-lite-idpsdk__development__push-notification__push-content.md) |
| [Push Localization](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/push-notification/push-localization) | [shift-lite-idpsdk__development__push-notification__push-localization.md](shift-lite-idpsdk__development__push-notification__push-localization.md) |
| [Push Token](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/push-notification/push-token) | [shift-lite-idpsdk__development__push-notification__push-token.md](shift-lite-idpsdk__development__push-notification__push-token.md) |

### development

| Page | Local copy |
|---|---|
| [Set/Get Device Information](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/set-device-name) | [shift-lite-idpsdk__development__set-device-name.md](shift-lite-idpsdk__development__set-device-name.md) |
| [Set and Get Properties](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/set-property) | [shift-lite-idpsdk__development__set-property.md](shift-lite-idpsdk__development__set-property.md) |
| [Start/Restart Event](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/start) | [shift-lite-idpsdk__development__start.md](shift-lite-idpsdk__development__start.md) |
| [Stay Logged In](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/stay-logged-in) | [shift-lite-idpsdk__development__stay-logged-in.md](shift-lite-idpsdk__development__stay-logged-in.md) |
| [Suspend and Resume](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/suspend_resume) | [shift-lite-idpsdk__development__suspend_resume.md](shift-lite-idpsdk__development__suspend_resume.md) |

### development/tokens

| Page | Local copy |
|---|---|
| [Token for External Services (Exchange IAM Token)](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/tokens/exchange-iam-token) | [shift-lite-idpsdk__development__tokens__exchange-iam-token.md](shift-lite-idpsdk__development__tokens__exchange-iam-token.md) |

### development/tokens/token-handling

| Page | Local copy |
|---|---|
| [Authentication Modes and Biometry](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/tokens/token-handling/auth_modes_and_biometry) | [shift-lite-idpsdk__development__tokens__token-handling__auth_modes_and_biometry.md](shift-lite-idpsdk__development__tokens__token-handling__auth_modes_and_biometry.md) |
| [Token Types](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/tokens/token-handling/token_handling_intro) | [shift-lite-idpsdk__development__tokens__token-handling__token_handling_intro.md](shift-lite-idpsdk__development__tokens__token-handling__token_handling_intro.md) |

### development/tokens

| Page | Local copy |
|---|---|
| [Overview](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/tokens/tokens-overview) | [shift-lite-idpsdk__development__tokens__tokens-overview.md](shift-lite-idpsdk__development__tokens__tokens-overview.md) |

### development

| Page | Local copy |
|---|---|
| [Transaction](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/transaction) | [shift-lite-idpsdk__development__transaction.md](shift-lite-idpsdk__development__transaction.md) |

### idp

| Page | Local copy |
|---|---|
| [Requirements for Anonymous Activation](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/idp-anonymous-enrollment-config) | [shift-lite-idpsdk__idp__idp-anonymous-enrollment-config.md](shift-lite-idpsdk__idp__idp-anonymous-enrollment-config.md) |
| [Configuration of Token Permissions](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/idp-exchange-token-permission) | [shift-lite-idpsdk__idp__idp-exchange-token-permission.md](shift-lite-idpsdk__idp__idp-exchange-token-permission.md) |
| [Configuration of Partial Import Json](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/idp-json-config) | [shift-lite-idpsdk__idp__idp-json-config.md](shift-lite-idpsdk__idp__idp-json-config.md) |
| [Overview](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/idp-overview) | [shift-lite-idpsdk__idp__idp-overview.md](shift-lite-idpsdk__idp__idp-overview.md) |
| [Realm Management](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/idp-realm-management) | [shift-lite-idpsdk__idp__idp-realm-management.md](shift-lite-idpsdk__idp__idp-realm-management.md) |
| [User Management](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/idp-user-management) | [shift-lite-idpsdk__idp__idp-user-management.md](shift-lite-idpsdk__idp__idp-user-management.md) |
| [User Role Management](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/idp-user-role-management) | [shift-lite-idpsdk__idp__idp-user-role-management.md](shift-lite-idpsdk__idp__idp-user-role-management.md) |

### idp/postman_usage

| Page | Local copy |
|---|---|
| [General Structure](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/postman_usage/postman_general) | [shift-lite-idpsdk__idp__postman_usage__postman_general.md](shift-lite-idpsdk__idp__postman_usage__postman_general.md) |
| [Platform Activities](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/postman_usage/postman_platform_activities) | [shift-lite-idpsdk__idp__postman_usage__postman_platform_activities.md](shift-lite-idpsdk__idp__postman_usage__postman_platform_activities.md) |
| [TMS APIs](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/postman_usage/postman_tms) | [shift-lite-idpsdk__idp__postman_usage__postman_tms.md](shift-lite-idpsdk__idp__postman_usage__postman_tms.md) |
| [Token Handling API](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/postman_usage/postman_token_rest_api) | [shift-lite-idpsdk__idp__postman_usage__postman_token_rest_api.md](shift-lite-idpsdk__idp__postman_usage__postman_token_rest_api.md) |
| [User Activities](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/postman_usage/postman_user_activities) | [shift-lite-idpsdk__idp__postman_usage__postman_user_activities.md](shift-lite-idpsdk__idp__postman_usage__postman_user_activities.md) |

### mcsdk-api

| Page | Local copy |
|---|---|
| [AST Events](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/ast_event_list) | [shift-lite-idpsdk__mcsdk-api__ast_event_list.md](shift-lite-idpsdk__mcsdk-api__ast_event_list.md) |
| [Base Events](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/base_event) | [shift-lite-idpsdk__mcsdk-api__base_event.md](shift-lite-idpsdk__mcsdk-api__base_event.md) |
| [Composite Data Types](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/composite_types) | [shift-lite-idpsdk__mcsdk-api__composite_types.md](shift-lite-idpsdk__mcsdk-api__composite_types.md) |
| [Enumerations and Bitsets](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/enumerations) | [shift-lite-idpsdk__mcsdk-api__enumerations.md](shift-lite-idpsdk__mcsdk-api__enumerations.md) |

### mcsdk-api/error-handling

| Page | Local copy |
|---|---|
| [Different Error Types](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/error-handling/error_handling) | [shift-lite-idpsdk__mcsdk-api__error-handling__error_handling.md](shift-lite-idpsdk__mcsdk-api__error-handling__error_handling.md) |
| [RuntimeErrorEvent Error Codes](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/error-handling/mc_error_codes) | [shift-lite-idpsdk__mcsdk-api__error-handling__mc_error_codes.md](shift-lite-idpsdk__mcsdk-api__error-handling__mc_error_codes.md) |
| [Warning Event Codes](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/error-handling/mc_warnings) | [shift-lite-idpsdk__mcsdk-api__error-handling__mc_warnings.md](shift-lite-idpsdk__mcsdk-api__error-handling__mc_warnings.md) |
| [Status Type Evaluation](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/error-handling/status_type) | [shift-lite-idpsdk__mcsdk-api__error-handling__status_type.md](shift-lite-idpsdk__mcsdk-api__error-handling__status_type.md) |

### mcsdk-api

| Page | Local copy |
|---|---|
| [Helper Classes](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/helper_classes) | [shift-lite-idpsdk__mcsdk-api__helper_classes.md](shift-lite-idpsdk__mcsdk-api__helper_classes.md) |
| [Individual Events](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/individual_events) | [shift-lite-idpsdk__mcsdk-api__individual_events.md](shift-lite-idpsdk__mcsdk-api__individual_events.md) |

### mcsdk-api/set-property

| Page | Local copy |
|---|---|
| [Property Flags](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/set-property/property_flags) | [shift-lite-idpsdk__mcsdk-api__set-property__property_flags.md](shift-lite-idpsdk__mcsdk-api__set-property__property_flags.md) |
| [Property Owner Type](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/set-property/property_owner_type) | [shift-lite-idpsdk__mcsdk-api__set-property__property_owner_type.md](shift-lite-idpsdk__mcsdk-api__set-property__property_owner_type.md) |
| [Property Type](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/set-property/property_type) | [shift-lite-idpsdk__mcsdk-api__set-property__property_type.md](shift-lite-idpsdk__mcsdk-api__set-property__property_type.md) |

### prerequisites/app-lifecycle/add-app

| Page | Local copy |
|---|---|
| [Add App in Security Server in KOBIL Shift Lite](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/app-lifecycle/add-app/add_app) | [shift-lite-idpsdk__prerequisites__app-lifecycle__add-app__add_app.md](shift-lite-idpsdk__prerequisites__app-lifecycle__add-app__add_app.md) |
| [Add App in Security Server Overview](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/app-lifecycle/add-app/add_app_overview) | [shift-lite-idpsdk__prerequisites__app-lifecycle__add-app__add_app_overview.md](shift-lite-idpsdk__prerequisites__app-lifecycle__add-app__add_app_overview.md) |

### prerequisites/app-lifecycle/register-app-version

| Page | Local copy |
|---|---|
| [Details](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/app-lifecycle/register-app-version/register_app_version) | [shift-lite-idpsdk__prerequisites__app-lifecycle__register-app-version__register_app_version.md](shift-lite-idpsdk__prerequisites__app-lifecycle__register-app-version__register_app_version.md) |
| [Overview](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/app-lifecycle/register-app-version/register_app_version_overview) | [shift-lite-idpsdk__prerequisites__app-lifecycle__register-app-version__register_app_version_overview.md](shift-lite-idpsdk__prerequisites__app-lifecycle__register-app-version__register_app_version_overview.md) |

### prerequisites/app-lifecycle

| Page | Local copy |
|---|---|
| [Requirements from KOBIL App Security](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/app-lifecycle/requirements) | [shift-lite-idpsdk__prerequisites__app-lifecycle__requirements.md](shift-lite-idpsdk__prerequisites__app-lifecycle__requirements.md) |

### prerequisites

| Page | Local copy |
|---|---|
| [Getting Authorization Tokens](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/auth_token_shift) | [shift-lite-idpsdk__prerequisites__auth_token_shift.md](shift-lite-idpsdk__prerequisites__auth_token_shift.md) |

### prerequisites/mc-config-files

| Page | Local copy |
|---|---|
| [MC Configuration file mc\_config.json](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/mc-config-files/mc_config_json_shift) | [shift-lite-idpsdk__prerequisites__mc-config-files__mc_config_json_shift.md](shift-lite-idpsdk__prerequisites__mc-config-files__mc_config_json_shift.md) |
| [MC Configuration Files Overview](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/mc-config-files/mc_configuration_files_overview) | [shift-lite-idpsdk__prerequisites__mc-config-files__mc_configuration_files_overview.md](shift-lite-idpsdk__prerequisites__mc-config-files__mc_configuration_files_overview.md) |
| [MC Configuration file sdk\_config.jwt](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/mc-config-files/sdk_config_jwt) | [shift-lite-idpsdk__prerequisites__mc-config-files__sdk_config_jwt.md](shift-lite-idpsdk__prerequisites__mc-config-files__sdk_config_jwt.md) |
| [Trust Store Configuration](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/mc-config-files/trust_store) | [shift-lite-idpsdk__prerequisites__mc-config-files__trust_store.md](shift-lite-idpsdk__prerequisites__mc-config-files__trust_store.md) |

### project-setup

| Page | Local copy |
|---|---|
| [Android](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/project-setup/android-project_setup) | [shift-lite-idpsdk__project-setup__android-project_setup.md](shift-lite-idpsdk__project-setup__android-project_setup.md) |
| [iOS](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/project-setup/ios-project_setup) | [shift-lite-idpsdk__project-setup__ios-project_setup.md](shift-lite-idpsdk__project-setup__ios-project_setup.md) |

### testing/enrollment

| Page | Local copy |
|---|---|
| [Details](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/testing/enrollment/test_user_registration_activation_login_digitanium+_shift) | [shift-lite-idpsdk__testing__enrollment__test_user_registration_activation_login_digitanium+_shift.md](shift-lite-idpsdk__testing__enrollment__test_user_registration_activation_login_digitanium+_shift.md) |
| [Overview](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/testing/enrollment/test_user_registration_activation_login_overview) | [shift-lite-idpsdk__testing__enrollment__test_user_registration_activation_login_overview.md](shift-lite-idpsdk__testing__enrollment__test_user_registration_activation_login_overview.md) |

### testing

| Page | Local copy |
|---|---|
| [Test Set and Get Properties](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/testing/test_properties_shift) | [shift-lite-idpsdk__testing__test_properties_shift.md](shift-lite-idpsdk__testing__test_properties_shift.md) |

### testing/tms

| Page | Local copy |
|---|---|
| [Details](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/testing/tms/test_tms) | [shift-lite-idpsdk__testing__tms__test_tms.md](shift-lite-idpsdk__testing__tms__test_tms.md) |
| [Overview](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/testing/tms/test_tms_overview) | [shift-lite-idpsdk__testing__tms__test_tms_overview.md](shift-lite-idpsdk__testing__tms__test_tms_overview.md) |
