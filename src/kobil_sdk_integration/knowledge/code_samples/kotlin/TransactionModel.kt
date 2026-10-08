// Source: GettingStarted (Kotlin), shift flavour, TransactionModel, trimmed to the SDK calls (timer, UI and status texts removed).
// Pushed events (TriggerBannerEvent, DisplayConfirmationRequestEvent) arrive in the listener; the app answers with
// StartTransactionEvent and DisplayConfirmationEvent. These events have no result event of their own: nothing to wait for.
// Not compiled here.
package com.example.app.models

import com.example.app.masterController.EventListener
import com.example.app.masterController.MasterControllerAdapter
import com.kobil.wrapper.events.BannerType
import com.kobil.wrapper.events.DisplayConfirmationEvent
import com.kobil.wrapper.events.DisplayConfirmationRequestEvent
import com.kobil.wrapper.events.DisplayConfirmationResultEvent
import com.kobil.wrapper.events.EventFrameworkEvent
import com.kobil.wrapper.events.StartTransactionEvent
import com.kobil.wrapper.events.TriggerBannerEvent

class TransactionModel : EventListener {

    companion object {
        // this function needs to be called directly after MasterControllerAdapter.init()
        fun init() {
            MasterControllerAdapter.addEventListener(TransactionModel())
        }
    }

    private var startCompletion: ((timer: Int, information: String) -> Unit)? = null

    override fun onEventReceived(event: EventFrameworkEvent?) {
        when (event) {
            is TriggerBannerEvent -> {
                if (event.bannerType == BannerType.TRANSACTION) {
                    // show the banner (event.timer seconds, event.payload), the user may start the transaction
                }
            }
            is DisplayConfirmationRequestEvent -> startCompletion?.invoke(event.timerValue, event.transactionInformation)
            is DisplayConfirmationResultEvent -> { /* update the UI: the transaction is finished */ }
        }
    }

    fun startTransaction(completion: (timer: Int, information: String) -> Unit) {
        startCompletion = completion
        MasterControllerAdapter.getInstance()?.postEvent(StartTransactionEvent())
    }

    fun confirmTransaction(confirmationType: com.kobil.wrapper.events.ConfirmationType, transactionInformation: String) {
        MasterControllerAdapter.getInstance()?.postEvent(DisplayConfirmationEvent(confirmationType, transactionInformation))
    }
}
