---
name: kobil-sdk
description: Integrate KOBIL SDK features into existing or fresh Kotlin Android, Swift iOS and Flutter/Dart apps on Android, iOS, Windows and macOS, using separately supplied SDKs and optional customer-selected provider modules.
---

# KOBIL SDK integration

Scope: all public SDK features across supported releases and the six
framework/OS combinations. Activation/login is the first milestone, not the
product boundary. The MCP supplies planning, artifact inspection and AST app/version/configuration
tools. Fresh Kotlin Android activation and returning login have passed on a
physical device; see [verified workflow](references/platforms.md#verified-android-activation-and-login).
Other platforms, backend/provider adapters and remaining feature recipes require
separate implementation and verification.

## Resolve the customer's request

Inspect the target app's rules, dependency/build files and configuration.
For a fresh app, resolve its framework, directory, targets and app identifiers.
Use existing session choices; ask only for missing decisions that affect the
result. Never infer a customer's tenant, account or provider from internal
examples. SDK binaries are supplied separately; never fetch an unauthorized
release or commit artifacts/credentials to this repository.

Use sdk_targets and sdk_plan to choose dependencies. Record requested features,
SDK/wrapper versions, platform architectures, artifact checksums, identifiers,
backend prerequisites, chosen modules and verification outcomes in the app's
integration record. Exclude tokens, passwords, PINs and activation codes.

## Feature recipes

For transaction confirmation or display messages, read [TMS](references/tms.md).
It separates AST backend operations, SDK event handling, authentication and push
from end-to-end verification. TMS is studied but not yet runtime-verified here.

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
   release against trusted metadata before use.
3. For AST/Shift, read [backend setup](../../docs/backend.md), then call
   sdk_backend_status, sdk_app_ensure and sdk_app_version_ensure with the exact
   environment and explicit registration user/integrity policy. Request signed
   configuration with sdk_config_write; never invent a JWT or expose it in chat.
   Prefer reusing an appropriate existing backend app/version and its selected
   registration user; a fresh client app does not require a new backend app.
   When creating an app/version, select an existing tenant user explicitly as
   registration user. The deployment owner may choose any existing user; do not
   invent a mandatory special registration-account type. For this AST API the
   registerUserId field is set on the version. Preserve an existing selection
   and verify readback; never silently replace it with the activation user.
   The registration user must already exist. Other backend/user-flow adapters
   remain separate work; never claim they ran based on module selection.
4. Add minimal adapters, SDK initialization, lifecycle/event handling, UI flow,
   errors and cancellation to the customer's app. Read
   [platforms.md](references/platforms.md) for native/Flutter requirements.
   Resolve SDK AuthenticationMode independently of the name of the input field:
   a backend password/PIN does not imply SDK PIN mode. In the inspected native
   implementation, PIN mode requires jwtSignKeySecurityPolicy; preserve the
   selected deployment contract instead of inventing that policy. Install
   the fatal/error event listener before sending the first Start/initialization
   request; follow the diagnostic requirements below.
5. Build and test each requested target. Verify actual feature behavior, restart,
   cancellation/errors and affected existing features. Track recipe-written,
   build-verified and runtime-verified separately. Repeat setup without duplicating
   backend resources or deleting existing device bindings.

Extend the feature inventory against public SDK APIs and release documentation.
For each feature record its platform/version support, dependencies, backend
operations, recipe and test evidence. Missing implementation is not proof that
an SDK feature is unsupported. Do not close the full-feature goal after login.

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
