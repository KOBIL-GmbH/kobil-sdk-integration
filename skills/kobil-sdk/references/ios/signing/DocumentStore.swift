//
//  DocumentStore.swift
//  KOBIL SDK reference implementation (email-code variant; verified on device)
//
//  PDFs waiting for the user's signature, and the signed or declined results, per user. The
//  files live in Documents/Signing/<SHA-256 of the user id>/, so a signed PDF can be copied off
//  the iPhone and the next user on this device does not see them. Load after sign-in, reset on
//  sign-out. Files an earlier version kept directly in Documents/Signing are no longer read.
//

import CryptoKit
import Foundation
import Observation
import UIKit

nonisolated struct SigningDocument: Identifiable, Codable, Equatable, Sendable {
    enum Status: String, Codable, Sendable {
        case pending, signed, declined
    }

    let id: UUID
    var title: String
    var sender: String
    var receivedAt: Date
    var field: PdfSignatureField
    var status: Status = .pending
    var decidedAt: Date?
    /// The user may move the field: true for imported PDFs, which come without one.
    var fieldIsMovable: Bool
    /// The KOBIL transaction (TMS signature request) this document records, if any.
    var transactionID: UUID? = nil

    var originalFileName: String { "\(id.uuidString).pdf" }
    var signedFileName: String { "\(id.uuidString)-signed.pdf" }
}

@Observable
final class DocumentStore {
    private(set) var documents: [SigningDocument] = []

    /// The base folder; each user's documents are in a subfolder of it.
    private let baseFolder: URL?
    private var userID: String?

    /// `folder` nil keeps everything in memory, for previews and tests; no user is needed then.
    init(folder: URL? = DocumentStore.defaultFolder) {
        self.baseFolder = folder
    }

    nonisolated static var defaultFolder: URL? {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first?
            .appending(path: "Signing", directoryHint: .isDirectory)
    }

    var pendingCount: Int { documents.filter { $0.status == .pending }.count }

    /// Shows the documents of the user who just signed in.
    func load(for userID: String) {
        self.userID = userID
        documents = []
        guard let indexURL, let data = try? Data(contentsOf: indexURL) else { return }
        documents = (try? JSONDecoder().decode([SigningDocument].self, from: data)) ?? []
    }

    /// Forgets the documents in memory, when the user signs out.
    func reset() {
        userID = nil
        documents = []
        memoryFiles = [:]
    }

    /// The signed-in user's folder; nil in memory mode or before `load(for:)`.
    private var folder: URL? {
        guard let baseFolder, let userID else { return nil }
        let digest = SHA256.hash(data: Data(userID.utf8))
        return baseFolder.appending(path: digest.map { String(format: "%02x", $0) }.joined(), directoryHint: .isDirectory)
    }

    // MARK: - Files

    private var memoryFiles: [String: Data] = [:]

    func originalPDF(of document: SigningDocument) -> Data? {
        read(document.originalFileName)
    }

    func signedPDF(of document: SigningDocument) -> Data? {
        read(document.signedFileName)
    }

    /// A file URL of the signed PDF, for sharing.
    func signedFileURL(of document: SigningDocument) -> URL? {
        guard let folder, document.status == .signed else { return nil }
        return folder.appending(path: document.signedFileName)
    }

    // MARK: - Changes

    @discardableResult
    func add(pdf: Data, title: String, sender: String, field: PdfSignatureField, fieldIsMovable: Bool) throws -> SigningDocument {
        let document = SigningDocument(
            id: UUID(), title: title, sender: sender, receivedAt: .now, field: field, fieldIsMovable: fieldIsMovable
        )
        try write(pdf, as: document.originalFileName)
        documents.insert(document, at: 0)
        try saveIndex()
        return document
    }

    /// Adds a PDF picked from Files, with the field at the bottom right of its last page.
    @discardableResult
    func importPDF(from url: URL) throws -> SigningDocument {
        let accessing = url.startAccessingSecurityScopedResource()
        defer { if accessing { url.stopAccessingSecurityScopedResource() } }
        let data = try Data(contentsOf: url)
        guard let provider = CGDataProvider(data: data as CFData), let pdf = CGPDFDocument(provider), pdf.numberOfPages > 0 else {
            throw ImportError.notPdf
        }
        if pdf.isEncrypted { throw PdfSigner.SignError.encrypted }
        let lastIndex = pdf.numberOfPages - 1
        let box = pdf.page(at: pdf.numberOfPages)?.getBoxRect(.cropBox) ?? CGRect(x: 0, y: 0, width: 595, height: 842)
        let size = CGSize(width: min(200, box.width * 0.4), height: min(72, box.height * 0.12))
        let field = PdfSignatureField(
            pageIndex: lastIndex,
            rect: CGRect(x: box.maxX - size.width - 36, y: box.minY + 48, width: size.width, height: size.height)
        )
        let title = url.deletingPathExtension().lastPathComponent
        return try add(pdf: data, title: title, sender: "Imported from Files", field: field, fieldIsMovable: true)
    }

    func moveField(of document: SigningDocument, to field: PdfSignatureField) {
        update(document.id) { $0.field = field }
    }

    func markSigned(_ document: SigningDocument, signedPDF: Data, at date: Date = .now) throws {
        try write(signedPDF, as: document.signedFileName)
        update(document.id) {
            $0.status = .signed
            $0.decidedAt = date
        }
    }

    func markDeclined(_ document: SigningDocument, at date: Date = .now) {
        update(document.id) {
            $0.status = .declined
            $0.decidedAt = date
        }
    }

    func delete(_ document: SigningDocument) {
        documents.removeAll { $0.id == document.id }
        remove(document.originalFileName)
        remove(document.signedFileName)
        try? saveIndex()
    }

    /// The document recording a TMS signature request, if one was made for it.
    func document(forTransaction id: UUID) -> SigningDocument? {
        documents.first { $0.transactionID == id }
    }

    /// Adds a TMS signature request as a PDF to sign: what was asked, the document's name and
    /// fingerprint, and a signature box. Its date is the request's, so the list stays in order.
    @discardableResult
    func addSignatureRequest(_ record: ApprovalRecord, signerName: String?) throws -> SigningDocument {
        let made = SignatureRequestPdf.make(record: record, signerName: signerName)
        let document = SigningDocument(
            id: UUID(),
            title: record.documentName ?? record.title ?? "Signature request",
            sender: record.title ?? "KOBIL Trust",
            receivedAt: record.receivedAt,
            field: made.field,
            fieldIsMovable: false,
            transactionID: record.id
        )
        try write(made.pdf, as: document.originalFileName)
        documents.append(document)
        documents.sort { $0.receivedAt > $1.receivedAt }
        try saveIndex()
        return document
    }

    /// Adds the bundled sample agreement, made out to the signed-in user.
    @discardableResult
    func addSampleAgreement(for signerName: String?) throws -> SigningDocument {
        let sample = SampleAgreement.make(signerName: signerName)
        return try add(pdf: sample.pdf, title: SampleAgreement.title, sender: SampleAgreement.issuer, field: sample.field, fieldIsMovable: false)
    }

    enum ImportError: LocalizedError {
        case notPdf
        var errorDescription: String? { "The file is not a PDF." }
    }

    enum StoreError: LocalizedError {
        case notSignedIn
        var errorDescription: String? { "Sign in to keep documents." }
    }

    // MARK: - Storage

    private func update(_ id: UUID, _ change: (inout SigningDocument) -> Void) {
        guard let index = documents.firstIndex(where: { $0.id == id }) else { return }
        change(&documents[index])
        try? saveIndex()
    }

    private var indexURL: URL? { folder?.appending(path: "index.json") }

    private func saveIndex() throws {
        guard baseFolder != nil else { return }
        guard let indexURL else { throw StoreError.notSignedIn }
        try ensureFolder()
        try JSONEncoder().encode(documents).write(to: indexURL, options: [.atomic, .completeFileProtection])
    }

    private func ensureFolder() throws {
        guard let folder else { return }
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
    }

    private func read(_ name: String) -> Data? {
        guard baseFolder != nil else { return memoryFiles[name] }
        guard let folder else { return nil }
        return try? Data(contentsOf: folder.appending(path: name))
    }

    private func write(_ data: Data, as name: String) throws {
        guard baseFolder != nil else {
            memoryFiles[name] = data
            return
        }
        guard let folder else { throw StoreError.notSignedIn }
        try ensureFolder()
        try data.write(to: folder.appending(path: name), options: [.atomic, .completeFileProtection])
    }

    private func remove(_ name: String) {
        guard baseFolder != nil else {
            memoryFiles[name] = nil
            return
        }
        guard let folder else { return }
        try? FileManager.default.removeItem(at: folder.appending(path: name))
    }
}

// MARK: - Sample agreement

/// A one-page A4 agreement with a marked signature box, drawn at runtime.
enum SampleAgreement {
    static let title = "Account Agreement"
    /// PER APP: the organisation named on the sample agreement.
    static let issuer = "KOBIL Demo Bank"

    static func make(signerName: String?, date: Date = .now) -> (pdf: Data, field: PdfSignatureField) {
        let page = CGRect(x: 0, y: 0, width: 595, height: 842)
        // The signature box in UIKit coordinates (origin top-left).
        let box = CGRect(x: 315, y: 650, width: 220, height: 80)
        let name = signerName ?? "Account holder"

        let format = UIGraphicsPDFRendererFormat()
        format.documentInfo = [
            kCGPDFContextTitle as String: title,
            kCGPDFContextCreator as String: "KOBIL Trusted App",
        ]
        let data = UIGraphicsPDFRenderer(bounds: page, format: format).pdfData { context in
            context.beginPage()
            let margin: CGFloat = 60
            var y: CGFloat = 64

            func draw(_ text: String, font: UIFont, color: UIColor = .black, spacing: CGFloat = 10) {
                let paragraph = NSMutableParagraphStyle()
                paragraph.lineSpacing = 3
                let attributed = NSAttributedString(
                    string: text,
                    attributes: [.font: font, .foregroundColor: color, .paragraphStyle: paragraph]
                )
                let bounds = attributed.boundingRect(
                    with: CGSize(width: page.width - margin * 2, height: .greatestFiniteMagnitude),
                    options: [.usesLineFragmentOrigin, .usesFontLeading],
                    context: nil
                )
                attributed.draw(with: CGRect(x: margin, y: y, width: page.width - margin * 2, height: bounds.height),
                                options: [.usesLineFragmentOrigin, .usesFontLeading], context: nil)
                y += ceil(bounds.height) + spacing
            }

            let brand = UIColor(red: 0x25 / 255, green: 0x63 / 255, blue: 0xEB / 255, alpha: 1)
            draw(issuer, font: .systemFont(ofSize: 13, weight: .semibold), color: brand, spacing: 4)
            draw(title, font: .systemFont(ofSize: 24, weight: .bold), spacing: 6)
            draw("Reference KDB-\(date.formatted(.iso8601.year().month().day().dateSeparator(.omitted)))-001  ·  \(date.formatted(date: .long, time: .omitted))",
                 font: .systemFont(ofSize: 10), color: .darkGray, spacing: 24)

            let body = UIFont.systemFont(ofSize: 11)
            let heading = UIFont.systemFont(ofSize: 12, weight: .semibold)
            draw("Between \(issuer) (\"the Bank\") and \(name) (\"the Customer\").", font: body, spacing: 16)
            draw("1. Account", font: heading, spacing: 4)
            draw("The Bank opens a current account in the Customer's name. Statements are provided monthly in the app and can be downloaded as PDF at any time.", font: body, spacing: 14)
            draw("2. Secure confirmation", font: heading, spacing: 4)
            draw("Payments and changes to this account are confirmed on the Customer's activated iPhone with KOBIL. The Bank never asks for a password, PIN or code by phone or email.", font: body, spacing: 14)
            draw("3. Electronic signature", font: heading, spacing: 4)
            draw("The Customer signs this agreement electronically. The signature is created with the Customer's personal KOBIL key on this device and embedded in this PDF, so any change after signing is detectable.", font: body, spacing: 14)
            draw("4. Fees and termination", font: heading, spacing: 4)
            draw("The account is free of charge for the first twelve months. Either party may end this agreement at any time with one month's notice.", font: body, spacing: 14)
            draw("This is a demonstration document. It has no legal effect.", font: .italicSystemFont(ofSize: 10), color: .gray)

            let cg = context.cgContext
            cg.setStrokeColor(UIColor.lightGray.cgColor)
            cg.setLineWidth(0.8)
            cg.stroke(box)
            let label = NSAttributedString(string: "Signature of the Customer", attributes: [.font: UIFont.systemFont(ofSize: 9), .foregroundColor: UIColor.darkGray])
            label.draw(at: CGPoint(x: box.minX, y: box.maxY + 6))
            NSAttributedString(string: name, attributes: [.font: UIFont.systemFont(ofSize: 10, weight: .medium)])
                .draw(at: CGPoint(x: box.minX, y: box.maxY + 20))
            NSAttributedString(string: "For the Bank: \(issuer)", attributes: [.font: UIFont.systemFont(ofSize: 9), .foregroundColor: UIColor.darkGray])
                .draw(at: CGPoint(x: margin, y: box.maxY + 6))
        }
        // PDF coordinates have their origin bottom-left.
        let field = PdfSignatureField(
            pageIndex: 0,
            rect: CGRect(x: box.minX, y: page.height - box.maxY, width: box.width, height: box.height)
        )
        return (data, field)
    }
}

// MARK: - Signature request

/// A one-page A4 record of a TMS signature request: what was asked, the document's name and
/// SHA-256 fingerprint, when it arrived and was answered, and the signer's box.
enum SignatureRequestPdf {
    static func make(record: ApprovalRecord, signerName: String?) -> (pdf: Data, field: PdfSignatureField) {
        let page = CGRect(x: 0, y: 0, width: 595, height: 842)
        let box = CGRect(x: 315, y: 620, width: 220, height: 80)
        let name = signerName ?? "Signer"
        let title = record.documentName ?? "Signature request"

        let format = UIGraphicsPDFRendererFormat()
        format.documentInfo = [
            kCGPDFContextTitle as String: title,
            kCGPDFContextCreator as String: "KOBIL Trusted App",
        ]
        let data = UIGraphicsPDFRenderer(bounds: page, format: format).pdfData { context in
            context.beginPage()
            let margin: CGFloat = 60
            let width = page.width - margin * 2
            var y: CGFloat = 64

            func draw(_ text: String, font: UIFont, color: UIColor = .black, spacing: CGFloat = 10) {
                let attributed = NSAttributedString(string: text, attributes: [.font: font, .foregroundColor: color])
                let height = ceil(attributed.boundingRect(
                    with: CGSize(width: width, height: .greatestFiniteMagnitude),
                    options: [.usesLineFragmentOrigin, .usesFontLeading], context: nil
                ).height)
                attributed.draw(with: CGRect(x: margin, y: y, width: width, height: height),
                                options: [.usesLineFragmentOrigin, .usesFontLeading], context: nil)
                y += height + spacing
            }

            let brand = UIColor(red: 0x25 / 255, green: 0x63 / 255, blue: 0xEB / 255, alpha: 1)
            draw("KOBIL Trust", font: .systemFont(ofSize: 13, weight: .semibold), color: brand, spacing: 4)
            draw(title, font: .systemFont(ofSize: 24, weight: .bold), spacing: 6)
            draw("Signature request · \(record.receivedAt.formatted(date: .long, time: .shortened))",
                 font: .systemFont(ofSize: 10), color: .darkGray, spacing: 26)

            let label = UIFont.systemFont(ofSize: 9, weight: .semibold)
            let value = UIFont.systemFont(ofSize: 11)
            var rows: [(String, String)] = [("REQUEST", record.text)]
            if let documentName = record.documentName { rows.append(("DOCUMENT", documentName)) }
            if let hash = record.documentHash { rows.append(("SHA-256 FINGERPRINT", hash)) }
            rows.append(("REQUESTED BY", record.title ?? "KOBIL transaction service"))
            rows += record.details.prefix(3).map { ($0.label.uppercased(), $0.value) }
            rows.append(("SIGNER", name))
            for (key, text) in rows {
                draw(key, font: label, color: .gray, spacing: 3)
                draw(text, font: key.hasPrefix("SHA-256") ? .monospacedSystemFont(ofSize: 10, weight: .regular) : value, spacing: 12)
            }
            y += 8
            draw("The signer answered this request on their activated iPhone. The KOBIL transaction service keeps the device signature over the request; this PDF is signed with the signer's personal KOBIL key, so any change after signing is detectable.",
                 font: .systemFont(ofSize: 10), color: .darkGray)

            let cg = context.cgContext
            cg.setStrokeColor(UIColor.lightGray.cgColor)
            cg.setLineWidth(0.8)
            cg.stroke(box)
            NSAttributedString(string: "Signature", attributes: [.font: UIFont.systemFont(ofSize: 9), .foregroundColor: UIColor.darkGray])
                .draw(at: CGPoint(x: box.minX, y: box.maxY + 6))
            NSAttributedString(string: name, attributes: [.font: UIFont.systemFont(ofSize: 10, weight: .medium)])
                .draw(at: CGPoint(x: box.minX, y: box.maxY + 20))
        }
        let field = PdfSignatureField(
            pageIndex: 0,
            rect: CGRect(x: box.minX, y: page.height - box.maxY, width: box.width, height: box.height)
        )
        return (data, field)
    }
}

#if DEBUG
extension DocumentStore {
    static func preview(declined: Bool = false) -> DocumentStore {
        let store = DocumentStore(folder: nil)
        if let document = try? store.addSampleAgreement(for: "Alex Example"), declined {
            store.markDeclined(document)
        }
        return store
    }
}
#endif
