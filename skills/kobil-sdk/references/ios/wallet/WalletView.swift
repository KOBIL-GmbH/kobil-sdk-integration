//
//  WalletView.swift
//  KOBIL SDK reference implementation: wallet (app-side; makes no SDK call). See wallet.md.
//
//  The user's cards. The default card is shown on payment approvals and recorded with each
//  approved payment. Cards stay on this device; nothing is sent to the provider.
//

import SwiftUI

struct WalletView: View {
    @Environment(WalletStore.self) private var wallet
    @State private var addsCard = false
    @State private var renaming: WalletCard?
    @State private var newLabel = ""
    @State private var removing: WalletCard?
    @State private var problem: String?

    var body: some View {
        Group {
            if wallet.cards.isEmpty {
                ContentUnavailableView {
                    Label("No cards yet", systemImage: "wallet.bifold")
                } description: {
                    Text("Add a debit or credit card. It's shown when you approve a payment, so you can see what you pay with.")
                } actions: {
                    Button("Add Card") { addsCard = true }
                        .buttonStyle(PrimaryButtonStyle())
                        .frame(maxWidth: 240)
                }
            } else {
                ScrollView {
                    VStack(spacing: 18) {
                        ForEach(wallet.cards) { card in
                            CardFace(card: card, isDefault: card.id == wallet.defaultCard?.id)
                                .contextMenu { menu(for: card) }
                        }
                        Text("Touch and hold a card to make it the default, rename it or remove it. Cards stay on this device.")
                            .font(.kLabel)
                            .foregroundStyle(Theme.textSecondary)
                            .multilineTextAlignment(.center)
                            .padding(.top, 4)
                    }
                    .padding(20)
                }
            }
        }
        .background(AmbientBackground())
        .navigationTitle("Wallet")
        .toolbar {
            Button("Add Card", systemImage: "plus") { addsCard = true }
        }
        .sheet(isPresented: $addsCard) {
            AddCardView()
        }
        .alert("Rename card", isPresented: Binding(get: { renaming != nil }, set: { if !$0 { renaming = nil } })) {
            TextField("Label", text: $newLabel)
            Button("Save") {
                if let card = renaming { perform { try wallet.rename(card, to: newLabel) } }
                renaming = nil
            }
            Button("Cancel", role: .cancel) { renaming = nil }
        }
        .confirmationDialog(
            "Remove \(removing?.shortName ?? "this card")?",
            isPresented: Binding(get: { removing != nil }, set: { if !$0 { removing = nil } }),
            titleVisibility: .visible
        ) {
            Button("Remove Card", role: .destructive) {
                if let card = removing { perform { try wallet.remove(card) } }
                removing = nil
            }
        } message: {
            Text("Payments you already approved keep their record.")
        }
        .alert("Wallet", isPresented: Binding(get: { problem != nil }, set: { if !$0 { problem = nil } })) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(problem ?? "")
        }
    }

    @ViewBuilder
    private func menu(for card: WalletCard) -> some View {
        if card.id != wallet.defaultCard?.id {
            Button("Make Default", systemImage: "checkmark.circle") { perform { try wallet.makeDefault(card) } }
        }
        Button("Rename", systemImage: "pencil") {
            newLabel = card.label
            renaming = card
        }
        Button("Remove", systemImage: "trash", role: .destructive) { removing = card }
    }

    private func perform(_ change: () throws -> Void) {
        do { try change() } catch { problem = error.localizedDescription }
    }
}

#if DEBUG
#Preview("Cards") {
    NavigationStack { WalletView() }
        .environment(WalletStore.preview([.sample]))
}

#Preview("Empty") {
    NavigationStack { WalletView() }
        .environment(WalletStore.preview())
}
#endif
