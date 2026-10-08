//
//  DocumentsView.swift
//  KOBIL SDK reference implementation (email-code variant; verified on device)
//
//  PDFs to sign, newest first, then the signed and declined ones. A PDF can be imported from
//  Files; the sample agreement is added the first time the list opens.
//

import SwiftUI
import UniformTypeIdentifiers

struct DocumentsView: View {
    @Environment(DocumentStore.self) private var store
    @Environment(MasterControllerSession.self) private var session
    @AppStorage("documents.sampleAdded") private var sampleAdded = false
    @State private var importsPDF = false
    @State private var errorMessage: String?

    private var pending: [SigningDocument] { store.documents.filter { $0.status == .pending } }
    private var completed: [SigningDocument] { store.documents.filter { $0.status != .pending } }

    var body: some View {
        Group {
            if store.documents.isEmpty {
                ScrollView {
                    EmptyStateCard(
                        symbol: "signature",
                        title: "No documents",
                        message: "PDFs you need to sign appear here. Import one from Files, or try the sample agreement.",
                        actionTitle: "Add Sample Agreement",
                        action: addSample
                    )
                    .padding(Theme.margin)
                }
                .background(AmbientBackground())
            } else {
                List {
                    if !pending.isEmpty {
                        Section("To sign") { rows(pending) }
                    }
                    if !completed.isEmpty {
                        Section("Completed") { rows(completed) }
                    }
                }
                .listStyle(.insetGrouped)
                .scrollContentBackground(.hidden)
                .background(AmbientBackground())
            }
        }
        .navigationTitle("Documents")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    Button("Import PDF", systemImage: "folder") { importsPDF = true }
                    Button("Add Sample Agreement", systemImage: "doc.text", action: addSample)
                } label: {
                    Label("Add", systemImage: "plus")
                }
            }
        }
        .fileImporter(isPresented: $importsPDF, allowedContentTypes: [.pdf]) { result in
            do {
                try store.importPDF(from: result.get())
            } catch {
                errorMessage = error.localizedDescription
            }
        }
        .alert("Document not added", isPresented: Binding(get: { errorMessage != nil }, set: { if !$0 { errorMessage = nil } })) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "")
        }
        .onAppear {
            if !sampleAdded {
                sampleAdded = true
                if store.documents.isEmpty { addSample() }
            }
        }
    }

    private func rows(_ documents: [SigningDocument]) -> some View {
        ForEach(documents) { document in
            NavigationLink {
                SignDocumentView(documentID: document.id)
            } label: {
                DocumentRow(document: document)
            }
            .listRowBackground(Theme.panel)
            .swipeActions(edge: .trailing) {
                Button("Delete", systemImage: "trash", role: .destructive) {
                    withAnimation { store.delete(document) }
                }
            }
        }
    }

    private func addSample() {
        do {
            try store.addSampleAgreement(for: session.userDisplayName)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

struct DocumentRow: View {
    let document: SigningDocument

    var body: some View {
        HStack(spacing: 14) {
            SymbolTile(symbol: symbol, tint: color, size: 44)
            VStack(alignment: .leading, spacing: 3) {
                Text(document.title)
                    .font(.kTextMedium)
                    .foregroundStyle(Theme.textPrimary)
                    .lineLimit(1)
                // The sender gives way to the date: a cut-off date says nothing.
                HStack(spacing: 0) {
                    Text(document.sender)
                        .lineLimit(1)
                    Text(" · \((document.decidedAt ?? document.receivedAt).formatted(.dateTime.month(.abbreviated).day().hour().minute()))")
                        .lineLimit(1)
                        .fixedSize()
                }
                .font(.kLabel)
                .foregroundStyle(Theme.textSecondary)
            }
            Spacer(minLength: 8)
            StatusPill(text: statusText, color: color)
        }
        .padding(.vertical, 6)
    }

    private var symbol: String {
        switch document.status {
        case .pending: "doc.text"
        case .signed: "checkmark.seal.fill"
        case .declined: "xmark.seal"
        }
    }

    private var color: Color {
        switch document.status {
        case .pending: Theme.brand
        case .signed: Theme.success
        case .declined: Theme.danger
        }
    }

    private var statusText: String {
        switch document.status {
        case .pending: "To sign"
        case .signed: "Signed"
        case .declined: "Declined"
        }
    }
}


#if DEBUG
#Preview {
    let session = MasterControllerSession(transactions: .preview())
    NavigationStack {
        DocumentsView()
    }
    .environment(DocumentStore.preview())
    .environment(SignatureStore.preview(.sample))
    .environment(session)
}
#endif
