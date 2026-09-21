# App flow sources and service boundary

The MCP exposes IDP and AST operations. It does not choose an app journey or
provision a replacement flow from an example. Backend flow administration is an
explicit API operation requested by the caller, not an integration default.

## Source selection

1. Select SDK family, version, native/Flutter framework, and deployment.
2. For native Shift integration, use the authorized WLA skill and its matching
   WLA Shift source branch. Do not apply SSMS instructions to Shift.
3. Cross-check with the matching MC_GettingStarted_Kotlin or
   MC_GettingStarted_Swift app supplied for that SDK version. Locate its native
   activation/login and multi-step implementations, state machine and tests.
4. Record repository revision, relative source file, SDK version and relevant
   events in the local project plan. Different flavors can implement different
   contracts. Sample client names are not universal defaults.
5. Obtain explicit deployment client/flow choices. SuperApp Login V2 is not a
   native Android/iOS flow. Do not infer a replacement from a lookup failure.
6. Implement the sequence of SDK events and form callbacks from those sources;
   keep activation, login, PIN changes, restart and TMS states distinct.

GettingStarted's native single-step and multi-step implementations are separate.
Support multiple pages/events when the selected native flow requires them. Never
impose a one-page restriction because another deployment had an XHTML defect.
Capture Warning, RuntimeError and FatalError with errorType, errorDescription and
errorCode. Report the last event and pending operation when the app stops making
progress. SDK startup, backend provisioning and successful app login are separate
verification steps.

WLA skills and source repositories can be private. They are optional local
references, not bundled customer content. If access is unavailable, use authorized
version-matched GettingStarted material or request it; do not invent the flow.
Do not copy customer configuration, credentials, internal URLs, or private source
into public plugin files.
