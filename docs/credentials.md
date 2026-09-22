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

## Create and maintain encrypted stores through MCP

These tools require both `age` and `age-keygen` on PATH:

1. `sdk_age_identity_create(identity_path)` creates a new owner-only private
   identity; only the public recipient is returned. Provision/backup this
   identity separately from the store. Existing identities are never replaced.
2. `sdk_age_store_create(store_path, identity_path)` creates an empty encrypted
   store. Existing files are never overwritten by creation.
3. `sdk_age_credential_put(store_path, identity_path, service, account, source)`
   resolves a credential reference internally and encrypts the value into the
   selected entry. Use explicit `replace=true` to replace an existing entry.
   This supports SFTP/SCP passwords as well as AST/IDP secrets. Source references
   use the same env/file/keyring/age schema; passwords never appear in arguments.
4. `sdk_age_environment_put(..., environment, profile_file)` reads a private
   reference-only AST/IDP connection profile and stores the entire named profile
   encrypted. Environment name must match; replacement is explicit.
5. `sdk_age_store_list(store_path, identity_path)` lists names/labels only.
6. `sdk_age_environment_selector_write(..., environment, output_path)` writes
   a new private selector for `KOBIL_SDK_CONNECTION`. The selector contains only
   store/identity paths and the environment name. Server settings are decrypted
   in memory by the backend; credentials are resolved separately when needed.
7. `sdk_age_environment_export(..., environment, output_path)` is an optional
   explicit export of the reference-only server profile to a new private file.
   Prefer the selector when server settings should remain encrypted on disk.

An SFTP/SCP password stored as service `customer-transfer`, account `sdk-user`
can be read by a credential consumer using:

```json
{
  "provider": "age",
  "store": "/private/customer.age",
  "identity": "/private/customer-identity.txt",
  "service": "customer-transfer",
  "account": "sdk-user"
}
```

This feature stores the password; it does not add an SCP/SFTP transport or run
transfers. A transfer client must support the reference resolver. Backend
profiles stored under environments use the AST/IDP profile schema.

Stores retain version 2 with optional `environments` alongside `keychain`.
Store writes encrypt in memory/pipes and publish ciphertext atomically, protected
by an exclusive `.lock` file against simultaneous MCP writers. A crashed writer
may leave a lock: verify no writer is running before removing it manually.
An encryption failure preserves the previous store. No plaintext store temporary
file is written. The explicitly requested identity and optional exported profile
are private plaintext files by design. Updates encrypt to the selected single
identity only; they do not preserve other recipients from externally created
multi-recipient envelopes. Sources remain intact and no host configuration is
switched automatically. Keep private files in a directory you control.

## macOS → macOS / Windows credential transfer

Use **recipient-based export** for machine-to-machine delivery. The sender never
needs the destination's private identity. A single export may contain several
public recipients, so both an authorized Mac and an authorized Windows machine
can decrypt it with their own identities.

1. On each destination, call `sdk_age_identity_create` with a private local path.
   Share only the returned public `age1...` recipient with the sender. Keep the
   `AGE-SECRET-KEY...` identity on its destination machine.
2. On the sender, call `sdk_age_transfer_export(output_path, recipients, entries)`.
   Every entry explicitly selects a source credential reference and the portable
   service/account labels to store. For example:

   ```json
   {
     "service": "customer-transfer",
     "account": "sdk-user",
     "source": {"provider": "keyring", "service": "local-sdk", "account": "sdk-user"}
   }
   ```

   Supply the Mac and/or Windows public recipients. All listed recipients can
   read all entries in that delivery. The MCP resolves Keychain credentials
   internally and writes ciphertext only; it does not transmit the file.
3. Transfer the `.age` file through your chosen file-transfer channel.
4. On each destination, use
   `sdk_age_credential_import_keyring(store_path, identity_path, service, account,
   destination_service, destination_account)` to import exactly one entry.
   `destination_service` is a label such as `server-a/idp`; the tool always writes
   `kobil-sdk/import/server-a/idp`, never the original source service.
   Existing entries require explicit `replace=true`. The encrypted file remains.
5. Use the destination reference
   `{"provider":"keyring","service":"kobil-sdk/import/customer-transfer","account":"sdk-user"}`
   in backend or transfer-client settings. The same provider selects macOS
   Keychain on macOS and native Windows Credential Manager on Windows. Use the returned `credential_reference` verbatim. The destination label is
   opaque; do not pass the expanded service name back as a label. Choose separate
   labels per server and purpose (for example server-a/idp and server-a/ast).

Alternatively use an `age` reference directly on the destination without import;
its store/identity paths must be local to that destination. Paths in server
profiles are not automatically translated from macOS to Windows. Keyring
service/account references avoid that path dependency. For profiles and credentials together, use the server-bundle tools below.
The credential-only sdk_age_transfer_export remains available.

This flow does not copy a macOS Keychain database to Windows and does not share
private age identities. It also supports Windows-to-Mac with the same interfaces.
Do not edit a multi-recipient delivery using single-identity store-update tools;
create a fresh transfer export to keep the intended recipient set explicit.

Validation: real macOS native-keystore → age → native-keystore round-trip,
multiple real age recipient identities, unauthorized identity rejection and
Windows backend-selection contract tests. A real Windows Credential Manager
import still requires validation on a Windows host. Before using private identity
files on Windows, provision a user-private directory/ACL; automatic ACL management
is not implemented by this package.

## Imported-credential namespace

Age-to-keystore imports always prefix destination service labels with
`kobil-sdk/import/`. Accounts remain explicitly selected. Source credentials and
existing local service names are not changed. Duplicate destination entries fail
unless `replace=true`; replacement is limited to that namespaced destination.

`sdk_credential_import` uses an existing connection profile and therefore cannot
silently change its credential reference. Its destination must already be under
`kobil-sdk/import/`; otherwise import fails before reading source credentials.
Update the profile explicitly using the reference returned by the age import.
Legacy references remain readable; this does not migrate or delete existing keys.

This changes the destination semantics of age imports: callers must use the
returned reference rather than assuming destination_service is a literal service.
Complete multi-environment transfer is provided by the explicit server-bundle
tools described below.

## Share several complete server environments

The recipient creates an identity with `sdk_age_identity_create` and shares only
its returned public `age1…` recipient. The private identity stays on that machine.

1. On the sender, prepare owner-only connection profile JSON files for the chosen
   servers. AST and optional IDP credentials are references to the sender's
   Keychain, age store, private file or environment; no raw secret tool arguments.
2. Call `sdk_age_server_bundle_export(output_path, recipients, profile_files)`.
   It validates all profiles, resolves only their referenced credentials, and
   encrypts profiles plus credentials in one new `.age` file. Sender paths and
   legacy environment-variable references are replaced by portable bundle labels.
   All supplied recipients can decrypt every server included in the file.
3. Share that file through the intended transfer channel. On the recipient, call
   `sdk_age_store_list` with its local identity to inspect environment names.
4. Call `sdk_age_server_bundle_import(store_path, identity_path, environments,
   namespace, output_store_path)` with the explicit environment-name subset.
   A namespace such as `partner-a` separates deliveries. Imported services are
   `kobil-sdk/import/partner-a/<encoded environment>/ast` and `/idp`, with account
   `credential`. No sender-selected service or filesystem path is used locally.
5. The result contains local credential references and a new encrypted profile
   store. Use `sdk_age_environment_selector_write` to create a private selector
   for one imported environment, then explicitly configure `KOBIL_SDK_CONNECTION`
   and restart the MCP. Server settings remain encrypted. Verify backend auth and
   native preflight after selection; import itself makes no backend requests.

Existing keystore entries or output files block imports. There is no batch
replacement: choose a new namespace or deliberately resolve an earlier import.
On failure, only entries created by that import are removed. If cleanup fails,
`status=cleanup_required` reports the leftover references without secret values;
resolve those before retrying. Process termination or a machine crash can still
leave partial entries; the OS keystore and filesystem are not one transaction.

Limits: at most 50 connection profiles per bundle and 20 recipients; plaintext
size is bounded. AST/IDP server profiles are supported. SFTP/SCP credentials can
still be shared separately using `sdk_age_transfer_export`; they are not AST/IDP
connection profiles. macOS Keychain round-trip tests passed with disposable data;
Windows Credential Manager runtime testing remains pending.
