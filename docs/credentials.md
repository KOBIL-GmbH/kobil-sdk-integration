# Shared credentials and server settings

Connection profiles hold server URLs, tenant and credential references. Secrets
are resolved inside the MCP process. `KOBIL_SDK_CONNECTION` selects the profile;
`expected_environment` guards every backend/credential operation. Profiles are
not switched implicitly. Existing environment-variable profiles still work.

## Reference-only profile

Keep this file outside source control. Example names below are placeholders.

```json
{
  "schema_version": 2,
  "environment": "customer-test",
  "tenant": "customer",
  "ast_url": "https://ast.example.org",
  "auth": {
    "type": "oauth_client_credentials",
    "token_url": "https://idp.example.org/auth/realms/customer/protocol/openid-connect/token",
    "client_id": "ast-admin",
    "scope": "your-approved-scope",
    "credential": {"provider": "keyring", "service": "customer-test", "account": "ast-admin"}
  },
  "admin": {
    "idp_url": "https://idp.example.org",
    "realm": "customer",
    "client_id": "admin-cli",
    "username": "your-admin",
    "credential": {"provider": "keyring", "service": "customer-test", "account": "idp-admin"}
  }
}
```

AST supports OAuth client credentials or `{"type":"bearer","credential":{...}}`.
IDP retains its configured password-grant administrative client, now with a
credential reference instead of `password_env`. This feature does not enable
password grants on the server or change client roles. Optional OAuth scope is
preserved. Use exactly one `credential` or `password_env` in the admin block.
Legacy AST `token_env`/`oauth` fields must not be mixed with schema version 2.

## Providers

- `keyring`: exact `service` and `account`. Uses native macOS Keychain,
  Windows Credential Manager or Linux Secret Service; plaintext/third-party
  keyring backends are not selected. OS authorization prompts may occur.
- `env`: `{"provider":"env","name":"CUSTOMER_SECRET"}`.
- `file`: `{"provider":"file","path":"/private/secret.txt"}`. UTF-8 secret,
  with trailing CR/LF removed. Owner-only regular file on POSIX; no symlinks.
- `age`: explicit absolute `store` and `identity` paths, `service` and `account`.
  Requires `age` and a native AGE-SECRET-KEY identity. No passphrase/plugin
  identity support. Both files must be owner-only regular files on POSIX.

Encrypted age plaintext schema:

```json
{"version":2,"keychain":{"customer-test":{"ast-admin":"value-entered-locally"}}}
```

The identity is provisioned separately. Decryption uses bounded pipes, never a
plaintext temporary file. A keyring reference may contain an age `fallback`.
Fallback applies only when the entry is absent/empty, never for locked, denied,
unavailable or malformed stores. Windows file ACL enforcement is not automated;
provision private ACLs before using file/age providers there.

## MCP management

- `sdk_credential_status(expected_environment, service="ast", probe=false)`:
  configuration metadata only; probe resolves the selected credential and
  reports status without exposing its value or fingerprint.
- `sdk_credential_import(expected_environment, source, service="ast", replace=false)`:
  resolve one source reference and store it in the profile-selected keyring
  entry. Source may be file/age/env/keyring. No raw password arguments.
  Existing entries require explicit `replace=true`.
- `sdk_credential_delete(expected_environment, service="ast", confirm=false)`:
  requires `confirm=true`, deletes only the selected local entry. It does not
  delete the backend account or the profile. An age fallback remains effective.
- `sdk_backend_auth_test(expected_environment, service="ast")`: test token
  acquisition separately; this does not prove resource permissions.

Use `service="idp"` to target the administrator credential. Import leaves the
source intact; arrange its retention or removal locally. No store enumeration or
get-secret tool is provided. The intentional activation-code/token-delivery tools
are separate from keystore management.

## Local setup CLI

After installation, run `kobil-sdk-credentials --help`. The CLI never prints a
secret. `set` reads hidden interactive input; `--stdin` is for private editor pipes.

```sh
kobil-sdk-credentials --config /private/connection.json status
kobil-sdk-credentials --config /private/connection.json set
kobil-sdk-credentials --config /private/connection.json --target idp set
kobil-sdk-credentials --config /private/connection.json status --probe
kobil-sdk-credentials --config /private/connection.json delete --confirm
```

Use `set --replace` for the selected entry only. `prepare-keyring --service NAME
--account NAME --output /private/new.json` creates a new reference-only profile
without copying secrets or switching the active connection. `--target idp`
selects the admin reference; `--service` on prepare-keyring names the keystore
service. Use the MCP import tool for an existing encrypted delivery.

## Validation and limits

Regression tests cover legacy/v2 validation, AST scope, distinct IDP/AST
references, private-file permissions, explicit replacement, failure redaction,
fallback policy and MCP discovery. Disposable native Keychain and real age
round-trips were tested on macOS. Windows/Linux native providers need platform
acceptance. Live customer authentication and editor installation are separate
steps; no customer credential is enrolled by installing the package.
