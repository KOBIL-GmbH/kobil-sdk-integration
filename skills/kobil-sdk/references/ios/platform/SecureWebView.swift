//
//  SecureWebView.swift
//  KOBIL SDK reference implementation: SwiftUI host for KsTrustedWebView (KSTrustedWebView
//  framework, TWV 9.7 in MCSDK 15.16). Verified on a device 2026-09-27; see
//  sdk-features.md for what was checked on a device.
//

import KSTrustedWebView
import SwiftUI
import WebKit

struct SecureWebView: UIViewRepresentable {
    /// First page to load; must match `internalHosts`.
    let url: URL
    /// Hosts the view may navigate to inside the app (PER APP).
    var internalHosts: [String]
    /// Hosts handed to the system browser instead (PER APP).
    var externalHosts: [String] = []
    /// Root or intermediate certificates the server chain must end in (PEM file bytes).
    /// Secure browsing blocks every page when this is empty (KS_CERTIFICATE_TRUSTSTORE_PARSING_ERROR).
    let pinnedCertificates: [Data]
    /// `.freeBrowsing` skips the extra pinning; only system trust applies then.
    var browsingMode: KsTrustedWebViewBrowsingMode = .secureBrowsing
    /// Called when the view refuses a URL (not on an allow-list, certificate mismatch, http).
    var onBlocked: (String, KSWEBVIEWERROR) -> Void = { _, _ in }
    /// Called when the page finishes or fails loading.
    var onFinished: ((any Error)?) -> Void = { _ in }

    func makeUIView(context: Context) -> KsTrustedWebView {
        let configuration = KsTrustedWebViewConfiguration()
        configuration.urlInternalWhiteList = internalHosts
        configuration.urlExternalWhiteList = externalHosts
        configuration.certsDataForValidation = pinnedCertificates
        configuration.allowHttpConnection = false
        configuration.browsingMode = browsingMode
        let view = KsTrustedWebView.createInstance(with: configuration, frame: .zero)
        view.delegate = context.coordinator
        view.loadUrl(url.absoluteString)
        return view
    }

    func updateUIView(_ view: KsTrustedWebView, context: Context) {
        context.coordinator.parent = self
    }

    func makeCoordinator() -> Coordinator { Coordinator(parent: self) }

    /// Every KsTrustedWebViewDelegate method is required (the header has no @optional).
    final class Coordinator: NSObject, KsTrustedWebViewDelegate {
        var parent: SecureWebView

        init(parent: SecureWebView) { self.parent = parent }

        func webView(_ webView: KsTrustedWebView, webViewDidFinishLoading error: (any Error)?) {
            parent.onFinished(error)
        }

        func webView(
            _ webView: KsTrustedWebView,
            onURLBlocked url: String?,
            reason: KSWEBVIEWERROR,
            subSystem: NSNumber?,
            errorCode: NSNumber?,
            userInfo: [AnyHashable: Any]?
        ) {
            parent.onBlocked(url ?? "", reason)
        }

        /// External hosts open in the system browser.
        func webView(_ webView: KsTrustedWebView, shouldHandleExternalUrl navigationAction: WKNavigationAction?, decisionHandler: ((Bool) -> Void)?) {
            if let url = navigationAction?.request.url {
                UIApplication.shared.open(url)
            }
            decisionHandler?(false)
        }

        /// Default server-trust evaluation; the pinned certificates are checked by the view itself.
        /// Implement only this form: its async twin has the same Objective-C selector.
        func webView(
            _ webView: KsTrustedWebView,
            didReceive challenge: URLAuthenticationChallenge?,
            completionHandler: (@Sendable (URLSession.AuthChallengeDisposition, URLCredential?) -> Void)?
        ) {
            completionHandler?(.performDefaultHandling, nil)
        }

        func webView(_ webView: KsTrustedWebView, requestMediaCapturePermission type: WKMediaCaptureType, decisionHandler: ((WKPermissionDecision) -> Void)?) {
            decisionHandler?(.deny)
        }

        func webView(_ webView: KsTrustedWebView, shouldDownloadFileFor response: WKNavigationResponse?) -> Bool { false }

        // Not used by this host; kept because the protocol requires them.
        func webView(_ webView: KsTrustedWebView, onUrlSchemeTriggeredWithPayload payload: String?) {}
        func webView(_ webView: KsTrustedWebView, webViewDidStartLoading webViewRequestTriggered: URLRequest?) {}
        func webView(_ webView: KsTrustedWebView, onSpecialCommandTriggered command: KSSPECIALCOMMAND) {}
        func webView(_ webView: KsTrustedWebView, onSpecialCommandTriggered command: KSSPECIALCOMMAND, parameters: [AnyHashable: Any]?) {}
        func webView(_ webView: KsTrustedWebView, onNSURLResponseReceived response: URLResponse?, withError error: (any Error)?) {}
        func webView(_ webView: KsTrustedWebView, onFileDownloadFinished dataPath: String?) {}
        func webView(_ webView: KsTrustedWebView, onFileDownloadProgressCurrentBytes currentBytes: Int64, totalBytes: Int64) {}
        func webView(_ webView: KsTrustedWebView, onEstimatedLoadingProgress percentage: Double) {}
        func webView(_ webView: KsTrustedWebView, didReceiveInformation infoDict: [AnyHashable: Any]?) {}
    }
}
