---
name: kobil-sdk
description: Integrate KOBIL SDK features into existing or fresh Kotlin Android, Swift iOS and Flutter/Dart apps on Android and iOS, using separately supplied SDKs and optional customer-selected provider modules. Also answers questions about how the KOBIL MCSDK works and what it can do.
---

# KOBIL SDK integration

Questions about how the SDK works or whether it can do something: answer from
[overview.md](references/overview.md) (`sdk_docs` section `overview`) first; it gives each
capability's tested status and the page with the details. Answer through the tools, in this
order: `sdk_docs` section `overview`; `sdk_official_docs_search` (official pages and this
plugin's guides, each result labelled `official` or `guide`); and for any class, event or
method name, `sdk_api_lookup`, which reads the installed SDK's headers and says whether the
binary exports the class. Say which of the three each part of the answer came from.

The official KOBIL MCSDK documentation (Shift Lite - IdpSdk and the MCSDK introduction) is
bundled in [references/official/](references/official/README.md): search it with
`sdk_official_docs_search`, read a page with `sdk_docs` section `official/<page>`, and cite
its source URL. It is the source of truth for SDK behaviour. Where it disagrees with the
delivered SDK headers (e.g. deprecated suspend/resume), the headers decide what compiles; the
index lists the known cases. Our guides add what was verified on devices on top of it.

Scope: all public SDK features across supported releases and the four
framework/OS combinations. Activation/login is the first milestone, not the
product boundary. The MCP supplies planning, artifact inspection and AST app/version/configuration
tools. Fresh Kotlin Android and Swift iOS activation and returning login have passed
on physical devices; see the [verified platform workflows](references/platforms.md).
Other platforms, backend/provider adapters and remaining feature recipes require
separate implementation and verification.

External-customer app targets are Android and iOS only. macOS and Windows
apps are outside this scope; do not offer or plan them as customer SDK targets.
This is a scope decision, not a claim that desktop SDKs do not exist.

## Resolve the customer's request

Inspect the target app's rules, dependency/build files and configuration.
For a fresh app, resolve its framework, directory, targets and app identifiers.
Use existing session choices; ask only for missing decisions that affect the
result. Never infer a customer's tenant, account or provider from internal
examples. SDK binaries are supplied separately; never fetch an unauthorized
release or commit artifacts/credentials to this repository.

Customers generally receive a separate SFTP account for SDK delivery. Read
[SDK delivery](references/sdk-delivery.md) when acquiring supplied artifacts;
SFTP access and backend provisioning are separate connections. After downloading
SDKs, ask which changelog to show: iOS, Android or Flutter. Wait for the user's
selection, then print the selected release notes as required by the delivery
recipe; a saved review or link alone is insufficient.

Use sdk_targets and sdk_plan to choose dependencies. Record requested features,
SDK/wrapper versions, platform architectures, artifact checksums, identifiers,
backend prerequisites, chosen modules and verification outcomes in the app's
integration record. Exclude tokens, passwords, PINs and activation codes.

## Feature recipes

Where each feature lives (every path is a `sdk_docs` section):

| The app needs | Read | Copy |
|---|---|---|
| activation and sign-in | [ios/README.md](references/ios/README.md), [login-standards.md](references/login-standards.md) | one variant folder |
| approve a payment, message or signature request | [tms.md](references/tms.md) | `ios/TransactionCenter.swift`, `ios/ui/ApprovalSheet.swift` |
| payment data shown on the sheet | [tms.md](references/tms.md) § Payment data | — |
| saved cards, "Pay with" | [wallet.md](references/wallet.md), [design-system.md](references/design-system.md) § Payment, cards and wallet | `ios/wallet/` |
| sign a PDF in the app | [signing.md](references/signing.md) | `ios/signing/` |
| profile photo | [profile-photo.md](references/profile-photo.md) | `ios/profile/` |
| Face ID, settings, users, tokens, web view, call guard | [sdk-features.md](references/sdk-features.md) | `ios/platform/`, `ios/sdk-requests/` |
| look of a whole app | [reference-app-design.md](references/reference-app-design.md) | `ios/ui/Theme.swift` |
| can the SDK do X? | [overview.md](references/overview.md) | — |

For transaction confirmation, display messages, server-requested signing or chat, read
[TMS](references/tms.md) first: the iOS MCSDK has no chat send/receive API, and a
server-requested signature is an accepted TMS.

For the user signing a PDF **in the app** (hand-drawn signature, "Sign here" field, signed
PDF file), read [signing.md](references/signing.md): the
SDK's `KSMSignDataEvent` returns a detached CMS that `ios/signing/PdfSigner.swift` embeds;
`pdfsig` on the device's file is the proof. For a profile photo read
[profile-photo.md](references/profile-photo.md) and check the profile service exists
before building an upload. For saved cards and a "Pay with" row on a payment approval read
[wallet.md](references/wallet.md): the wallet is app-side (the SDK has no card API), keeps no
card number or security code, and only labels the approval; it moves no money.

For any other MCSDK feature, read [sdk-features.md](references/sdk-features.md) first. Its
"What the developer asks for" table maps each request to a reference file. This covers:
- settings: SDK state, users on the device, device name, Face ID sign-in (`ios/platform/BiometricSignIn.swift`; the SDK-native biometric mode needs IDP scopes a Shift realm lacks), change PIN;
- user lifecycle: add, delete (deactivate), reactivate, offline, token or anonymous login;
- push token, IAM tokens and HTTP calls to your own backend, upload, decrypt, data store,
  properties;
- update check, licences, connection and busy status, tracing, workspace switch;
- PIN or token transactions and app-initiated transactions;
- the trusted web view and scam-call protection.

The guide says per call how far it was checked. 12 classes are declared in the 15.16 headers
but missing from the binary (muting, multipart upload), so those can't be built.

Copy the reference code for these features (`ios/signing/`, `ios/profile/`, `ios/ui/`,
`ios/tests/`, `ios/sdk-requests/`, `ios/platform/`, `ios/wallet/`) and write only the wiring
the guides show. They compile as a set in Swift 5 and 6, Debug and Release, with
`SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor` (the plugin's test suite type-checks every variant); signing, profile and TMS passed on a device, and
sdk-features.md marks per call what did. Rewriting them is how a PDF ends up looking signed yet failing validation.
It separates AST backend operations, SDK event handling, authentication and push
from end-to-end verification. Foreground native Android and iOS accept/reject/timeout/server-cancel scenarios passed; consult
the recorded tuple and limits before extending coverage to other TMS modes.

## Modules

Read [modules.md](references/modules.md). Providers are conditional: a customer
using Updraft, TestFlight or Grafana should be offered the corresponding module.
Requesting its distribution/observability capability selects the dependency.
Selection does not install an adapter, configure credentials or authorize an
upload, publication, notification or account change. Missing adapters remain
explicit work; do not claim connections that this starter does not implement.

## Integration workflow

1. Resolve exact SDK APIs, compatible native and wrapper versions, target
   architectures and backend requirements from the supplied SDK documentation.
2. Inspect separately supplied artifacts with sdk_artifact_info. Its checksum
   is a fingerprint, not compatibility or authenticity verification. Verify the
   release against trusted metadata before use. For iOS, sdk_ios_project_integrate
   wires the SDK into the Xcode project (frameworks as Embed & Sign, bridging header,
   version) and, when the local store is empty, first imports the delivery bundled with
   this MCP, verified against the shipped .sha512 files. Then show the release notes
   with sdk_artifacts_notes and build before coding. Use sdk_artifacts_import or
   sdk_artifacts_install only for a delivery that arrived somewhere else.
3. For AST/Shift, read [backend setup](../../docs/backend.md). Then, in this order:
   - **Connection.** sdk_backend_status, then sdk_backend_verify before any write.
   - **App and version.** A new app gets its own backend app: call sdk_app_ensure with a
     name derived from the app the user asked for (for "KOBILTrustilo", `KOBILTrustilo`),
     never with an app you found in sdk_app_get. Other tenants' apps belong to other
     products; reuse one only when the user names it. When extending an existing project,
     keep the app name its code already uses. sdk_app_get and sdk_app_versions show what
     exists, so that ensure calls stay idempotent. Create the app and version with
     sdk_app_ensure and sdk_app_version_ensure with the exact environment, the platform
     string sdk_platforms reports, an explicit integrity policy and an explicit
     registration user. For this AST API the registerUserId field is set on the version.
     Any existing tenant user may be the registration user; reuse the one on an existing
     version, or create a dedicated registrar with sdk_activation_user_ensure and use its
     uuid. Do not invent a special registration-account type. Preserve an existing
     selection and verify readback; never silently replace it with the activation user.
     App categories are push-notification categories ("tms" for transaction
     confirmation, "chat" for messaging); sdk_app_get shows the tenant's values.
   - **Bundle files.** sdk_trusted_certificate_write, then sdk_config_write with that
     certificate (never invent a JWT or expose it in chat), then sdk_mc_config. Its client
     is the one that issues the login tokens: the login client for email-code activation
     and for both official login standards (KSSIDPWebBasedLogin or BDDKLogin), the
     activation-code client only for the custom one-page activation-code journey
     (sdk_mc_config explains why). All three refuse to overwrite. For explicit-authentication transactions also
     run sdk_tms_scope_ensure on that client.
   - **Official login standards first.** KOBIL defines two native standards, each a pair
     of clients and flows from KOBIL's official IDP exports: `kssidp` (current;
     KSSIDPWebBasedEnrollment / KSSIDPWebBasedLogin, three enrollment pages with an
     admin-issued temporary password) and `bddk` (deprecated, removal planned for IDP 6.0;
     BDDKEnrollment / BDDKLogin, one page). sdk_idp_journeys tags their clients with
     `login_standard`. When the realm has them, or the customer names one, read
     [login-standards.md](references/login-standards.md) and run sdk_login_standard_check
     before any app code; it must say `configuration_checked`. A blocked result goes to the
     IDP administrator with the official export; never build a look-alike flow. Use bddk
     only where it already runs, and say it is deprecated. The iOS files are
     `references/ios/login-standards/`.
   - **Choose the activation, in this fixed order.** sdk_idp_journeys lists the realm's
     clients, whatever they are named; never assume a client name from another realm.
     1. A client tagged `login_standard: kssidp` exists: use the **login-standards variant**
        (kssidp), even when `email_code` clients exist too. This is KOBIL's official native
        standard.
     2. Only `bddk` is tagged: use the login-standards variant with bddk, and say it is deprecated.
     3. Neither, but `email_code` clients exist: the email-code variant.
     4. None of these: create an activation-code flow and client (sdk_activation_flow_ensure,
        sdk_activation_client_ensure) under names of your choosing.
     Deviate only when the user asks for a different activation; say which one you chose and why.
   - **Activation-code test users only** (for the kssidp standard see login-standards.md:
     the password is temporary). Create a separate activation user with
     sdk_activation_user_ensure, give it its permanent login password with
     sdk_activation_password_set (the activation-code journey sets none) and issue its
     one-time code with sdk_activation_code_set. Both need the optional admin block in the
     connection file. Hand the code to the tester only; never log, commit or repeat it, and
     do not reissue after a failure before inspecting whether it was consumed.
     These admin tools are the only way to issue codes. The app never requests a code from a
     helper service, and no helper is built to write the IDP database, restart IDP pods or send
     the code by mail. A dev realm without working mail is not a reason for one: the tester types
     the issued code. Mail delivery is the realm's own email setting, owned by the backend team.
   - **Before the first device run** read
     [activation-login-findings.md](references/activation-login-findings.md): the token-time
     513_4036 defect, its `acr_values=1` bypass, and the client/flow/theme pairings that work.
     Before a login test, and first whenever a login hangs on a spinner, run
     sdk_idp_theme_check on the login client: a page KSSIDP cannot parse fails silently.
     It does not apply to the login standards (kssidp, bddk): their login clients start with
     an AST step and answer 406 ("not checkable"). For kssidp, sdk_login_standard_check checks
     the theme; after that only a device validates the pages.
   - **Evidence.** When the device console is silent or expired, sdk_activation_user_status
     is the record: a session for the login client proves a login, a failure count proves a
     rejected credential, a consumed ACTIVATION_CODE proves the activation reached the end.
   Other backend/user-flow adapters remain separate work; never claim they ran based on
   module selection. Creating backend app/version records does not prove that SDK
   app/device registration has completed.
4. Add minimal adapters, SDK initialization, lifecycle/event handling, UI flow,
   errors and cancellation to the customer's app. Read
   [platforms.md](references/platforms.md) for native/Flutter requirements. For Swift
   iOS start from the verified reference implementation in
   [references/ios/README.md](references/ios/README.md) and its source files; they
   encode every device failure found so far, so copy them before writing new SDK code.
   The look is the customer's choice. If they give none, take ideas from
   [reference-app-design.md](references/reference-app-design.md) (screen flow, tabs, layout
   hints for a whole app) and [design-system.md](references/design-system.md) (KOBIL
   tokens and components); `references/ios/ui/Theme.swift` and `ui/ApprovalSheet.swift` are
   ready-made building blocks you may use or restyle. These are suggestions, not a required design.
   Follow the assistant rules at the end of design-system.md, and check every screen you
   change with the bundled `ios-visual-check` skill (light and dark screenshots) before done.
   The README's first table says which files belong to the email-code, the
   activation-code and the login-standards variant; copy one variant, never both sessions. Use the simulator for
   layout only; activation and login are verified on physical devices.
   Resolve SDK AuthenticationMode independently of the name of the input field:
   a backend password/PIN does not imply an SDK PIN mode. The iOS 15.16 headers offer
   `.no`, `.biometric` and `.password` only; the official docs also list PIN, which this
   iOS delivery does not have. `jwtSignKeySecurityPolicy` in mc_config.json governs the
   signed-JWT (authorization-grant) login, not a PIN mode; preserve the selected deployment
   contract instead of inventing that policy. Install
   the fatal/error event listener before sending the first Start/initialization
   request; follow the diagnostic requirements below.
5. Build and test each requested target. Verify actual feature behavior, restart,
   cancellation/errors and affected existing features. Credential entry on the device
   is the tester's job: run the app, hand the tester the user id, one-time code and
   password in chat, and wait; then read the console or sdk_activation_user_status.
   Do not automate those screens with UI tests or synthesized taps, and never write
   an activation code or password into source files, test files, scripts, logs or
   commits. Never uninstall, replace or reconfigure other apps or settings on the
   tester's device, or delete files outside the project, without asking first and
   getting a yes; report what would be removed and why. To test the approval screens,
   sdk_tms_test_sequence sends a display message, a signature request and a payment one after
   another (each waits for the device's answer); sdk_tms_test_sequence_status reports them. A code embedded in a test is both a leak and a one-time value that the
   test will spend. Track recipe-written,
   build-verified and runtime-verified separately. Repeat setup without duplicating
   backend resources or deleting existing device bindings.

Extend the feature inventory against public SDK APIs and release documentation.
For each feature record its platform/version support, dependencies, backend
operations, recipe and test evidence. Missing implementation is not proof that
an SDK feature is unsupported. Do not close the full-feature goal after login.

For SDK log collection, read [log export](references/log-export.md): locate the
actual native log directories, create and validate an encrypted ZIP, then share
through the platform UI. Export and decryption are separate operations.

## Warning, runtime and fatal error diagnostics

Treat asynchronous fatal/error events as essential diagnostic output. A failed
Start/result callback can have errorCode=0 even when a separate FatalErrorEvent
contains the actual cause. Logging only the event class or status is insufficient.

- Attach the SDK's event/delegate listener as soon as its instance exists, before
  the first Start request. Verify that wrapper-specific listeners forward fatal
  events; observe the underlying SDK event stream when needed.
- Handle WarningEvent, RuntimeErrorEvent and FatalErrorEvent explicitly (or the
  release's equivalents). All three MC-to-UI events carry errorType,
  errorDescription and errorCode. Capture their
  numeric error code, subsystem, explanation/message, report/correlation ID and
  timestamp where exposed. Inspect the selected SDK's real API; field names vary
  between Kotlin, Swift and Dart wrappers. Do not invent getters.
- Record the matching request/result status and the event sequence. Preserve the
  useful error explanation in a restricted local diagnostic file. Redact tokens,
  PINs, activation codes and personal data before sharing; never dump arbitrary
  event objects or encrypted/decrypted logs into a public repository.
- On failure, inspect the fatal-event explanation and documented error-code
  meaning first. A zero result code is not evidence that no diagnostic exists.
  Check the concrete resource/configuration named in the error before guessing
  SDK incompatibility or changing TLS, integrity, signing or hardening settings.
- For KSSIDP REQUEST_FAILED, capture HTTP status, SDK request status, application
  error code/subsystem and private error description. HTTP 200 can carry a
  rejected activation. Read the actual explanation before interpreting numeric
  codes across layers. Resolve the configured password/PIN policy and hashing
  contract before generating test input; never weaken policy to pass a test.
- Correct the identified cause and repeat initialization, activation and login
  after restart. Report each result separately. If fatal events are not received,
  verify listener registration/forwarding before escalating to SDK log decryption.

## Start and restart lifecycle

Follow the [Start/Restart documentation](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/start#restartevent).
Gate SDK operations on successful StartResultEvent or RestartResultEvent. A
global listener must handle unsolicited restart results at any time. Handle
RuntimeErrorEvent immediately; its explanation precedes the automatic restart.
Do not wait for the original operation result to discover the failure or start
a competing retry loop. Clear readiness during restart, then route by the new
SDK state. StartLoginEvent is for previously activated users after start/restart;
do not wait for it on first activation or immediately after Shift Lite activation.

For signed AST configuration, include astUrl and the deployment-specific services
map in the backend signing request:
the SDK requires the gateway in the signed payload even if the backend accepts
its omission. A successfully issued JWT is not proof of SDK compatibility.
Never patch a signed JWT locally; request a corrected one from the backend.
With MC 188.1.2937039, an empty services map allowed Start but caused error
800000271 (REST module is not initialised) during GetAstClientData. Check that
astLogin and the other required service endpoints are included before retrying
registration/activation. Creating backend app/version records does not prove
that SDK app/device registration has completed.

## Ask when progress stalls

When a failure has no evidence-backed next correction, ask the user promptly
with the exact event/error, the last successful step and the specific missing
input or access. Do not keep trying authentication modes, identities or settings
to find one that works. If a failure may have consumed an activation code or
changed backend credentials, inspect that state and explain it before continuing.

## Record each verified step

After each successful integration step, record in the app's integration record (not
in this installed, version-pinned skill) what worked, the applicable SDK/platform
versions, prerequisites and verification method; findings the skill should carry are
reported to its maintainers for the next release. Do this at the checkpoint, not only at the end of the task. Keep reports
to maintainers reusable and customer-neutral; internal hosts, credentials, test identities,
JWTs and private logs stay in local evidence. Record build, launch, SDK start,
activation and return-login separately. Failed or untested steps remain explicitly
pending; a passed backend request is not a passed SDK integration.
