> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/invalid-state> on 2026-09-28. Converted to Markdown; wording unchanged.

# Invalid state

If you triggered an event that is not the correct event which master controller is waiting for in that case, master controller returns an invalid-state event in the callback of the event that you have triggered.

i.e. assume you triggered Start event and you received StartLogin event and instead of providing KSMLoginEvent you triggered KSMProvideSetPinEvent. Then you will received KSMInvalidStateEvent.

Invalid-state

```
/// send events to master controller
func sendEvent2MasterController(_ event: KsEvent, withCompletionHandler completionBlock: ((KsEvent?) -> Void)? = nil){
// use extra own concurrent queue to make sure nothing is blocked
self.concurrentQueueSendEvents.async {
// forward event to super event listener, independent of master controller initialization status
self.forwardEvent(event, to: self.superEventListeners)
// if not initialised, then master controller instance is not existing, so return
if self.isInitialized() == false {
return
}
guard let macroEvent = event as? KSMEvent else{return}
// log with a tag to easier find the log later in support cases
Logger.sharedLogger.logInfo(content: "\(self.loggingTag) send event now: \(type(of: macroEvent))",
context: "\(type(of: self)).\(#function)")
// MARK: send event to MC and receive event
self.masterController?.receive(event, withCompletionHandler: { (receivedEvent) in
// log with a tag to easier find the log later in support cases
Logger.sharedLogger.logInfo(content: "\(self.loggingTag) received event: \(type(of: receivedEvent)) (for sent event: \(type(of: macroEvent))",
context: "\(type(of: self)).\(#function)")
self.forwardEvent(event, to: self.eventListeners)
self.forwardEvent(event, to: self.superEventListeners)
Logger.sharedLogger.logInfo(content: "\(1234) receive event in callback: \(type(of: event))",
context: "\(type(of: self)).\(#function)")
if (receivedEvent is KSMInvalidStateEvent){
// Handle invalid state event. If you trigger get state event then you will receive the same event from master controller for which master controller is waiting for.
self.sendEvent2MasterController(KSMGetStateEventEvent()) { _ in
}
}else {
completionBlock?(receivedEvent)
}
})
}
}
```
