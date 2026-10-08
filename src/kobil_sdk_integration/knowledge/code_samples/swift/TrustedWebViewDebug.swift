// ADDITION (not from the GettingStarted): print every callback of the trusted WebView and of the SDK to the console, so a blank
// page or a stalled step shows up in the Xcode console (and in GetConsoleOutput) instead of staying silent. Rules: print the
// event or callback name, the status, error domain, code and description; print URLs without their query (state, code and
// tokens live there); never print codes, tokens, passwords or cookies.
import Foundation
import WebKit
import KSMasterController
import KSTrustedWebView

func debugLog(_ text: String) {
    print("[kobil-debug] \(text)")
}

/// Strip the query so that no authorisation code or state ends up in a log.
func loggable(_ url: URL?) -> String {
    guard let url = url, var parts = URLComponents(url: url, resolvingAgainstBaseURL: false) else { return "nil" }
    parts.query = nil
    parts.fragment = nil
    return parts.string ?? "nil"
}

final class DebugWebViewDelegate: NSObject, KsTrustedWebViewDelegate {
    func webView(_ webView: KsTrustedWebView, onUrlSchemeTriggeredWithPayload payload: String?) {
        debugLog("webView onUrlSchemeTriggered payloadLength=\(payload?.count ?? 0)")
    }

    func webView(_ webView: KsTrustedWebView, webViewDidStartLoading webViewRequestTriggered: URLRequest?) {
        debugLog("webView didStartLoading \(loggable(webViewRequestTriggered?.url))")
    }

    func webView(_ webView: KsTrustedWebView, webViewDidFinishLoading error: Swift.Error?) {
        if let error = error as NSError? {
            debugLog("webView didFinishLoading FAILED domain=\(error.domain) code=\(error.code) \(error.localizedDescription)")
        } else {
            debugLog("webView didFinishLoading ok")
        }
    }

    // The remaining methods are required by the protocol; a debug build declines downloads and external links.
    func webView(_ webView: KsTrustedWebView, shouldHandleExternalUrl navigationAction: WKNavigationAction?, decisionHandler: ((Bool) -> Void)?) {
        debugLog("webView shouldHandleExternalUrl \(loggable(navigationAction?.request.url))")
        decisionHandler?(false)
    }

    func webView(_ webView: KsTrustedWebView, onFileDownloadProgressCurrentBytes currentBytes: Int64, totalBytes: Int64) {}

    func webView(_ webView: KsTrustedWebView, onEstimatedLoadingProgress percentage: Double) {
        debugLog("webView loading \(Int(percentage * 100))%")
    }

    func webView(_ webView: KsTrustedWebView, shouldDownloadFileFor response: WKNavigationResponse?) -> Bool {
        return false
    }

    func webView(_ webView: KsTrustedWebView, didReceiveInformation information: [AnyHashable: Any]?) {
        debugLog("webView didReceiveInformation keys=\(information?.keys.map { "\($0)" } ?? [])")
    }

    func webView(_ webView: KsTrustedWebView, requestMediaCapturePermission type: WKMediaCaptureType, decisionHandler: ((WKPermissionDecision) -> Void)?) {
        debugLog("webView requestMediaCapturePermission denied")
        decisionHandler?(.deny)
    }

    /// Called when the SDK refuses a navigation (whitelist, certificate, scheme). The usual reason for a blank page.
    func webView(_ webView: KsTrustedWebView, onURLBlocked url: String?, reason: KSWEBVIEWERROR, subSystem: NSNumber?, errorCode: NSNumber?, userInfo: [AnyHashable: Any]?) {
        debugLog("webView onURLBlocked url=\(loggable(url.flatMap { URL(string: $0) })) reason=\(reason.rawValue) subSystem=\(subSystem?.intValue ?? -1) errorCode=\(errorCode?.intValue ?? -1)")
    }

    func webView(_ webView: KsTrustedWebView, onNSURLResponseReceived response: URLResponse?, withError error: Swift.Error?) {
        let status = (response as? HTTPURLResponse)?.statusCode ?? -1
        debugLog("webView response url=\(loggable(response?.url)) http=\(status) error=\((error as NSError?).map { "\($0.domain)/\($0.code)" } ?? "none")")
    }

    func webView(_ webView: KsTrustedWebView, onFileDownloadFinished dataPath: String?) {
        debugLog("webView onFileDownloadFinished")
    }

    // Required by the protocol (deprecated variant), kept silent: the variant with parameters below logs.
    func webView(_ webView: KsTrustedWebView, onSpecialCommandTriggered command: KSSPECIALCOMMAND) {}

    /// Required by the protocol. Logging only: hand the challenge back to the default handling, trust is decided by the
    /// certificates in the web view configuration.
    func webView(_ webView: KsTrustedWebView, didReceive challenge: URLAuthenticationChallenge?,
                 completionHandler: ((URLSession.AuthChallengeDisposition, URLCredential?) -> Void)?) {
        debugLog("webView authenticationChallenge host=\(challenge?.protectionSpace.host ?? "nil") method=\(challenge?.protectionSpace.authenticationMethod ?? "nil")")
        completionHandler?(.performDefaultHandling, nil)
    }

    func webView(_ webView: KsTrustedWebView, onSpecialCommandTriggered command: KSSPECIALCOMMAND, parameters: [AnyHashable: Any]?) {
        debugLog("webView onSpecialCommand \(command.rawValue) parameterKeys=\(parameters?.keys.map { "\($0)" } ?? [])")
    }
}

/// Log lines of the WebView framework itself (certificate checks, whitelist decisions, blocked navigations).
final class DebugWebViewLogListener: NSObject, KsTrustedWebViewLogListener {
    func onTwvLog(_ log: String?) {
        debugLog("twv \(log ?? "")")
    }
}

// Register once, before the first web view is created:
//   KsTrustedWebView.setLogListener(DebugWebViewLogListener())
// And keep a strong reference to the delegate (webView.delegate is weak).

/// Same idea for the SDK: log every reply and every pushed event by type, status and error fields, never by content.
func debugLog(event: KsEvent?, via: String) {
    guard let event = event else { debugLog("\(via): nil"); return }
    debugLog("\(via): \(type(of: event))")
}
