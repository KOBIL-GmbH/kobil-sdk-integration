# Bundled native SDK knowledge

The MCP includes eight first-priority Shift topics: setup, lifecycle, activation,
login, multi_step, tms, diagnostics and logs. It reads packaged resources through
Python importlib.resources; no customer-side WLA skill, Git checkout or network
lookup is needed to retrieve them.

- `sdk_knowledge_topics(platform, sdk_family)` lists content and qualification.
- `sdk_knowledge_get(topic, platform, sdk_family, sdk_version)` returns a complete
  recipe with prerequisites, sequence, expected result, failure handling,
  platform notes, concrete example and checks.
- `sdk_integration_checklist(...)` returns acceptance items, initially `not_run`.
  It does not scan an application or certify a completed integration.

Use platform `android` for Kotlin or `ios` for Swift. Unsupported targets/families
return `knowledge_gap`. Flutter examples require their own source and runtime
qualification. There is no substitution of SSMS/SuperApp/IDPSDK flows for a native
Shift example.

## Qualification

All 16 platform examples compile and link in fresh apps against classic MCSDK
Android 15.16.3088426 and iOS 15.16.803.3089231. They are concrete SDK dispatch,
configuration and utility functions, not complete application templates. The
caller supplies UI, selected deployment inputs, controller ownership and result
handling. `compile_ready=true` applies to that function in the stated SDK context.

Each example records its exact artifact version and validation scope. Complete
recipes remain `source_reviewed_unqualified` until live flow acceptance is done;
`version_verified=false` deliberately refers to that broader qualification.
Source revisions and file hashes identify inspected source snapshots, not SDK
release versions. MCP package version is a third distinct value.

Native deployment clients and backend flows are explicitly selected by the
customer. No customer aliases or backend settings are bundled. Administrative
MCP operations are separate from app-side SDK behavior. The knowledge tools never
create a flow, generate a transaction, approve one or mutate a backend.

## Maintainer qualification procedure

1. Acquire authorized Android/iOS artifacts and verify supplied checksums.
2. Select the integration generation (classic MCSDK/KSSIDP versus standalone
   IDPSDK); do not treat similarly numbered bundles as identical APIs.
3. Build fresh apps using only bundled recipes and supplied SDK API material.
4. Record exact app/source/artifact versions and command/device evidence.
5. Verify cold start, activation, returning login, multi-step cancellation,
   test-transaction approve/reject/terminal result, error capture and log export.
6. Update recipe qualification only for combinations actually verified; retain
   gaps and failed checks explicitly. Building is not runtime acceptance.

## MCSDK 15.16 diagnostic example checks

Fresh Kotlin and Swift harness apps were built with checksum-verified classic SDK
artifacts and run on physical devices on 2026-09-22:

| Platform | SDK artifact | Device | Result |
| --- | --- | --- | --- |
| Android | 15.16.3088426 | Pixel 8 | Synthetic event adapter passed |
| iOS | 15.16.803.3089231 | iPhone 17 Pro Max | Synthetic event adapter passed |

Both checks construct Warning, RuntimeError and FatalError SDK event objects,
verify category/description retention, retain code 800000271, and convert signed
-1 to unsigned 4294967295. This verifies adapter behavior, not the meaning of that
error code. Android used AGP 8.11.1/Kotlin 2.1.20/Gradle 8.13; iOS used Xcode 27.0.
The iOS launch requires the supplied hnb framework embedded alongside the controller.
Android AAR manifest label conflicts require an explicit app override when present.

The examples carry this limited validation independently of recipe qualification.
Real initialization, asynchronous event delivery, activation/login, multi-step,
TMS and log export are not qualified by these synthetic tests. SDK binaries,
signing identities and private device/backend configuration are not included.

Use the [native integration handoff](../skills/kobil-sdk/references/native-integration.md)
to connect backend tools, asset packaging, app callbacks and user acceptance.

[Candidate testing instructions](native-knowledge-testing.md) explain how to use
the matching MCP and skill without mixing them with an older installation.
