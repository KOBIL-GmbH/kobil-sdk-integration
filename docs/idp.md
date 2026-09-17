# IDP test users and activation codes (unreleased)

These optional tools require the upcoming runtime, not pinned v0.3.3. They do
not depend on Xcode device-interaction support. App-version registration users
and device-activation identities are different roles.

Set `KOBIL_SDK_IDP_CONNECTION` in the MCP server environment to a private JSON
profile outside the repository. `admin_url` is the deployment's complete admin
base, including `/auth` when needed; `/realms/{realm}` is appended. Use an IDP
service client authorized to view/manage users in that realm. AST permissions
alone do not imply IDP permissions. No deployment/admin credentials are bundled.

```json
{
  "schema_version": 2,
  "environment": "development",
  "realm": "your-realm",
  "admin_url": "https://identity.example/auth/admin",
  "allow_test_provisioning": true,
  "auth": {
    "type": "oauth_client_credentials",
    "token_url": "https://identity.example/auth/realms/your-realm/protocol/openid-connect/token",
    "client_id": "your-idp-service-client",
    "credential": {
      "provider": "keyring",
      "service": "kobil-sdk-idp-development",
      "account": "service-client"
    }
  }
}
```

Credential references use the existing [shared credential resolver](credentials.md):
OS keyring, explicit age-encrypted file transport (with private identity file),
or runtime environment reference. A keyring reference may declare an explicit
age fallback. No plaintext passwords/client secrets belong in profiles or tool
arguments. The profile only selects a credential; `sdk_idp_status` does not read
it. `allow_test_provisioning` is a local opt-in gate, not a server permission.

## Workflow

1. `sdk_idp_status`: validate local profile, returning environment/realm and
   provisioning gate. `connection_verified:false` means no network request.
2. `sdk_idp_user_get(expected_environment, username)`: exact lookup returning
   only existence, user ID and enabled state. Select that ID for the activation
   user; do not substitute an app-version registration ID.
3. If explicitly requested and absent, `sdk_idp_test_user_create` creates a new
   enabled passwordless test user. Existing names are refused without modification.
   No email, password, role grants or verification bypasses are created. Realm
   policy may require additional enrollment steps outside this test-user recipe.
4. `sdk_idp_activation_write(expected_environment, username, user_id, output_path)`
   generates an eight-digit random code in the MCP runtime and registers the
   `ACTIVATION_CODE` credential through the KOBIL IDP admin API. Lifetime defaults
   to `1d`; explicitly choose `1h` through `24h` when appropriate. This credential
   type is KOBIL-specific, not a standard Keycloak feature.
5. Deliver the private JSON to the test harness without printing it or committing
   it. Map `activation_code` explicitly to the SDK's `activation-code` credential
   key. The file contains no PIN/password; use private input for those if required.
   Require actual SDK activation success before marking the user/device activated.

The output directory must already exist, be user-owned with mode 0700, and use
its resolved path without symlinks. A new 0600 file is exclusively reserved and
fsynced before the backend write. Existing files are refused. This preview's
private output delivery supports POSIX hosts only; Windows secure-output ACL
support is not implemented. Host limitations do not change the mobile target scope.

Existing non-activation credentials are refused: this is initial test activation,
not a reset or reactivation tool for enrolled users. Existing activation credentials
require `replace_existing:true` after the user explicitly requests replacement.
Inspect previous partial enrollment before replacing; never cycle through codes
or erase users to work around an SDK error. Concurrent administrators can race
with the metadata check; the backend offers no atomic conditional credential PUT.

## Failure handling and verification

There is no automatic write retry. Failed user creation may have committed; run
exact user lookup before deciding how to proceed. A failed activation PUT returns
`status:unknown`, `retry_safe:false` and the private file path. The file remains
`pending`: it may contain a valid credential. Preserve it and inspect backend
state before attempting activation or issuing another code. File status `issued`
means the backend accepted the update, not that device activation succeeded.

HTTP errors are sanitized; tokens, codes and backend response bodies are not tool
results. Credentials are read at runtime, never during configuration validation.
Unit/HTTP mock and MCP protocol tests verify contracts and redaction. A real IDP
service-client connection and device flow still require deployment validation.

User endpoints follow the [Keycloak Admin REST API](https://www.keycloak.org/docs-api/latest/rest-api/index.html).
