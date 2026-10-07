# Deployment and built-artifact gates

These checks supplement `sdk_native_preflight` (selected flow/client bindings)
and `sdk_tls_chain_check` (server trust anchors). They do not replace either.
Run `sdk_tls_chain_check` again right before activation: besides anchor coverage it
reports hostname, expiry and whether the file alone reaches a self-signed root
(`status` other than `ok` blocks the round; `warnings` such as an anchor expiring
soon should be resolved first). A trusted_certs.pem built only from the CA
certificates copied out of a cross-signed served chain fails that path check.
Keep the customer's selected themed enrollment/login clients, authentication
mode and explicit-authentication policy. Missing deployment information is a
prerequisite to resolve, not permission to copy a sample's values.

## Before activation and explicit-auth TMS

Run `sdk_deployment_preflight` against the actual `mc_config_path`, with the
customer's explicit `expected_mtls` choice. A sample `maverick.mTLS` value is
not evidence that the selected issuer supports client certificates. Obtain the
choice from the deployment owner or verified deployment documentation; retain
it locally with its evidence. Do not change shared issuer/TLS policy to make a
sample work, or disable server certificate validation or pinning.

When an offline token exists, supply `expected_token_client` from observed token
holder/session metadata and compare it with SDK IAM `clientId`. The WebView
login client's name does not establish ownership of an enrollment-issued token.
Preserve the selected WebView clients; any app-local IAM correction must match
the actual token contract, not a guessed client name. Inspect fixture state
before retrying: failure can consume codes and create partial bindings.

For explicit-auth tests pass `require_explicit_authentication=true` and the
observed `expected_token_client`; token-holder evidence is always required.
Set `granted_scope_stage` to identify which token the supplied `granted_scopes`
describe:

- `current` (default): the existing token may legitimately lack `tms`. Missing
  scope produces a warning/pending check, not a blocker: StartTransaction may
  obtain it through SDK token exchange or step-up authentication.
- `explicit_auth`: supply the actual scopes of the resulting exchanged/step-up
  token. Missing `tms` or missing resulting-token scope evidence blocks the gate.
  Recheck this stage before claiming explicit-auth success at the backend decision.

Requested scopes and client-assigned scopes are not actual granted-token evidence.
`tms` is necessary on the token used for the observed AST explicit-auth decision,
not universally on the token before the SDK exchange. Its presence alone does not
prove fresh user authentication or a complete authorization policy.

The tool checks supplied configuration and metadata only: it does not probe
issuer capability, decode/validate a live token, verify the provenance of the
expected values, or prove server acceptance. With explicit-auth checking disabled,
omitted token/scope evidence remains unverified rather than establishing token
readiness. Never print a token to obtain these fields.
Before claiming explicit-auth acceptance, obtain the missing evidence and test
the actual SDK/backend path. Never switch explicit authentication off or blindly
create/grant a realm scope to get a green result. A missing `tms` scope may require
a documented step-up flow or mapper; that contract must be established first.

## Before a requested SignedJWT returning-login path

Pass `require_signed_jwt=true` and the observed SDK `authentication_mode` to
`sdk_deployment_preflight`. The actual `mc_config` passed to Start must contain
an explicitly approved `maverick.jwtSignKeySecurityPolicy` and
`useTokenBasedLogin=true`; password mode does not select this factor in the
reviewed source. Missing prerequisites block this requested path without
blocking ordinary OfflineLogin when SignedJWT checking is not requested.

Do not substitute a sample policy or change existing key protection to get a
green result. Configuration inspection is not proof of effective stored keys
or exact delivered-version compatibility. Confirm the deployment-approved
policy before any key-creating operation; preserve existing bindings and use
a separately authorized isolated fixture if new keys are required.

Only runtime jwt-bearer/issuer evidence proves the grant. Never use `CLEAR_ALL`;
fresh token timestamps or biometric prompts do not establish SignedJWT.

## Before any physical iOS installation

Run `sdk_ios_signing_preflight(app_path, expected_team_id, device_udid)` on the
actual built `.app`, using the customer's expected signing team and target
physical device identifier (the tool accepts an omitted device for artifact-only
inspection, which does not verify device eligibility). A project setting or a
successful build is not artifact verification. Check the code signature,
entitlements authorized by the embedded profile, signer certificate membership
in the profile, expected team and target eligibility before
installation; recheck after rebuilding or changing identity/provisioning.

Keep preferred team identifiers in the customer's local project configuration,
never as a public SDK default. Do not fall back to a personal/other team because
it builds. Resolve missing signing prerequisites before installing. An update
across team identifiers can be rejected; inspect existing application/data state
and obtain any required removal authorization instead of uninstalling an
activated app. Simulator success does not satisfy the physical signing gate.

## Distinguish these failures

| Native/backend evidence | Meaning and next check |
|---|---|
| `510000015`, issuer rejects `TLS_CLIENT_WITH_KEY` | Check actual `maverick.mTLS` against the selected issuer/deployment contract. Not a generic SDK incompatibility. |
| `700000022`, HTTP403 `Client is not the holder of the token` | Check token holder versus IAM exchange client. The numeric wrapper alone is insufficient. |
| `516004034`, HTTP403 `Required explicit authentication scope 'tms' is missing` | Check granted scope and documented explicit-auth issuance policy; do not relax the trigger or grant scope blindly. |
| `516004035`, access token older than required | Authentication freshness is a separate condition; inspect the HTTP explanation and requested freshness interval. |

A result can report FAILED with `errorCode=0` and emit no Warning, RuntimeError
or FatalError. Keep listeners attached before Start, but also inspect sanitized
native SDK/backend diagnostics. Record the event sequence, operation, native
numeric code, HTTP status and explanation without tokens or credential values.

These are mandatory agent workflow gates. They do not add server-wide enforcement
to the SDK/backend or block independent raw service API calls. A result of
`configuration_checked` from deployment preflight is metadata verification with
runtime acceptance false. Signing preflight returns `artifact_checked`; this does
not prove on-device trust or successful launch.
