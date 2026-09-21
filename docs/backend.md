# AST/Shift backend connection

The MCP supports app creation/reuse, app-version creation/reuse and delivery of a
backend-issued SDK configuration JWT. No backend is configured by default.

## Runtime setup

Create a JSON file outside this repository. Set `KOBIL_SDK_CONNECTION` to its
absolute path in your MCP client's process environment. Example (replace all
values with your own non-production connection):

```json
{
  "environment": "development",
  "tenant": "your-tenant",
  "ast_url": "https://backend.example",
  "services": [
    {"name": "astCa", "url": "https://backend.example"},
    {"name": "astLogin", "url": "https://backend.example"}
  ],
  "oauth": {
    "token_url": "https://identity.example/realms/your-realm/protocol/openid-connect/token",
    "client_id": "your-service-client",
    "client_secret_env": "KOBIL_SDK_CLIENT_SECRET"
  }
}
```

Have your secret manager supply `KOBIL_SDK_CLIENT_SECRET` to the server process.
Do not paste secrets into chat, tool arguments, profiles or committed files.
Alternatively replace `oauth` with `"token_env": "KOBIL_SDK_ACCESS_TOKEN"` and
supply that environment variable through your runtime. Configure exactly one
method. Token renewal for this second method is the runtime's responsibility.

Use the actual OAuth token endpoint from your deployment, including any required
path prefix. The service client needs permission for the selected AST tenant and
operations. HTTPS verification is mandatory; redirects and environment proxy
settings are disabled. This release uses the standard public certificate trust
store. Private CA/proxy deployments need an explicit future connection extension.

## Operations

1. `sdk_backend_status()` checks configuration locally. It does not test credentials.
2. `sdk_app_ensure(expected_environment, app_name, categories)` reads the named
   app; `categories` are push-notification categories ("tms" for transaction
   confirmation, "chat" for messaging); `sdk_app_get` on a missing app lists the
   values the tenant already uses. The registration user of a version is any existing
   tenant user; create a dedicated one with `sdk_activation_user_ensure` when none is
   known. It
   app and creates it only after an app-endpoint 404. Authentication failures
   never imply the app is absent. Existing settings are not changed or certified.
3. `sdk_app_version_ensure(expected_environment, app_name, platform, version,
   register_user_id, check_integrity)` reads all version pages before reuse or
   creation. Version must be `major.minor.patch`; supply the exact platform name
   supported by your backend. Registration user and integrity policy are explicit.
   Locked/conflicting versions fail without changes. Policy-ID registration is
   not yet exposed.
4. `sdk_config_write(expected_environment, certificate_paths, output_path)` sends
   public TLS certificates, the configured `astUrl` gateway and explicit SDK
   `services` endpoint list to
   `/v1/tenants/{tenant}/sdkconfig` and writes its
   `sdkConfig` JWT into a new file. Supply trusted PEM/DER certificates separately,
   one per file. Existing files and symlinks are refused. Output contains only a
   path, SHA-256 and `signature_verified: false`; the SDK must verify the signature.
   Use a private directory. POSIX files use mode 0600; Windows access protection
   depends on the directory's ACLs. The parent directory must already exist.

Mutating tools must be invoked for an explicitly requested backend setup.
Selecting a planner module does not invoke these tools. There is no retry of
writes: a timeout can mean the server committed the operation. Inspect backend
state before retrying. Concurrent external administrators can race with checks;
server conflicts are surfaced without overwrite or automatic retry. Version
pagination stops at 100 pages and refuses incomplete or changing listings.

## Contract and verification boundaries

The adapter uses AST app/version and certificate-authority REST contracts. Unit
and HTTP mock tests cover request shapes, OAuth, resource reuse, pagination,
conflicts, environment checks, redirects, error redaction and JWT file handling.
MCP stdio checks cover discovery and execution. Customer deployment permissions,
API-version compatibility, live issuance and SDK consumption require live tests.

This is backend setup tooling. It does not activate a device or implement the
SDK login UI, IDP authentication flow, complete SDK feature recipes, SSMS,
provider installation, distribution or native app builds. These remain separate
modules and integration work, tracked explicitly by the skill and planner.

The example service list is illustrative. Supply the complete endpoint map for
selected SDK features and your deployment, using its authorized configuration.
The MCP refuses an absent/empty map, duplicate names or non-HTTPS URLs. Do not
assume every service shares the AST gateway. Missing `astLogin`, for example,
can allow Start to succeed but prevent registration/key exchange and activation.
App/version records alone do not complete the SDK's app/device registration flow.

Prefer reusing an appropriate existing AST app/version with its existing
registration user. Creating a fresh client application does not require a new
AST app record. For new provisioning, select an existing tenant user explicitly;
this API records registerUserId on the version. Do not silently replace an
existing registration user with the device activation identity.

## Foreground TMS transactions

- `sdk_tms_trigger` creates one authorized transaction for a Keycloak recipient
  UUID with explicit retrieval/confirmation timeouts in seconds and explicit
  authentication/freshness settings. This first adapter skips push and accepts
  plain text; it does not support arbitrary structured payloads or display messages.
- `sdk_tms_status` reads progress; `sdk_tms_result` reads final result metadata.
  Returned data excludes transaction payloads, recipient identities and signatures.
  No-result/404 is ambiguous (pending, unknown or expired); it is never success.
- `sdk_tms_cancel` requests cancellation; query the final result separately.

These tools do not confirm transactions on the device or cryptographically verify
server signatures. Do not retry an uncertain creation automatically. Use only
authorized recipients/content and preserve the returned transaction ID. Push,
explicit re-authentication and platform behavior require separate runtime tests.

## Read existing registration metadata

Use sdk_app_get(expected_environment, app_name) to check a named app without
creating it. Use sdk_app_versions(expected_environment, app_name) to retrieve
all paginated versions with platform, version, register_user_id, check_integrity
and locked fields. Only these fields are returned. Incomplete policy metadata
fails explicitly; no defaults silently replace missing backend settings.
Reuse the selected registration user and policy with sdk_app_version_ensure.

## First activation of a device

App and version records do not make an app usable: its first launch reports
ACTIVATION_REQUIRED and asks for a user id and a one-time activation code. Issuing
that code is an IDP operation with administrative rights, not an AST one, so it needs
the optional `admin` block in the connection file:

    "admin": {"idp_url": "https://idp.<host>", "realm": "master",
              "client_id": "admin-cli", "username": "<admin>",
              "password_env": "KOBIL_SDK_ADMIN_PASSWORD"}

The password is read from that environment variable at runtime, exactly like the AST
client secret; it is never an argument and never written to the connection file. Every
other tool works when the block is absent.

### The realm needs a journey that consumes the code

An activation code is useless if no client offers an activation journey. The client named
in `mc_config.json` decides which browser flow the SDK is sent through, and a realm whose
clients only carry login and registration journeys will render a password form instead,
whatever the app sends.

`sdk_activation_flow_ensure` creates a browser flow from KOBIL's activation authenticators,
`sdk_activation_client_ensure` creates the public client bound to it, and
`sdk_activation_flow_describe` reads a flow back. All three are additive: an existing flow
or client is returned unmodified, so a wrong guess is undone by deleting the two resources
that were created.

Two things decide whether the result works:

- **The login theme must render well-formed XHTML.** The SDK parses the page with a strict
  parser and fails before sending any credential when tags are unbalanced. Check a candidate
  theme by requesting the authorisation endpoint and running the reply through an XML parser.
- **The AST step is driven by the SDK, not by a browser.** With action `activate` it requires
  the `X-KOBIL-ASTCLIENTID` header, so a plain request to the authorisation endpoint returns
  HTTP 406 even when the flow is correct. Only a device can validate an activation flow.

`sdk_activation_user_ensure` creates a tenant user with no credential, or reports an
existing one unmodified. Keep this user separate from the registration user recorded on
the version. `sdk_activation_password_set` gives that user the permanent IDP password the
login journey checks: the activation journey sets none, so without it the first login
fails. `sdk_activation_code_set` generates the activation code itself, stores it as an
ACTIVATION_CODE credential, reads it back to confirm storage, and returns it once. Both
values are generated by the tools, never taken as arguments, and shown once: never log or
commit them, and treat a failed activation as possibly having consumed the code rather
than reissuing blindly.

`sdk_artifacts_import` installs every zip found in the delivery folder (the `sdk-delivery/`
bundled next to the package, `KOBIL_SDK_DELIVERY`, or `~/.kobil-sdk/delivery`), iOS and
Android, each verified against its SHA-512 sidecar, keeping the release notes;
`sdk_artifacts_install` does one zip; `sdk_artifacts_notes` serves a delivered document;
`sdk_artifacts_list` shows what is installed;
`sdk_ios_project_integrate` adds the four XCFrameworks to an Xcode app target as Embed &
Sign with the bridging header, editing project.pbxproj the way the device-verified app has
it and verifying by readback. Verified by a headless build of a fresh Xcode 27 project.

`sdk_idp_journeys` classifies the realm's clients by the journey their browser flow runs
(activation code, or one-page login) so no client name has to be assumed. It needs the
admin block and returns the minimum: id, flow alias, theme and step providers of the
classified clients, a count of the rest, never secrets, redirect URIs or attributes; with
`client_ids` it reads only those clients. Realm administrators already see all of this.

`sdk_trusted_certificate_write` reads the verified TLS chain of the IDP host, saves its root
as a new PEM file and checks every backend host in the connection file against that file
alone, so the certificate the SDK pins is known to fit before the first device run.
`sdk_mc_config` saves its result when `output_path` is given; it never overwrites.

`sdk_idp_theme_check` fetches a client's first login page and parses it as strict XML, the
way the SDK does. Run it on the login client before a device test and first whenever a login
hangs silently; a malformed theme is dropped by the SDK without any error. Reads only.

The default flow `sdk_activation_flow_ensure` creates is the one verified on a device:
AST activate, the activation-code page, AST link, delete code. The two AST steps carry
different settings, addressed as `ast-login-authenticator#1` and `#2` in `step_config`
and through `occurrence` in `sdk_activation_step_config`. A password page inside the flow
is unreachable on the current IDP build (see the skill's activation-login-findings
reference), which is why the password is set by the tool instead.

TMS status/result reads reject a conflicting transaction ID and missing status.
Missing IDs may inherit the requested ID for endpoints that omit it. Missing
results (HTTP404) remain explicitly unavailable, rather than successful results.
