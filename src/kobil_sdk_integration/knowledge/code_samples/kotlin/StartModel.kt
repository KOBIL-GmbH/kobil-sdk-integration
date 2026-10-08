// Source: GettingStarted (Kotlin), StartModel (performStartEvent) and StateMachine (setState for
// StartResultEvent), trimmed. The reply of a request comes back in then { resultEvent -> ... }; check the type and the status.
// Not compiled here.
package com.example.app.models

import com.example.app.masterController.MasterControllerAdapter
import com.kobil.wrapper.events.SdkState
import com.kobil.wrapper.events.StartEvent
import com.kobil.wrapper.events.StartResultEvent
import com.kobil.wrapper.events.StatusType

class StartModel {
    fun start(startEvent: StartEvent, next: (String) -> Unit) {
        MasterControllerAdapter.getInstance()?.postEvent(startEvent)?.then { resultEvent ->
            when (resultEvent) {
                is StartResultEvent -> {
                    if (resultEvent.status == StatusType.OK) {
                        // Continue by SDK state, as the GettingStarted state machine does.
                        when (resultEvent.sdkState) {
                            SdkState.ACTIVATION_REQUIRED, SdkState.UNIDENTIFIED -> next("activation")
                            SdkState.LOGIN_REQUIRED -> next("login")
                            else -> next("other")
                        }
                    } else {
                        next("start failed: ${resultEvent.status}")
                    }
                }
                else -> next("unexpected event: $resultEvent")
            }
        }
    }
}
