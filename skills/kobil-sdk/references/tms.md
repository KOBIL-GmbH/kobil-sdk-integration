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
PIN events or assume a plain confirmation proves re-authentication. The iOS 15.16
response is `KSMProvidePinEvent(confirmationType:andPin:)` → `KSMProvidePinResultEvent`;
`TransactionCenter.secretRequest` and `ui/TransactionSecretSheet.swift` implement it
(compiled, never run on a device); see
[sdk-features.md](sdk-features.md#flows-and-administrative-calls-sdkflowsswift).

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

`requireFreshnessOfAuthentication` (the `freshness_seconds` of `sdk_tms_trigger`) is the
maximum age in seconds of the user's access token when the phone answers; `-1` disables
it. `0` is not "off": every answer is refused with HTTP 403, code 4035 "The access token
is N seconds older than required", and the SDK ends the transaction with status Failed (39).
Seen on iPhone 15 Pro / iOS 26.6.1, MCSDK 15.16, 2026-09-26.

Retain the returned transaction ID. Read status and final result independently;
result may not be available while pending. Acceptance, rejection and expiry must
be checked against the final server response, not inferred from an HTTP200,
notification, button tap or local success banner. Cancellation and display-message
operations are separate capabilities.

The standalone MCP provides sdk_tms_trigger, sdk_tms_status, sdk_tms_result and
sdk_tms_cancel for foreground transactions, and sdk_display_message_send for one-way
messages. See [backend contract](../../../docs/backend.md). Push delivery is separate
work. Results never return the payload or the signature bytes; sdk_tms_result reports
the fields `signed_data_present`, `signed_data_bytes`, `signed_data_is_der_sequence` and
`signed_data_sha256` instead, and does not
cryptographically verify the signature. Never copy internal connection profiles or
environment defaults here.

## Document signing

AST has no separate signing endpoint for the MCSDK. Every transaction the user
**accepts** is signed on the device, and the backend keeps that signature as
`TmsResult.signedData` (a PKCS#7/CMS structure). A timed-out, rejected or cancelled
transaction has none. So a document signature is a TMS that names the document:

- `sdk_tms_trigger(..., text="Sign {{documentName}} (SHA-256 {{documentSha256}})",
  data={"requestType": "signature", "documentName": "...", "documentSha256": "<hex>"})`.
  `data` fills the Mustache placeholders in `text` (at most 20 keys, keys
  `[A-Za-z][A-Za-z0-9_]{0,63}`, values up to 1024 bytes, text plus data up to 8192 bytes).
- Hash the document on the server; send the fingerprint, never the document.
- The app parses `transactionInformation` (plain text or a JSON envelope), shows a
  signature screen with the document name and fingerprint, and answers with the
  normal DisplayConfirmation (OK = sign, CANCEL = decline). The SDK signs; the app
  never builds a signature itself.
- Prove it with `sdk_tms_result`: `status: ACCEPTED` and `signed_data_present: true`.
  A local "Signed" banner is not evidence.
- Log only the structure of what arrived (JSON key names or byte size), never values.

A separate KOBIL PDF-signing service (`/auth/realms/{realm}/mpower/v1/users/{userId}/signature`)
is not part of AST or the MCSDK; do not promise it for a
plain MCSDK app. A PDF the user signs inside the app needs no TMS and no backend: the SDK's
`KSMSignDataEvent` returns a detached CMS for the PDF's byte range; see
[signing.md](signing.md) (verified with `pdfsig` on 2026-09-26).

## Payment data

A payment request is a TMS whose `data` the app reads by key. `ios/TransactionCenter.swift`
understands these keys (case-insensitive); anything else is listed as a detail row:

| Key | Shown as |
|---|---|
| `requestType` | `payment` or `signature`; without it the text decides |
| `amount` with `currency` | the large amount, e.g. "EUR 24.50" (neither is repeated as a row) |
| `merchant`, `payee` or `recipient` | "To", and the name in the history |
| `documentName`, `documentSha256` | signature requests, see above |

```
sdk_tms_trigger(..., text="Pay {{amount}} {{currency}} to {{merchant}}",
  data={"requestType": "payment", "amount": "24.50", "currency": "EUR",
        "merchant": "Example Coffee"}, freshness_seconds=-1)
```

Send the amount as text with a dot and two decimals; the app displays it, it does not
calculate with it. The approval is the user's consent on the phone; moving money is the
payment provider's job on the server. A saved card chosen on the sheet ("Pay with", see
[wallet.md](wallet.md)) is only a label on the local record.

## Test sequence

`sdk_tms_test_sequence(expected_environment, user_uuid, steps=["message", "signature",
"payment"], delay_seconds)` sends the three kinds of request one after another in the
background: the next one goes out only after the device answered the previous one or it timed
out. It returns a run id at once; `sdk_tms_test_sequence_status(run_id)` reports each step's
transaction id and final status. A failed step is recorded and not retried. Use it after
changing the approval screens; tap through the requests on the phone while it runs.

## Display messages

`sdk_display_message_send(expected_environment, user_uuid, text, timeout_seconds)`
posts `/v1/tenants/{tenant}/display-message`. HTTP 202 means accepted for delivery
only; the backend offers no read receipt, so the tool returns `delivery_verified: false`.
On the device the SDK sends KSMTriggerBannerEvent with the display-message banner
type; the app answers with KSMStartDisplayMessageEvent and then receives
KSMDisplayMessageEvent (messageInformation, messageType). Verify delivery from the
app's own log or UI, not from the 202.

## Chat is not in the iOS MCSDK

The ObjC/Swift MCSDK exposes only chat lifecycle events (for example
KSMChatInitialised). There is no API to send or receive chat messages. KOBIL's chat
uses the Dart wrapper's SendMessage/NewMessage events and separate backend services,
neither of which a plain iOS app has. Do not invent a chat API: for a native iOS app,
build the "messages" screen on display messages (one-way, server to device) and say
plainly that two-way chat needs the chat-capable SDK and backend.

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

iPhone 15 Pro / iOS 26.6.1, MCSDK 15.16, 2026-09-26:
- `transactionInformation` and `messageInformation` arrive as the JSON envelope
  `{"text": ..., "external": false, "data": {...}}`, not as plain text. Parse it; show
  `text`; hide `external`; read your own keys from `data`. Return the original string
  unchanged in the DisplayConfirmationEvent.
- Document signing passed: a TMS with `data.requestType = "signature"` opened the
  app's signature screen, the user signed, and sdk_tms_result returned ACCEPTED with
  `signed_data_present: true` (2953-byte DER CMS).
- Display message passed: 202 from sdk_display_message_send; the SSE stream delivered
  `dmsAvl` at the app's next login (not while the old session was idle), then
  KSMTriggerBannerEvent → KSMStartDisplayMessageEvent → KSMDisplayMessageEvent (Info).
  Expect delivery on the next connection, not instantly.
- A plain-style SwiftUI button with only its label tappable caused a mistaken accept
  on a "decline" test. Give both decision buttons a full-size `contentShape`.
- After the full-size `contentShape` fix, on the same tuple: decline sent Cancel(1),
  SDK status 3, backend REJECTED, no signature; a 30 s timeout with no tap ended with
  SDK status 4, backend TIMEOUT, no signature. Returning login passed before each case.

## Explicit authentication (device-verified 2026-09-27)

`sdk_tms_trigger(require_explicit_authentication=True)` does not make the SDK ask an IDP-login
user for a PIN. When the transaction arrives, the SDK silently exchanges the user's login token
for one with scope `tms` (`RetrieveAuthTokenInternalEvent` → `PostIamTokenExchange`, as the
`mc_config.json` `iam.clientId` client), then answers with that token. Two backend and config
conditions must hold. If either fails, the transaction ends `TransactionEnd status=Failed` with
nothing on screen, and `KSMTransactionPinRequiredEvent` and `KSMTransactionTokenRequiredEvent`
never arrive:

| Symptom in the device log | Cause | Fix |
|---|---|---|
| IDP 403 `access_denied` "Client is not the holder of the token" | `iam.clientId` is not the client that issued the login tokens. Keycloak lets a public client exchange only tokens it holds; no permission changes that. | Set `iam.clientId` to the login client (email-code apps pass the activation client explicitly, so activation is unaffected). |
| AST 403 code 4034 "Required explicit authentication scope 'tms' is missing" | The realm has no `tms` client scope, or the login client does not offer it; Keycloak silently drops the requested scope. | `sdk_tms_scope_ensure(client_id=<iam.clientId>)` creates the scope and adds it as optional. |

Verified sequence on the verification realm (iPhone, MCSDK 15.16):
1. With the activation client (for example `<App>Activation`) as `iam.clientId`, the result was "not the holder".
2. With `IDPSubsequentLoginHeadlessV2` as `iam.clientId`, the result was 4034.
3. After adding the `tms` scope, the transaction was ACCEPTED with a device signature.

`KSMExchangeIamTokenEvent` (a token for your own backend) also worked after step 2. Keep the
phone unlocked for it: when the phone is locked the keychain answers -25308 and the result is
status 39.

The cause and the fix are platform-neutral. Android and Flutter read the same `iam.clientId`
from their MasterController configuration and use the same realm; only iOS was device-tested.
