# TMS: transaction confirmation

Status: foreground MCP tools and native Android/iOS handling are implemented.
Accept, reject, timeout and server cancellation passed on the recorded device tuples below. Activation/login success does not
verify transaction signing, notification delivery or backend completion.

## Prerequisites and ownership

Use the selected SDK family's transaction contract. This recipe covers AST/Shift;
SSMS has a separate backend API and must not inherit these REST paths.

- Reuse the registered app/version and an activated recipient. Keep registration
  user, Keycloak user UUID and SDK device/user identifiers distinct.
- Verify the signed service map and required transaction certificates/readiness.
  A login result alone does not prove that transaction signing is ready.
- Handle incoming events globally, including while another screen is open.
  Current [KSSIDP initialization documentation](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-kssidp/development/kssidp-initialization/)
  deprecates shouldKssIdpHandleTms/shouldHandleTms: implement application-owned
  handling. Older binaries may retain the flag; inspect the actual release.
- Start with foreground delivery as a separate test from background notification.
  Push testing additionally requires provider configuration, a device push token
  registered through SetPushTokenEvent, and the backend's push request settings.
  See [TMS APIs](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-twv/idp/postman_usage/postman_tms).

Before explicit-auth tests, run `sdk_deployment_preflight` with
`require_explicit_authentication=true` and observed token-holder identity.
At `granted_scope_stage="current"` (default), missing `tms` warns rather than
blocks: the SDK may acquire it through token exchange/step-up. Recheck the actual
resulting token using `granted_scope_stage="explicit_auth"`; missing `tms` or
missing resulting-token scope evidence blocks that gate. See
[deployment gates](deployment-preflight.md): scope `tms` is necessary at the
observed AST decision, not sufficient proof of step-up/user authentication.
A request for scope is not a grant. Never disable explicit auth
or blindly create/assign a scope. Distinguish token-holder HTTP403/700000022,
missing explicit scope 516004034 and freshness 516004035 using native HTTP detail,
even when SDK result code is zero and no fatal event is emitted.

## Explicit authentication: what the token client needs (measured 2026-10-01/05)

The documented contract (KOBIL AST TMS Service documentation, parameter
`requireExplicitAuthentication`): "The explicit authentication is done in terms
of a dedicated OIDC scope. The scope to use is configured in the service's
configuration. When a client wants to answer a TMS with this requirement set,
it must retrieve a token with the configured scope from the IDP and use this
token for sending the answer." The scope name is an AST deployment setting; on
the inspected deployments it is `tms`. Read it from the AST configuration, do
not assume it. The SDK fulfils the contract with a silent token exchange using
`iam.clientId` (`process_transaction_task.cc:278-301`); it does not start an
interactive step-up and does not re-check the issued scope. The IDP resolves
the requested scope only against the client's configured default/optional
client scopes and silently drops unknown names
(`KobilTokenExchangeProvider.java:390-396`).

Device-verified (SDK 15.16, IDP core 8.0.x, AST trusted-message-sign 0.40.0)
on a physical Android device with a hardware-backed key and on an Android
emulator with a software-backed key (`jwtSignKeySecurityPolicy =
ALLOW_VIRTUAL_SMART_CARD`), each time with an isolated token client and no
change to shared clients:

| Token client state | Explicit TMS result |
|---|---|
| no `tms` client scope on the token client | exchange HTTP 200 without `tms`, AST HTTP 403 / SDK 516004034 |
| `tms` optional scope, but the SDK token is still held by the enrollment client | IDP `TOKEN_EXCHANGE_ERROR not_allowed "client is not the token holder"`, SDK `FAILED/0` before the dialog, backend stays DOWNLOADED/TIMEOUT |
| `tms` optional scope, holder fixed, realm default browser flow | interactive login `CANNOT_ACQUIRE_TOKEN_DATA`, IDP `X-KOBIL-ASTCLIENTDATA is missing` |
| `tms` optional scope + holder + KOBIL mobile browser-flow override | `DisplayConfirmationResult OK`, `TransactionEnd OK`, AST **ACCEPTED**; reject path `USER_CANCEL` / **REJECTED** |

Preconditions, all checked read-only by `sdk_tms_explicit_preflight`:

1. `tms` assigned to the token client as **optional** client scope (not default,
   not realm-wide, not on unrelated clients).
2. The token client is the **holder of the SDK's current token** at the moment
   the transaction is answered. Two situations break this:
   - after activation through a separate enrollment client the SDK still holds
     that client's token;
   - after a cold start with `OfflineLogin` (signed-JWT or offline-token path)
     the SDK's token is again issued to the enrollment client (`azp` =
     enrollment client), even if an interactive login with the token client
     happened in an earlier session.
   One interactive login with the token client in the **current session** fixes
   the holder; verify with the access-token claims (`azp` = token client)
   before triggering an explicit transaction. The wrong holder fails silently:
   SDK `FAILED/0` without a dialog, no SDK error code, backend never leaves
   DOWNLOADED. Ordinary transactions are not affected.
3. The token client carries the client-level browser-flow override used by the
   KOBIL mobile clients (`authenticationFlowBindingOverrides.browser` =
   "KOBIL Mobile Login"); kobil-support `idp_client_flow_override` sets it.

Customer deployments usually do **not** have (1) and (3) on their login client
unless explicit TMS was planned; the observed symptom there is exactly row one
(403 / 516004034) while activation, login and ordinary TMS work. Treat it as a
realm configuration decision for the customer, not as an SDK defect, and never
change a customer realm from a test run.

What this does not establish:

- that the exchanged token represents a **fresh** user authentication. With
  `requireFreshnessOfAuthentication` at the default 3600 s no biometric prompt
  appears at confirmation; the exchange reuses the existing session. With
  `0` (or any value below the confirmation latency) the transaction is created
  but fails at confirmation with HTTP 403 "access token is N seconds older than
  required", surfaced by the SDK only as 516004035 "A network error occurred".
  The SDK has no step-up path for this today; whether `tms` should be bound to
  a real re-authentication is a product decision, not a test defect.
  How to report it: this is neither an SDK defect nor a customer configuration
  error. If the customer only needs the scope check, use the default 3600 (or
  `-1`). If the customer needs a **forced re-authentication at confirmation**,
  say plainly that the current SDK/AST combination cannot deliver it and
  escalate it as a product requirement; do not present a lower freshness value
  as the fix for that requirement.
- that any production integration sets `requireExplicitAuthentication=true`;
  the inspected backend callers hard-code or default to `false`.

Do not disable `requireExplicitAuthentication` and do not add `tms` as a
default scope to make a run pass.

## Diagnose requested versus issued transaction scope

Use `sdk_tms_auth_diagnose` with scope names and numeric status/error codes only.
For the inspected Maverick SDK implementation, transaction retrieval supplies
`requiresExplicitAuthenticationScope`. The SDK compares that requirement with
its token and internally requests OAuth token exchange using `iam.clientId` and
the required scope. This happens before confirmation presentation; a token
request after the decision can instead be the app's own claims lookup.
Do not invent an extra application WebView step from missing ordinary scopes.
Check this contract against the supplied SDK version.

Record these separately: downloaded requirement, requested exchange scope,
exchange HTTP result, issued token scopes, and AST decision result. An exchange
HTTP200 can be followed by PATCH HTTP403/516004034: success at the token endpoint
does not prove the requested scope was granted. Inspect the actual exchange
result, not a later ordinary token. Compare users with the same client and
explicit-auth policy; a prior non-explicit TMS pass is not a valid control.
Successful activation does not prove transaction authorization, and a missing
scope does not establish a user-creation defect. Do not recreate users or assign
a default scope to force a pass. Correct issuance requires the documented
server authentication contract.

Capture inherited result error fields (`hasErrorOccurred`, `errorCode`,
`errorDescription`, `reportId`, where exposed) on confirmation and terminal
events. A Swift status39 may carry server516004034 and the full HTTP error;
logging only status discards the diagnosis even with Warning/Runtime/Fatal
listeners installed. Use the exact transaction ID and UTC timestamps to
correlate SDK and backend traces. Claims lookup can update session lastAccess;
that timestamp alone is not evidence of transaction exchange.

Timeout and server cancellation are independently testable. A local timeout
can terminate before the SDK sends a decision PATCH; accept/reject scope errors
must not automatically block those separate gates. The inspected SDK's legacy
explicit-auth integration tests are disabled, so do not present them or older
non-explicit four-mode passes as current explicit-auth support evidence.

## GettingStarted baseline versus explicit authentication

The inspected bundled GettingStarted ApiHelper request builder uses
`requireExplicitAuthentication=false` and `requireFreshnessOfAuthentication=-1`.
Those ordinary transaction tests are not equivalent to an explicit-authentication
scenario. Record these request settings with every result; match the reference
policy for a labelled baseline comparison instead of changing users or clients.
Do not silently relax a customer's explicit-authentication requirement or report
a baseline pass as its fix. SDK/API-helper versions and backend must also be
recorded. A different platform's helper binary requires its own verification.

The inspected Swift sample logs success on confirmation/end without evaluating
the event status, and UI tests can pass on navigation alone. Always check actual
SDK status and backend terminal result rather than copying that success logic.

## App event sequence

The [transaction guide](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-kssidp/development/transaction/)
separates notification, presentation and completion:

| Event/stage | App behavior |
|---|---|
| TriggerBannerEvent | Inspect banner type; transaction and display-message flows differ. |
| StartTransactionEvent | Begin the selected transaction flow; avoid unrelated SDK operations while it is active. |
| DisplayConfirmationRequestEvent | Present transactionInformation and its timer; obtain the user's accept/reject decision. |
| DisplayConfirmationEvent | Submit the decision with transaction information according to the SDK contract. |
| DisplayConfirmationResultEvent | Inspect status/errors; do not assume final backend acceptance. |
| TransactionEndEvent | Handle completion, rejection, timeout, server cancellation and transport failures; clear stale UI. |

For display messages, follow StartDisplayMessageEvent/DisplayMessageEvent instead
of treating the message as a transaction approval. Handle any required
TransactionPinRequiredRequestEvent and its release-specific response. Explicit
or fresh authentication depends on backend policy and SDK mode; do not fabricate
PIN events or assume a plain confirmation proves re-authentication.

Kotlin reference code uses the event names above. Swift documentation uses KSM
names and includes KSMTransactionFinishedEvent; Flutter examples use T-suffixed
bindings. Inspect supplied APIs before adapting names or interpreting completion
status. Validate Android and iOS separately for Flutter; desktop targets are outside
the external-customer scope.

## Backend contract

The [AST test guide](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-kssidp/testing/tms/test_tms/)
uses POST /v1/tenants/{tenant}/tms with the recipient's internal Keycloak UUID,
not their username. The request includes tmsData, retrievalTimeout, tmsTimeout,
requireExplicitAuthentication and requireFreshnessOfAuthentication. Resolve
units and policy semantics from the deployed API; do not copy sample timeout
numbers without checking them. Backend authorization remains server-side.

requireFreshnessOfAuthentication is the maximum age in seconds of the confirming
device's authentication, checked at confirmation time — not at trigger time.
`sdk_tms_trigger` defaults it to 3600 and `-1` disables the check. `0` (or any
value below the confirmation latency) creates a transaction that is guaranteed
to fail at confirmation: observed 2026-09-29 (iOS MCSDK 15.16.803.3089231) as
HTTP 403 "The access token is 85 seconds older than required", which the SDK
wraps as generic errorCode 516004035 "A network error occurred" — the freshness
cause is visible only in the embedded HTTP body. The tool creates the
transaction but returns an explicit warning for such values.

Retain the returned transaction ID. Read status and final result independently;
result may not be available while pending. While a transaction is not yet
terminal, the backend result endpoint answers HTTP 412; `sdk_tms_result` maps
this to an explicit lowercase status `pending` (observed 2026-09-29 during
bounded-wait polling). Pending is not a backend error: keep bounded polling and
never re-trigger because a result is still pending. Terminal transactions are
not kept readable for long: recorded 2026-10-05, both the status and the result
endpoint answered HTTP 404 for ACCEPTED, REJECTED, TIMEOUT and CANCELLED
transactions about 2.5 h after completion. `sdk_tms_status` / `sdk_tms_result`
map that to the lowercase status `not_found` (unknown id, routing, masked authorization or possible retention, not
failure). Read status and result **directly after the SDK terminal event** and
record them then; a later 404 proves nothing either way. Acceptance, rejection and expiry must
be checked against the final server response, not inferred from an HTTP200,
notification, button tap or local success banner. Cancellation and display-message
operations are separate capabilities.

The standalone MCP provides sdk_tms_trigger, sdk_tms_status, sdk_tms_result and
sdk_tms_cancel for foreground plain-text transactions. See [backend contract](../../../docs/backend.md).
Push and display-message backend adapters remain separate work. Results omit
payloads and signatures; final status checks do not cryptographically verify a
signature. Never copy internal connection profiles or environment defaults here.

## Verification plan

Use clearly labelled synthetic test content and one pending transaction at a
time for the first implementation. Record the transaction ID, redacted recipient
reference, app/SDK versions, timestamps, SDK events and backend final result.
Keep payloads and authentication input out of routine shared logs.

Verify separately: accept, reject, user timeout, server cancellation, interrupted
connectivity, required re-authentication, display message, and background push.
Do not automatically approve real transactions; synthetic automated confirmation
requires the user's test scope. Handle duplicate notifications without duplicate
submission and reject clicks after timeout/cancellation.

On failure, capture Warning/RuntimeError/FatalError fields and the specific
transaction result/status. Compare the last completed SDK stage with backend
state before retrying. Ask the user when the next correction is unclear. After
each passed scenario, add a version/platform-scoped skill checkpoint; until then,
keep this recipe marked studied, not verified.

## Patterns learned from existing apps

Read-only Kotlin, Swift and Flutter app implementations confirm a reusable split:
global SDK listener, transaction state, presentation, decision submission and
terminal result handling. Keep platform-specific presentation outside the core flow.

When implementing this split, check these demonstrated pitfalls:
- Swift completion events expose status; do not construct success unconditionally.
- Preserve cancellation, rejection and error distinctions instead of collapsing
  every non-success event into a generic failure.
- Cancel timers and clear completion callbacks on every terminal path, including
  early timeout/server-cancel branches. Cancel every stream subscription on disposal
  and prevent delayed callbacks from writing into closed state objects.
- Retain the original transaction information for the SDK response separately
  from formatted presentation. Avoid duplicate submission while a response is pending.

These are code-review findings and implementation requirements, not new runtime
checkpoints. The reference apps were not modified or exercised by this review.

## Verified foreground Android checkpoints

On Pixel 8/API36 arm64 with KSSIDP1.7.0 / MC188.1.2937039, a synthetic
foreground transaction triggered through sdk_tms_trigger was received, presented
and accepted once. DisplayConfirmationResult and TransactionEnd returned OK;
sdk_tms_result independently reported ACCEPTED. SDK transactionInformation
contained a JSON envelope: parse text for presentation/automation matching but
return the unchanged original information in the confirmation. Each scenario is verified separately below.

On the same tuple, explicit rejection sent one CANCEL decision; the SDK returned
USER_CANCEL for confirmation and transaction end, and the backend final result
was REJECTED. UI/timer state was cleared before the next transaction.

Timeout was also verified: no accept/reject input, one timer-driven TIMEOUT
response, SDK USER_CONFIRMATION_TIMEOUT and backend TIMEOUT. The confirmation
timer used the SDK-provided seconds; expired UI was cleared and accepted no click.

Server cancellation was verified after the backend reported DOWNLOADED:
sdk_tms_cancel returned successful cancellation request, the SDK emitted
SERVER_CANCEL without a local decision, and sdk_tms_result reported CANCELLED.
The dialog and timer were cleared. These four tests preserved activation and
login; the TMS build passed returning login before the transaction series.

Live coverage remains limited to foreground single transactions on this Android
tuple, without explicit re-authentication. Background push, display messages,
concurrent transactions, connection interruption and Flutter targets are
not verified. Swift foreground coverage is recorded below. The app reports unsupported explicit-authentication requests rather
than silently bypassing them.

A subsequent visible demo was manually accepted on the device: no automation
tapped a decision, and both SDK OK and backend ACCEPTED were observed.

## iOS foreground checkpoint

Fresh Swift app, MCSDK 15.16.803.3089231 with bundled KSSIDP, iPhone 17 Pro Max / iOS 26.6.2: synthetic foreground acceptance passed. SDK DisplayConfirmationResult and TransactionFinished returned OK, dialog/timer cleared, and independent MCP backend result returned ACCEPTED. The debug harness matched an exact synthetic text before submitting once; original transactionInformation was preserved. Other iOS scenarios are tracked separately.

On the same iOS device tuple, foreground reject passed: backend REJECTED, SDK terminal event recorded and dialog/timer cleared. One local decision was submitted.

On the same iOS device tuple, foreground timeout passed: backend TIMEOUT, SDK terminal event recorded and dialog/timer cleared. One local decision was submitted.

On the same iOS device tuple, foreground cancel passed: backend CANCELLED, SDK terminal event recorded and dialog/timer cleared. Server cancellation completed without a local decision.

For iOS the observed terminal status values were 0 (accept), 3 (reject), 4 (timeout) and 53 (server cancellation). Each accept/reject/timeout submitted one local decision; cancellation submitted none. Returning login passed before every case. Disable debug scenario arguments after testing; normal confirmations require user input. Background push, explicit re-authentication and network interruption remain unverified.

Retention intervals are deployment-specific; the observed delay is not a universal guarantee. A 404 does not by itself establish the cause.
