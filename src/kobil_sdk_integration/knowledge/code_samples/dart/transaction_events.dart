// Source: Flutter superapp, transaction cubit and transaction services, trimmed (UI state, JSON model and timer removed).
// Pushed events: TriggerBannerEventT (a transaction is waiting) and DisplayConfirmationRequestEventT (the transaction data).
// The app answers with StartTransactionEventT and DisplayConfirmationEventT. These events have no result event of their
// own: nothing to wait for. Not compiled here.

class TransactionHandler implements EventListener {
  McWrapperApi api;
  TransactionHandler(this.api);

  @override
  bool isSubscribed(EventT event) =>
      event is TriggerBannerEventT || event is DisplayConfirmationRequestEventT;

  @override
  void onEventReceived(EventT event) {
    if (event is TriggerBannerEventT) {
      switch (event.bannerType) {
        case BannerType.transaction:
          api.send(StartTransactionEventT()); // the SDK answers with DisplayConfirmationRequestEventT
          break;
        case BannerType.displayMessage:
          break; // show the message
        default:
          break;
      }
    } else if (event is DisplayConfirmationRequestEventT) {
      // show event.transactionInformation (a JSON string) and event.timerValue seconds to decide
    }
  }

  /// After the user decided.
  void confirm(ConfirmationType confirmationType, String transactionInformation) {
    api.send(DisplayConfirmationEventT(
        confirmationType: confirmationType, transactionInformation: transactionInformation));
  }
}
