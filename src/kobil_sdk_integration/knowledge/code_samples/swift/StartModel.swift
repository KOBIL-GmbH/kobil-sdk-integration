// Source: GettingStarted (Swift), Models/StartModel.swift (startMaster), trimmed. The "continue by sdkState" switch is an
// addition (the GettingStarted shows the next screen from its state machine); the SDK state cases are
// .activationRequired, .loginRequired, .loggedIn, .uninitialised, .unidentified (prefix stripped), the status is .KSMOK.
import Foundation
import KSMasterController

enum NextScreen {
    case activation
    case login(users: [KsUserIdentifier])
    case failed(String)
}

class StartModel {
    static let sharedInstance = StartModel()

    func startMaster(startEvent: KSMStartEventEx, completion: @escaping (NextScreen) -> Void) {
        MasterControllerAdapter.sharedInstance.sendEvent2MasterController(event: startEvent) { event in
            if let startResultEvent = event as? KSMStartResultEvent {
                if startResultEvent.status == .KSMOK {
                    switch startResultEvent.sdkState {
                    case .activationRequired, .unidentified, .uninitialised:
                        completion(.activation)
                    case .loginRequired, .loggedIn:
                        completion(.login(users: startResultEvent.userList))
                    @unknown default:
                        completion(.failed("unknown SDK state"))
                    }
                } else {
                    print("Start failed")
                    completion(.failed("Failed with Status \(startResultEvent.status.rawValue)"))
                }
            } else {
                print("unexpected Event")
                completion(.failed("unexpected Event"))
            }
        }
    }
}
