//
//  HeadlessIdpFlow.swift
//  KOBIL SDK iOS reference implementation (verified on a device 2026-09-26)
//
//  A native client for the IDP's multi-page headless-v2 journeys (`kobil-headless-v2` theme):
//  the self-service email + emailed-code registration, first login and forgot-password
//  journeys. Use it for first activation when the realm activates devices that way.
//
//  KSSIDP cannot run these journeys: it parses every page as strict XML and silently drops the
//  second page of a Keycloak flow. This engine does what KOBIL's `headless_v2`
//  feature does instead. Every request goes through the SDK's KSMCreateHttpCommonRequestEvent
//  (so the trusted certificate still applies), each page's `jsonInput` step is read and drawn
//  natively, answers are posted back page after page with the IDP's cookies, and the final
//  authorisation code is handed to the MasterController with KSMSetAuthorisationCodeEvent.
//  The wiring into MasterControllerSession is in README.md, "Email-code activation".
//

import Foundation
import os

// MARK: - Page model

/// A localised text as the IDP sends it: `{"en": "...", "de": "...", "tr": "..."}`.
nonisolated struct HeadlessText: Sendable, Equatable {
    let translations: [String: String]

    init?(_ value: Any?) {
        guard let map = value as? [String: Any] else { return nil }
        var translations: [String: String] = [:]
        for (language, text) in map {
            if let text = text as? String { translations[language] = text }
        }
        self.translations = translations
    }

    /// The device language, then English, then any non-empty translation.
    var localized: String {
        let language = Locale.current.language.languageCode?.identifier ?? "en"
        for candidate in [language, "en"] {
            if let text = translations[candidate], !text.isEmpty { return text }
        }
        return translations.values.first { !$0.isEmpty } ?? ""
    }
}

/// One input of a headless step.
nonisolated struct HeadlessField: Sendable, Equatable, Identifiable {
    enum Kind: String, Sendable {
        case text, password, otp, displayText, changeText, button
        case unsupported
    }

    let key: String
    let kind: Kind
    /// The raw type string, kept so an unsupported field can be named in a message.
    let rawType: String
    let keyboardType: String?
    let title: String
    let placeholder: String
    let initialValue: String
    let isOptional: Bool
    let isEditable: Bool
    let minLength: Int?
    let maxLength: Int?
    let pattern: String?
    let errorTitle: String?
    let errorMessage: String?
    /// Seconds until the "resend code" action becomes available; nil when the step has none.
    let resendWaitSeconds: Int?
    let resendButtonText: String?
    let resendTimerText: String?
    /// The action a `button` input offers, such as "forgotPassword".
    let actionButton: HeadlessButton?

    var id: String { key }

    /// Whether the user has to type something before the step can be submitted.
    var requiresInput: Bool {
        switch kind {
        case .text, .password, .otp, .changeText: return isEditable && !isOptional
        case .displayText, .button, .unsupported: return false
        }
    }

    /// Checks a value against the step's own rules and returns the IDP's message if it fails.
    func validationMessage(for value: String) -> String? {
        guard kind != .displayText, kind != .button else { return nil }
        if value.isEmpty {
            return requiresInput ? (errorMessage ?? "\(title) is required.") : nil
        }
        if let minLength, value.count < minLength { return errorMessage ?? "\(title) is too short." }
        if let maxLength, maxLength > 0, value.count > maxLength { return errorMessage ?? "\(title) is too long." }
        if let pattern, !pattern.isEmpty,
           let expression = try? NSRegularExpression(pattern: pattern),
           expression.firstMatch(in: value, range: NSRange(value.startIndex..., in: value)) == nil {
            return errorMessage ?? "\(title) is not valid."
        }
        return nil
    }
}

/// A button the step offers, such as the submit button or "resend email".
nonisolated struct HeadlessButton: Sendable, Equatable {
    let action: String
    let title: String

    init(action: String, title: String) {
        self.action = action
        self.title = title
    }

    init?(_ value: Any?) {
        guard let button = value as? [String: Any], let action = button["action"] as? String else { return nil }
        self.init(action: action, title: HeadlessText(button["text"])?.localized ?? action)
    }
}

/// A message the IDP put into the page's `error-msg` paragraph.
nonisolated struct HeadlessPageMessage: Sendable, Equatable {
    let code: String?
    let title: String
    let message: String
    let isSevere: Bool
    /// What the IDP offers next, e.g. "login" when the email already belongs to an account.
    let buttons: [HeadlessButton]

    var displayText: String {
        [title, message].filter { !$0.isEmpty }.joined(separator: ": ")
    }
}

/// One rendered step of a headless journey. The raw JSON is kept because the answer is the
/// same document posted back with values filled in.
nonisolated struct HeadlessForm: Sendable, Equatable {
    let formId: String
    let title: String
    let description: String
    let fields: [HeadlessField]
    let buttons: [HeadlessButton]
    fileprivate let rawStep: Data
    /// Distinguishes two servings of the same step, e.g. after a rejected code.
    let serial: UUID

    var submitButton: HeadlessButton? { buttons.first { $0.action == "submit" } }
    var offersResendEmail: Bool { buttons.contains { $0.action == "resendEmail" } }
    var otpField: HeadlessField? { fields.first { $0.kind == .otp } }
    var unsupportedFields: [HeadlessField] {
        fields.filter { $0.kind == .unsupported && !$0.isOptional }
    }

    fileprivate init?(json: Data) {
        guard let step = (try? JSONSerialization.jsonObject(with: json)) as? [String: Any] else { return nil }
        formId = step["formId"] as? String ?? ""
        title = HeadlessText(step["formDisplayTitle"])?.localized ?? ""
        description = HeadlessText(step["formDescription"])?.localized ?? ""
        fields = (step["formInputs"] as? [[String: Any]] ?? []).compactMap(Self.field(from:))
        buttons = (step["formDisplayButtons"] as? [Any] ?? []).compactMap(HeadlessButton.init)
        rawStep = json
        serial = UUID()
    }

    private static func field(from input: [String: Any]) -> HeadlessField? {
        guard let key = input["key"] as? String, !key.isEmpty else { return nil }
        let rawType = input["type"] as? String ?? "text"
        let attributes = input["attributes"] as? [String: Any] ?? [:]
        let error = input["error"] as? [String: Any]
        let resend = attributes["resendCodeModel"] as? [String: Any]
        let kind = HeadlessField.Kind(rawValue: rawType) ?? .unsupported
        return HeadlessField(
            key: key,
            kind: kind,
            rawType: rawType,
            keyboardType: input["keyboardType"] as? String,
            title: HeadlessText(input["name"])?.localized ?? key,
            placeholder: HeadlessText(input["placeholder"])?.localized ?? "",
            initialValue: input["value"] as? String ?? "",
            isOptional: attributes["optional"] as? Bool ?? false,
            isEditable: attributes["editable"] as? Bool ?? true,
            minLength: attributes["minLength"] as? Int,
            maxLength: attributes["maxLength"] as? Int,
            pattern: attributes["regex"] as? String,
            errorTitle: HeadlessText(error?["title"])?.localized,
            errorMessage: HeadlessText(error?["errorMessage"])?.localized,
            resendWaitSeconds: kind == .otp ? (resend?["timer"] as? Int ?? 90) : nil,
            resendButtonText: HeadlessText(resend?["resendButtonText"])?.localized,
            resendTimerText: HeadlessText(resend?["resendTimerText"])?.localized,
            actionButton: HeadlessButton(attributes["actionButton"])
        )
    }

    /// The answer to this step: the served document with values, the pressed button and
    /// optionally a resend request filled in, as the `jsonInput` form field.
    fileprivate func answer(values: [String: String], action: String, resendKey: String?, onlyKeys: Set<String>?) -> Data? {
        guard var step = (try? JSONSerialization.jsonObject(with: rawStep)) as? [String: Any] else { return nil }

        var inputs = step["formInputs"] as? [[String: Any]] ?? []
        if let onlyKeys {
            inputs = inputs.filter { ($0["key"] as? String).map(onlyKeys.contains) ?? false }
        }
        for index in inputs.indices {
            guard let key = inputs[index]["key"] as? String else { continue }
            if let value = values[key], inputs[index]["type"] as? String != "button" {
                inputs[index]["value"] = value
            }
            if key == resendKey {
                var attributes = inputs[index]["attributes"] as? [String: Any] ?? [:]
                var resend = attributes["resendCodeModel"] as? [String: Any] ?? [:]
                resend["resend"] = true
                attributes["resendCodeModel"] = resend
                inputs[index]["attributes"] = attributes
            }
        }
        step["formInputs"] = inputs

        // The step is answered by reporting which of its buttons was pressed.
        var buttons = step["formDisplayButtons"] as? [[String: Any]] ?? []
        for index in buttons.indices { buttons[index]["isClicked"] = false }
        if let index = buttons.firstIndex(where: { $0["action"] as? String == action }) ?? buttons.indices.first {
            buttons[index]["isClicked"] = true
            buttons[index]["key"] = action
        }
        step["formDisplayButtons"] = buttons

        return try? JSONSerialization.data(withJSONObject: step)
    }
}

// MARK: - HTTP through the MasterController

/// One HTTP exchange's result, reduced to Sendable values.
nonisolated struct HeadlessHttpResponse: Sendable {
    let status: KSMCreateHttpCommonRequestStatus
    let httpStatus: Int
    let body: Data
    let headers: [String: String]

    init(_ event: KSMCreateHttpCommonRequestResultEvent) {
        status = event.status
        httpStatus = Int(event.httpStatus)
        body = event.response
        var headers: [String: String] = [:]
        for (rawKey, rawValue) in event.responseHeaders {
            let key = String(describing: rawKey)
            if let values = rawValue as? [Any] {
                headers[key] = values.map { String(describing: $0) }.joined(separator: ", ")
            } else {
                headers[key] = String(describing: rawValue)
            }
        }
        self.headers = headers
    }

    func header(_ name: String) -> String? {
        headers.first { $0.key.caseInsensitiveCompare(name) == .orderedSame }?.value
    }
}

nonisolated enum HeadlessIdpError: LocalizedError {
    case requestFailed(String)
    case timedOut
    case unexpectedStatus(Int, String)
    case unreadablePage(String)
    case idpMessage(HeadlessPageMessage)
    case authorisationError(String)
    case tooManyRedirects
    case cancelled

    var errorDescription: String? {
        switch self {
        case .requestFailed(let reason):
            return "The identity server could not be reached (\(reason))."
        case .timedOut:
            return "The identity server did not answer in time. Check the connection and try again."
        case .unexpectedStatus(let status, let detail):
            return "The identity server answered HTTP \(status). \(detail)"
        case .unreadablePage(let detail):
            return "The identity server sent a page this app cannot read. \(detail)"
        case .idpMessage(let message):
            return message.displayText
        case .authorisationError(let detail):
            return "The identity server refused the sign-in: \(detail)"
        case .tooManyRedirects:
            return "The identity server redirected too many times."
        case .cancelled:
            return "Cancelled."
        }
    }
}

/// Sends KSMCreateHttpCommonRequestEvent one at a time and awaits its result. The result can
/// arrive through the send's completion handler or the global event receiver; the first wins.
@MainActor
final class HeadlessHttpTransport {
    typealias Controller = any KSAsyncEventReceiver & KSEcoModulInterface & KSEventSource

    private let controller: Controller
    private let certificate: Data
    private var pending: CheckedContinuation<HeadlessHttpResponse, any Error>?
    private var pendingTimeout: Task<Void, Never>?
    private static let timeoutSeconds: UInt64 = 60

    init(controller: Controller, certificate: Data) {
        self.controller = controller
        self.certificate = certificate
    }

    func send(url: String, post body: String?, headers: [String: String]) async throws -> HeadlessHttpResponse {
        precondition(pending == nil, "One headless request at a time")
        let event = KSMCreateHttpCommonRequestEvent(
            followRedirect: false,
            fullUrl: url,
            httpMethod: body == nil ? .get : .post,
            content: body ?? "",
            contentType: "application/x-www-form-urlencoded",
            userName: "",
            password: "",
            certificate: certificate,
            httpHeaders: headers,
            cookieIdentifier: ""
        )
        return try await withCheckedThrowingContinuation { continuation in
            pending = continuation
            pendingTimeout = Task { [weak self] in
                try? await Task.sleep(nanoseconds: Self.timeoutSeconds * 1_000_000_000)
                guard !Task.isCancelled else { return }
                self?.finish(.failure(HeadlessIdpError.timedOut))
            }
            let deliver = deliverOnMainActor()
            controller.receive(event) { result in
                guard let result = result as? KSMCreateHttpCommonRequestResultEvent else { return }
                deliver(HeadlessHttpResponse(result))
            }
        }
    }

    /// A Sendable entry point the SDK's threads can use to reach this transport.
    private func deliverOnMainActor() -> @Sendable (HeadlessHttpResponse) -> Void {
        { [weak self] response in
            let transport = self
            Task { @MainActor in transport?.deliver(response) }
        }
    }

    /// Hands over a result the global event receiver saw.
    func deliver(_ response: HeadlessHttpResponse) {
        finish(.success(response))
    }

    func cancel() {
        finish(.failure(HeadlessIdpError.cancelled))
    }

    private func finish(_ result: Result<HeadlessHttpResponse, any Error>) {
        guard let continuation = pending else { return }
        pending = nil
        pendingTimeout?.cancel()
        pendingTimeout = nil
        continuation.resume(with: result)
    }
}

// MARK: - The journey

/// Runs one headless journey from its authorisation URL to the authorisation code.
@MainActor
final class HeadlessIdpFlow {
    enum Step: Sendable {
        /// The IDP rendered a step; `message` is a non-severe notice such as a wrong code.
        case form(HeadlessForm, message: HeadlessPageMessage?)
        /// The journey ended at the redirect URI with this authorisation code.
        case authorisationCode(String)
    }

    private static let log = Logger(subsystem: "com.example.kobilsdk", category: "HeadlessIdp")  // PER APP
    private static let maxRedirects = 10

    private let transport: HeadlessHttpTransport
    private let redirectUri: String
    private var headers: [String: String]
    private var cookies: [String: String] = [:]
    private var postUrl: String?
    private var isCancelled = false

    /// `headers` carries X-KOBIL-ASTCLIENTDATA and X-KOBIL-ASTCLIENTID on every request.
    init(transport: HeadlessHttpTransport, redirectUri: String, headers: [String: String]) {
        self.transport = transport
        self.redirectUri = redirectUri
        self.headers = headers
    }

    func start(authorizationUrl: String) async throws -> Step {
        try await load(url: authorizationUrl, post: nil)
    }

    /// Posts the answer to `form`. `onlyKeys` limits the answer to those inputs, e.g.
    /// for "resend email".
    func submit(
        _ form: HeadlessForm,
        values: [String: String],
        action: String = "submit",
        resendKey: String? = nil,
        onlyKeys: Set<String>? = nil
    ) async throws -> Step {
        guard let postUrl else { throw HeadlessIdpError.unreadablePage("The step has no form to post to.") }
        guard let answer = form.answer(values: values, action: action, resendKey: resendKey, onlyKeys: onlyKeys),
              let json = String(data: answer, encoding: .utf8)
        else {
            throw HeadlessIdpError.unreadablePage("The answer could not be encoded.")
        }
        Self.log.info("Posting headless step \(form.formId, privacy: .public), action \(action, privacy: .public)")
        return try await load(url: postUrl, post: "jsonInput=\(Self.formEncoded(json))")
    }

    func cancel() {
        isCancelled = true
        transport.cancel()
    }

    // MARK: Exchange

    private func load(url: String, post body: String?) async throws -> Step {
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
                throw response.status == .timeout
                    ? HeadlessIdpError.timedOut
                    : HeadlessIdpError.requestFailed(Self.statusName(response.status))
            }
            storeCookies(from: response, url: url)
            Self.log.info("Headless \(body == nil ? "GET" : "POST", privacy: .public) → HTTP \(response.httpStatus, privacy: .public)")

            switch response.httpStatus {
            case 200:
                return try parsePage(response.body)
            case 301, 302, 303, 307, 308:
                guard let location = response.header("Location"),
                      let next = URL(string: location, relativeTo: URL(string: url))?.absoluteString
                else {
                    throw HeadlessIdpError.unexpectedStatus(response.httpStatus, "The redirect has no location.")
                }
                if next.hasPrefix(redirectUri) {
                    return try authorisationCode(fromRedirect: next)
                }
                url = next
                body = nil
            default:
                throw HeadlessIdpError.unexpectedStatus(response.httpStatus, Self.pageSummary(response.body))
            }
        }
        throw HeadlessIdpError.tooManyRedirects
    }

    private func parsePage(_ data: Data) throws -> Step {
        let html = String(decoding: data, as: UTF8.self)
        let page = HeadlessHtml(html)

        var message: HeadlessPageMessage?
        if let errorJson = page.textOfElement(id: "error-msg"),
           !errorJson.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            message = Self.pageMessage(fromJson: errorJson)
            if let message, message.isSevere {
                Self.log.error("IDP reported a severe error, code \(message.code ?? "none", privacy: .public)")
                throw HeadlessIdpError.idpMessage(message)
            }
        }

        let action = page.formAction()
        // response_mode=form_post: the last page is a self-posting form aimed at the redirect URI.
        if let action, action.hasPrefix(redirectUri) {
            if let code = page.inputValue(name: "code"), !code.isEmpty {
                Self.log.info("Headless journey reached the redirect URI with an authorisation code")
                return .authorisationCode(code)
            }
            let error = page.inputValue(name: "error_description") ?? page.inputValue(name: "error") ?? "no code returned"
            throw HeadlessIdpError.authorisationError(error)
        }

        guard let json = page.inputValue(id: "jsonInput"), let form = HeadlessForm(json: Data(json.utf8)) else {
            throw HeadlessIdpError.unreadablePage(message?.displayText ?? Self.pageSummary(data))
        }
        postUrl = action
        Self.log.info("""
            Headless step \(form.formId, privacy: .public) asks for \
            \(form.fields.map { "\($0.key):\($0.rawType)" }.joined(separator: ", "), privacy: .public)
            """)
        return .form(form, message: message)
    }

    private func authorisationCode(fromRedirect location: String) throws -> Step {
        // The code may arrive in the query or, for fragment response modes, after '#'.
        let normalised = location.replacingOccurrences(of: "#", with: "?")
        let items = URLComponents(string: normalised)?.queryItems ?? []
        if let code = items.first(where: { $0.name == "code" })?.value, !code.isEmpty {
            return .authorisationCode(code)
        }
        let error = items.first(where: { $0.name == "error_description" })?.value
            ?? items.first(where: { $0.name == "error" })?.value
            ?? "no code returned"
        throw HeadlessIdpError.authorisationError(error)
    }

    private func storeCookies(from response: HeadlessHttpResponse, url: String) {
        guard let setCookie = response.header("Set-Cookie"), let requestUrl = URL(string: url) else { return }
        let parsed = HTTPCookie.cookies(withResponseHeaderFields: ["Set-Cookie": setCookie], for: requestUrl)
        for cookie in parsed {
            if let expiry = cookie.expiresDate, expiry < Date() {
                cookies[cookie.name] = nil
            } else {
                cookies[cookie.name] = cookie.value
            }
        }
    }

    // MARK: Helpers

    private static func pageMessage(fromJson json: String) -> HeadlessPageMessage? {
        guard let object = (try? JSONSerialization.jsonObject(with: Data(json.utf8))) as? [String: Any] else {
            return HeadlessPageMessage(code: nil, title: "", message: json, isSevere: false, buttons: [])
        }
        return HeadlessPageMessage(
            code: object["errorCode"].map { String(describing: $0) },
            title: HeadlessText(object["title"])?.localized ?? "",
            message: HeadlessText(object["errorMessage"])?.localized ?? "",
            isSevere: object["severe"] as? Bool ?? false,
            buttons: (object["buttons"] as? [Any] ?? []).compactMap(HeadlessButton.init)
        )
    }

    /// A short, credential-free description of an unexpected page for the error message.
    private static func pageSummary(_ data: Data) -> String {
        let page = HeadlessHtml(String(decoding: data, as: UTF8.self))
        if let text = page.textOfElement(id: "kc-error-message") ?? page.textOfElement(tag: "title") {
            let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty { return String(trimmed.prefix(200)) }
        }
        return "(\(data.count) bytes)"
    }

    private static func formEncoded(_ value: String) -> String {
        var allowed = CharacterSet.alphanumerics
        allowed.insert(charactersIn: "-._~")
        return value.addingPercentEncoding(withAllowedCharacters: allowed) ?? value
    }

    private static func statusName(_ status: KSMCreateHttpCommonRequestStatus) -> String {
        switch status {
        case .success: return "success"
        case .serverNotReachable: return "server not reachable"
        case .sslHandshakeFailed: return "TLS handshake failed"
        case .failed: return "request failed"
        case .timeout: return "timeout"
        @unknown default: return "status \(status.rawValue)"
        }
    }
}

// MARK: - Minimal HTML reading

/// Reads the few things a headless page carries: input values, the form action and the text
/// of an element by id. The pages are Keycloak templates, not arbitrary HTML, and the values
/// are attribute-escaped JSON, so tag-level scanning with entity decoding is enough.
nonisolated struct HeadlessHtml {
    private let html: String

    init(_ html: String) {
        self.html = html
    }

    func inputValue(id: String) -> String? {
        inputs().first { $0["id"] == id }?["value"]
    }

    func inputValue(name: String) -> String? {
        inputs().first { $0["name"] == name }?["value"]
    }

    func formAction() -> String? {
        tags(named: "form").first?["action"]
    }

    func textOfElement(id: String) -> String? {
        let pattern = #"<([a-zA-Z][a-zA-Z0-9]*)\b[^>]*\bid\s*=\s*["']"# + NSRegularExpression.escapedPattern(for: id)
            + #"["'][^>]*>(.*?)</\1\s*>"#
        return firstCapture(pattern, group: 2).map(Self.decodeEntities)
    }

    func textOfElement(tag: String) -> String? {
        let pattern = "<\(tag)\\b[^>]*>(.*?)</\(tag)\\s*>"
        return firstCapture(pattern, group: 1).map(Self.decodeEntities)
    }

    private func inputs() -> [[String: String]] {
        tags(named: "input")
    }

    /// The attributes of every `<name ...>` tag, names lowercased, values entity-decoded.
    func tags(named name: String) -> [[String: String]] {
        guard let tagExpression = try? NSRegularExpression(
            pattern: "<\(name)\\b((?:[^>\"']|\"[^\"]*\"|'[^']*')*)/?>",
            options: [.caseInsensitive]
        ) else { return [] }
        let range = NSRange(html.startIndex..., in: html)
        return tagExpression.matches(in: html, range: range).compactMap { match in
            guard let attributesRange = Range(match.range(at: 1), in: html) else { return nil }
            return Self.attributes(in: String(html[attributesRange]))
        }
    }

    private static func attributes(in text: String) -> [String: String] {
        guard let expression = try? NSRegularExpression(
            pattern: #"([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"#
        ) else { return [:] }
        var result: [String: String] = [:]
        let range = NSRange(text.startIndex..., in: text)
        for match in expression.matches(in: text, range: range) {
            guard let nameRange = Range(match.range(at: 1), in: text) else { continue }
            let value = (2...4).lazy
                .compactMap { Range(match.range(at: $0), in: text) }
                .first
                .map { String(text[$0]) } ?? ""
            result[text[nameRange].lowercased()] = decodeEntities(value)
        }
        return result
    }

    private func firstCapture(_ pattern: String, group: Int) -> String? {
        guard let expression = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive, .dotMatchesLineSeparators]),
              let match = expression.firstMatch(in: html, range: NSRange(html.startIndex..., in: html)),
              let range = Range(match.range(at: group), in: html)
        else { return nil }
        return String(html[range])
    }

    static func decodeEntities(_ text: String) -> String {
        guard text.contains("&") else { return text }
        let named: [String: String] = ["quot": "\"", "amp": "&", "lt": "<", "gt": ">", "apos": "'", "nbsp": "\u{00A0}"]
        var output = ""
        var index = text.startIndex
        while index < text.endIndex {
            let character = text[index]
            guard character == "&",
                  let semicolon = text[index...].prefix(12).firstIndex(of: ";")
            else {
                output.append(character)
                index = text.index(after: index)
                continue
            }
            let entity = text[text.index(after: index)..<semicolon]
            var replacement: String?
            if entity.hasPrefix("#x") || entity.hasPrefix("#X") {
                replacement = UInt32(entity.dropFirst(2), radix: 16).flatMap(Unicode.Scalar.init).map { String($0) }
            } else if entity.hasPrefix("#") {
                replacement = UInt32(entity.dropFirst()).flatMap(Unicode.Scalar.init).map { String($0) }
            } else {
                replacement = named[String(entity)]
            }
            if let replacement {
                output += replacement
                index = text.index(after: semicolon)
            } else {
                output.append(character)
                index = text.index(after: index)
            }
        }
        return output
    }
}
