// Source: GettingStarted (Swift), MasterController/MasterControllerAdapter.swift, trimmed to the SDK calls.
import Foundation
import KSMasterController

/// main access to the master controller
class MasterControllerAdapter: KSAsyncEventReceiver {

    static let sharedInstance: MasterControllerAdapter = {
        var sharedInstance = MasterControllerAdapter()
        return sharedInstance
    }()

    /// the master controller instance
    var masterController: (KSAsyncEventReceiver & KSEcoModulInterface & KSEventSource)?

    private init() {
        if masterController == nil {
            masterController = KSMasterControllerFactory.getMasterController(withParmeter: "", andConsumer: self)
        }
    }
}

extension MasterControllerAdapter {
    /// Send a request. The reply of the request (for Start: KSMStartResultEvent) comes back in the completion handler
    /// and nowhere else, so pass a handler for every request that has a result event.
    func sendEvent2MasterController(event: KSMEvent, withCompletionHandler completionBlock: ((KsEvent?) -> Void)? = nil) {
        if masterController != nil {
            masterController?.receive(event, withCompletionHandler: { resultEvent in
                if resultEvent != nil {
                    completionBlock?(resultEvent)
                }
            })
        }
    }

    /// Events the SDK sends on its own arrive here (and at every delegate added with addDelegate).
    func receive(_ event: KsEvent, withCompletionHandler completionBlock: ((KsEvent?) -> Void)? = nil) {
    }
}
