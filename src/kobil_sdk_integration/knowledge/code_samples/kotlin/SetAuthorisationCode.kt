// Source: GettingStarted (Kotlin), shift flavour: TrustedWebViewModel (performSetAuthorisationCodeEvent), trimmed. The WebView
// ends the login by navigating to the redirect URI with &code=...; the app takes the code (the GettingStarted cuts the string, here
// the query parameter is read with Uri, an ADDITION) and hands it to the SDK. The reply SetAuthorisationCodeResultEvent comes in
// then { }. The code is never logged. Not compiled here.
package com.example.app.webview

import com.example.app.masterController.MasterControllerAdapter
import com.kobil.wrapper.events.AuthenticationMode
import com.kobil.wrapper.events.SetAuthorisationCodeEvent
import com.kobil.wrapper.events.SetAuthorisationCodeResultEvent
import com.kobil.wrapper.events.StatusType

/** ADDITION: the code of the redirect URL, or null when it is not the redirect with a code. */
fun authorisationCode(url: String, redirectUri: String): String? {
    if (!url.startsWith(redirectUri)) return null
    return android.net.Uri.parse(url).getQueryParameter("code")?.takeIf { it.isNotEmpty() }
}

fun performSetAuthorisationCodeEvent(
    tenantId: String, authCode: String, clientId: String, mode: AuthenticationMode,
    completion: (ok: Boolean, status: StatusType?) -> Unit
) {
    MasterControllerAdapter.getInstance()?.postEvent(SetAuthorisationCodeEvent(tenantId, mode, authCode, clientId))?.then { resultEvent ->
        when (resultEvent) {
            is SetAuthorisationCodeResultEvent -> {
                android.util.Log.d("kobil-debug", "SetAuthorisationCodeResult status=${resultEvent.status}") // status, never the code
                completion(resultEvent.status == StatusType.OK, resultEvent.status)
            }
            else -> completion(false, null)
        }
    }
}
