//
//  TransactionCenter.swift
//  KOBIL SDK reference implementation (email-code variant; verified on device)
//
//  Transaction confirmations (payment approvals) and display messages pushed to this device
//  by the KOBIL transaction service. The session routes the SDK's TMS events here; the UI
//  presents `pending` app-wide and lists `history` and `inbox`. History and inbox are kept per
//  user in Application Support/Transactions/<SHA-256 of the user id>.json: load after sign-in,
//  reset on sign-out. The single transactions.json of earlier versions is no longer read.
//
//  SDK sequence (iOS, MCSDK 15.16): TriggerBanner(transaction) -> app sends StartTransaction
//  -> DisplayConfirmationRequest(timer, information) -> app sends DisplayConfirmation(decision,
//  original information) -> DisplayConfirmationResult(status) -> TransactionFinished(status).
//  Terminal statuses seen on iOS: 0 OK, 3 USER_CANCEL, 4 USER_CONFIRMATION_TIMEOUT,
//  53 SERVER_CANCEL.
//

import CryptoKit
import Foundation
import Observation
import OSLog

/// What the service asked the user to confirm, prepared for display. The SDK's original
/// `transactionInformation` is kept separately and returned unchanged.
struct TransactionContent: Equatable, Sendable {
    struct Detail: Equatable, Sendable, Hashable {
        let label: String
        let value: String
    }

    /// What the backend asks for. A signature request is a transaction whose data carries
    /// `requestType: "signature"`, or whose text starts with "Sign "; either way the user's
    /// approval is signed on this device and the backend keeps the signature (TMS signedData).
    enum Kind: String, Codable, Sendable {
        case payment, signature
    }

    let title: String?
    let text: String
    let details: [Detail]
    /// The amount, for display only; nothing is decided on it. Taken from `data.amount`
    /// (plus `data.currency`) when the backend sent them, else the first amount in the text.
    let amount: String?
    /// Who is paid, from `data.merchant` (or `payee`, `recipient`), when the backend sent it.
    let merchant: String?
    let kind: Kind
    /// For a signature request: the document's name and fingerprint, when the backend sent them.
    let documentName: String?
    let documentHash: String?

    /// Parses the information the SDK delivered: a JSON envelope when it is one, else the text.
    init(information: String) {
        var parsedAmount: String?
        let trimmed = information.trimmingCharacters(in: .whitespacesAndNewlines)
        if let data = trimmed.data(using: .utf8),
           let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            var flat: [(String, String)] = []
            Self.flatten(object, into: &flat)
            let textKeys = ["text", "message", "displaytext", "transactiontext", "tmsdata", "body", "content", "description"]
            let titleKeys = ["title", "subject", "header", "sender"]
            let text = flat.first { textKeys.contains($0.0.lowercased()) }?.1
            let title = flat.first { titleKeys.contains($0.0.lowercased()) }?.1
            let used = Set([text, title].compactMap { $0 })
            let resolvedText = text ?? flat.first?.1 ?? trimmed
            let value = { (keys: [String]) in flat.first { keys.contains($0.0.lowercased()) }?.1 }
            let documentName = value(["documentname", "document", "filename"])
            let documentHash = value(["documentsha256", "documenthash", "sha256", "hash"])
            let isSignature = value(["requesttype"])?.lowercased() == "signature"
            // The payment data contract (tms.md, "Payment data"): amount and currency as
            // separate keys. They become `amount` and are not repeated as detail rows.
            let structuredAmount = value(["amount"]).map { amount in
                guard let currency = value(["currency"]), Self.firstAmount(in: amount) == nil else { return amount }
                return "\(currency) \(amount)"
            }
            var hidden = Set(["requesttype", "documentname", "document", "filename", "documentsha256", "documenthash", "sha256", "hash"])
            if structuredAmount != nil { hidden.formUnion(["amount", "currency"]) }
            self.text = resolvedText
            self.title = title
            self.details = flat
                .filter { !used.contains($0.1) && $0.1 != resolvedText && !Self.isTechnicalKey($0.0) && !hidden.contains($0.0.lowercased()) }
                .prefix(8)
                .map { Detail(label: Self.humanize($0.0), value: $0.1) }
            self.documentName = documentName
            self.documentHash = documentHash
            self.merchant = value(["merchant", "payee", "recipient"])
            self.kind = isSignature || Self.readsAsSignature(resolvedText) ? .signature : .payment
            parsedAmount = structuredAmount
        } else {
            self.text = trimmed
            self.title = nil
            self.details = []
            self.documentName = nil
            self.documentHash = nil
            self.merchant = nil
            self.kind = Self.readsAsSignature(trimmed) ? .signature : .payment
        }
        self.amount = kind == .signature ? nil : parsedAmount ?? Self.firstAmount(in: ([self.text] + details.map(\.value)).joined(separator: " "))
    }

    private static func readsAsSignature(_ text: String) -> Bool {
        text.lowercased().hasPrefix("sign ")
    }

    /// The shape of what the SDK delivered, without any values: safe to log.
    static func structure(of information: String) -> String {
        let trimmed = information.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let data = trimmed.data(using: .utf8),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return "plain text, \(trimmed.utf8.count) bytes"
        }
        return "JSON keys [\(object.keys.sorted().joined(separator: ", "))]"
    }

    private static func flatten(_ object: [String: Any], into result: inout [(String, String)]) {
        for key in object.keys.sorted() {
            switch object[key] {
            case let string as String where !string.isEmpty:
                // A nested JSON string (envelope inside envelope) is unwrapped once.
                if let data = string.data(using: .utf8),
                   let nested = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    flatten(nested, into: &result)
                } else {
                    result.append((key, string))
                }
            case let number as NSNumber:
                result.append((key, number.stringValue))
            case let nested as [String: Any]:
                flatten(nested, into: &result)
            default:
                continue
            }
        }
    }

    private static func isTechnicalKey(_ key: String) -> Bool {
        let lowered = key.lowercased()
        return ["id", "transactionid", "signature", "nonce", "timestamp", "type", "version", "mimetype", "external"].contains(lowered)
            || lowered.hasSuffix("uuid")
    }

    private static func humanize(_ key: String) -> String {
        var words: [String] = []
        var current = ""
        for character in key {
            if character == "_" || character == "-" {
                if !current.isEmpty { words.append(current) }
                current = ""
            } else if character.isUppercase, !current.isEmpty {
                words.append(current)
                current = String(character)
            } else {
                current.append(character)
            }
        }
        if !current.isEmpty { words.append(current) }
        return words.joined(separator: " ").capitalized
    }

    private static let amountPattern = /(?:(?:EUR|USD|GBP|CHF|TRY|€|\$|£|₺)\s?\d[\d.,' ]*\d|\d[\d.,']*\s?(?:EUR|USD|GBP|CHF|TRY|€|\$|£|₺))/

    static func firstAmount(in text: String) -> String? {
        guard let match = text.firstMatch(of: amountPattern) else { return nil }
        return String(match.output).trimmingCharacters(in: .whitespaces)
    }
}

/// One confirmation the user answered, or that ended without an answer.
struct ApprovalRecord: Identifiable, Codable, Equatable, Sendable {
    enum Outcome: String, Codable, Sendable, CaseIterable {
        case approved, declined, expired, cancelledByServer, failed

        var title: String {
            switch self {
            case .approved: "Approved"
            case .declined: "Declined"
            case .expired: "Expired"
            case .cancelledByServer: "Withdrawn"
            case .failed: "Failed"
            }
        }
    }

    let id: UUID
    let receivedAt: Date
    let finishedAt: Date
    let title: String?
    let text: String
    let amount: String?
    let details: [TransactionContent.Detail]
    let outcome: Outcome
    /// Who was paid (`data.merchant`), when the backend said.
    var merchant: String? = nil
    /// The SDK's terminal status, kept for support.
    let statusCode: Int
    /// Optional so records saved before signing existed still load.
    var kind: TransactionContent.Kind? = nil
    var documentName: String? = nil
    var documentHash: String? = nil
    /// The wallet card shown when the user accepted a payment, e.g. "Visa •• 4242".
    var paidWith: String? = nil
    var isSignature: Bool { kind == .signature }
    /// "Signed" rather than "Approved" for a document.
    var outcomeTitle: String { isSignature && outcome == .approved ? "Signed" : outcome.title }
}

extension TransactionContent.Detail: Codable {}

/// A display message the service sent to this device.
struct SecureMessage: Identifiable, Codable, Equatable, Sendable {
    enum Kind: String, Codable, Sendable {
        case info, warning, error
    }

    let id: UUID
    let receivedAt: Date
    let title: String?
    let text: String
    let kind: Kind
    var isRead: Bool
}

/// A transaction step that needs the user's SDK PIN or a token (OTP).
struct SecretRequest: Equatable {
    enum Kind: String {
        case pin, token
    }

    let kind: Kind
    let deadline: Date?
    /// Remaining attempts after a wrong PIN; nil before the first answer.
    var retryCounter: Int?
    var isSubmitting: Bool
}

/// The confirmation currently on screen.
struct PendingApproval: Identifiable, Equatable {
    enum Decision: Equatable {
        case approve, decline, timeout
    }

    let id = UUID()
    let receivedAt: Date
    /// Returned unchanged in the DisplayConfirmationEvent.
    let originalInformation: String
    let content: TransactionContent
    /// When the SDK's confirmation timer runs out; nil when it gave none.
    let deadline: Date?
    var decision: Decision?
    /// The wallet card the user saw on the request when accepting it.
    var paidWith: String?
    var isSignature: Bool { content.kind == .signature }
    /// Set once DisplayConfirmationResult arrived; TransactionFinished ends it.
    var confirmationStatus: Int?
}

@MainActor
@Observable
final class TransactionCenter {
    private(set) var pending: PendingApproval?
    private(set) var history: [ApprovalRecord] = []
    private(set) var inbox: [SecureMessage] = []
    /// Something the app could not do, for example a re-authentication it does not support.
    var lastProblem: String?
    /// Set while the SDK waits for the user's PIN or token for a transaction.
    private(set) var secretRequest: SecretRequest?
    /// Set when a transaction ends; the approval overlay shows it until the user taps Done.
    private(set) var lastFinished: ApprovalRecord?

    /// Delivers events to the MasterController; set by the session.
    @ObservationIgnored var sender: ((KsMacroEvent) -> Void)?

    @ObservationIgnored private var timeoutTask: Task<Void, Never>?
    @ObservationIgnored private var bannerTimerSeconds = 0
    /// The folder of the per-user files; nil keeps everything in memory (previews, tests).
    @ObservationIgnored private let storageFolder: URL?
    @ObservationIgnored private var userID: String?
    private static let log = Logger(subsystem: "com.example.kobilsdk", category: "Transactions")  // PER APP: your bundle identifier

    var unreadCount: Int { inbox.filter { !$0.isRead }.count }
    /// Payments and approvals; signature requests are listed with the documents instead.
    var payments: [ApprovalRecord] { history.filter { !$0.isSignature } }
    var signatureRequests: [ApprovalRecord] { history.filter(\.isSignature) }

    init(persisting: Bool = true) {
        storageFolder = persisting ? Self.defaultFolder() : nil
    }

    /// Shows the history and inbox of the user who just signed in.
    func load(for userID: String) {
        self.userID = userID
        history = []
        inbox = []
        guard let storage, let data = try? Data(contentsOf: storage),
              let stored = try? JSONDecoder().decode(Stored.self, from: data) else { return }
        history = stored.history
        inbox = stored.inbox
    }

    /// Forgets the history and inbox in memory, when the user signs out.
    func reset() {
        endSession()
        userID = nil
        history = []
        inbox = []
    }

    // MARK: - SDK events

    func handleBanner(type: KSMBannerType, payload: String, timerSeconds: Int) {
        switch type {
        case .transaction:
            guard pending == nil else {
                Self.log.info("Transaction banner ignored: a confirmation is already open")
                return
            }
            bannerTimerSeconds = timerSeconds
            Self.log.info("Transaction banner received, starting the transaction")
            sender?(KSMStartTransactionEvent())
        case .displayMessage:
            Self.log.info("Display message banner received, starting the display message")
            sender?(KSMStartDisplayMessageEvent())
        @unknown default:
            Self.log.error("Unknown banner type \(type.rawValue, privacy: .public)")
        }
    }

    func handleConfirmationRequest(timerSeconds: Int, information: String) {
        if let pending, pending.originalInformation == information { return }
        let seconds = timerSeconds > 0 ? timerSeconds : bannerTimerSeconds
        let deadline = seconds > 0 ? Date().addingTimeInterval(TimeInterval(seconds)) : nil
        Self.log.info("Confirmation request: \(TransactionContent.structure(of: information), privacy: .public)")
        pending = PendingApproval(
            receivedAt: Date(),
            originalInformation: information,
            content: TransactionContent(information: information),
            deadline: deadline
        )
        lastFinished = nil
        armTimeout(seconds: seconds)
    }

    /// The user's answer. Sent once; later taps and taps after the deadline are ignored.
    func decide(approve: Bool, paidWith: String? = nil) {
        guard var current = pending, current.decision == nil else { return }
        if let deadline = current.deadline, Date() >= deadline { return }
        current.decision = approve ? .approve : .decline
        current.paidWith = approve ? paidWith : nil
        pending = current
        timeoutTask?.cancel()
        send(approve ? .ok : .cancel, information: current.originalInformation)
    }

    func handleConfirmationResult(_ status: KSMEventStatusType) {
        guard var current = pending else { return }
        current.confirmationStatus = status.rawValue
        pending = current
        Self.log.info("Confirmation result \(status.rawValue, privacy: .public)")
    }

    func handleTransactionFinished(_ status: KSMEventStatusType) {
        timeoutTask?.cancel()
        timeoutTask = nil
        guard let current = pending else { return }
        let outcome: ApprovalRecord.Outcome
        switch status {
        case .KSMOK:
            outcome = current.decision == .approve ? .approved : .failed
        case .KSMUSER_CANCEL:
            outcome = .declined
        case .KSMUSER_CONFIRMATION_TIMEOUT:
            outcome = .expired
        case .KSMSERVER_CANCEL:
            outcome = .cancelledByServer
        default:
            outcome = .failed
        }
        var record = ApprovalRecord(
            id: current.id,
            receivedAt: current.receivedAt,
            finishedAt: Date(),
            title: current.content.title,
            text: current.content.text,
            amount: current.content.amount,
            details: current.content.details,
            outcome: outcome,
            statusCode: status.rawValue,
            kind: current.content.kind,
            documentName: current.content.documentName,
            documentHash: current.content.documentHash,
            paidWith: outcome == .approved ? current.paidWith : nil
        )
        record.merchant = current.content.merchant
        history.insert(record, at: 0)
        lastFinished = record
        pending = nil
        save()
        Self.log.info("Transaction finished: \(outcome.rawValue, privacy: .public) (\(status.rawValue, privacy: .public))")
    }

    /// The SDK asked for the user's PIN or a token before it continues a transaction
    /// (KSMTransactionPinRequiredRequestEvent / KSMTransactionTokenRequiredRequestEvent).
    /// Present a secure field while this is set, then call `provideSecret` or `cancelSecret`.
    func handleSecretRequired(_ kind: SecretRequest.Kind, timerSeconds: Int) {
        let deadline = timerSeconds > 0 ? Date().addingTimeInterval(TimeInterval(timerSeconds)) : nil
        secretRequest = SecretRequest(kind: kind, deadline: deadline, retryCounter: nil, isSubmitting: false)
        Self.log.info("Transaction needs a \(kind.rawValue, privacy: .public) (\(timerSeconds, privacy: .public) s)")
    }

    /// Answers the request with KSMProvidePinEvent / KSMProvideTokenEvent. A wrong PIN leaves
    /// the request open with the SDK's remaining retry count. The secret is never logged.
    func provideSecret(_ secret: String) {
        guard var request = secretRequest, !request.isSubmitting else { return }
        if let deadline = request.deadline, Date() >= deadline { return }
        request.isSubmitting = true
        secretRequest = request
        sendSecret(request.kind, confirmation: .ok, secret: secret)
    }

    /// The user declined to enter the PIN or token; the SDK cancels the transaction.
    func cancelSecret() {
        guard let request = secretRequest else { return }
        secretRequest = nil
        sendSecret(request.kind, confirmation: .cancel, secret: "")
    }

    private func sendSecret(_ kind: SecretRequest.Kind, confirmation: KSMConfirmationType, secret: String) {
        let id = UUID()
        // The answer comes as KSMProvidePinResultEvent / KSMProvideTokenResultEvent.
        SdkResultRouter.shared.register(id) { [weak self] event in
            let answer: (KSMEventStatusType, Int32?)?
            switch event {
            case let result as KSMProvidePinResultEvent: answer = (result.status, result.retryCounter)
            case let result as KSMProvideTokenResultEvent: answer = (result.status, nil)
            default: answer = nil
            }
            guard let answer else { return false }
            SdkResultRouter.shared.remove(id)
            let (status, retryCounter) = answer
            Task { @MainActor [weak self] in self?.handleSecretResult(status, retryCounter: retryCounter) }
            return true
        }
        switch kind {
        case .pin: sender?(KSMProvidePinEvent(confirmationType: confirmation, andPin: secret))
        case .token: sender?(KSMProvideTokenEvent(confirmationType: confirmation, andToken: secret))
        }
    }

    private func handleSecretResult(_ status: KSMEventStatusType, retryCounter: Int32?) {
        Self.log.info("Secret answer status \(status.rawValue, privacy: .public), retries \(retryCounter ?? -1, privacy: .public)")
        guard var request = secretRequest else { return }
        if status == .KSMOK {
            secretRequest = nil
        } else if status == .KSMINVALID_PIN, let retryCounter, retryCounter > 0 {
            request.isSubmitting = false
            request.retryCounter = Int(retryCounter)
            secretRequest = request
        } else {
            secretRequest = nil
            lastProblem = "The transaction could not be confirmed (status \(status.rawValue))."
        }
    }

    func handleDisplayMessage(information: String, type: KSMMessageType) {
        let content = TransactionContent(information: information)
        let kind: SecureMessage.Kind = switch type {
        case .warning: .warning
        case .error: .error
        default: .info
        }
        inbox.insert(
            SecureMessage(id: UUID(), receivedAt: Date(), title: content.title, text: content.text, kind: kind, isRead: false),
            at: 0
        )
        save()
    }

    /// Logout: an open confirmation can no longer be answered.
    func endSession() {
        timeoutTask?.cancel()
        timeoutTask = nil
        pending = nil
        secretRequest = nil
        lastFinished = nil
        bannerTimerSeconds = 0
    }

    // MARK: - User actions

    func markRead(_ message: SecureMessage) {
        guard let index = inbox.firstIndex(where: { $0.id == message.id }), !inbox[index].isRead else { return }
        inbox[index].isRead = true
        save()
    }

    func markAllRead() {
        guard unreadCount > 0 else { return }
        for index in inbox.indices { inbox[index].isRead = true }
        save()
    }

    func delete(_ message: SecureMessage) {
        inbox.removeAll { $0.id == message.id }
        save()
    }

    func clearHistory() {
        history.removeAll()
        lastFinished = nil
        save()
    }

    func clearInbox() {
        inbox.removeAll()
        save()
    }

    func acknowledgeLastFinished() {
        lastFinished = nil
    }

    // MARK: - Internals

    private func send(_ type: KSMConfirmationType, information: String) {
        Self.log.info("Sending confirmation \(type.rawValue, privacy: .public)")
        sender?(KSMDisplayConfirmationEvent(confirmationType: type, andTransactionInformation: information))
    }

    /// Answers `.timeout` once when the SDK's timer runs out without a decision.
    private func armTimeout(seconds: Int) {
        timeoutTask?.cancel()
        guard seconds > 0, let id = pending?.id else { return }
        timeoutTask = Task { [weak self] in
            try? await Task.sleep(for: .seconds(seconds))
            guard !Task.isCancelled, let self, var current = self.pending, current.id == id, current.decision == nil else { return }
            current.decision = .timeout
            self.pending = current
            self.send(.timeout, information: current.originalInformation)
        }
    }

    private struct Stored: Codable {
        var history: [ApprovalRecord]
        var inbox: [SecureMessage]
    }

    private static func defaultFolder() -> URL? {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first?
            .appending(path: "Transactions", directoryHint: .isDirectory)
    }

    /// The signed-in user's file, named by the hashed user ID so it reveals nothing about the account.
    private var storage: URL? {
        guard let storageFolder, let userID else { return nil }
        let digest = SHA256.hash(data: Data(userID.utf8))
        return storageFolder.appending(path: digest.map { String(format: "%02x", $0) }.joined() + ".json")
    }

    private func save() {
        guard let storageFolder else { return }
        guard let storage else {
            Self.log.error("Transactions not saved: no signed-in user loaded (call load(for:) after sign-in)")
            return
        }
        do {
            try FileManager.default.createDirectory(at: storageFolder, withIntermediateDirectories: true)
            let data = try JSONEncoder().encode(Stored(history: history, inbox: inbox))
            try data.write(to: storage, options: [.atomic, .completeFileProtection])
        } catch {
            Self.log.error("Could not save transactions: \(error.localizedDescription, privacy: .public)")
        }
    }
}

#if DEBUG
extension TransactionCenter {
    /// Xcode previews only: a center with the given records and no SDK or storage.
    static func preview(
        history: [ApprovalRecord] = [],
        inbox: [SecureMessage] = [],
        pendingInformation: String? = nil,
        timerSeconds: Int = 0,
        finished: ApprovalRecord? = nil
    ) -> TransactionCenter {
        let center = TransactionCenter(persisting: false)
        center.history = history
        center.inbox = inbox
        if let pendingInformation {
            center.handleConfirmationRequest(timerSeconds: timerSeconds, information: pendingInformation)
        }
        if let finished {
            center.lastFinished = finished
        }
        return center
    }
}
#endif
