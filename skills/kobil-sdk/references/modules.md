# Customer modules

The declarative catalog ships in the Python package as modules.json. All listed
provider/backend adapters currently have status adapter_pending; dependency
planning is implemented, provider execution and automatic installation are not.
No external skill package or customer connection is silently installed.

| Module family | Selection | Purpose |
|---|---|---|
| Backend | backend=ast-shift or ssms | App/version setup and SDK configuration |
| Artifacts | artifact_source=local or teamcity | Customer-supplied SDK binaries |
| Distribution | distribution=[updraft,testflight] | Optional platform-specific build distribution |
| Observability | observability=[grafana] | Optional customer logs/metrics |
| Device diagnostics | diagnostics=[android-device,ios-device] | Device/simulator inspection |
| SDK logs | diagnostics=[sdk-logs] | Decryption using an authorized service/key source |
| QA | testing=[robot-appium] | Mobile test adapter contract |
| Infrastructure | infrastructure=[kubernetes] | Customer cluster access contract |
| Documentation | documentation=[confluence] | Customer documentation service contract |
| Issue tracking | issue_tracking=[jira] | Customer issue service contract |

Provider fields are lists of names. sdk_plan's capabilities list promotes
matching optional modules to required dependencies. Capability names:
distribution, observability, diagnostics, testing, infrastructure, documentation,
issue-tracking. Providers not selected by the customer are not prerequisites.

Every future adapter needs customer-configured endpoints, account/resource
scope, secret handling within trusted runtime helpers, platform coverage and
validation evidence. Log upload destinations and publication actions require
appropriate user scope. Do not embed customer examples or internal endpoints.

The initial Updraft/TestFlight contracts cover Android/iOS respectively. Desktop
provider coverage and broader service support require implementation and tests.
A missing distribution adapter must not prevent unrelated SDK build work.
