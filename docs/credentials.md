# Local credential providers (feature branch)

Implemented on the portable-credentials feature branch; **not in release v0.3.3**.
The shipped editor installers still pin v0.3.3 and deliberately reject v2 profiles
until a new release is tested and pinned. Do not point production installations
at this branch. Existing environment-variable profiles remain compatible.

## How credentials reach the backend

A private connection profile identifies an environment and a credential reference.
Only a backend operation resolves that reference. Planning and configuration
status do not unlock the store. The MCP exchanges a client secret for an OAuth
access token, or uses the referenced bearer token directly. Secrets are never
accepted or returned through MCP tool arguments/results. SDK configuration JWTs
are separate artifacts written through `sdk_config_write`.

There is no token cache in this implementation: OAuth gets a fresh token for
each backend request. No failed write is automatically replayed. Caller-supplied
bearer tokens require caller-managed renewal. Python memory cannot be securely
zeroized; this protects against accidental disclosure, not a compromised host.

## Version-2 profile

Create this file privately, outside the application/release repositories. Use
your deployment's complete service map rather than assuming the sample is complete.

```json
{
  "schema_version": 2,
  "environment": "development",
  "tenant": "your-tenant",
  "ast_url": "https://backend.example",
  "services": [{"name": "astLogin", "url": "https://backend.example"}],
  "auth": {
    "type": "oauth_client_credentials",
    "token_url": "https://identity.example/token",
    "client_id": "your-client",
    "credential": {
      "provider": "keyring",
      "service": "kobil-sdk-development",
      "account": "your-client"
    }
  }
}
```

Bearer auth is `{"type":"bearer","credential":{...}}`. Legacy `token_env` or
`oauth.client_secret_env` continues to work unchanged; mixing legacy fields with
v2 is rejected. Set `KOBIL_SDK_CONNECTION` to the profile's absolute path.

Providers:

- `keyring`: exact `service` and `account`; native macOS Keychain, Windows
  Credential Manager or Linux Secret Service. The resolver constructs the native
  backend directly; user-configured third-party/plaintext/null backends are not
  selected. Lookup runs in a subprocess with a 120-second limit for OS prompts.
- `env`: `{"provider":"env","name":"KOBIL_SDK_CLIENT_SECRET"}`. Retains
  compatibility with runtime injection and VS Code SecretStorage. GUI processes
  do not reliably inherit exports from a terminal.
- `age`: explicit absolute `store` and `identity` paths plus exact `service` and
  `account`. Requires `age` on PATH. Supports native AGE-SECRET-KEY identities;
  interactive passphrases and age plugins are not supported. This provider reads
  an existing envelope; enrollment/distribution is separate.

An optional `fallback` on a keyring reference may contain an age reference. It
runs only for a missing/empty primary entry. Locked, denied, unavailable or
malformed providers do not trigger fallback. Prefer age as an explicit primary
for headless environments instead of bypassing OS access controls.

Age plaintext schema (encrypt before storing):

```json
{"version":2,"keychain":{"kobil-sdk-development":{"your-client":"VALUE_ENTERED_LOCALLY"}}}
```

No internal store discovery or legacy account aliases. Decryption uses captured
pipes, bounded input/output and timeouts; no decrypted temporary files. On POSIX,
both files must be owner-only regular files, not symlinks. On Windows, restrict
ACLs yourself; automated Windows ACL enforcement is not implemented yet. Identity
files must be provisioned separately and are not exported by the integration.

## Local onboarding commands

From the feature checkout after `uv sync --frozen`:

```sh
# Does not retrieve a secret or contact the backend.
uv run --frozen kobil-sdk-credentials --config /private/connection.json status
# Hidden local input; keyring only, refuses overwrite by default.
uv run --frozen kobil-sdk-credentials --config /private/connection.json set
# Checks the selected credential but never prints its value.
uv run --frozen kobil-sdk-credentials --config /private/connection.json status --probe
# Explicit, read-only check with environment guard.
uv run --frozen kobil-sdk-credentials --config /private/connection.json test-backend --environment development --app your-existing-app
```

Use `set --replace` only to rotate the exact selected entry. Restart MCP after
rotation. `delete --confirm` removes only that entry; profiles remain unchanged.
No get/show-secret command exists. The editor bridge supports `set --stdin` for
a private pipe from a native password dialog, never a shell password argument.

To prepare a new reference-only profile from a legacy profile:

```sh
uv run --frozen kobil-sdk-credentials --config /private/old.json prepare-keyring \
  --service kobil-sdk-development --account your-client --output /private/new.json
```

The new path must not exist. This does not copy or enroll a credential, switch
the active connection, or modify the old profile. Enroll locally, probe and test
before switching. Roll back by selecting the old profile and old pinned runtime.
POSIX files use mode 0600; Windows users must apply a user-restricted ACL before
use. Never commit private profiles, credentials or encrypted stores/identity keys.

## Editors and verification

VS Code retains SecretStorage and adds a v2 OS-store import/enrollment path;
secrets travel through a private stdin pipe when enrollment is selected. Xcode
v2 profiles resolve directly in the MCP, with no legacy injection launcher.
Both adapters remain gated until their pinned release supports v2. Two editors
can reference the same OS-store entry without copying the password between them.

Verified: legacy suites, resolver/CLI failure tests, native macOS test-entry
creation/read/exact-account rejection/rotation/deletion, and real age encryption,
lookup and corrupt-envelope rejection. Test credentials were disposable and
removed. Windows/Linux native tests and live customer backend checks remain
pending; mocked coverage is not runtime certification. Editor UI enrollment and
updated release installation also remain pending.

Errors use fixed codes such as CREDENTIAL_NOT_FOUND, STORE_LOCKED, ACCESS_DENIED,
PROVIDER_UNAVAILABLE and AGE_DECRYPT_FAILED. OS libraries can report denial and
lock as the same condition; no stronger distinction is inferred. Raw provider
exceptions and subprocess stderr are never echoed. Native backend reference:
[keyring documentation](https://keyring.readthedocs.io/en/latest/).

## Repeat the native checks

Use only a development machine whose local credential store you may test:

```sh
KOBIL_RUN_NATIVE_CREDENTIAL_TESTS=1 uv run --frozen python -m unittest discover -s tests -v
```

The native-store case creates a random, disposable service/account, verifies
lookup and rotation, and deletes it. Without the flag that case is skipped.
The real age case uses temporary keys/files and skips if age is unavailable.
Report skipped cases explicitly when validating another OS.
