// Source: GettingStarted (Swift), Shift flavour: AstClientDataModel.swift (KSMGetAstClientDataEvent), ShiftHelpers.swift
// (ShiftWebPageHelper, ShiftWebViewUrlRequest), WebViewController (setupTrustedView, load), trimmed.
// What the GettingStarted does and a plain URL does not: the SDK delivers the AST client data and the PKCE challenge
// (GetAstClientData), the authorisation request carries code_challenge and the headers X-KOBIL-ASTCLIENTDATA and
// X-KOBIL-ASTCLIENTID, and the web view loads that URLRequest (not a bare URL string). Without the headers the IDP flow
// (ast-headers-to-session) refuses the page: blank WebView, HTTP 403 for a plain request.
import Foundation
import KSMasterController
import KSTrustedWebView

struct AstClientData {
    var data: String
    var id: String
    var codeChallange: String
    var codeChallangeMethod: String
}

/// Ask the SDK for the AST client data of the tenant. The reply comes through the completion handler.
func getAstClientData(tenantId: String, completion: @escaping (AstClientData?) -> Void) {
    let event = KSMGetAstClientDataEvent(tenantId: tenantId)
    MasterControllerAdapter.sharedInstance.sendEvent2MasterController(event: event) { resultEvent in
        if let clientDataResult = resultEvent as? KSMGetAstClientDataResultEvent, clientDataResult.status == .KSMOK {
            completion(AstClientData(data: clientDataResult.clientData,
                                     id: clientDataResult.astClientId,
                                     codeChallange: clientDataResult.codeChallange,
                                     codeChallangeMethod: clientDataResult.codeChallangeMethod))
        } else {
            print("[kobil-debug] GetAstClientData failed: \(String(describing: resultEvent))")
            completion(nil)
        }
    }
}

enum ShiftWebPageHelper {
    /// IMPORTANT: this value must fit the redirect URIs registered for the client in the IAM system.
    static let redirectUri = "https://kobil/OpenIdRedirectUri"

    /// authorizationEndpoint comes from sdk_idp_flow_overview / sdk_native_preflight (<host>/auth/realms/<realm>/protocol/openid-connect/auth).
    static func authorizationUrl(authorizationEndpoint: String, clientId: String, astData: AstClientData) -> URL? {
        guard var components = URLComponents(string: authorizationEndpoint) else { return nil }
        components.queryItems = [
            .init(name: "client_id", value: clientId),
            .init(name: "redirect_uri", value: redirectUri),
            .init(name: "scope", value: "openid"),
            .init(name: "response_type", value: "code"),
            .init(name: "nonce", value: UUID().uuidString.lowercased().replacingOccurrences(of: "-", with: "")),
            .init(name: "code_challenge", value: astData.codeChallange),
            .init(name: "code_challenge_method", value: astData.codeChallangeMethod),
            .init(name: "state", value: UUID().uuidString.lowercased().replacingOccurrences(of: "-", with: ""))
        ]
        return components.url
    }
}

enum ShiftWebViewUrlRequest {
    static let astClientData = "X-KOBIL-ASTCLIENTDATA"
    static let astClientId = "X-KOBIL-ASTCLIENTID"

    static func request(url: URL, astData: AstClientData) -> URLRequest {
        var request = URLRequest(url: url)
        // The AST client id is all zeros before the first activation: then it is not sent.
        if astData.id != "00000000000000000000000000" {
            request.setValue(astData.id, forHTTPHeaderField: astClientId)
        }
        request.setValue(astData.data, forHTTPHeaderField: astClientData)
        return request
    }
}

/// The web view as the GettingStarted sets it up: certificates to validate the IDP, internal and external whitelist.
/// certsDataForValidation: the PEM/DER data of mc_config iam.trustedSslServerCerts. whiteList: regular expressions of the IDP host.
func makeTrustedWebView(certsDataForValidation: [Data], whiteList: [String]) -> KsTrustedWebView {
    let configuration = KsTrustedWebViewConfiguration()
    configuration.certsDataForValidation = certsDataForValidation
    configuration.urlInternalWhiteList = whiteList
    configuration.urlExternalWhiteList = whiteList
    return KsTrustedWebView.createInstance(with: configuration, frame: .zero)
}

// Load: trustedWebView.load(request)   // the URLRequest with the headers, NOT loadUrl(urlString)
