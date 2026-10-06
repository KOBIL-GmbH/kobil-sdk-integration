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
(VAL-27): cold OfflineLogin and interactive trusted-WebView login. OfflineLogin
may reuse an access token, refresh an offline token, or use a SignedJWT factor;
success alone does not distinguish them. Claim SignedJWT only when the effective
`maverick.jwtSignKeySecurityPolicy`, non-password auth mode, and jwt-bearer grant
evidence are verified. A timeout in one path is never attributed to biometric
failure or credited to the other path.

For a controlled diagnostic, first verify the effective sign-key policy and
selected auth mode. Clear only access and refresh tokens; do not clear all token
data, which also removes the offline token. If the effective policy or jwt-bearer
grant evidence is unavailable, record the SignedJWT claim as NOT_PROVEN.

Each run records package/source and mobile-SDK versions, app ID, asset
fingerprint, fixture ownership and the real backend outcome via readback. The
final matrix reports PASS/FAIL/BLOCKED/NOT_RUN per case; blocked cases are never
marked passed and policy is never weakened to force green. Cold login must
preserve activation data; the exported log ZIP must be reopened and its nonempty
encrypted SDK entries verified.

Use bounded waits sized from evidence: the first TMS confirmation took ~60s from
trigger to presentation (2026-09-29; later ones 2–17s). Preserve failure
evidence before any retry. Reserve each physical device explicitly through the
per-device lease protocol below; keep apps and fixtures isolated.

Interrupted-run cleanup (VAL-32, 2026-09-29): an interrupted xcodebuild device
run can leave the app process alive on the physical device. Clean up by exact
PID only — list processes with devicectl and use
`devicectl device process terminate --pid <exact PID>` for the task-owned
runner/app; never name-based kills and never processes owned by another session.
Preserve the .xcresult bundle, but do not rely on its UI snapshots for
post-mortem diagnosis: an app-private diagnostics file (for example a
diagnostics.jsonl pulled from the app container) is the effective diagnosis
channel. Physical-device tests remain distinct from simulator tests.

Owner-interaction protocol (VAL-31): announce required user interaction
(PIN/biometric/OTP) immediately before triggering it. For unattended TMS cases
(confirmation timeout, server cancel) announce beforehand that the owner must
not touch the live confirmation dialog; owner interaction invalidates the case —
preserve its evidence and retry cleanly.

Live coordination channel (E11): agent-turn message delivery can lag 40–60
minutes, so the worker maintains a live status file — for example
`<app>/OWNER_CHANNEL.md` — next to the app under test. At every device-blocking
step it appends `AWAITING_OWNER: <exact action>` with a timestamp before
blocking, and polls the same file for the owner's written reply before and after
each device step; the supervisor tails the file and answers inline. Blocking
steps must surface within seconds via the file, never only via turn boundaries.
Actions and status only — no credentials, codes, tokens or URLs. This
complements, never replaces, the announce-before-trigger protocol above and the
per-device lease below.

## Report durability, helper processes and budget (round 4, 2026-10-01)

- Write `TEST_REPORT.md` after EVERY gate (scaffold, Start, activation, each
  named returning-login path, each TMS case, export), not once at the end.
  Round 4 (O-16): three parallel workers were hard-stopped by a usage limit
  after ~35 min; two had passed gates but left no report. The report file is
  the durable record; chat output and heartbeat lines are not.
- Minute-log / heartbeat helpers (the WAIT line writers) are child processes
  of the worker, write a line also during long edits (O-06), and are killed by
  the worker before it reports COMPLETE or exits; the launcher kills the whole
  process group on stop. O-17: an orphaned heartbeat appended "WAIT - still
  working" every minute for 20 hours after the worker had died. A heartbeat is
  a liveness signal of the worker, never of a shell loop; a WAIT line with no
  tool activity for minutes is an orphan, not progress.
- Budget parallel runs against the usage limits before starting: three parallel
  workers exhausted a shared 5-hour window in ~35 min. Stagger legs, run
  build-only phases on a cheaper model or run one leg at a time, and record the
  resume handle (session id) per leg before the first call so a limit stop is a
  pause, not a loss.

## Per-device lease protocol (2026-09-29 user decision)

Acquire an exclusive per-device lease before any physical interaction (install,
launch, UI command, log pull). Parallel runs on separate phones are allowed;
never two test runners on one phone. The protocol is a shared JSON lease file
per test round — no daemon, one entry per device id:

```json
{"leases": {"<device-id>": {"owner": "<session-name>", "state": "active",
            "updated": "<ISO-8601>", "reason": "<test purpose>"}}}
```

- A second runner refuses all operations on a device whose lease is active and
  owned by someone else.
- Handoff is explicit: the owner sets `state: released` with a fresh `updated`
  timestamp and stops only its known task-owned processes by exact PID. App
  data (activation state) is retained unless the case owns its deletion. Use
  distinguishable app labels so resident apps are attributable.
- Steal an expired/stale lease, or recover from a failed session, only after a
  process check confirms no runner/app processes of the previous owner remain.
- System authentication prompts (device PIN/biometric dialogs) stay untouched
  by automation and cleanup; they belong to the announced owner interaction.

This protocol is motivated by the VAL-26 collision report; the audit found
overlapping resident apps, not two active runners, and concurrent-runner
causation of the observed authentication-prompt cancellation remains unproven.
The MCP ships this protocol as documentation only — it provides no lease-file
helper tool; runners maintain the shared lease file themselves.

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

## Issue-ID registry convention (E15)

Workers never mint central `VAL-nn` identifiers: app-local issue files use
descriptive slugs only (for example
`flutter-android-sdk-no-encrypted-log-files`). The supervisor assigns the
central `VAL-nn` at reconciliation and records the slug-to-ID mapping. Cite
already-assigned central IDs verbatim; never renumber or reuse a slug for a
different finding. Motivated by a 2026-09-29 collision between a worker-local
ISSUES.md numbering and the central registry.

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

## Knowledge decisions before runtime tests

Run the [knowledge interrogation workflow](knowledge-interrogation.md) before building apps: isolated reader-only questions, MCP knowledge retrieval, separately held expected answers, and answer-bound semantic review. Keyword checks alone are not acceptance.
