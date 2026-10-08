> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/enable_tracing> on 2026-09-28. Converted to Markdown; wording unchanged.

# Enabling Tracing

Our SDK supports collecting distributed traces via OpenCensus. To this end, you need to configure the server side used to collect the relevant data (provide a "Zipkin via TLS" endpoint with Basic Auth reachable from the internet, e.g., by Jaeger tracing component) and to explicitly enable tracing on the MC level.

## Event Ordering Requirements

The tracing events must be sent in a specific order:

1. **ConfigurationEvent** must be sent **before StartEvent** to configure the tracing server endpoint and credentials. This ensures that the StartEvent and all internal processing during the Start operation can be properly traced. Without configuring tracing before StartEvent, you will miss trace data for the initial MC startup and all events triggered during this process.
2. **EnableOpenCensusTracingEvent** and **EnableServerTracingEvent** may only be called **after receiving StartResultEvent**.

Note that neither the ConfigurationEvent nor the EnableOpenCensusTracingEvent trigger a response event, so you only need to send these events without waiting for a response.

## Configuration and Enabling Tracing

Right after receiving the result for your Start event, you can enable tracing. To this end, send a ConfigurationEvent which sets:

* the exporterURL of the server collecting the trace data,
* the credentials (Basic Auth "userName" and "password") needed to access it, and
* the list of trusted TLS server certificates in PEM format. See [Trust Store Configuration](shift-lite-idpsdk__prerequisites__mc-config-files__trust_store.md) for details on which certificates to put into the trust store.

Then, send an EnableOpenCensusTracingEvent (which takes a boolean parameter) to enable or disable the tracing.

## Tracing Propagation Probability

When you enable OpenCensus tracing, it sets the propagation probability to 100%, meaning all traces will be collected. If tracing is not explicitly enabled, MC tracing will either:

* Default to 10% propagation probability, or
* Use whatever propagation probability is defined in the `traceParent` that was passed to MC events

This allows for fine-grained control over trace sampling rates in production environments.

## Trace Context

Every EventFrameworkEvent has the methods **setTraceContext** and **getTraceContext**.
You can create your own TraceContext object and set it in a particular event via setTraceContext.
You can use getTraceContext to get some existing TraceContext and reuse it for other event calls belonging to the same flow.

### iOS/Swift

For Swift, the following snippet can be used to enable tracing:

Enable Tracing (Swift)

```
func configureOpenCensusTracing(openCensusConfig: OpenCensusConfig) {
let event = KSMConfigurationEvent(exporterUrl: openCensusConfig.exporterUrl,
userName: openCensusConfig.userName,
password: openCensusConfig.password,
serverCertificate: openCensusConfig.cert)
MasterControllerAdapter.sharedInstance.sendEvent2MasterController(event: event)
}
func enableOpenCensusTracing(enable: Bool) {
let event = KSMEnableOpenCensusTracingEvent(tracingEnabled: enable)
MasterControllerAdapter.sharedInstance.sendEvent2MasterController(event: event)
}
```

### Android/Kotlin

Enable Tracing (Kotlin)

```
fun triggerConfigurationEvent(
exporterUrl: String?,
username: String?,
password: String?,
serverCertificate: ByteArray?
) {
synchronousEventHandler.postEvent(
ConfigurationEvent(
exporterUrl,
username,
password,
serverCertificate
)
)?.then {
// NOTE: ConfigurationEvent does not have a response event
triggerEnableOpenCensusTracingEvent(true)
}
}
fun triggerEnableOpenCensusTracingEvent(tracingEnabled: Boolean) {
synchronousEventHandler.postEvent((EnableOpenCensusTracingEvent(tracingEnabled)))
// NOTE: EnableOpenCensusTracingEvent does not have a response event
}
```
