// Source: GettingStarted (Swift), Models/TransactionModel/TransactionModel.swift, receive() trimmed to the dispatch; the
// confirm call is the one the GettingStarted sends from its confirmation screen.
import Foundation
import KSMasterController

class TransactionModel: NSObject {
    static let sharedInstance = TransactionModel()

    private override init() {
        super.init()
        MasterControllerAdapter.sharedInstance.masterController?.addDelegate(self)
    }

    /// Answer a KSMDisplayConfirmationRequestEvent after the user decided.
    func confirm(type: KSMConfirmationType, transactionInformation: String) {
        let event = KSMDisplayConfirmationEvent(confirmationType: type, andTransactionInformation: transactionInformation)
        MasterControllerAdapter.sharedInstance.masterController?.receive(event)
    }
}

extension TransactionModel: KSAsyncEventReceiver {
    func receive(_ event: KsEvent, withCompletionHandler completionBlock: ((KsEvent?) -> Void)? = nil) {
        if let triggerBannerEvent = event as? KSMTriggerBannerEvent {
            print("banner: \(triggerBannerEvent)")
        } else if let displayConfirmationRequestEvent = event as? KSMDisplayConfirmationRequestEvent {
            print("confirmation requested: \(displayConfirmationRequestEvent)")
        } else if let displayConfirmationResultEvent = event as? KSMDisplayConfirmationResultEvent {
            print("confirmation result: \(displayConfirmationResultEvent)")
        } else if let transactionFinished = event as? KSMTransactionFinishedEvent {
            print("transaction finished: \(transactionFinished)")
        }
    }
}
