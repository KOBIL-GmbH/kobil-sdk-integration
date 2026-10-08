// Source: Flutter superapp, mini app WebView body (onLoadStop, onReceivedError, onReceivedHttpError, shouldOverrideUrlLoading),
// trimmed. ADDITION: the rules. Print every WebView step to the console, so that a blank page shows its reason. Print URLs
// without their query (state and the authorisation code live there); never print codes, tokens, passwords or cookies.
// Not compiled here.

String loggable(Uri? url) => url == null ? 'null' : url.replace(query: '', fragment: '').toString();

void debugLog(String text) => print('[kobil-debug] $text');

// Pass these to the InAppWebView:
//   onLoadStart: (controller, url) => debugLog('webView loadStart ${loggable(url)}'),
//   onLoadStop: (controller, url) => debugLog('webView loadStop ${loggable(url)}'),
//   onReceivedError: (controller, request, error) =>
//       debugLog('webView error url=${loggable(request.url)} type=${error.type} ${error.description}'),
//   onReceivedHttpError: (controller, request, response) =>
//       debugLog('webView http=${response.statusCode} url=${loggable(request.url)}'),
//   shouldOverrideUrlLoading: (controller, action) async {
//     debugLog('webView navigation ${loggable(action.request.url)}');
//     return NavigationActionPolicy.ALLOW; // CANCEL for the redirect with the code, see setAuthCode
//   },
