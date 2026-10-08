// Source: GettingStarted (Kotlin), shift flavour: GetAstClientDataModel, TrustedWebViewModel (headers), ShiftHelper (header names),
// TrustedWebViewFragment (loadUrl with headers, TWV client, PinningProxy). Trimmed. A bare URL is refused (blank page): the SDK
// delivers the AST client data and the PKCE challenge (GetAstClientData), the URL carries code_challenge and the request carries the
// headers X-KOBIL-ASTCLIENTDATA and X-KOBIL-ASTCLIENTID. Not compiled here.
package com.example.app.webview

import android.webkit.WebView
import com.example.app.masterController.MasterControllerAdapter
import com.kobil.wrapper.events.GetAstClientDataEvent
import com.kobil.wrapper.events.GetAstClientDataResultEvent
import com.kobil.wrapper.events.StatusType

const val X_HEADER_AST_CLIENT_DATA = "X-KOBIL-ASTCLIENTDATA"
const val X_HEADER_AST_CLIENT_ID = "X-KOBIL-ASTCLIENTID"

class WebRequest(val headers: HashMap<String, String>, val codeChallenge: String, val codeChallengeMethod: String)

/** Ask the SDK for the AST client data of the tenant; the reply comes in then { }. */
fun getAstClientData(tenantId: String, completion: (WebRequest?) -> Unit) {
    MasterControllerAdapter.getInstance()?.postEvent(GetAstClientDataEvent(tenantId))?.then { resultEvent ->
        if (resultEvent is GetAstClientDataResultEvent && resultEvent.status == StatusType.OK) {
            val headers = HashMap<String, String>()
            // always needed
            headers[X_HEADER_AST_CLIENT_DATA] = resultEvent.clientData
            // only when a valid value exists (all zeros before the first activation)
            if (!resultEvent.astClientId.isNullOrBlank() && resultEvent.astClientId.toIntOrNull() != 0) {
                headers[X_HEADER_AST_CLIENT_ID] = resultEvent.astClientId
            }
            completion(WebRequest(headers, resultEvent.codeChallenge, resultEvent.codeChallengeMethod))
        } else {
            completion(null)
        }
    }
}

/**
 * authorizationEndpoint comes from sdk_idp_flow_overview / sdk_native_preflight (<host>/auth/realms/<realm>/protocol/openid-connect/auth).
 * The redirect URI must be one the client has registered.
 */
fun authorizationUrl(authorizationEndpoint: String, clientId: String, redirectUri: String, request: WebRequest): String =
    android.net.Uri.parse(authorizationEndpoint).buildUpon()
        .appendQueryParameter("client_id", clientId)
        .appendQueryParameter("redirect_uri", redirectUri)
        .appendQueryParameter("scope", "openid")
        .appendQueryParameter("response_type", "code")
        .appendQueryParameter("code_challenge", request.codeChallenge)
        .appendQueryParameter("code_challenge_method", request.codeChallengeMethod)
        .build().toString()

/** Load the page with the headers (loadUrl(url, headers), not loadUrl(url)) on a WebView that already has the TWV client set. */
fun loadAuthorizationPage(webView: WebView, url: String, request: WebRequest) {
    webView.loadUrl(url, request.headers)
}
