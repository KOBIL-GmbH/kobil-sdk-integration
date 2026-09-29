# Automated native app testing

Retrieve `sdk_knowledge_get("automated_testing", "android")` or `"ios"` and
`sdk_integration_checklist("automated_testing", platform)`. The packaged recipe
contains the workflow, runner templates, assertions, limitations and inspected
source hashes. No GSA checkout, test-helper binary or internal skill is required
to retrieve or apply the knowledge in a customer app.

## Test layers

| Layer | Purpose | Required evidence |
| --- | --- | --- |
| Model/unit | App logic and result mapping | Assertions with controlled inputs; no live-backend claim |
| SDK integration | Real callbacks and state transitions | Exact artifact/device, bounded event waits, SDK result |
| UI/backend | User journey through the real app | UI plus SDK plus backend result for the same fixture |

## Acceptance gates (2026-09-29 validation round)

Gates are strictly separated and reported independently: scaffold/unit/build ≠
real SDK dependency + concrete adapter + observed SDK Start event ≠ activation ≠
returning login ≠ TMS ≠ log export. A green scaffold build with a throwing/stub
adapter can never pass an integration gate (VAL-02); report scaffold tests
separately. Returning login has TWO distinct paths with separate acceptance rows
(VAL-27): the OfflineLogin/SignedJWT token path (user-preferred primary path,
with trusted-WebView enrollment and biometric protection) and the interactive
trusted-WebView login. A timeout in one path is never attributed to biometric
failure or credited to the other path.

Each run records package/source and mobile-SDK versions, app ID, asset
fingerprint, fixture ownership and the real backend outcome via readback. The
final matrix reports PASS/FAIL/BLOCKED/NOT_RUN per case; blocked cases are never
marked passed and policy is never weakened to force green. Cold login must
preserve activation data; the exported log ZIP must be reopened and its nonempty
encrypted SDK entries verified.

Use bounded waits sized from evidence: the first TMS confirmation took ~60s from
trigger to presentation (2026-09-29; later ones 2–17s). Preserve failure
evidence before any retry. Reserve each physical device explicitly (per-device
lock): parallel runs on separate phones are fine, never two runners on one
phone; keep apps and fixtures isolated.

Owner-interaction protocol (VAL-31): announce required user interaction
(PIN/biometric/OTP) immediately before triggering it. For unattended TMS cases
(confirmation timeout, server cancel) announce beforehand that the owner must
not touch the live confirmation dialog; owner interaction invalidates the case —
preserve its evidence and retry cleanly.

Provision unique users and activation codes through the configured MCP; backend
admin credentials stay out of app/test code. Register the app version and its
registration user before issuing the SDK config. Feed app-side inputs through a
private test channel. Record non-secret fixture IDs for ownership and cleanup.

The minimum native happy path checks fresh Start, activation, process termination
and returning login with persisted activation data. Add TMS terminal-state
checks, isolated negative cases and SDK log export checks for the requested
features. A green activation dialog is not evidence of returning login, and a
transaction request or displayed dialog is not terminal TMS success.

Use finally/teardown for run-owned cleanup; export SDK logs before reset and
restore changed device settings. Report passed, failed, skipped and not_run
separately. Retain Warning/RuntimeError/FatalError category, description, unsigned
code and last state without credentials or unfiltered event payloads.

## Qualification

Runner commands are source-derived templates, not executed test results. Discover
actual tasks/schemes and supported destinations in the customer app; adapt UI
selectors and fixtures. Existing GSA test names, ignored/commented cases and
skipped plan entries must not be counted as passing coverage. The topic identifies
specific source pitfalls so they are not copied into a fresh app.

This addition does not qualify Flutter or standalone IDPSDK and does not rerun
prior device acceptance. Native classic MCSDK/KSSIDP knowledge remains explicitly
scoped by each recipe. It adds one topic to the existing three knowledge tools;
it does not launch device tests or mutate a backend when retrieved.
