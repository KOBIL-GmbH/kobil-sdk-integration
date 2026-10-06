# Sign-key policy, test target and what each can prove

`maverick.jwtSignKeySecurityPolicy` in `mc_config` decides how the SDK's JWT
signing key must be protected. The policy is read at SDK Start and the key is
created at activation, so the value must be present **before** the first
activation; changing it later needs a fresh activation (new user or new app
identity). Unknown values fail configuration parsing. Without the policy the SDK
has no signing key and selects the offline-token first factor; `OfflineLogin`
still succeeds, but no jwt-bearer grant happens and SignedJWT is not in use.

## Policy versus target (measured SDK 15.16, 2026-10-02/05)

| Policy | Key requirement | Physical device | Android emulator | iOS simulator |
|---|---|---|---|---|
| `ENFORCE_STRONG_HARDWARE` | StrongBox / Secure Enclave | works when the device has it | fails: Start `NOT_SUPPORTED` (status 46 / 800000278) | fails: key creation Secure Enclave `-25293`, LocalAuthentication `-1020`, SDK 802025293 |
| `ENFORCE_HARDWARE` | TEE-backed key (`securityLevel >= 1`) | works | fails the same way (`isKeyInsideSecureHardware securityLevel 0`) | fails the same way |
| `ALLOW_VIRTUAL_SMART_CARD` | hardware when available, otherwise a software-backed key | works, key stays hardware-backed | works with a software key: jwt-bearer grant and token HTTP 200 measured | works with a software key |
| not set | - | offline-token first factor, no SignedJWT | same | same |

`NOT_SUPPORTED` at Start is **not** proof that the device lacks hardware: the
same status appeared on a physical device when the Android CSR helper could not
load `JcaContentSignerBuilder` (missing `org.bouncycastle:bcpkix-jdk15to18`
dependency). Read the native log (`isKeyInsideSecureHardware`, `GetKeystoreInfo
has strong hardware keystore ...`) before attributing the failure. On a
decrypted log, `sdk_log_markers(decrypted_log_path)` does this reading
deterministically: it reports the jwt-bearer grant correlation, the key kind
(software / hardware), the NOT_SUPPORTED attribution (missing dependency vs
undetermined) and explicit-TMS exchange refusals - line numbers and booleans
only, never payload text.

## What a target can prove

| Claim | Emulator / simulator | Physical device |
|---|---|---|
| Protocol: Start, activation, WebView login, claims, ordinary and explicit TMS, log archive | yes | yes |
| SignedJWT grant path (`GetIamAccessTokenUsingJwtBearer` -> token endpoint 200) | yes, with `ALLOW_VIRTUAL_SMART_CARD` only; this is the only target that exercises the software-key fallback | yes |
| Key protection level, attestation, `securityLevel`, StrongBox/Secure Enclave | no (`securityLevel 0`, no SE) | yes |
| Biometric as a security statement (STRONG class, no credential fallback) | no: the virtual sensor only proves the prompt appears and the flow continues | yes, with the owner's finger/face |
| Freshness / step-up at explicit TMS | not target dependent (server side) | same |
| Push delivery, Doze, OS update behaviour | no | yes |

Record on every result which target produced it; a software-key pass does not
qualify a hardware-only deployment and a hardware pass does not prove the
virtual fallback.

## Agent duty: do not let the user fail on configuration

The user of this MCP must not run into a dead end because of a target or a
backend configuration they could not know about. Before the first key-creating
operation (activation) and before the first explicit transaction:

1. **Resolve the target first.** If the chosen target is an emulator or
   simulator and the configured or intended policy is `ENFORCE_STRONG_HARDWARE`
   or `ENFORCE_HARDWARE`, stop before activation and say so: the activation will
   fail with the codes above and consume the activation code. Offer the two
   valid options - `ALLOW_VIRTUAL_SMART_CARD` for this test fixture, or a
   physical device - and let the user choose. Never silently downgrade a
   deployment policy and never apply a test policy to a customer configuration.
2. **Run `sdk_deployment_preflight` with `require_signed_jwt=true`** against the
   actual `mc_config` when SignedJWT is intended. A missing policy blocks there
   with a clear message instead of after a consumed activation.
3. **Run `sdk_tms_explicit_preflight(token_client, enrollment_client)`** before
   the first explicit transaction. It reports read-only which of the three
   preconditions (optional `tms` scope, token holder, browser-flow override
   "KOBIL Mobile Login") is missing and the exact failure signature the user
   would otherwise see (403/516004034, silent `FAILED/0`,
   `CANNOT_ACQUIRE_TOKEN_DATA`; a freshness value below the confirmation
   latency shows as 516004035). Report the finding as a realm configuration
   item for the owner of that realm; do not fix a customer realm from a test
   run.
4. **After a cold `OfflineLogin` re-check the token holder** (`azp` claim) before
   an explicit transaction; if it is the enrollment client, run one interactive
   login with the token client first.
5. When a step fails anyway, name the measured cause from the tables above, not
   "SDK error", and state what the user has to change (target, policy, realm
   configuration) in one sentence.
