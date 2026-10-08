//
//  SignDocumentView.swift
//  KOBIL SDK reference implementation (email-code variant; verified on device)
//
//  Opens a PDF for signing: the real PDF in PDFKit with a
//  "Sign here" field, Decline in the top bar and Send in the footer. Tapping the field places
//  the stored signature, or opens the canvas first when there is none. Send signs the PDF
//  with the user's KOBIL key (KSMSignDataEvent) and embeds the signature in the file.
//

import PDFKit
import SwiftUI

struct SignDocumentView: View {
    let documentID: UUID

    @Environment(DocumentStore.self) private var store
    @Environment(SignatureStore.self) private var signatures
    @Environment(MasterControllerSession.self) private var session
    @State private var pdf: PDFDocument?
    @State private var isPlaced = false
    @State private var showsPad = false
    @State private var confirmsDecline = false
    @State private var isSending = false
    @State private var errorMessage: String?

    private var document: SigningDocument? {
        store.documents.first { $0.id == documentID }
    }

    var body: some View {
        Group {
            if let document {
                content(for: document)
            } else {
                ContentUnavailableView("Document removed", systemImage: "doc.questionmark")
            }
        }
        .navigationTitle(document?.title ?? "Document")
        .navigationBarTitleDisplayMode(.inline)
        .task(id: document?.status) { loadPDF() }
    }

    @ViewBuilder
    private func content(for document: SigningDocument) -> some View {
        VStack(spacing: 0) {
            if let pdf {
                PDFKitView(
                    document: pdf,
                    field: document.status == .pending ? document.field : nil,
                    placedSignature: isPlaced ? signatures.signature : nil,
                    onTapField: { tapField() },
                    onTapPage: document.status == .pending && document.fieldIsMovable && !isSending
                        ? { index, point in moveField(of: document, toPage: index, center: point) }
                        : nil
                )
                .ignoresSafeArea(edges: .horizontal)
            } else {
                ContentUnavailableView("The PDF cannot be opened", systemImage: "doc.badge.ellipsis")
                    .frame(maxHeight: .infinity)
            }
            footer(for: document)
        }
        .background(Theme.screen)
        .toolbar {
            if document.status == .pending {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Decline", role: .destructive) { confirmsDecline = true }
                        .tint(Theme.danger)
                        .disabled(isSending)
                }
            } else if document.status == .signed, let url = store.signedFileURL(of: document) {
                ToolbarItem(placement: .topBarTrailing) {
                    ShareLink(item: url) {
                        Label("Share", systemImage: "square.and.arrow.up")
                    }
                }
            }
        }
        .confirmationDialog("Decline \(document.title)?", isPresented: $confirmsDecline, titleVisibility: .visible) {
            Button("Decline", role: .destructive) { store.markDeclined(document) }
        } message: {
            Text("The document stays unsigned and \(document.sender) is told you declined it.")
        }
        .sheet(isPresented: $showsPad) {
            SignaturePadView { signature in
                try await signatures.save(signature)
                isPlaced = true
            }
        }
    }

    @ViewBuilder
    private func footer(for document: SigningDocument) -> some View {
        VStack(spacing: 12) {
            switch document.status {
            case .pending:
                if let errorMessage {
                    NoticeBanner(kind: .error, title: "Not signed", message: errorMessage)
                }
                Text(hint(for: document))
                    .font(.kLabel)
                    .foregroundStyle(Theme.textSecondary)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity)
                Button {
                    send(document)
                } label: {
                    if isSending {
                        ProgressView().tint(.white)
                    } else {
                        Text("Send")
                    }
                }
                .buttonStyle(PrimaryButtonStyle())
                .disabled(!isPlaced || signatures.signature == nil || isSending)
            case .signed:
                resultRow(
                    symbol: "checkmark.seal.fill",
                    color: Theme.success,
                    text: "Signed with your KOBIL key\(document.decidedAt.map { " on \($0.formatted(date: .abbreviated, time: .shortened))" } ?? "")."
                )
            case .declined:
                resultRow(
                    symbol: "xmark.seal.fill",
                    color: Theme.danger,
                    text: "You declined this document\(document.decidedAt.map { " on \($0.formatted(date: .abbreviated, time: .shortened))" } ?? "")."
                )
            }
        }
        .padding(.horizontal, Theme.margin)
        .padding(.top, 14)
        .padding(.bottom, 10)
        .background(Theme.panel.shadow(.drop(color: .black.opacity(0.06), radius: 8, y: -2)))
    }

    private func resultRow(symbol: String, color: Color, text: String) -> some View {
        HStack(spacing: 10) {
            Image(systemName: symbol)
                .font(.title3)
                .foregroundStyle(color)
            Text(text)
                .font(.kText)
                .foregroundStyle(Theme.textPrimary)
            Spacer(minLength: 0)
        }
        .padding(.vertical, 6)
        .accessibilityElement(children: .combine)
    }

    private func hint(for document: SigningDocument) -> String {
        if isPlaced { return "Check the document, then send it signed." }
        var text = signatures.signature == nil
            ? "Tap Sign here to draw your signature."
            : "Tap Sign here to place your signature."
        if document.fieldIsMovable { text += " Tap elsewhere on a page to move the field." }
        return text
    }

    // MARK: - Actions

    private func loadPDF() {
        guard let document else { return }
        let data = document.status == .signed ? store.signedPDF(of: document) : store.originalPDF(of: document)
        pdf = data.flatMap(PDFDocument.init(data:))
        if document.status != .pending { isPlaced = false }
    }

    private func tapField() {
        guard !isSending else { return }
        if signatures.signature == nil {
            showsPad = true
        } else {
            isPlaced.toggle()
        }
    }

    private func moveField(of document: SigningDocument, toPage index: Int, center: CGPoint) {
        guard let page = pdf?.page(at: index) else { return }
        let bounds = page.bounds(for: .cropBox)
        let size = document.field.rect.size
        let origin = CGPoint(
            x: min(max(center.x - size.width / 2, bounds.minX), bounds.maxX - size.width),
            y: min(max(center.y - size.height / 2, bounds.minY), bounds.maxY - size.height)
        )
        store.moveField(of: document, to: PdfSignatureField(pageIndex: index, rect: CGRect(origin: origin, size: size)))
    }

    private func send(_ document: SigningDocument) {
        guard let signature = signatures.signature, let original = store.originalPDF(of: document) else { return }
        isSending = true
        errorMessage = nil
        let appearance = PdfSigner.Appearance(
            signature: signature,
            signerName: session.userDisplayName ?? session.userEmail ?? "KOBIL user",
            reason: "Signed \(document.title) with KOBIL",
            date: .now
        )
        Task {
            do {
                let signed = try await PdfSigner.sign(pdf: original, field: document.field, appearance: appearance) { [session] bytes in
                    try PdfSigner.cms(from: await session.signData(bytes))
                }
                try store.markSigned(document, signedPDF: signed)
            } catch {
                errorMessage = error.localizedDescription
            }
            isSending = false
        }
    }
}

extension PdfSigner {
    /// The CMS to embed, from whichever part of the SDK's answer is one.
    nonisolated static func cms(from result: MasterControllerSession.SdkSignature) throws -> Data {
        #if DEBUG
        // Kept for inspecting what the SDK returns: Documents/Signing/sdk-*.bin.
        if let folder = DocumentStore.defaultFolder {
            try? result.signedData.write(to: folder.appending(path: "sdk-signedData.bin"))
            try? result.signature.write(to: folder.appending(path: "sdk-signature.bin"))
        }
        #endif
        if isCmsSignedData(result.signature) { return result.signature }
        if isCmsSignedData(result.signedData) { return result.signedData }
        throw SignError.notCms("signedData \(result.signedData.count) bytes, signature \(result.signature.count) bytes")
    }
}

// MARK: - PDFKit

/// A PDFView with the signature field drawn as an annotation, and taps reported in page space.
struct PDFKitView: UIViewRepresentable {
    let document: PDFDocument
    var field: PdfSignatureField?
    var placedSignature: HandSignature?
    var onTapField: () -> Void = {}
    var onTapPage: ((Int, CGPoint) -> Void)?

    func makeUIView(context: Context) -> PDFView {
        let view = PDFView()
        view.autoScales = true
        view.displayMode = .singlePageContinuous
        view.displayDirection = .vertical
        view.backgroundColor = UIColor(Theme.screen)
        view.pageShadowsEnabled = true
        let tap = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.tapped(_:)))
        tap.delegate = context.coordinator
        view.addGestureRecognizer(tap)
        context.coordinator.view = view
        return view
    }

    func updateUIView(_ view: PDFView, context: Context) {
        let coordinator = context.coordinator
        coordinator.parent = self
        if view.document !== document {
            coordinator.annotation = nil
            view.document = document
            if let field, let page = document.page(at: field.pageIndex) {
                view.go(to: field.rect.insetBy(dx: -40, dy: -120), on: page)
            }
        }
        coordinator.showField(field, signature: placedSignature, in: document)
    }

    func makeCoordinator() -> Coordinator { Coordinator(parent: self) }

    final class Coordinator: NSObject, UIGestureRecognizerDelegate {
        var parent: PDFKitView
        weak var view: PDFView?
        var annotation: SignatureFieldAnnotation?

        init(parent: PDFKitView) {
            self.parent = parent
        }

        func showField(_ field: PdfSignatureField?, signature: HandSignature?, in document: PDFDocument) {
            if let annotation, annotation.field == field, annotation.signature == signature { return }
            annotation?.page?.removeAnnotation(annotation!)
            annotation = nil
            guard let field, let page = document.page(at: field.pageIndex) else { return }
            let added = SignatureFieldAnnotation(field: field, signature: signature)
            page.addAnnotation(added)
            annotation = added
        }

        @objc func tapped(_ recognizer: UITapGestureRecognizer) {
            guard let view, let document = view.document else { return }
            let location = recognizer.location(in: view)
            guard let page = view.page(for: location, nearest: false) else { return }
            let point = view.convert(location, to: page)
            let index = document.index(for: page)
            if let field = parent.field, field.pageIndex == index, field.rect.insetBy(dx: -8, dy: -8).contains(point) {
                parent.onTapField()
            } else {
                parent.onTapPage?(index, point)
            }
        }

        func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldRecognizeSimultaneouslyWith other: UIGestureRecognizer) -> Bool {
            true
        }
    }
}

/// The on-screen field: a dashed "Sign here" box, or the placed signature. It only exists in
/// the viewer; the signed PDF gets its own signature widget from PdfSigner.
nonisolated final class SignatureFieldAnnotation: PDFAnnotation {
    let field: PdfSignatureField
    let signature: HandSignature?

    init(field: PdfSignatureField, signature: HandSignature?) {
        self.field = field
        self.signature = signature
        super.init(bounds: field.rect, forType: .stamp, withProperties: nil)
    }

    required init?(coder: NSCoder) { nil }

    override func draw(with box: PDFDisplayBox, in context: CGContext) {
        let rect = bounds
        context.saveGState()
        // Draw top-down like UIKit: flip about the field's own centre line.
        context.translateBy(x: 0, y: rect.minY + rect.maxY)
        context.scaleBy(x: 1, y: -1)
        UIGraphicsPushContext(context)
        defer {
            UIGraphicsPopContext()
            context.restoreGState()
        }

        let brand = UIColor(red: 0x1D / 255, green: 0x19 / 255, blue: 1, alpha: 1)
        let outline = UIBezierPath(roundedRect: rect, cornerRadius: 4)
        if let signature {
            UIColor.white.withAlphaComponent(0.6).setFill()
            outline.fill()
            let ink = signature.inkComponents
            UIColor(red: ink.red, green: ink.green, blue: ink.blue, alpha: 1).setStroke()
            for stroke in signature.strokes(fittedInto: rect.insetBy(dx: 6, dy: 6)) {
                let path = UIBezierPath(cgPath: HandSignature.smoothPath(stroke).cgPath)
                path.lineWidth = 1.6
                path.lineCapStyle = .round
                path.lineJoinStyle = .round
                path.stroke()
            }
        } else {
            brand.withAlphaComponent(0.08).setFill()
            outline.fill()
            brand.setStroke()
            outline.lineWidth = 1.2
            outline.setLineDash([4, 3], count: 2, phase: 0)
            outline.stroke()
            let text = NSAttributedString(string: "Sign here", attributes: [
                .font: UIFont.systemFont(ofSize: min(14, rect.height * 0.3), weight: .semibold),
                .foregroundColor: brand,
            ])
            let size = text.size()
            text.draw(at: CGPoint(x: rect.midX - size.width / 2, y: rect.midY - size.height / 2))
        }
    }
}


#if DEBUG
#Preview {
    let store = DocumentStore.preview()
    let session = MasterControllerSession(transactions: .preview())
    NavigationStack {
        SignDocumentView(documentID: store.documents[0].id)
    }
    .environment(store)
    .environment(SignatureStore.preview(.sample))
    .environment(session)
}
#endif
