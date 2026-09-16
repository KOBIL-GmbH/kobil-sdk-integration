# AST/Shift backend connection

The MCP supports app creation/reuse, app-version creation/reuse and delivery of a
backend-issued SDK configuration JWT. No backend is configured by default.

See [the shared credential provider work](credentials.md) for version-2 profiles
on main (unreleased). Released v0.3.3 uses the legacy setup below.

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
These tools neither create activation users nor return their credentials.

TMS status/result reads reject a conflicting transaction ID and missing status.
Missing IDs may inherit the requested ID for endpoints that omit it. Missing
results (HTTP404) remain explicitly unavailable, rather than successful results.

## Connection diagnostics (unreleased)

Configuration failures return a fixed error code and recovery instruction. The
same code is logged to the MCP process stderr through Python logging; no profile
contents, paths, credentials or underlying exception text are included.

| Code | Action |
| --- | --- |
| `CONNECTION_NOT_SELECTED` | Set `KOBIL_SDK_CONNECTION` in the server setup or use your configured credential launcher. Restart the MCP server. |
| `CONNECTION_FILE_NOT_FOUND` | Reselect an existing connection JSON file. |
| `CONNECTION_FILE_UNREADABLE` | Check path, file permissions and UTF-8 encoding. |
| `CONNECTION_JSON_INVALID` | Correct the JSON syntax. |
| `CONNECTION_SCHEMA_UNSUPPORTED` | Match the profile schema to the installed runtime. |
| `CONNECTION_FIELDS_INVALID` | Check the required connection and authentication fields. |

Released v0.3.3 reports these cases as `Invalid connection configuration`.
An Xcode plugin imported without a connection is planning-only: skill discovery
and tool listing can work while backend tools fail before any network request.
Inspect the installed server command, arguments and environment rather than
assuming a successful import configured backend access. Reopen the editor's
server settings after saving to confirm the changes persisted. Then restart the
server or start a fresh agent session and call `sdk_backend_status`; follow with
an explicitly requested read-only `sdk_app_get` to verify backend access.
