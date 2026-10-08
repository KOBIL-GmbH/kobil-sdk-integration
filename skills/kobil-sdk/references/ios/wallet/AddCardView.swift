//
//  AddCardView.swift
//  KOBIL SDK reference implementation: wallet (app-side; makes no SDK call). See wallet.md.
//
//  Adds a card: number (checked, then reduced to its last four digits), expiry, holder and
//  an optional label. No security code is asked for.
//

import SwiftUI

struct AddCardView: View {
    @Environment(WalletStore.self) private var wallet
    @Environment(\.dismiss) private var dismiss

    @State private var number = ""
    @State private var expiry = ""
    @State private var holder = ""
    @State private var label = ""
    @State private var problem: String?

    private var digits: String { CardInput.digits(number) }
    private var network: WalletCard.Network { .of(digits) }
    private var numberComplete: Bool { digits.count >= network.numberLengths.lowerBound }
    private var numberInvalid: Bool { numberComplete && !CardInput.isValidNumber(digits) }
    private var expiryInvalid: Bool { CardInput.digits(expiry).count == 4 && CardInput.expiry(expiry) == nil }
    private var canSave: Bool { CardInput.isValidNumber(digits) && CardInput.expiry(expiry) != nil }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    if let problem {
                        NoticeBanner(kind: .error, title: nil, message: problem)
                    }
                    FieldContainer(title: "Card number", isInvalid: numberInvalid) {
                        HStack {
                            TextField("1234 5678 9012 3456", text: $number)
                                .keyboardType(.numberPad)
                                .textContentType(.creditCardNumber)
                                .onChange(of: number) { _, value in
                                    let limited = String(CardInput.digits(value).prefix(19))
                                    let formatted = CardInput.grouped(limited)
                                    if formatted != value { number = formatted }
                                }
                            if !digits.isEmpty {
                                Text(network.name)
                                    .font(.kLabelMedium)
                                    .foregroundStyle(Theme.textSecondary)
                            }
                        }
                    }
                    if numberInvalid {
                        Text("This number isn't valid. Check the digits.")
                            .font(.kLabel)
                            .foregroundStyle(Theme.danger)
                    }
                    FieldContainer(title: "Expiry (MM/YY)", isInvalid: expiryInvalid) {
                        TextField("08/30", text: $expiry)
                            .keyboardType(.numberPad)
                            .textContentType(.creditCardExpiration)
                            .onChange(of: expiry) { _, value in
                                let formatted = CardInput.groupedExpiry(value)
                                if formatted != value { expiry = formatted }
                            }
                    }
                    FieldContainer(title: "Name on card") {
                        TextField("As printed on the card", text: $holder)
                            .textContentType(.creditCardName)
                            .textInputAutocapitalization(.words)
                    }
                    FieldContainer(title: "Label (optional)") {
                        TextField("For example Everyday", text: $label)
                            .textInputAutocapitalization(.words)
                    }
                    Label("Only the last four digits are kept, on this device. The security code is never needed.", systemImage: "lock.shield")
                        .font(.kLabel)
                        .foregroundStyle(Theme.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .surface(padding: 20)
                .padding(20)
            }
            .scrollDismissesKeyboard(.interactively)
            .background(AmbientBackground())
            .navigationTitle("Add Card")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add", action: save)
                        .disabled(!canSave)
                }
            }
        }
    }

    private func save() {
        do {
            try wallet.add(number: number, expiry: expiry, holder: holder, label: label)
            number = ""
            dismiss()
        } catch {
            problem = error.localizedDescription
        }
    }
}

#if DEBUG
#Preview {
    AddCardView()
        .environment(WalletStore.preview())
}
#endif
