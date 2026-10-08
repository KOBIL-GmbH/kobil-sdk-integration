// Source: GettingStarted (Kotlin), BaseTrustedWebViewViewModel (PinningProxy.loggingCallBack), trimmed. ADDITION: the rules around it.
// Print the WebView framework's own log and every WebView step to the console (Logcat), so that a blank page shows its reason.
// Print URLs without their query (state and the authorisation code live there); never print codes, tokens, passwords or cookies.
// Not compiled here.
package com.example.app.webview

import android.util.Log

private const val TAG = "kobil-debug"

fun loggable(url: String?): String = url?.substringBefore('?')?.substringBefore('#') ?: "null"

/** Register once, before the first WebView is created. */
fun startPinningProxyLogging() {
    PinningProxy.loggingCallBack = object : LoggingCallBackInterface {
        override fun logMessage(logLevel: Int, logMessage: String) {
            Log.d(TAG, "[TWV] level=$logLevel $logMessage")
        }
    }
}

/** Call from the WebViewClient / TWV client callbacks of the app. */
fun debugPageStarted(url: String?) = Log.d(TAG, "webView pageStarted ${loggable(url)}")
fun debugPageFinished(url: String?) = Log.d(TAG, "webView pageFinished ${loggable(url)}")
fun debugReceivedError(url: String?, errorCode: Int, description: CharSequence?) =
    Log.d(TAG, "webView error url=${loggable(url)} code=$errorCode $description")
fun debugHttpError(url: String?, status: Int) = Log.d(TAG, "webView http=$status url=${loggable(url)}")
