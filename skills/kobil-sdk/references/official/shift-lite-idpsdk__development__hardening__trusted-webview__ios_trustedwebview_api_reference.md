> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/hardening/trusted-webview/ios_trustedwebview_api_reference> on 2026-09-28. Converted to Markdown; wording unchanged.

# Trusted WebView iOS API Reference

`KsTrustedWebView` is a `WKWebView` subclass that provides certificate pinning, URL whitelist enforcement, and cookie sharing between SDK components. Configure it with a `KsTrustedWebViewConfiguration` object before creating an instance.

---

## Configuration

### `KsTrustedWebViewConfiguration`

Build a configuration object and pass it to the factory method.

| Property | Type | Description |
| --- | --- | --- |
| `certsDataForValidation` | `NSArray<NSData*>` | DER-encoded certificate data used for certificate validation. |
| `urlInternalWhiteList` | `NSArray` | URLs allowed to load inside the WebView. |
| `urlExternalWhiteList` | `NSArray` | URLs that may be opened outside the WebView (triggers `shouldHandleExternalUrl`). |
| `browsingMode` | `KsTrustedWebViewBrowsingMode` | `SecureBrowsing` (default) — validates against `certsDataForValidation`. `FreeBrowsing` — no certificate validation by TWV. |
| `customUrlSchemes` | `NSArray<NSString*>` | Custom URL schemes to intercept (triggers `onUrlSchemeTriggeredWithPayload`). |
| `allowHttpConnection` | `BOOL` | Allow plain HTTP connections. Default `NO`. |
| `allowsInlineMediaPlayback` | `BOOL` | Enable inline media playback. Default `NO`. |
| `mimeTypesToDownload` | `NSArray` | MIME types that trigger a file download callback instead of rendering. |

**Objective-C:**

```
KsTrustedWebViewConfiguration *config = [[KsTrustedWebViewConfiguration alloc] init];
NSData *certData = [NSData dataWithContentsOfFile:[[NSBundle mainBundle] pathForResource:@"pinned" ofType:@"der"]];
config.certsDataForValidation = @[certData];
config.urlInternalWhiteList = @[@"https://portal.example.com", @"https://login.example.com"];
config.browsingMode = KsTrustedWebViewBrowsingModeSecureBrowsing;
```

**Swift:**

```
let config = KsTrustedWebViewConfiguration()
let certURL = Bundle.main.url(forResource: "pinned", withExtension: "der")!
config.certsDataForValidation = [try! Data(contentsOf: certURL)]
config.urlInternalWhiteList = ["https://portal.example.com", "https://login.example.com"]
config.browsingMode = .secureBrowsing
```

---

## Creating an Instance

### `createInstanceWithConfiguration:frame:`

```
+ (KsTrustedWebView *)createInstanceWithConfiguration:(KsTrustedWebViewConfiguration *)configuration
frame:(CGRect)frame;
```

Factory method that creates and returns a configured `KsTrustedWebView` instance.

**Objective-C:**

```
KsTrustedWebView *webView = [KsTrustedWebView createInstanceWithConfiguration:config
frame:self.view.bounds];
webView.delegate = self;
[self.view addSubview:webView];
```

**Swift:**

```
let webView = KsTrustedWebView.createInstance(with: config, frame: view.bounds)
webView.delegate = self
view.addSubview(webView)
```

### `createInstanceWithConfiguration:dataStore:frame:`

```
+ (KsTrustedWebView *)createInstanceWithConfiguration:(KsTrustedWebViewConfiguration *)configuration
dataStore:(WKWebsiteDataStore *)dataStore
frame:(CGRect)frame;
```

Use this variant to supply a custom `WKWebsiteDataStore`, for example to share cookies across multiple WebView instances.

**Objective-C:**

```
WKWebsiteDataStore *sharedStore = [WKWebsiteDataStore nonPersistentDataStore];
KsTrustedWebView *webView = [KsTrustedWebView createInstanceWithConfiguration:config
dataStore:sharedStore
frame:self.view.bounds];
```

**Swift:**

```
let sharedStore = WKWebsiteDataStore.nonPersistent()
let webView = KsTrustedWebView.createInstance(with: config, dataStore: sharedStore, frame: view.bounds)
```

---

## Loading URLs

### `loadUrl:`

```
- (void)loadUrl:(NSString *)URL;
```

Loads the given URL string.

**Objective-C:**

```
[webView loadUrl:@"https://portal.example.com"];
```

**Swift:**

```
webView.loadUrl("https://portal.example.com")
```

---

## Delegate

Set `webView.delegate` to an object conforming to `KsTrustedWebViewDelegate` to receive navigation, error, and security events.

| Method | Description |
| --- | --- |
| `webView:webViewDidStartLoading:` | Page load started. |
| `webView:webViewDidFinishLoading:` | Page load finished. `error` is `nil` on success. |
| `webView:onURLBlocked:reason:subSystem:errorCode:userInfo:` | A navigation was blocked. See `KSWEBVIEWERROR` for reason codes. |
| `webView:onSpecialCommandTriggered:parameters:` | A special command was triggered. See `KSSPECIALCOMMAND`. Use this variant; the parameterless `webView:onSpecialCommandTriggered:` is deprecated. |
| `webView:onUrlSchemeTriggeredWithPayload:` | A custom URL scheme was triggered. |
| `webView:didReceiveAuthenticationChallenge:completionHandler:` | An authentication challenge was received (e.g. HTTP Basic Auth). |
| `webView:shouldHandleExternalUrl:decisionHandler:` | A URL in the external whitelist was triggered. Call the decision handler with `YES` to allow or `NO` to block. |
| `webView:onNSURLResponseReceived:withError:` | Response received for a request. |
| `webView:onFileDownloadFinished:` | A file download completed. `dataPath` is the path to the saved file. |
| `webView:onFileDownloadProgressCurrentBytes:totalBytes:` | File download progress update. |
| `webView:onEstimatedLoadingProgress:` | Page load progress as a percentage (0.0–1.0). |
| `webView:shouldDownloadFileForResponse:` | Return `YES` to trigger a file download for the given response. |
| `webView:didReceiveInformation:` | Informational events (non-error), mainly for debugging. |
| `webView:requestMediaCapturePermission:decisionHandler:` | Camera or microphone access requested. iOS 15+. |

---

## Error Codes

`KSWEBVIEWERROR` is reported in `onURLBlocked:reason:`.

| Value | Description |
| --- | --- |
| `KS_CALLED_URL_NOT_IN_URL_WHITELISTS` | URL not found in any configured whitelist. |
| `KS_CERTIFICATE_ERROR` | Request blocked due to a certificate validation failure. |
| `KS_CERTIFICATE_TRUSTSTORE_PARSING_ERROR` | Failed to parse the certificates provided in configuration. |
| `KS_SERVER_CERTS_PARSE_ERROR` | Failed to parse the certificate received from the server. |
| `KS_UNHANDLED_SHOW_EXTERNAL_URL_CALLBACK` | External URL callback was not implemented. |
| `KS_UNHANDLED_SPECIAL_COMMAND` | A special command was triggered but not handled. |
| `KS_INSECURE_HTTP_CONNECTION` | A plain HTTP connection was attempted and `allowHttpConnection` is `NO`. |
| `KS_CALLED_URL_DOES_NOT_MATCH_SERVER_CERTIFICATE` | The server certificate does not match the requested URL. |
| `KS_BASICAUTH_CREDENTIALS_WRONG` | HTTP Basic Auth credentials were rejected. |

---

## Browsing Mode

| Value | Description |
| --- | --- |
| `KsTrustedWebViewBrowsingModeSecureBrowsing` | Only connections validated against `certsDataForValidation` are allowed. Default. |
| `KsTrustedWebViewBrowsingModeFreeBrowsing` | No certificate validation by TWV. Relies on ATS and system trust. |

---

## Additional Instance Methods

### `loadRequest:`

```
- (WKNavigation *)loadRequest:(NSURLRequest *)request;
```

Loads an `NSURLRequest`. Use this instead of `loadUrl:` when you need to set custom HTTP headers or other request properties.

**Objective-C:**

```
NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:[NSURL URLWithString:@"https://portal.example.com"]];
[request setValue:@"MyApp/1.0" forHTTPHeaderField:@"User-Agent"];
[webView loadRequest:request];
```

**Swift:**

```
var request = URLRequest(url: URL(string: "https://portal.example.com")!)
request.setValue("MyApp/1.0", forHTTPHeaderField: "User-Agent")
webView.loadRequest(request)
```

### `getHTMLContent` / `getHTMLContentCompletionHandler:`

```
- (NSString *)getHTMLContent;
- (void)getHTMLContentCompletionHandler:(void (^)(NSString *htmlContent, NSError *error))completionHandler;
```

Returns the HTML source of the currently loaded page. Use the completion handler variant for reliable results after page load.

**Swift:**

```
webView.getHTMLContentCompletionHandler { html, error in
guard let html = html else { return }
print(html)
}
```

### `getState`

```
- (KsTrustedWebViewState)getState;
```

Returns the current state of the TWV instance. See [WebView State](#webview-state).

### `hasEverLoadedAnURL`

```
- (BOOL)hasEverLoadedAnURL;
```

Returns `YES` if the instance has successfully loaded at least one URL since creation.

### `getVersionString`

```
+ (NSString *)getVersionString;
```

Returns the framework version string.

**Objective-C:**

```
NSString *version = [KsTrustedWebView getVersionString];
```

**Swift:**

```
let version = KsTrustedWebView.getVersionString()
```

### `getKsCookieSharingManager`

```
- (id<KsCookieSharingManager>)getKsCookieSharingManager;
```

Returns the cookie sharing manager for this instance, which can be used to share cookies with other SDK components.

---

## WebView State

`KsTrustedWebViewState` is returned by `getState`.

| Value | Description |
| --- | --- |
| `KsTrustedWebViewStateDefault` | Normal operating state. |
| `KsTrustedWebViewStateHttpBasicAuthInProgress` | An HTTP Basic Auth challenge is currently in progress. |

---

## Logging

Logging is controlled via `KsTwvLog`.

```
+ (void)setLogLevel:(KsTwvLogLevel)logLevel;
+ (void)setLogListener:(id<KsTrustedWebViewLogListener>)logListener;
```

| Log Level | Description |
| --- | --- |
| `KsTwvLogLevelDebug` | Most verbose. |
| `KsTwvLogLevelInformative` | Informational messages. |
| `KsTwvLogLevelWarning` | Warnings. |
| `KsTwvLogLevelError` | Errors only. |

**Objective-C:**

```
[KsTwvLog setLogLevel:KsTwvLogLevelDebug];
[KsTwvLog setLogListener:self];
```

**Swift:**

```
KsTwvLog.setLogLevel(.debug)
KsTwvLog.setLogListener(self)
```

Implement the `KsTrustedWebViewLogListener` protocol:

```
- (void)onTwvLog:(NSString *)log {
NSLog(@"[TWV] %@", log);
}
```

```
func onTwvLog(_ log: String?) {
print("[TWV]", log ?? "")
}
```

---

## Example Flow

A complete setup showing configuration, delegate, blocked-URL alert, and page load.

**Swift:**

```
// 1. Configure
let config = KsTrustedWebViewConfiguration()
let certURL = Bundle.main.url(forResource: "pinned", withExtension: "der")!
config.certsDataForValidation = [try! Data(contentsOf: certURL)]
config.urlInternalWhiteList = ["https://portal.example.com"]
config.browsingMode = .secureBrowsing
// 2. Create instance
let webView = KsTrustedWebView.createInstance(with: config, frame: view.bounds)
webView.delegate = self
view.addSubview(webView)
// 3. Load
webView.loadUrl("https://portal.example.com")
```

**Delegate implementation (Swift):**

```
extension MyViewController: KsTrustedWebViewDelegate {
func webView(_ webView: KsTrustedWebView, webViewDidStartLoading request: URLRequest?) {}
func webView(_ webView: KsTrustedWebView, webViewDidFinishLoading error: Error?) {
if let error = error { print("Load error:", error) }
}
func webView(_ webView: KsTrustedWebView, onURLBlocked url: String?,
reason: KSWEBVIEWERROR, subSystem: NSNumber?,
errorCode: NSNumber?, userInfo: [AnyHashable: Any]?) {
let alert = UIAlertController(
title: "Navigation Blocked",
message: "Access to \(url ?? "unknown") is not allowed.",
preferredStyle: .alert
)
alert.addAction(UIAlertAction(title: "OK", style: .default))
present(alert, animated: true)
}
func webView(_ webView: KsTrustedWebView, onSpecialCommandTriggered command: KSSPECIALCOMMAND,
parameters: [AnyHashable: Any]?) {}
func webView(_ webView: KsTrustedWebView, onUrlSchemeTriggeredWithPayload payload: String?) {}
func webView(_ webView: KsTrustedWebView, didReceiveAuthenticationChallenge challenge: URLAuthenticationChallenge,
completionHandler: ((URLSession.AuthChallengeDisposition, URLCredential?) -> Void)?) {
completionHandler?(.performDefaultHandling, nil)
}
func webView(_ webView: KsTrustedWebView, shouldHandleExternalUrl navigationAction: WKNavigationAction,
decisionHandler: ((Bool) -> Void)?) {
decisionHandler?(false)
}
func webView(_ webView: KsTrustedWebView, onNSURLResponseReceived response: URLResponse?, withError error: Error?) {}
func webView(_ webView: KsTrustedWebView, onFileDownloadFinished dataPath: String?) {}
func webView(_ webView: KsTrustedWebView, onFileDownloadProgressCurrentBytes currentBytes: Int64, totalBytes: Int64) {}
func webView(_ webView: KsTrustedWebView, onEstimatedLoadingProgress percentage: Double) {}
func webView(_ webView: KsTrustedWebView, shouldDownloadFileForResponse response: WKNavigationResponse) -> Bool {
return false
}
func webView(_ webView: KsTrustedWebView, didReceiveInformation infoDict: [AnyHashable: Any]?) {}
@available(iOS 15.0, *)
func webView(_ webView: KsTrustedWebView, requestMediaCapturePermission type: WKMediaCaptureType,
decisionHandler: ((WKPermissionDecision) -> Void)?) {
decisionHandler?(.prompt)
}
}
```
