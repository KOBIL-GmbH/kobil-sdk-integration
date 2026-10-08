// Source: GettingStarted (Kotlin), shift flavour, MasterControllerAdapter and EventListener,
// trimmed to the SDK calls (configuration, tracing and logging removed). Not compiled here.
package com.example.app.masterController

import com.kobil.kssidp.wrapper.models.KssIdp
import com.kobil.kssidp.wrapper.models.KssIdpConfig
import com.kobil.wrapper.SynchronousEventHandler
import com.kobil.wrapper.events.EventFrameworkEvent

interface EventListener {
    fun onEventReceived(event: EventFrameworkEvent?)
}

class MasterControllerAdapter : com.kobil.kssidp.wrapper.masterController.EventListener {

    companion object {
        @Volatile
        private var instance: MasterControllerAdapter? = null
        private val listeners: ArrayList<EventListener> = ArrayList()

        /** The SDK instance: send requests with getInstance()?.postEvent(event)?.then { resultEvent -> ... } */
        fun getInstance(): SynchronousEventHandler? {
            return KssIdp.getSdkInstance() ?: throw IllegalArgumentException("KssIdp not initialized. Call init() first.")
        }

        fun init(application: android.app.Application, config: KssIdpConfig) {
            if (instance == null) {
                KssIdp.init(application, config)
                instance ?: MasterControllerAdapter().also {
                    instance = it
                    KssIdp.addEventListener(it)
                }
            }
        }

        fun addEventListener(listener: EventListener) {
            synchronized(listeners) {
                listeners.add(listener)
            }
        }
    }

    /** Events the SDK sends on its own arrive here and go to every listener. */
    override fun onEventReceived(event: EventFrameworkEvent?) {
        synchronized(listeners) {
            listeners.forEach { listener ->
                listener.onEventReceived(event)
            }
        }
    }
}
