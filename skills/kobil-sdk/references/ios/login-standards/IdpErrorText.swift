//
//  IdpErrorText.swift
//
//  Turns what the IDP sends back on a failure (an HTML error page, often wrapped in an SDK
//  error string) into one short sentence for the user. kobil-lite error pages carry
//  <p id="error-subsystem">513</p><p id="error-code">4042</p><p id="error">…</p>; the full
//  text still goes to the device log, never to the screen.
//

import Foundation

nonisolated enum IdpErrorText {
    /// A plain message for `raw`, or `fallback` when nothing useful can be read from it.
    static func plain(_ raw: String?, fallback: String) -> String {
        guard let raw, !raw.isEmpty else { return fallback }
        let page = HeadlessHtml(raw)
        let subsystem = text(page.textOfElement(id: "error-subsystem"))
        let code = text(page.textOfElement(id: "error-code"))
        if let subsystem, let code, let known = known["\(subsystem)_\(code)"] {
            return known
        }
        // Codes that appear in plain text too, e.g. "513_4042" in an SDK description.
        for (key, message) in known where raw.contains(key) {
            return message
        }
        let lowered = raw.lowercased()
        if lowered.contains("activation code") || lowered.contains("activation_code") {
            return "The activation code is wrong or has expired. Ask for a new one."
        }
        if lowered.contains("invalid username or password") || lowered.contains("invalid_user_credentials") {
            return "The user ID or password is wrong."
        }
        if let message = text(page.textOfElement(id: "error")) ?? text(page.textOfElement(id: "kc-error-message")) {
            let reference = [subsystem, code].compactMap { $0 }.joined(separator: "_")
            return reference.isEmpty ? message : "\(message) (\(reference))"
        }
        // Not HTML: a short plain explanation can be shown as it is.
        if !raw.contains("<"), raw.count <= 200 { return raw }
        return fallback
    }

    /// Plain wording for the AST codes a user can actually meet.
    private static let known: [String: String] = [
        "513_4042": "This phone is activated for a different account. Sign in with the account you activated it with.",
        "513_4041": "This phone is not activated yet. Activate it first.",
        "513_4036": "The security check of this phone failed. Try again; if it repeats, activate the phone again.",
    ]

    /// Tags removed, whitespace collapsed; nil when empty.
    private static func text(_ html: String?) -> String? {
        guard let html else { return nil }
        let stripped = html
            .replacingOccurrences(of: "<!--.*?-->", with: " ", options: .regularExpression)
            .replacingOccurrences(of: "<[^>]+>", with: " ", options: .regularExpression)
            .split(whereSeparator: \.isWhitespace).joined(separator: " ")
        return stripped.isEmpty ? nil : HeadlessHtml.decodeEntities(stripped)
    }
}
