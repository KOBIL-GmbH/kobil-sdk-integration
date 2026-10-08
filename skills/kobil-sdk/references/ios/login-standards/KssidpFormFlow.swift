//
//  KssidpFormFlow.swift
//
//  Runs the KSSIDP enrollment ("KSSIDP Enrollment - Multi form flow", kobil-lite theme)
//  natively. The flow spans several HTML pages: user id and activation code, then the
//  temporary password, then the new password. KSSIDP fills only the first page it is offered
//  and silently drops the next one, in single-form and multiflow mode alike, so the pages are
//  posted here instead, over the SDK's own HTTP channel (HeadlessHttpTransport) with the AST
//  headers and the IDP's cookies. The authorisation code at the end is handed to the
//  MasterController by the caller, as for the headless journeys.
//

import Foundation
import os

nonisolated enum KssidpFormError: LocalizedError {
    /// The IDP answered a page with the same page again: a value was refused.
    case rejected(String)
    /// A page asks for something the app has not collected.
    case unknownField(String)
    case noForm(String)
    case tooManyPages
    /// The IDP answered with an error page; already in plain words.
    case idpError(String)

    var errorDescription: String? {
        switch self {
        case .idpError(let message):
            return message
        case .rejected(let detail):
            return "The identity server refused the enrollment: \(detail)"
        case .unknownField(let name):
            return "The identity server asks for \"\(name)\", which this app does not collect."
        case .noForm(let detail):
            return "The identity server sent a page without a form. \(detail)"
        case .tooManyPages:
            return "The enrollment did not finish within the expected number of pages."
        }
    }
}

@MainActor
final class KssidpFormFlow {
    struct Credentials: Sendable {
        let userId: String
        let activationCode: String
        let temporaryPassword: String?
        let newPassword: String
    }

    private enum Page {
        case html(String, url: String)
        case authorisationCode(String)
    }

    private static let log = Logger(subsystem: "com.example.kobilsdk", category: "KSSIDPForm")  // PER APP: your bundle identifier
    private static let maxPages = 8
    private static let maxRedirects = 10

    private let transport: HeadlessHttpTransport
    private let redirectUri: String
    private let headers: [String: String]
    private let credentials: Credentials
    private var cookies: [String: String] = [:]
    private var temporaryPasswordSent = false
    private var postedPages: Set<String> = []
    private var isCancelled = false

    /// `headers` carries X-KOBIL-ASTCLIENTDATA and X-KOBIL-ASTCLIENTID on every request.
    init(transport: HeadlessHttpTransport, redirectUri: String, headers: [String: String], credentials: Credentials) {
        self.transport = transport
        self.redirectUri = redirectUri
        self.headers = headers
        self.credentials = credentials
    }

    /// Walks the flow from the authorisation URL and returns the authorisation code.
    func run(authorizationUrl: String) async throws -> String {
        var page = try await load(url: authorizationUrl, post: nil)
        for _ in 0..<Self.maxPages {
            switch page {
            case .authorisationCode(let code):
                return code
            case .html(let html, let url):
                let (action, body) = try answer(html, pageUrl: url)
                page = try await load(url: action, post: body)
            }
        }
        throw KssidpFormError.tooManyPages
    }

    func cancel() {
        isCancelled = true
        transport.cancel()
    }

    // MARK: Pages

    /// Fills the page's form from the credentials and returns where to post it.
    private func answer(_ html: String, pageUrl: String) throws -> (action: String, body: String) {
        let page = HeadlessHtml(html)
        let errorText = Self.errorText(page)
        guard let form = page.tags(named: "form").first,
              let rawAction = form["action"],
              let action = URL(string: rawAction, relativeTo: URL(string: pageUrl))?.absoluteString
        else {
            throw KssidpFormError.noForm(errorText ?? Self.title(page) ?? "")
        }

        let inputs = page.tags(named: "input").filter { !($0["name"] ?? "").isEmpty }
        let names = inputs.compactMap { $0["name"] }
        // Page 1 and the password page share the form id, so a page is known by its fields too.
        let pageKey = (form["id"] ?? "") + ":" + names.joined(separator: ",")
        if postedPages.contains(pageKey) {
            throw KssidpFormError.rejected(errorText ?? "the page \(form["id"] ?? "") came back unchanged.")
        }
        if let errorText {
            Self.log.info("IDP notice on \(form["id"] ?? "form", privacy: .public): \(errorText, privacy: .public)")
        }

        let asksForNewPassword = names.contains { Self.isNewPasswordField(Self.normalised($0)) }
        var usedTemporaryPassword = false
        var pairs: [(String, String)] = []
        for input in inputs {
            guard let name = input["name"] else { continue }
            let type = (input["type"] ?? "text").lowercased()
            switch type {
            case "hidden":
                pairs.append((name, input["value"] ?? ""))
            case "submit", "button", "reset", "image":
                continue
            case "checkbox", "radio":
                if input["checked"] != nil { pairs.append((name, input["value"] ?? "on")) }
            default:
                let key = Self.normalised(name)
                let value: String?
                if Self.isNewPasswordField(key) {
                    value = credentials.newPassword
                } else if ["currentpassword", "oldpassword", "temporarypassword", "temppassword"].contains(key) {
                    value = credentials.temporaryPassword
                    usedTemporaryPassword = true
                } else if key == "password" || type == "password" {
                    // A lone password field is the temporary password until that has been
                    // verified; on the new-password page it is the new password.
                    if let temporary = credentials.temporaryPassword, !temporaryPasswordSent, !asksForNewPassword {
                        value = temporary
                        usedTemporaryPassword = true
                    } else {
                        value = credentials.newPassword
                    }
                } else if ["username", "userid", "user", "email"].contains(key) {
                    value = credentials.userId
                } else if ["activationcode", "code", "otp"].contains(key) {
                    value = credentials.activationCode
                } else {
                    value = input["value"].flatMap { $0.isEmpty ? nil : $0 }
                }
                guard let value else { throw KssidpFormError.unknownField(name) }
                pairs.append((name, value))
            }
        }
        // A named submit button is part of what a browser posts.
        if let button = page.tags(named: "button").first(where: { !($0["name"] ?? "").isEmpty && ($0["type"] ?? "submit") == "submit" }),
           let name = button["name"] {
            pairs.append((name, button["value"] ?? ""))
        }

        postedPages.insert(pageKey)
        if usedTemporaryPassword { temporaryPasswordSent = true }
        Self.log.info("Posting \(form["id"] ?? "form", privacy: .public) with \(names.joined(separator: ", "), privacy: .public)")
        let body = pairs.map { "\(Self.formEncoded($0.0))=\(Self.formEncoded($0.1))" }.joined(separator: "&")
        return (action, body)
    }

    // MARK: Exchange

    private func load(url: String, post body: String?) async throws -> Page {
        var url = url
        var body = body
        for _ in 0...Self.maxRedirects {
            if isCancelled { throw HeadlessIdpError.cancelled }
            var requestHeaders = headers
            if !cookies.isEmpty {
                requestHeaders["Cookie"] = cookies.map { "\($0.key)=\($0.value)" }.joined(separator: "; ")
            }
            let response = try await transport.send(url: url, post: body, headers: requestHeaders)
            if isCancelled { throw HeadlessIdpError.cancelled }
            guard response.status == .success else {
                throw response.status == .timeout ? HeadlessIdpError.timedOut : HeadlessIdpError.requestFailed("status \(response.status.rawValue)")
            }
            storeCookies(from: response, url: url)
            Self.log.info("KSSIDP form \(body == nil ? "GET" : "POST", privacy: .public) → HTTP \(response.httpStatus, privacy: .public)")

            switch response.httpStatus {
            case 200:
                let html = String(decoding: response.body, as: UTF8.self)
                // response_mode=form_post: the last page is a self-posting form aimed at the redirect URI.
                let page = HeadlessHtml(html)
                if let action = page.formAction(), action.hasPrefix(redirectUri) {
                    return try Self.authorisationCode(page.inputValue(name: "code"),
                                                      error: page.inputValue(name: "error_description") ?? page.inputValue(name: "error"))
                }
                return .html(html, url: url)
            case 301, 302, 303, 307, 308:
                guard let location = response.header("Location"),
                      let next = URL(string: location, relativeTo: URL(string: url))?.absoluteString
                else {
                    throw HeadlessIdpError.unexpectedStatus(response.httpStatus, "The redirect has no location.")
                }
                if next.hasPrefix(redirectUri) {
                    let items = URLComponents(string: next.replacingOccurrences(of: "#", with: "?"))?.queryItems ?? []
                    return try Self.authorisationCode(
                        items.first { $0.name == "code" }?.value,
                        error: items.first { $0.name == "error_description" }?.value ?? items.first { $0.name == "error" }?.value
                    )
                }
                url = next
                body = nil
            default:
                throw KssidpFormError.idpError(IdpErrorText.plain(
                    String(decoding: response.body, as: UTF8.self),
                    fallback: "The identity server refused the enrollment (HTTP \(response.httpStatus))."
                ))
            }
        }
        throw HeadlessIdpError.tooManyRedirects
    }

    private static func authorisationCode(_ code: String?, error: String?) throws -> Page {
        if let code, !code.isEmpty { return .authorisationCode(code) }
        throw HeadlessIdpError.authorisationError(error ?? "no code returned")
    }

    private func storeCookies(from response: HeadlessHttpResponse, url: String) {
        guard let setCookie = response.header("Set-Cookie"), let requestUrl = URL(string: url) else { return }
        for cookie in HTTPCookie.cookies(withResponseHeaderFields: ["Set-Cookie": setCookie], for: requestUrl) {
            if let expiry = cookie.expiresDate, expiry < Date() {
                cookies[cookie.name] = nil
            } else {
                cookies[cookie.name] = cookie.value
            }
        }
    }

    // MARK: Helpers

    private static func normalised(_ name: String) -> String {
        name.lowercased().filter { $0.isLetter || $0.isNumber }
    }

    private static func isNewPasswordField(_ key: String) -> Bool {
        key.contains("password") && (key.contains("new") || key.contains("confirm"))
    }

    /// The text kobil-lite puts in `#error-parameters` (or Keycloak's error page), tags removed.
    private static func errorText(_ page: HeadlessHtml) -> String? {
        for id in ["error-parameters", "kc-error-message", "input-error"] {
            if let raw = page.textOfElement(id: id) {
                let text = raw.replacingOccurrences(of: "<[^>]+>", with: " ", options: .regularExpression)
                    .split(whereSeparator: \.isWhitespace).joined(separator: " ")
                if !text.isEmpty { return String(text.prefix(300)) }
            }
        }
        return nil
    }

    private static func title(_ page: HeadlessHtml) -> String? {
        page.textOfElement(tag: "title").map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.flatMap { $0.isEmpty ? nil : $0 }
    }

    private static func formEncoded(_ value: String) -> String {
        var allowed = CharacterSet.alphanumerics
        allowed.insert(charactersIn: "-._~")
        return value.addingPercentEncoding(withAllowedCharacters: allowed) ?? value
    }
}
