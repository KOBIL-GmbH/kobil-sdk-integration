# TMS: transaction confirmation

Status: foreground MCP tools and Android handling are implemented. Accept,
reject, timeout and server cancellation passed on the Android tuple below. Activation/login success does not
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

Retain the returned transaction ID. Read status and final result independently;
result may not be available while pending. Acceptance, rejection and expiry must
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
concurrent transactions, connection interruption, Swift and Flutter targets are
not verified. The app reports unsupported explicit-authentication requests rather
than silently bypassing them.

A subsequent visible demo was manually accepted on the device: no automation
tapped a decision, and both SDK OK and backend ACCEPTED were observed.

## iOS foreground checkpoint

Fresh Swift app, MCSDK 15.16.803.3089231 with bundled KSSIDP, iPhone 17 Pro Max / iOS 26.6.2: synthetic foreground acceptance passed. SDK DisplayConfirmationResult and TransactionFinished returned OK, dialog/timer cleared, and independent MCP backend result returned ACCEPTED. The debug harness matched an exact synthetic text before submitting once; original transactionInformation was preserved. Other iOS scenarios are tracked separately.

On the same iOS device tuple, foreground reject passed: backend REJECTED, SDK terminal event recorded and dialog/timer cleared. One local decision was submitted.

On the same iOS device tuple, foreground timeout passed: backend TIMEOUT, SDK terminal event recorded and dialog/timer cleared. One local decision was submitted.

On the same iOS device tuple, foreground cancel passed: backend CANCELLED, SDK terminal event recorded and dialog/timer cleared. Server cancellation completed without a local decision.
