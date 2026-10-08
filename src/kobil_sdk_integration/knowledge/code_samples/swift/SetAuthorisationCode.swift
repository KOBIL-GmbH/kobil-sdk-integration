// Source: GettingStarted (Swift), Shift flavour: IdpWebModel (handleNavigationActionPolicyFor, setAuthorizationCode), trimmed.
// The WebView ends the login by navigating to the redirect URI with ?code=...: the app stops that navigation (the decision
// handler of shouldHandleExternalUrl gets false), takes the code and hands it to the SDK with KSMSetAuthorisationCodeEvent. The
// reply KSMSetAuthorisationCodeResultEvent comes through the completion handler. Differences to the GettingStarted: the code is read
// with URLComponents instead of cutting the string (ADDITION), and the code is NEVER printed or logged.
import Foundation
import KSMasterController

enum AuthorisationOutcome {
    case ok
    case failed(status: Int)
    case unexpected
}

/// ADDITION: read the code from the query of the redirect URL.
func authorisationCode(from url: URL, redirectUri: String) -> String? {
    guard url.absoluteString.hasPrefix(redirectUri),
          let items = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems,
          let code = items.first(where: { $0.name == "code" })?.value, !code.isEmpty else { return nil }
    return code
}

/// Send the code to the SDK. clientId is the activation or login client of the WebView; authenticationMode is .password or .biometric.
func setAuthorisationCode(tenantId: String, clientId: String, authenticationMode: KSMAuthenticationMode, code: String,
                          completion: @escaping (AuthorisationOutcome) -> Void) {
    let event = KSMSetAuthorisationCodeEvent(tenantId: tenantId,
                                             authenticationMode: authenticationMode,
                                             authorisationCode: code,
                                             clientId: clientId)
    MasterControllerAdapter.sharedInstance.sendEvent2MasterController(event: event) { resultEvent in
        if let result = resultEvent as? KSMSetAuthorisationCodeResultEvent {
            print("[kobil-debug] SetAuthorisationCodeResult status=\(result.status.rawValue)")   // the status, never the code
            completion(result.status == .KSMOK ? .ok : .failed(status: Int(result.status.rawValue)))
        } else {
            print("[kobil-debug] SetAuthorisationCode: unexpected reply \(String(describing: resultEvent.map { type(of: $0) }))")
            completion(.unexpected)
        }
    }
}

/// Use from KsTrustedWebViewDelegate.webView(_:shouldHandleExternalUrl:decisionHandler:):
///   decisionHandler?(handleRedirect(url: ..., ...))
/// Returns false (stop the navigation) when the URL was the redirect with a code, true for every other URL.
func handleRedirect(url: URL?, redirectUri: String, tenantId: String, clientId: String,
                    authenticationMode: KSMAuthenticationMode, completion: @escaping (AuthorisationOutcome) -> Void) -> Bool {
    guard let url = url, let code = authorisationCode(from: url, redirectUri: redirectUri) else { return true }
    setAuthorisationCode(tenantId: tenantId, clientId: clientId, authenticationMode: authenticationMode, code: code, completion: completion)
    return false
}
