---
name: kobil-sdk
description: Integrate KOBIL SDK features into existing or fresh Kotlin Android, Swift iOS and Flutter/Dart apps on Android and iOS, using separately supplied SDKs and optional customer-selected provider modules.
---

# KOBIL SDK integration

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
Use `sdk_sftp_list` and `sdk_sftp_download` for SFTP acquisition; do not create
a temporary downloader when these tools are available. SFTP access and backend
provisioning are separate connections. After downloading
SDKs, ask which changelog to show: iOS, Android or Flutter. Wait for the user's
selection, then print the selected release notes as required by the delivery
recipe; a saved review or link alone is insufficient.

Use sdk_targets and sdk_plan to choose dependencies. Record requested features,
SDK/wrapper versions, platform architectures, artifact checksums, identifiers,
backend prerequisites, chosen modules and verification outcomes in the app's
integration record. Exclude tokens, passwords, PINs and activation codes.

## Feature recipes

For transaction confirmation or display messages, read [TMS](references/tms.md).
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
3. For AST/Shift, read [backend setup](../../docs/backend.md), then call
   sdk_backend_status, then sdk_app_get and sdk_app_versions to discover existing
   registration/security metadata. Use sdk_app_ensure and sdk_app_version_ensure with the exact
   environment and explicit registration user/integrity policy. Request signed
   configuration with sdk_config_write; never invent a JWT or expose it in chat.
   Prefer reusing an appropriate existing backend app/version and its selected
   registration user; a fresh client app does not require a new backend app.
   When creating an app/version, select an existing tenant user explicitly as
   registration user. The deployment owner may choose any existing user; do not
   invent a mandatory special registration-account type. With no known user,
   create a dedicated registrar with sdk_activation_user_ensure and use its uuid.
   App categories are push-notification categories ("tms" for transaction
   confirmation, "chat" for messaging); sdk_app_get shows the tenant's values. For this AST API the
   registerUserId field is set on the version. Preserve an existing selection
   and verify readback; never silently replace it with the activation user.
   The registration user must already exist. Other backend/user-flow adapters
   remain separate work; never claim they ran based on module selection.
   For the first activation of a device, find the realm's journeys with
   sdk_idp_journeys: it reports which clients run an activation-code flow and which run
   a login flow, whatever they are named; never assume a client name from another realm.
   sdk_activation_flow_ensure with sdk_activation_client_ensure create an activation
   journey when the realm has none, under names of your choosing. Then create a separate activation user with sdk_activation_user_ensure, give it
   its permanent login password with sdk_activation_password_set (the activation journey
   sets none) and issue its one-time code with sdk_activation_code_set. Both need the optional admin block in the connection
   file. Hand the code to the tester only; never log, commit or repeat it, and do
   not reissue after a failure before inspecting whether it was consumed.
   Before the first device run read
   [activation-login-findings.md](references/activation-login-findings.md): the token-time
   513_4036 defect, its `acr_values=1` bypass, and the client/flow/theme pairings that work.
   Before a login test, and first whenever a login hangs on a spinner, run
   sdk_idp_theme_check on the login client: a page KSSIDP cannot parse fails silently.
   When the device console is silent or expired, sdk_activation_user_status is the
   record: a session for the login client proves a login, a failure count proves a
   rejected credential, a consumed ACTIVATION_CODE proves the activation reached the end.
4. Add minimal adapters, SDK initialization, lifecycle/event handling, UI flow,
   errors and cancellation to the customer's app. Read
   [platforms.md](references/platforms.md) for native/Flutter requirements. For Swift
   iOS start from the verified reference implementation in
   [references/ios/README.md](references/ios/README.md) and its five source files; they
   encode every device failure found so far, so copy them before writing new SDK code.
   Resolve SDK AuthenticationMode independently of the name of the input field:
   a backend password/PIN does not imply SDK PIN mode. In the inspected native
   implementation, PIN mode requires jwtSignKeySecurityPolicy; preserve the
   selected deployment contract instead of inventing that policy. Install
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
   getting a yes; report what would be removed and why. A code embedded in a test is both a leak and a one-time value that the
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

After each successful integration step, update the relevant skill/reference with
what worked, the applicable SDK/platform versions, prerequisites and verification
method. Do this at the checkpoint, not only at the end of the task. Keep the
entry reusable and customer-neutral; internal hosts, credentials, test identities,
JWTs and private logs stay in local evidence. Record build, launch, SDK start,
activation and return-login separately. Failed or untested steps remain explicitly
pending; a passed backend request is not a passed SDK integration.
