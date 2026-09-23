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

## Source of app-flow logic

Follow [app-flow sources](references/app-flow-sources.md). App behavior comes from
the self-contained bundled knowledge pack via sdk_knowledge_get. Source repositories
and other skills are not required on customer machines. Recipes report their own
platform/family scope and qualification; do not treat source review or synthetic
event checks as live flow validation. The MCP supplies IDP/AST service operations; it must not
choose a login journey or create a replacement to fit sample code. Never use
SuperApp Login V2 for native Android/iOS. Missing discovery is unknown, not absence.
Use `sdk_service_catalog` to inspect installed operations and explicit gaps.
For a fresh native app, follow the [integration handoff](references/native-integration.md).

## Mandatory native flow gate

For native Android/iOS select exactly one path:

- KSTrustedWebView for a login journey inside the trusted WebView. Select its
  deployment clients explicitly; do not substitute the native KSSIDP clients.
- KSSIDP: activation **BDDKEnrollment**, login **BDDKLogin**,
  **useTokenBasedLogin=true**, **astServerBackend=maverick**, login header
  **X-KOBIL-ASTUSERID** containing the selected user ID.

Run `sdk_native_preflight` against the actual backend before building or testing.
Proceed only on `configuration_checked`; missing clients, unknown bindings,
SuperApp Login V2 or errors are blockers. Do not create/rebind backend flows or
reuse similarly named test clients. If the installed MCP lacks this tool, stop
and install the matching release. A checked binding is not runtime acceptance.

Never set useTokenBasedLogin=false as an activation workaround: it can prevent
IAM setup and produce CannotAcquireTokenData(50) before token exchange. Preserve
backend errors for investigation. Select PIN hashing/authentication policy
consistently with the existing native flow; do not change it for existing users.
On Swift match `.success`, `.eventFailed` and `.requestFailed` explicitly. Keep
the detailed event's status/code/description; never match success using strings.

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

For transaction confirmation or display messages, read [TMS](references/tms.md).
It separates AST backend operations, SDK event handling, authentication and push
from end-to-end verification. Foreground native Android and iOS accept/reject/timeout/server-cancel scenarios passed; consult
the recorded tuple and limits before extending coverage to other TMS modes.

## Automated app tests

When building or testing a native app, retrieve
`sdk_knowledge_get(topic="automated_testing", platform="android" or "ios")`
and its `sdk_integration_checklist`. This bundles Getting Started App test
know-how; customers do not need those repositories or another skill.
Keep unit checks, SDK integration and UI/backend acceptance separate. Adapt the
runner and app UI selectors to the actual project. Provision dedicated fixtures
through MCP tools, use bounded event waits, test cold returning login without
clearing activation data, and collect SDK errors/logs before cleanup. Preserve
source-noted gaps, ignored tests and unexecuted cases in the result report.
See [automated testing](../../docs/automated-testing.md).

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
   sdk_backend_status, then sdk_app_get and sdk_app_versions to discover existing
   registration/security metadata. Use sdk_app_ensure and sdk_app_version_ensure with the exact
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

## Additional service helpers

See [service interfaces](../../docs/service-interfaces.md) for explicit flow configuration operations, login-page fetch, activation-code generation/set, authentication testing, private AST token export and optional Grafana correlation. These tools do not select app flows.

## Encrypted connection stores

Use the `sdk_age_*` tools to create an encrypted store, import SFTP/SCP or backend passwords by reference, and store named AST/IDP profiles. Prefer `sdk_age_environment_selector_write` so server settings remain encrypted at rest. See [credential setup](../../docs/credentials.md). Store creation is separate from provisioning real credentials and from editor installation; never claim a transfer or backend login from successful storage alone.

For Mac-to-Mac or Mac-to-Windows credential delivery, use `sdk_age_transfer_export` with destination public recipients, then `sdk_age_credential_import_keyring` on the destination. Keep each private identity on its own machine. `keyring` selects native macOS Keychain or Windows Credential Manager automatically. Never transfer a private identity merely to make a delivery decryptable. See the cross-platform section in the credential setup guide.

## Importing shared credentials

Keep imported credentials under `kobil-sdk/import/`. Age import destination
labels should distinguish environment and purpose, such as `server-a/idp` and
`server-b/ast`; the MCP adds the prefix. Use its returned `credential_reference`
in recipient profiles. Never target unrelated local services, copy sender paths,
or replace an existing import unless explicitly requested. Profile-based imports
must already select the import namespace; existing legacy references stay readable.


For a complete server transfer, use `sdk_age_server_bundle_export` with explicit
private profile files and recipient public keys. On the recipient, list encrypted
environment names and call `sdk_age_server_bundle_import` with the selected names
and a local namespace. It imports credentials into the dedicated namespace and
writes encrypted profiles with local references. Create an environment selector
next; use `sdk_environment_select` for an explicitly requested session switch. Do not
carry sender filesystem paths to the recipient or claim backend verification
from a successful import. See the complete workflow in docs/credentials.md.

### Local file layout and access-error recovery

Keep received encrypted bundles inside the current project, for example
`.kobil-sdk/incoming/servers.age`, and imported encrypted settings at
`.kobil-sdk/environments.age`. Keep the private identity outside the project,
for example `~/.config/kobil-sdk/identities/<recipient>.key`. These are layout
recommendations, not hard-coded defaults. Resolve paths to absolute paths when
calling tools. Exclude local settings, selectors and deliveries from version control.

Never guess an identity path or reuse another component's private identity just
because its file exists. Use the recipient identity selected during setup and
share only its public recipient. A new identity cannot decrypt an old delivery:
the sender must export again for its public key. Keep private identities separate
from bundles; never copy them into the project or transfer them to another machine.

On `ACCESS_DENIED`, first inspect metadata only for the input identified by the
error: existence, owner, permissions and whether it is a symlink. Reads require
regular, owner-only files on POSIX (normally mode 0600); symlinks are refused.
Do not print contents or silently change ownership, permissions or unrelated
component files. Report the specific metadata problem and repair only the intended
local delivery/setup files. This error does not prove a wrong recipient or bundle
format. Only proceed to `sdk_age_store_list` after access succeeds; it returns
names without secrets. `AGE_DECRYPT_FAILED` means decryption or document validation
failed and does not by itself distinguish the two. Ask only for missing setup
information; derive project paths and a proposed namespace from the workspace.

### Two-chat server delivery: receiver public key first

When the user requests the MCP public key for receiving servers, call
`sdk_age_project_identity(project_path, project_uuid)` with the receiving project
directory. The optional project_uuid accepts the host project UUID when available.
Otherwise the MCP reads its project memory `.kobil-sdk/identity-reference.json`;
on first setup it generates and persists a UUID once. Never use a chat/session UUID.
Keep this memory file when moving the project so its ID and key remain discoverable.
The MCP enforces the private identity convention:
`~/.config/kobil-sdk/identities/<project-slug>-<persistent-project-uuid>/identity.key`.
The UUID identifies the project; the slug makes the directory readable.
Different project UUIDs keep same-named projects separate.
Do not invent personal identity filenames. Repeated calls reuse the same key.
Existing project identity references are adopted without rotating the key; the
old identity file is retained. A moved project must retain its identity reference
and access to its old private key; a new machine creates its own recipient.
The MCP writes `.kobil-sdk/recipient.txt` and `identity-reference.json` locally.
Exclude `.kobil-sdk/` from version control. Explicit-path identity tools remain
available for advanced setup; normal project setup uses this convention tool.
Return the full public `age1...` recipient prominently. Do not ask for bundle
path, environments or namespace merely to supply the receiver public key.

The user pastes that public key in the sender chat and specifies which servers
to export. The sender uses `sdk_age_server_bundle_export` with that recipient and
only the requested profiles. The user places the resulting encrypted `.age` file
in the receiving project. The receiver uses its retained identity to list names
with `sdk_age_store_list`, then imports the selected servers through
`sdk_age_server_bundle_import`. Use project-local encrypted output settings and
the `kobil-sdk/import/` namespace. A private key is never part of the handoff.

### Switching the active backend

For an explicit server change, finish current backend workflows, call
`sdk_backend_status`, then `sdk_environment_select(connection_path,
expected_current_environment, expected_environment)` with the existing absolute
connection JSON or age-selector path. Use the reported current environment and
requested target name; never guess them. The MCP validates both profiles and
switches subsequent calls without a reconnect. Failed selection leaves the old
selection intact. Credential import alone never activates a server.

Selection is local to the running MCP process, does not edit app assets or launcher
configuration, and does not verify credentials or connectivity. Restart restores
`KOBIL_SDK_CONNECTION` from the launcher. For persistent setup, update that launch
configuration separately. After switching, verify backend authentication and the
native preflight, select app/version and obtain a new SDK JWT before rebuilding
apps. Do not reuse assets/JWTs from the previous backend. Older installed versions
without this tool require a one-time upgrade/reconnect.
