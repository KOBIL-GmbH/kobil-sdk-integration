// ADDITION (not from the GettingStarted): never wait for a reply without a limit. One request, one answer: the reply, an
// unexpected event or the timeout, whichever comes first, exactly once. Not compiled here.
package com.example.app.models

import android.os.Handler
import android.os.Looper
import com.example.app.masterController.MasterControllerAdapter
import com.kobil.wrapper.events.EventFrameworkEvent
import java.util.concurrent.atomic.AtomicBoolean

fun postEventWithTimeout(event: EventFrameworkEvent, seconds: Long = 30, done: (EventFrameworkEvent?) -> Unit) {
    val finished = AtomicBoolean(false)
    val handler = Handler(Looper.getMainLooper())
    val timeout = Runnable { if (finished.compareAndSet(false, true)) done(null) } // null = timed out
    handler.postDelayed(timeout, seconds * 1000)
    MasterControllerAdapter.getInstance()?.postEvent(event)?.then { resultEvent ->
        if (finished.compareAndSet(false, true)) {
            handler.removeCallbacks(timeout)
            done(resultEvent)
        }
    }
}
