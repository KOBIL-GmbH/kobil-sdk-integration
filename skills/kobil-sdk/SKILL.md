---
name: kobil-sdk
description: Build a new app with the KOBIL SDK ("build me an app with MCSDK") or integrate KOBIL SDK features into existing or fresh Kotlin Android, Swift iOS and Flutter/Dart apps on Android and iOS, using separately supplied SDKs and optional customer-selected provider modules.
---

# KOBIL SDK integration

## Start here: the minimal native journey (one knowledge call, one tool load)

Load the standard-journey tools once with a single ToolSearch
`select:` of these exact names: `sdk_service_catalog`, `sdk_backend_status`,
`sdk_knowledge_bundle`, `sdk_artifact_info`, `sdk_plan`, `sdk_native_preflight`,
`sdk_deployment_preflight`, `sdk_idp_user_search`,
`sdk_idp_activation_code_generate`, `sdk_idp_user_credentials_list`,
`sdk_tms_explicit_preflight`, `sdk_tms_trigger`, `sdk_tms_status`,
`sdk_tms_result`, `sdk_tms_cancel`. Then follow this order; every later section
of this skill refines a step, none replaces it.

00. "Build me an app with the KOBIL SDK" (or any similar short request): call `sdk_build_app_brief` first. It returns
   the complete task for this project with the exact tools and parameters, the gates and the rules; follow it without
   asking, and ask the owner only for what its `needs_input` lists.
0. Binding first: `sdk_runtime_info` (which runtime and which project this MCP is
   bound to) and `sdk_backend_status`. `configured: true` means the installation is
   already onboarded: use that connection, never call `sdk_onboarding_prepare`,
   never draft an access request, even if `.kobil-sdk/credential-request.txt`
   exists in the project. Only the error `CONNECTION_NOT_SELECTED` leads to the
   onboarding section at the end of this skill. If the bound project differs from
   the project open in the IDE, stop and tell the user to regenerate the adapter.
1. Knowledge: `sdk_knowledge_bundle(platform="android"|"ios")` returns setup,
   activation, login, tms, logs and diagnostics in one call (replaces ~10
   sequential `sdk_knowledge_get` calls). Read
   [native-integration.md](references/native-integration.md) once; open
   [tms.md](references/tms.md) and [log-export.md](references/log-export.md)
   when you reach those steps. `lifecycle`, `multi_step`, `automated_testing`
   stay separate `sdk_knowledge_get` topics.
2. Backend and artifacts: `sdk_backend_status` (also returns `hosts`,
   `idp_realm_base` and `tls_check_hosts`: the authorization endpoint is
   `<idp_realm_base>/protocol/openid-connect/auth`, never guess the realm path;
   run `sdk_tls_chain_check` for every host in `tls_check_hosts`),
   `sdk_artifact_info(path)` on
   each delivery ZIP (see [sdk-delivery.md](references/sdk-delivery.md) for
   locating AARs/xcframeworks inside it), `sdk_plan(profile)`.
3. Gates before code: `sdk_native_preflight`, then `sdk_deployment_preflight`
   with the actual mc_config. Proceed only on `configuration_checked`.
   Resolve the test target against the sign-key policy first: an emulator or
   simulator cannot satisfy `ENFORCE_STRONG_HARDWARE` / `ENFORCE_HARDWARE` and
   would fail at activation after consuming the code. Stop and offer
   `ALLOW_VIRTUAL_SMART_CARD` for the fixture or a physical device; see
   [signing-policy.md](references/signing-policy.md). Never downgrade a
   deployment policy silently.
   iOS, before the first build with SDK code: Xcode's own agent tools cannot embed a
   framework, and an app that is only linked builds and then crashes at launch with
   "Library not loaded". Call `sdk_ios_project_integrate(project_path, target_name,
   frameworks_dir)` with the debug set (`sdk_artifact_info` accepts the `.xcframework`
   folders to check them first). It links and embeds all four with code sign on copy,
   writes the bridging header and limits the target to iPhone and iPad; build once, then
   check that the app starts on a simulator. Do not edit `project.pbxproj` by hand. If it
   refuses (the project already references XCFrameworks another way), the owner does it
   once in Xcode: target > General > Frameworks, Libraries, and Embedded Content > set all
   four to **Embed & Sign**. The console warning `Class VersionInfo is implemented in both
   kssidp.framework and KSMasterController.framework` is a known duplicate-class warning:
   **ignore it**. Do not try to fix it, do not remove or re-link a framework because of it, and do not
   report it as a problem.
4. Start: register listeners, Start the SDK, observe the Start result event.
   iOS Swift: the result of a request event (Start, GetSdkState, login, TMS) returns through the completion handler of
   `controller.receive(event, withCompletionHandler: { reply in ... })`; with `withCompletionHandler: nil` (never pass nil) the
   `KSMStartResultEvent` is lost and anything that waits for it, a continuation or a test, waits forever. Feed the reply of the
   handler and the events the consumer's `receive` gets into one dispatch function. Every wait on an SDK event, in the app and in
   tests, needs a timeout (for example 30 seconds) that fails with a message. Symptom of the trap: the SDK log shows
   `StartResult ... status=Ok` and the next event, then no further log line and the test never ends.
5. For iOS KSTrustedWebView 9.7, pass PEM file bytes unchanged to
   `certsDataForValidation`, not DER. Prove a read-only page loads before
   consuming activation codes; TLS asset coverage is not runtime acceptance.
   Activation via trusted WebView: fixture = `sdk_idp_user_search` ->
   `sdk_idp_activation_code_generate(user_uuid)` (code is returned once in the
   result; no reference file needed). Allowlist + redirect pattern per platform:
   native-integration.md "Trusted-WebView allowlist and redirect". Biometric
   prompt timing varies by delivered SDK, platform and key policy; announce
   possible physical prompts before activation or protected key access, then
   record whether a prompt actually appeared. On a stall read back
   `sdk_idp_user_credentials_list` before consuming another code.
6. Interactive login in the trusted WebView with the token client
   (`iam.clientId`) so that client holds the SDK's current token.
7. Cold login: kill the process, relaunch, `OfflineLoginEvent`. This may reuse
   an access token or refresh an offline token; success and a fresh `iat` do not
   prove a SignedJWT grant. The biometric prompt, when enabled, is on protected
   credential access, not necessarily at activation or interactive login.
8. Claim SignedJWT only when the effective SDK configuration has
   `maverick.jwtSignKeySecurityPolicy` and the selected auth mode is not password.
   On the inspected source path, that policy selects the SignedJWT first factor;
   without it, the SDK selects the offline-token factor. A safe diagnostic run
   may clear only access and refresh tokens (`CLEAR_ACCESS_AND_REFRESH`), then
   post `OfflineLoginEvent` and inspect whitelisted claims. Confirm the
   jwt-bearer grant in sanitized SDK diagnostics or equivalent issuer evidence.
   If the policy or grant cannot be verified, record `NOT_PROVEN`. Never use
   `CLEAR_ALL` for this check: it also removes the offline token and can leave
   the user without a returning-login credential. Never print tokens. Which
   target can prove which claim (protocol vs key protection vs biometric) is
   tabulated in [signing-policy.md](references/signing-policy.md).
9. TMS: `sdk_tms_explicit_preflight(iam.clientId)` once, then `sdk_tms_trigger`
   for ordinary accept, ordinary reject, explicit accept, explicit reject,
   timeout (owner must not touch) and `sdk_tms_cancel` (server cancel); confirm
   each with `sdk_tms_status` / `sdk_tms_result` against the SDK terminal event.
10. Export: the reopened ZIP with non-empty, CRC-clean entries IS the pass; the
    share sheet is optional and bounded to 60 s, then skipped.

Write TEST_REPORT.md after every one of these gates, not at the end.

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
  Prefer the realm's kobil-mobile themed copies where they exist
  (`KobilMobileEnrollment` / `KobilMobileLogin`); the BDDK clients carry the
  plain kobil-lite theme and render a desktop-styled page inside the app.
  `sdk_native_preflight` reports `warnings` and per-binding `theme_warning`
  for a plain theme; treat a warning as a presentation defect to fix before
  the first activation, not as a blocker.
- KSSIDP: activation **BDDKEnrollment**, login **BDDKLogin**,
  **useTokenBasedLogin=true**, **astServerBackend=maverick**, login header
  **X-KOBIL-ASTUSERID** containing the selected user ID.

Preferred method (user decision, 2026-09-29 validation round): trusted WebView
enrollment and interactive login with SignedJWT token-based returning login
(useTokenBasedLogin=true, SE-signed JWT OfflineLogin), protected by device
biometrics. PIN/password/no-authentication are documented alternatives, not
defaults; decide the authentication mode explicitly before activation.

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

## Mandatory deployment and signing gates

Before activation, run `sdk_deployment_preflight` with the actual mc_config and
explicit deployment mTLS choice. Before explicit-auth TMS, reconcile the IAM
exchange client with the observed token holder. Current-token missing `tms` is
a warning while SDK exchange/step-up is pending; require it on the resulting
token at `granted_scope_stage="explicit_auth"`, not universally before exchange.
Before the first explicit-auth TMS, run `sdk_tms_explicit_preflight` on the
token client (`iam.clientId`): it needs `tms` as optional client scope, the
KOBIL mobile browser-flow override, and it must hold the SDK's current token
(one interactive login with it after activation through a separate enrollment
client). See [TMS](references/tms.md) for the measured contract and failure
signatures. For repeated TMS failures use `sdk_tms_auth_diagnose`: compare
requested versus issued transaction scope, not a later ordinary claims lookup.
On a decrypted SDK log, `sdk_log_markers(path)` reads the jwt-bearer proof,
the key kind, the NOT_SUPPORTED attribution and explicit-TMS refusals
deterministically instead of scanning by eye. Capture inherited
error fields on confirmation/terminal events; status alone loses the cause.
Before a physical iOS install, run `sdk_ios_signing_preflight` on the actual built
.app for the customer-selected team and target device. Never guess missing
values from templates or silently choose another signing team. These checks
verify supplied metadata, not backend capability or runtime acceptance.
See [deployment and artifact gates](references/deployment-preflight.md) for inputs,
evidence limits and distinct error diagnostics.

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
During device rounds maintain the live owner/worker channel: write
`AWAITING_OWNER: <exact action>` to `<app>/OWNER_CHANNEL.md` at every
device-blocking step and poll it for the owner's reply — device acceptance must
never stall silently on an unannounced owner action (no secrets in the file).
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

## Flutter trusted WebView
For Flutter Android/iOS activation, token/SignedJWT login and foreground TMS, read
[Flutter WebView](references/flutter-webview.md) and call
`sdk_knowledge_get(topic="flutter_webview", platform="flutter_android")`
(or `flutter_ios`). Keep deployment settings local and respect qualification limits.

## First-start credential onboarding

Only when `sdk_backend_status` fails with `CONNECTION_NOT_SELECTED`: call
`sdk_onboarding_prepare(project_path)`. With a selected connection the tool
returns `connection_already_configured` and nothing is to be requested.
It creates/reuses the project's age identity, keeps its private key outside the
project, and returns the public recipient, recipient.txt, and a copy-paste email.
Show the complete draft and public key to the user. The email requests IDP/AST
and SDK SFTP access encrypted for that recipient. Do not send email automatically.
Wait for the delivery in `.kobil-sdk/incoming/`, then use the existing age import
tools with the project identity. Do not ask for plaintext credentials or the
bundled distribution's private key. Existing configurations remain unchanged.
The encrypted package bundle remains available for explicitly managed deployments;
normal onboarding uses a recipient-specific credential delivery.

## Mobile identity and AST registration

Android applicationId and iOS bundle identifier are mobile application identities.
AST app_name and its registered version identify backend registration records;
they are not automatically the same identifier. A new mobile bundle ID alone
neither proves an existing AST registration is incompatible nor proves it reusable.
Never recommend adopting the SuperApp mobile bundle ID just to reuse its assets.

For an authorized app integration, proceed with sdk_app_list, sdk_app_get and
sdk_app_versions without asking for another confirmation for these read-only
checks. Inspect the selected platform/version, registration user, lock state,
integrity policy, and any signing/package binding required by the supplied SDK
and deployment. If returned metadata cannot establish a required binding, identify
that exact gap; do not claim compatibility from the app name or integrity flag alone.
Reuse a suitable existing app/version and preserve its registration user and
security policy. Create new records only when none is suitable or the user requests
separate registration. Do not disable integrity to force reuse.

Do not assert that a delivered sdk_config.jwt is bound to a mobile package or AST
app/version without inspecting the documented configuration contract and applicable
claims privately. sdk_config_write in this MCP takes certificates and connection
service settings, not a mobile bundle ID or AST app_name. Obtain a fresh
backend-signed configuration when required; never edit signed JWT contents.

Preserve the user's previously selected test security policy and flow. Ask only
for an unresolved binding/policy choice or an actual blocker; do not request the
same decision repeatedly. A test selection is not a default for other customers.


## Signed configuration and retained choices
Within an authorized app build, request a fresh signed SDK configuration with
sdk_config_write using the selected environment service map and verified public
TLS certificates. Do not ask the user to supply a JWT or propose trying an
unverified sample JWT when the MCP can issue one. If certificates, permissions
or services are missing, report that concrete prerequisite; never disable TLS
verification or edit a signed configuration.
Read project instructions (including CLAUDE.md when present) for previously
selected test policy before asking again. Reuse an explicit current-project
ALLOW_VIRTUAL_SMART_CARD/device-PIN decision; do not extend that test choice to
other projects. This does not authorize changing shared backend security policy.

## Feedback and problem reports

- If `sdk_runtime_info` or `sdk_backend_status` returns `feedback_prompt`, ask the user once, in one short sentence, whether anything was confusing or broken. Do not ask again in the same session.
- If the user reports a problem or an idea, or the host froze or failed, offer to send a report. Show the exact text, then call `sdk_report_problem` only after the user agrees. Category is `bug`, `hang`, `idea` or `other`.
- For personal support the user may add an email address. It is optional; never ask for it twice and never invent one.
- Never put credentials, activation codes, tokens or customer data into the report text. The tool redacts secret shapes, but do not rely on that.

## Exact parameters of the first calls

Required parameters only; the tool schema lists the optional ones. Agents lost time guessing these names
(`host` for `hosts`, a missing `expected_environment`, a trust asset file that did not exist yet).

- `sdk_app_get(expected_environment, app_name)`
- `sdk_app_versions(expected_environment, app_name)`
- `sdk_tls_chain_check(hosts, trust_asset_path)` (`hosts` is a list; `trust_asset_path` must be an existing PEM bundle, `platform` is optional)
- `sdk_artifact_info(path)` (a file, or a `.xcframework` folder)
- `sdk_config_write(expected_environment, certificate_paths, output_path)`
- `sdk_deployment_preflight(mc_config_path, expected_mtls)`
- `sdk_ios_signing_preflight(app_path, expected_team_id)` (no simulator mode: it checks a signed device build)
- `sdk_ios_project_integrate(project_path, target_name, frameworks_dir)`
- `sdk_log_markers(decrypted_log_path)` (a decrypted log file, not the encrypted ks*.log)

## Look and feel

Call `sdk_theme_get` before building any screen. It returns the theme in force as plain words and tables (colour roles with
light and dark values, shapes, type scale, movement, components, screens in words, what to avoid) and says where it comes from:
the owner's own theme or the bundled KOBIL default. The owner's own theme replaces the default: they give you the text and you
store it with `sdk_theme_set` (scope `project` or `user`), or they put it in `.kobil-sdk/theme.md`; `sdk_theme_reset` removes it.
The owner's own design always wins over any default. Build the screens from the roles, with the native controls of the platform
(iOS, Android or Flutter) and keep the values in one place of the app. Check every screen in light and dark before calling it
done. Detail pages: [look-and-feel.md](references/look-and-feel.md), [design-system.md](references/design-system.md),
[reference-app-design.md](references/reference-app-design.md). There is no code template to copy.

## Events, errors and waiting: code samples

Call `sdk_code_samples(platform)` (`ios`, `android`, `flutter`; optional `topic`: adapter, start, errors, events, timeout) before
writing the code that talks to the SDK. It returns the GettingStarted code (Swift, Kotlin) and the Flutter app code, trimmed to the
SDK calls; samples marked ADDITION are ours. Rules the samples follow: the reply of a request comes only through the request
itself (completion handler, `then`, `Future`), never wait for it in a pushed-event handler; every wait has a timeout; a failed
request shows in the `status` of its result event; a wrong event gives InvalidStateEvent; a runtime error event is pushed and the
SDK restarts itself, so handle it right away. Swift samples are compiled against the delivered frameworks, Kotlin and Dart are
taken from the apps and not compiled here.

### When the completion handler may be nil

Pass a completion handler for **every event that has a result event** (Start, Restart, Activate, AddUser, Reactivation,
OfflineLogin, SetAuthorisationCode, DeleteUser, GetInformation, GetProperty, SetProperty, SetPushToken, ...): the result
comes only through the handler. `nil` (or leaving it out, as `sendEvent2MasterController(event:)` allows) is for events
whose result is *none* or *Acknowledge*: Cancel, DisplayConfirmation, StartTransaction, StartDisplayMessage, ProvidePIN,
ProvideSetNewPIN, ProvideSetPIN, StartChangePIN, StartAddUser, StartReactivation, StartDeleteUser, GetStateEvent,
Enable/DisableServerTracing, EnableOpenCensusTracing, Configuration. Their outcome arrives as pushed events at your delegate.
Source: the "Result Event" column of the API reference, checked against every send of the GettingStarted Swift app. When
unsure, pass a handler; it is never wrong. **Look up every event you send with `sdk_event_result(event)` before writing the call**
(it gives the result event and whether nil is allowed; without a name it returns the whole table of 138 events).

## Addresses for the trusted WebView

Do not assemble the authorization address yourself. `sdk_native_preflight` returns for each client (activation and login)
the address the server accepts: `authorization_endpoint` (`<host>/auth/realms/<realm>/protocol/openid-connect/auth`, note
the `/auth`), the registered `redirect_uri` and a ready `authorization_url_template` (replace `<random state>`). `sdk_backend_status`
gives the same realm base as `idp_realm_base`. A 404 on a path without `/auth` is the wrong path, not a backend outage.

## Which journeys the IDP offers

Call `sdk_idp_flow_overview(expected_environment)` before choosing the activation and login clients. It reads every client with
its own browser flow and tells you per client: `based_on` (`kssidp` = current standard, `bddk` = deprecated, `other`), `role`
(activation or login), `login_theme`, whether the flow has the official name or is a copy, the registered `redirect_uri` and a
ready `authorization_url_template`. The realm `endpoints` come from the realm's own OpenID configuration (`source: well-known`;
`derived` means not confirmed). Clients such as `KobilMobileEnrollment`/`KobilMobileLogin` are copies of the BDDK flows with the
`kobil-mobile` theme (a styled child of `kobil-lite`). The tool only lists; the owner's selection always wins. Use its
addresses, never assemble them yourself.

## Debug output on the console

Print to the console from every completion handler and every delegate callback, so that nothing stays silent: the event or
callback name, the status, error domain, code and description. Print URLs without their query (state and authorisation code
live there); never print codes, tokens, passwords or cookies. For the trusted WebView log every `KsTrustedWebViewDelegate`
callback (`onURLBlocked` is the usual reason for a blank page, `webViewDidFinishLoading` carries the load error,
`onNSURLResponseReceived` the HTTP status) and set `KsTrustedWebView.setLogListener(...)`. `sdk_code_samples(platform="ios",
topic="debug")` has a complete delegate that compiles against the delivered frameworks. Read the output with
`GetConsoleOutput` instead of guessing from a blank screen.
