> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/implement-interface> on 2026-09-28. Converted to Markdown; wording unchanged.

# Implement MasterController interface (iOS/Swift)

KSAsyncEventReceiver

```
extension MasterControllerAdapter {
func receive(_ event: KsEvent, withCompletionHandler completionBlock: ((KsEvent?) -> Void)? = nil) {
let eventContainer = EventInterface(event: event, interface: "receive", direction: "FromMaster")
LoggingModel.sharedInstance.eventHistory.append(eventContainer)
}
}
```

When events are triggered by the master controller, your app will receive them through this method. It is your adapter's responsibility to pass these events to your controller.
In the controller, you can perform specific functionality based on the received events.
To ensure your class receives events, make sure to register it as a **KSAsyncEventReceiver** delegate. This way, any events triggered by the master controller will be received by your class through this delegate.

```
private init() {
if masterController == nil {
masterController = KSMasterControllerFactory.getMasterController(withParmeter: "", andConsumer: self)
}
}
```
