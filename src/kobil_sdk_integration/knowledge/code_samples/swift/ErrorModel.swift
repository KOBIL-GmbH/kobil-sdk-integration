// Source: GettingStarted (Swift), Models/ErrorModel/ErrorModel.swift, trimmed (logging and localisation removed).
// Rules from the official error-handling page: a failed request shows in the status of its result event; a wrong event for
// the SDK state gives KSMInvalidStateEvent; a KSMErrorRuntimeEvent is pushed and the SDK restarts itself afterwards, so
// handle it right away and do not wait for the result of the request that was running.
import Foundation
import KSMasterController

class ErrorModel: NSObject {
    static let sharedInstance = ErrorModel()

    /// Set by the app to show or log a problem.
    var onError: (Error) -> Void = { _ in }

    private override init() {
        super.init()
        MasterControllerAdapter.sharedInstance.masterController?.addDelegate(self)
    }

    func handleInvalidState(invalidState: KSMInvalidStateEvent) {
        let error = Error(errorType: .invalidState, description: "not allowed event was triggered", errorCode: -1)
        print("the performed action was not allowed in this state of the master controller")
        onError(error)
    }
}

extension ErrorModel: KSAsyncEventReceiver {
    func receive(_ event: KsEvent, withCompletionHandler completionBlock: ((KsEvent?) -> Void)? = nil) {
        if let warningEvent = event as? KSMWarningEvent {
            onError(Error(errorType: .warning,
                          description: warningEvent.errorDescription,
                          errorCode: Int(warningEvent.errorCode)))
        } else if let errorRuntimeEvent = event as? KSMErrorRuntimeEvent {
            onError(Error(errorType: .runtimeError,
                          description: errorRuntimeEvent.errorDescription,
                          errorCode: Int(errorRuntimeEvent.errorCode)))
        } else if let errorFatalEvent = event as? KSMErrorFatalEvent {
            onError(Error(errorType: .fatal,
                          description: errorFatalEvent.errorDescription,
                          errorCode: Int(errorFatalEvent.errorCode)))
        } else if let invalidState = event as? KSMInvalidStateEvent {
            handleInvalidState(invalidState: invalidState)
        }
    }
}

struct Error {
    var errorType: ErrorType
    var description: String
    var errorCode: Int
}

enum ErrorType {
    case warning
    case runtimeError
    case fatal
    case invalidState
}
