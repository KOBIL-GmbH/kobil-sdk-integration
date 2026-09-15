---
name: kobil-sdk
description: Integrate KOBIL SDK features into existing or fresh Kotlin Android, Swift iOS and Flutter/Dart apps on Android, iOS, Windows and macOS, using separately supplied SDKs and optional customer-selected provider modules.
---

# KOBIL SDK integration

Scope: all public SDK features across supported releases and the six
framework/OS combinations. Activation/login is the first milestone, not the
product boundary. The MCP supplies planning, artifact inspection and AST app/version/configuration
tools. Live verification, other backend/provider adapters and complete feature
recipes remain pending.

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
   The registration user must already exist. Other backend/user-flow adapters
   remain separate work; never claim they ran based on module selection.
4. Add minimal adapters, SDK initialization, lifecycle/event handling, UI flow,
   errors and cancellation to the customer's app. Read
   [platforms.md](references/platforms.md) for native/Flutter requirements.
5. Build and test each requested target. Verify actual feature behavior, restart,
   cancellation/errors and affected existing features. Track recipe-written,
   build-verified and runtime-verified separately. Repeat setup without duplicating
   backend resources or deleting existing device bindings.

Extend the feature inventory against public SDK APIs and release documentation.
For each feature record its platform/version support, dependencies, backend
operations, recipe and test evidence. Missing implementation is not proof that
an SDK feature is unsupported. Do not close the full-feature goal after login.
