# Bundled app integration knowledge

Use sdk_knowledge_topics, sdk_knowledge_get and sdk_integration_checklist.
The native Shift pack covers setup, lifecycle, activation, login, multi-step
interaction, TMS, diagnostics and SDK log export. It is packaged with the MCP;
customers need no WLA skill or GettingStarted checkout.

Select platform, SDK family and mobile SDK artifact version explicitly. The MCP
release number is not the mobile SDK version. This initial pack is source-reviewed
with mostly illustrative examples. Diagnostic adapters include limited synthetic
device-test evidence in their example validation metadata; this does not qualify
a complete recipe or live backend flow. Unsupported
platforms/families return a knowledge gap; do not infer Flutter or SSMS behavior.

Choose existing deployment clients/flows explicitly. Never use SuperApp Login V2
for native Android/iOS or create a replacement backend flow to fit an example.
Native multi-step interaction is supported conceptually; do not impose a one-page
constraint. Keep initialization, activation, login and transaction completion distinct.

Capture Warning, RuntimeError and FatalError with original error type (the iOS
15.16 Warning property is errorStatus),
errorDescription and errorCode. On a stall report state, last event and pending
operation. Never include credentials, activation codes or tokens in logs.

Maintainers use version-matched source evidence to improve and qualify the bundled
content. Source provenance is evidence, not a runtime dependency. Customer-specific
names, infrastructure settings, binary assets and private test constants must not
be published in the pack.
