//
//  IdpActivation.swift
//  KOBIL SDK iOS reference implementation (verified on a device 2026-09-16/17)
//
//  Runs the IDP enrolment that activates a user against this AST backend.
//

import Foundation
import UIKit
import os

/// The result of an IDP enrolment attempt, reduced to Sendable values.
enum IdpActivationEvent: Sendable {
    /// The login form contained a field this app cannot fill, so nothing was
    /// posted. The keys are the form's own field names.
    case formNotFillable(unfilledKeys: [String], allKeys: [String])
    /// The IDP flow ran to a result.
    case finished(Outcome)

    struct Outcome: Sendable {
        let status: KSMEventStatusType
        let errorCode: Int
        let reportId: Int
        let userId: String
        let errorDescription: String?
        /// Status of the SetAuthorisationCode result KSSIDP nests in its own result.
        let authorisationCodeStatus: KSMEventStatusType?
        let authorisationCodeErrorCode: Int?
        let authorisationCodeReportId: Int?
    }
}

/// Drives KSSIDP for a first activation or a login: it fetches the IDP form,
/// fills the fields this deployment asks for, and lets KSSIDP hand the resulting
/// authorisation code to the MasterController. Activation and login are the same
/// exchange against different IDP clients; only the credentials differ.
final class IdpActivationRunner: NSObject, KssIdpDelegate {
    private static let log = Logger(subsystem: "com.example.kobilsdk", category: "KSSIDP")

    private let userId: String
    /// Only an activation holds a code. A login form that asks for one cannot be
    /// filled and is reported instead of being posted half empty.
    private let activationCode: String?
    private let password: String
    private let deliver: @Sendable (IdpActivationEvent) -> Void
    private var idp: KssIdp?

    init(
        userId: String,
        activationCode: String? = nil,
        password: String,
        deliver: @escaping @Sendable (IdpActivationEvent) -> Void
    ) {
        self.userId = userId
        self.activationCode = activationCode
        self.password = password
        self.deliver = deliver
        super.init()
    }

    /// Starts the exchange. `url` must carry the IDP client id; KSSIDP builds the
    /// rest of the authorisation request itself. `astClientId` is the null ULID on
    /// a first activation and the device's minted id once it is activated.
    func start(
        masterController: any KSAsyncEventReceiver & KSEcoModulInterface & KSEventSource,
        url: String,
        certificateChain: Data,
        astClientData: String,
        astClientId: String,
        tenantId: String
    ) {
        let idp = KssIdp(
            masterController: masterController,
            delegate: self,
            shouldKssIdpHandleTms: false,
            retryOnTimeout: true,
            timeout: Self.requestTimeoutSeconds,
            enableTracing: false
        )
        // Multiflow is for forms that offer a choice: KSSIDP reports each option as a
        // DataModel of label and value, which is what the device picker of a 2FA flow
        // needs. It does not parse the headless JSON — the framework binary contains no
        // "formInputs", "jsonInput" or "formDisplayButtons" at all — so on a JSON page it
        // reports one empty DataModel and there is nothing to answer. The JSON contract
        // belongs to the app: KSSIDP carries the envelope field, this class fills it.
        idp.isMultiflow = false
        // KssIdp declares two delegate-typed properties, both non-optional: `delegate`,
        // set by the initialiser, and `dataSource`, which the initialiser does not touch.
        // Left nil, the form-filling callback has nobody to call: the page arrives, no
        // credentials are requested, nothing is posted, and no error is raised anywhere.
        idp.dataSource = self
        self.idp = idp
        Self.log.info("Starting IDP enrolment against \(url, privacy: .public)")
        // The AST client data is supplied here on purpose. Left to itself, KSSIDP asks the
        // MasterController for its own copy in order to build the X-KOBIL-ASTCLIENTDATA
        // header, and that request regenerates the PKCE pair. The authorisation code is then
        // bound to the challenge this app put in the URL while KSSIDP presents the newer
        // verifier, and the token exchange ends in invalid_grant, "PKCE verification failed:
        // Code mismatch". Passing the header keeps one pair for the whole exchange.
        idp.initiateConnection(
            withURL: url,
            certificate: certificateChain,
            // X-KOBIL-ASTCLIENTID must be present on a first activation, because the AST
            // activate step branches on it. Omitted, the step mints a client but activation
            // never closes, and the token-time AST login then reports "Attempted login with
            // ULID.nullValue" and rejects with 513_4036 ast_login_with_unactivated_client.
            // The value goes into the request path verbatim: the IDP called
            // /v1/tenants/<tenant>/clients/NULL_ID/activate when this said "NULL_ID", and AST
            // answered 513_4002 Invalid AST Client ID.
            headers: [
                "X-KOBIL-ASTCLIENTDATA": astClientData,
                // The null ULID itself, not the words "NULL_ID": AST parses this header as
                // a ULID and rejects anything else as an invalid client id. The same value
                // appears inside the client data blob as astClientId on a fresh device.
                // After activation the MasterController reports the minted id and that
                // is what a login has to present.
                "X-KOBIL-ASTCLIENTID": astClientId,
            ],
            tenantId: tenantId,
            // KSSIDP forwards the authorisation code to the MasterController itself. It has
            // to: ResultObject exposes no authorisation code, so the app cannot do it.
            requiresSetAuthorizationCode: true,
            // This deployment stores a backend password and does not hash it client side.
            shouldHashPin: false,
            retryOnTimeout: true
        )
    }

    func cancel() {
        idp?.cancelTransaction()
    }

    private static let requestTimeoutSeconds: Int32 = 60

    /// A ULID of 26 zeros: the "no client yet" value a first activation presents.
    static let nullAstClientId = String(repeating: "0", count: 26)

    // MARK: - KssIdpDelegate

    func provideCredentials(
        _ data: NSMutableDictionary,
        withCompletion completion: @escaping (NSMutableDictionary, KSMAuthenticationMode) -> Void
    ) {
        let keys = data.allKeys.compactMap { $0 as? String }
        Self.log.info("IDP login form fields: \(keys.joined(separator: ", "), privacy: .public)")

        var unfilled: [String] = []
        for key in keys {
            guard let field = data[key] as? FormDataTextField else { continue }
            if key == Self.headlessEnvelopeField {
                unfilled.append(contentsOf: fillHeadlessEnvelope(field))
            } else if let value = value(forFormField: key) {
                field.value = NSMutableData(data: Data(value.utf8))
            } else if field.value.length == 0 {
                // An empty field this app does not recognise: posting the form
                // would send an incomplete enrolment and could spend the code.
                unfilled.append(key)
            }
        }

        guard unfilled.isEmpty else {
            Self.log.error("Unfillable IDP form fields: \(unfilled.joined(separator: ", "), privacy: .public)")
            cancel()
            deliver(.formNotFillable(unfilledKeys: unfilled, allKeys: keys))
            return
        }

        completion(data, .no)
    }

    /// Answers one step of the JSON described flow.
    ///
    /// The dictionary is keyed by the form field that carries the step, and each
    /// value is the list of inputs that step asks for, as `DataModel` pairs whose
    /// `title` is the input's key. The fields are therefore inside the arrays, not
    /// in `data.allKeys`: reading the keys alone sees only the envelope field name.
    /// KSSIDP wants the answers back keyed by those titles.
    func provideCredentials(
        forMultiflow data: NSMutableDictionary,
        errorObject error: NSMutableDictionary?,
        withCompletion completion: @escaping (NSMutableDictionary, KSMAuthenticationMode) -> Void
    ) {
        if let error, error.count > 0 {
            let errorKeys = error.allKeys.compactMap { $0 as? String }
            Self.log.error("IDP step reported an error for: \(errorKeys.joined(separator: ", "), privacy: .public)")
        }

        let answers = NSMutableDictionary()
        var unfilled: [String] = []
        var described: [String] = []

        for (rawKey, rawValue) in data {
            guard let key = rawKey as? String else { continue }
            // Report what actually arrived before interpreting it: a failed cast
            // and an genuinely empty list are indistinguishable once coalesced.
            let elements = (rawValue as? NSArray).map { Array($0) } ?? []
            described.append("\(key) -> \(type(of: rawValue)) count=\(elements.count)")

            for element in elements {
                guard let input = element as? DataModel else {
                    described.append("  element \(type(of: element)): \(element)")
                    continue
                }
                described.append("  \(input.title)=\"\(input.value)\"")
                if let value = value(forFormField: input.title) {
                    answers[input.title] = value
                } else if input.value.isEmpty {
                    // An empty input this app has no value for. Submitting anyway
                    // would post an incomplete step.
                    unfilled.append(input.title)
                }
            }
        }

        Self.log.info("IDP step asks for: \(described.joined(separator: "; "), privacy: .public)")

        // Answering nothing makes the IDP re-serve the same step, which loops
        // forever; stop instead and report what could not be filled.
        guard unfilled.isEmpty, answers.count > 0 else {
            Self.log.error("""
                Unmapped IDP step fields: \(unfilled.joined(separator: ", "), privacy: .public); \
                filled \(answers.count, privacy: .public)
                """)
            cancel()
            deliver(.formNotFillable(unfilledKeys: unfilled, allKeys: described))
            return
        }

        completion(answers, .no)
    }

    func handleResult(_ result: ResultObject) {
        let authorisationCodeEvent = result.event
        Self.log.info("""
            IDP result status \(result.status.rawValue, privacy: .public), \
            errorCode \(result.errorCode, privacy: .public), \
            reportId \(result.reportId, privacy: .public), \
            setAuthorisationCode \(authorisationCodeEvent?.status.rawValue ?? -1, privacy: .public)
            """)
        if let description = result.errorDescription {
            Self.log.error("IDP result explanation: \(description)")
        }
        deliver(.finished(IdpActivationEvent.Outcome(
            status: result.status,
            errorCode: result.errorCode,
            reportId: result.reportId,
            userId: result.userId,
            errorDescription: result.errorDescription,
            authorisationCodeStatus: authorisationCodeEvent?.status,
            authorisationCodeErrorCode: authorisationCodeEvent.map { Int($0.errorCode) },
            authorisationCodeReportId: authorisationCodeEvent.map { Int($0.reportId) }
        )))
    }

    // MARK: - The headless JSON envelope

    /// The single form field the IDP*HeadlessV2 clients carry their JSON step in.
    private static let headlessEnvelopeField = "jsonInput"

    /// Fills a headless JSON step in place and returns the keys it could not answer.
    ///
    /// The field arrives holding the step the IDP rendered: a `formInputs` array whose
    /// entries each carry a `key` and an empty `value`, and a `formDisplayButtons`
    /// array. Answering it means writing the values into that same structure, marking
    /// the submit button clicked, and putting the result back into the field, because
    /// the whole step is posted back as this one form value.
    private func fillHeadlessEnvelope(_ field: FormDataTextField) -> [String] {
        guard var step = (try? JSONSerialization.jsonObject(with: field.value as Data))
                as? [String: Any] else {
            Self.log.error("The headless step is not JSON; nothing can be answered")
            return [Self.headlessEnvelopeField]
        }

        let formId = step["formId"] as? String ?? "unknown"
        var unfilled: [String] = []

        var inputs = step["formInputs"] as? [[String: Any]] ?? []
        for index in inputs.indices {
            guard let key = inputs[index]["key"] as? String else { continue }
            // A button is an action offered by the step, not an input to answer.
            if inputs[index]["type"] as? String == "button" { continue }

            if let value = value(forFormField: key) {
                inputs[index]["value"] = value
            } else if ((inputs[index]["value"] as? String) ?? "").isEmpty {
                let attributes = inputs[index]["attributes"] as? [String: Any]
                if attributes?["optional"] as? Bool != true {
                    unfilled.append(key)
                }
            }
        }
        step["formInputs"] = inputs

        // The step is submitted by reporting which of its buttons was pressed.
        var buttons = step["formDisplayButtons"] as? [[String: Any]] ?? []
        for index in buttons.indices where buttons[index]["action"] as? String == "submit" {
            buttons[index]["isClicked"] = true
        }
        step["formDisplayButtons"] = buttons

        guard let filled = try? JSONSerialization.data(withJSONObject: step) else {
            Self.log.error("The answered headless step could not be serialised")
            return [Self.headlessEnvelopeField]
        }
        field.value = NSMutableData(data: filled)

        let answered = inputs.compactMap { $0["key"] as? String }.joined(separator: ", ")
        Self.log.info("""
            Headless step \(formId, privacy: .public) asks for \(answered, privacy: .public), \
            unanswered \(unfilled.joined(separator: ", "), privacy: .public)
            """)
        return unfilled
    }

    // MARK: - Form field mapping

    /// Maps an IDP form field name onto the value this app holds for it.
    private func value(forFormField key: String) -> String? {
        switch Self.normalised(key) {
        // "userIdentity" is what this deployment's first step asks for, as an
        // email address.
        case "userid", "username", "user", "loginname", "useridentity", "email", "emailaddress":
            return userId
        case "activationcode", "code", "activationcodekey", "otp", "onetimecode":
            return activationCode
        case "password", "newpassword", "pin", "passwordconfirm", "confirmpassword":
            // An empty password is "not available": a journey that asks for one is then
            // reported as not fillable instead of being posted with a blank value.
            return password.isEmpty ? nil : password
        case "devicelabel", "label", "devicename":
            return UIDevice.current.name
        default:
            return nil
        }
    }

    private static func normalised(_ key: String) -> String {
        key.lowercased().filter(\.isLetter)
    }
}
