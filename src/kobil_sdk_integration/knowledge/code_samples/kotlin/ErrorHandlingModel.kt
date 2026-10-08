// Source: GettingStarted (Kotlin), models/ErrorHandlingModel.kt, trimmed to the dispatch; the rules are from the official
// error-handling page: a failed request shows in the status of its result event; a wrong event for the SDK state gives
// InvalidStateEvent; a RuntimeErrorEvent is pushed and the SDK restarts itself afterwards, so handle it right away and do not
// wait for the result of the request that was running. Not compiled here.
package com.example.app.models

import com.example.app.masterController.EventListener
import com.example.app.masterController.MasterControllerAdapter
import com.kobil.wrapper.events.EventFrameworkEvent
import com.kobil.wrapper.events.InvalidStateEvent
import com.kobil.wrapper.events.RuntimeErrorEvent
import com.kobil.wrapper.events.WarningEvent

class ErrorHandlingModel : EventListener {

    companion object {
        // this function needs to be called directly after MasterControllerAdapter.init()
        fun init() {
            MasterControllerAdapter.addEventListener(ErrorHandlingModel())
        }
    }

    override fun onEventReceived(event: EventFrameworkEvent?) {
        when (event) {
            is RuntimeErrorEvent -> { /* show or log event.errorCode and event.errorDescription; the SDK restarts itself */ }
            is WarningEvent -> { /* show or log, no state change */ }
            is InvalidStateEvent -> { /* the request did not fit the SDK state: show the possible actions of the current state */ }
        }
    }
}
