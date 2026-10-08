//
//  TransactionSecretSheet.swift
//  KOBIL SDK reference implementation: asks for the SDK PIN or a token (OTP) when a
//  transaction needs one (TransactionCenter.secretRequest). Present it as a sheet while
//  `secretRequest` is set; it answers once and shows the SDK's remaining retries.
//

import SwiftUI

struct TransactionSecretSheet: View {
    @Environment(TransactionCenter.self) private var transactions
    @State private var secret = ""

    var body: some View {
        if let request = transactions.secretRequest {
            VStack(spacing: 20) {
                Image(systemName: request.kind == .pin ? "lock.fill" : "key.fill")
                    .font(.largeTitle)
                    .foregroundStyle(Theme.brand)
                Text(request.kind == .pin ? "Enter your PIN" : "Enter the code")
                    .font(.kSmallTitle)
                Text(request.kind == .pin
                     ? "This payment needs your KOBIL PIN before it continues."
                     : "This payment needs the one-time code you received.")
                    .font(.kText)
                    .foregroundStyle(Theme.textSecondary)
                    .multilineTextAlignment(.center)
                SecureField(request.kind == .pin ? "PIN" : "Code", text: $secret)
                    .keyboardType(.numberPad)
                    .textContentType(.oneTimeCode)
                    .padding()
                    .background(Theme.fieldFill, in: .rect(cornerRadius: Theme.fieldRadius))
                if let retries = request.retryCounter {
                    Text("Wrong PIN. \(retries) attempts left.")
                        .font(.kLabel)
                        .foregroundStyle(Theme.danger)
                }
                if let deadline = request.deadline {
                    Text(timerInterval: Date()...deadline, countsDown: true)
                        .font(.kLabelMedium).monospacedDigit()
                        .foregroundStyle(Theme.textSecondary)
                }
                Button("Confirm") {
                    transactions.provideSecret(secret)
                    secret = ""
                }
                .buttonStyle(PrimaryButtonStyle())
                .disabled(secret.isEmpty || request.isSubmitting)
                Button("Cancel", role: .cancel) { transactions.cancelSecret() }
                    .buttonStyle(SecondaryButtonStyle())
            }
            .padding(Theme.margin)
            .interactiveDismissDisabled()
        }
    }
}
