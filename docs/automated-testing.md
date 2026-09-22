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
