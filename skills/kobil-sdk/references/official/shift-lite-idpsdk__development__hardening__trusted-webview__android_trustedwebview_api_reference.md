> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/hardening/trusted-webview/android_trustedwebview_api_reference> on 2026-09-28. Converted to Markdown; wording unchanged.

# Trusted WebView Android API Reference

`PinningProxy` is the main entry point for Trusted WebView on Android. All members are static — accessed via `PinningProxy` directly (Kotlin) or `PinningProxy.Companion` (Java).

---

## Certificate Pinning

### `cp1` — Enable Certificate Pinning

```
PinningProxy.cp1(webView: WebView, certificates: String)
```

Enables certificate pinning for the given WebView using the provided PEM certificate chain.

| Parameter | Description |
| --- | --- |
| `webView` | The `WebView` instance to apply pinning for. |
| `certificates` | One or more PEM-encoded certificates concatenated as a single string. |

**Kotlin:**

```
val pem = assets.open("pinned.pem").bufferedReader().readText()
PinningProxy.cp1(webView, pem)
```

**Java:**

```
String pem = // load PEM string from assets or resources
PinningProxy.Companion.cp1(webView, pem);
```

---

### `cp2` — Disable Certificate Pinning (System Store Fallback)

```
PinningProxy.cp2(webView: WebView, certificates: String)
```

Disables strict certificate pinning and falls back to the system certificate store combined with the provided PEM certificates.

| Parameter | Description |
| --- | --- |
| `webView` | The `WebView` instance to apply the fallback for. |
| `certificates` | Additional PEM-encoded certificates to include alongside system CAs. Pass an empty string if no extra certificates are needed. |

**Kotlin:**

```
val pem = assets.open("ca.pem").bufferedReader().readText()
PinningProxy.cp2(webView, pem)
```

**Java:**

```
String pem = // load PEM string
PinningProxy.Companion.cp2(webView, pem);
```

---

## WebView Client

`TWVClient` is a `WebViewClient` subclass that integrates URL whitelist enforcement, SSL error handling, and proxy authentication into the WebView lifecycle. Set it as the WebView's client before registering with `cp3`.

It requires a `TWVCallBack` implementation to receive navigation and error events.

```
val client = object : TWVClient(myCallBack) {}
webView.webViewClient = client
```

### `setWhiteListUrls`

```
fun setWhiteListUrls(whitelistUrls: List<String>)
```

Restricts WebView navigation to the provided list of allowed URLs. Navigation to any URL not on the list triggers `TWVCallBack.sendOnUrlBlocked`.

```
client.setWhiteListUrls(listOf("https://portal.example.com", "https://login.example.com"))
```

### `withJSCookieEncryption` (optional)

```
fun withJSCookieEncryption(webView: WebView, onlyDecryption: Boolean = false)
```

Enables encryption of JavaScript cookies set via `document.cookie`. When `onlyDecryption` is `true`, existing encrypted cookies can be read by JavaScript but new cookies are not encrypted.

```
client.withJSCookieEncryption(webView)
```

### `withNoPersistentStorage` (optional)

```
fun withNoPersistentStorage(context: Context)
```

Prevents the WebView from writing Local Storage, Session Storage, and blob storage to disk.

```
client.withNoPersistentStorage(this)
```

---

## TWVCallBack

`TWVCallBack` is the interface for receiving events from `TWVClient`. Implement all methods.

| Method | Description |
| --- | --- |
| `sendOnUrlBlocked(url, reason)` | A navigation was blocked. `reason` is `WHITE_LIST_ERROR` or `CERTIFICATE_ERROR`. |
| `sendOnHTTPError(errorCode, errorDescription, failingUrl)` | An HTTP or WebView error occurred while loading a page. |
| `sendOnPageStarted(url)` | Page load started. |
| `sendOnPageFinished(url)` | Page load finished. |
| `sendOnWebPageTitleFetched(title)` | Page title was retrieved. |
| `sendOnSpecialCommand(specialCommand)` | A special command URL was intercepted. |
| `sendWebToNativeCommand(url)` | A web-to-native command URL was intercepted. |
| `sendOpenIdRedirectUriCode(code)` | An OpenID redirect URI was intercepted; contains the authorization code. |
| `sendWebViewAction(url)` | A system action URL was intercepted (e.g. `tel:`, `mailto:`). |

---

## Setup

### `cp3` — Register a WebView

```
PinningProxy.cp3(view: WebView)
```

Registers a WebView with the proxy. Call after setting `webViewClient` and configuring certificate pinning, before loading any URL.

| Parameter | Description |
| --- | --- |
| `view` | The `WebView` instance to register. |

**Kotlin:**

```
PinningProxy.cp3(webView)
```

**Java:**

```
PinningProxy.Companion.cp3(webView);
```

---

### `cp4` — Unregister a WebView

```
PinningProxy.cp4(view: WebView)
```

Removes the WebView from the proxy and clears its session cookies. Call when the WebView is destroyed or the session ends.

| Parameter | Description |
| --- | --- |
| `view` | The `WebView` instance to unregister. |

**Kotlin:**

```
PinningProxy.cp4(webView)
```

**Java:**

```
PinningProxy.Companion.cp4(webView);
```

---

## Cookie Encryption

Do not call cookie encryption functions from the main thread.

### `cp11` — Encrypt and Store a Cookie

```
PinningProxy.cp11(cookieLine: String, hostName: String)
```

Encrypts a cookie and stores the encrypted form.

| Parameter | Description |
| --- | --- |
| `cookieLine` | Cookie in `Set-Cookie` line format: `key=value; Path="/"; ...` |
| `hostName` | The host the cookie belongs to, e.g. `https://www.example.com`. |

```
PinningProxy.cp11("sessionId=abc123; Path=/", "https://www.example.com")
```

---

### `cp12` — Decrypt Cookies

```
PinningProxy.cp12(encryptedCookies: String): String
```

Decrypts cookies previously encrypted by `cp11`. Returns the decrypted cookie string.

| Parameter | Description |
| --- | --- |
| `encryptedCookies` | The encrypted cookie string as retrieved from `CookieManager`. |

```
val cookies = CookieManager.getInstance().getCookie(url)
val decrypted = PinningProxy.cp12(cookies)
```

---

## Configuration

### `cp15` — Set Connection Timeout

```
PinningProxy.cp15(webView: WebView, m: Long)
```

Sets the proxy connection timeout for the given WebView. Default is **15 000 ms**. Pass `-1` to disable the timeout.

| Parameter | Description |
| --- | --- |
| `webView` | The `WebView` instance to configure. |
| `m` | Timeout in milliseconds. Use `-1` for no timeout. |

```
PinningProxy.cp15(webView, 30_000L)
```

---

## Error Codes

The `PinningProxy.ErrorCode` enum describes runtime error categories reported via `runTimeErrorCallBack`.

| Value | Code | Description |
| --- | --- | --- |
| `System` | `0` | System-level error. |
| `Network` | `1` | Network connectivity error. |
| `Security` | `2` | Security or certificate error. |
| `UntrustedSocketConnections` | `3` | Connection to an untrusted socket was attempted. |
| `UNKNOWN` | `-1` | Unrecognized error code. |

---

## Callbacks

### `loggingCallBack`

```
var loggingCallBack: LoggingCallBackInterface?
```

Assign to receive log messages from the proxy.

### `runTimeErrorCallBack`

```
var runTimeErrorCallBack: RunTimeErrorCallBackInterface?
```

Assign to receive runtime error notifications. The callback receives a description string and an `ErrorCode` integer.

---

## Example Flow

A complete setup showing certificate pinning, `TWVClient` with whitelist, a blocked-URL popup, a runtime error alert, WebView registration, and page load.

```
// 1. Load pinned certificate
val pem = assets.open("pinned.pem").bufferedReader().readText()
// 2. Enable certificate pinning
PinningProxy.cp1(webView, pem)
// 3. Build TWVClient with callbacks
val twvCallBack = object : TWVCallBack {
override fun sendOnUrlBlocked(url: String, reason: AstUrlBlockedReason) {}
override fun sendOnHTTPError(errorCode: Int, errorDescription: String, failingUrl: String) {}
override fun sendOnPageStarted(url: String) {}
override fun sendOnPageFinished(url: String) {}
override fun sendOnWebPageTitleFetched(title: String) {}
override fun sendOnSpecialCommand(specialCommand: Pair<KobilSpecialCommands?, String>) {}
override fun sendWebToNativeCommand(url: String) {}
override fun sendOpenIdRedirectUriCode(code: String) {}
override fun sendWebViewAction(url: String) {}
}
val client = object : TWVClient(twvCallBack) {}
client.setWhiteListUrls(listOf("https://portal.example.com"))
webView.webViewClient = client
// 4. Register runtime error callback
PinningProxy.runTimeErrorCallBack = RunTimeErrorCallBackInterface { description, errorCode ->
runOnUiThread {
AlertDialog.Builder(this@MyActivity)
.setTitle("Connection Error")
.setMessage("[$errorCode] $description")
.setPositiveButton("OK", null)
.show()
}
}
// 5. Register WebView and load
PinningProxy.cp3(webView)
webView.loadUrl("https://portal.example.com")
```

Unregister when the WebView is destroyed:

```
override fun onDestroy() {
super.onDestroy()
PinningProxy.cp4(webView)
}
```
