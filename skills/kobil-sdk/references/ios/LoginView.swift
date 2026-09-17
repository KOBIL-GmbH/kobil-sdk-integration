//
//  LoginView.swift
//  KOBIL SDK iOS reference implementation (verified on a device 2026-09-16/17)
//
//  Collects the credentials that log an activated user in.
//

import SwiftUI

/// Shown while the SDK reports login required. The login journey of this
/// deployment asks for the user's email address and password on one page, and
/// the session runs it through KSSIDP exactly like the activation.
struct LoginView: View {
    let session: MasterControllerSession

    @State private var email = ""
    @State private var password = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            switch session.loginStep {
            case .none:
                credentialFields
            case .submitting:
                HStack(spacing: 8) {
                    ProgressView()
                    Text("Logging in…")
                        .font(.subheadline)
                }
                Button("Cancel") {
                    session.cancelLogin()
                }
                .buttonStyle(.bordered)
            case .loggedIn:
                Label("Logged in", systemImage: "checkmark.circle")
                    .font(.headline)
                    .foregroundStyle(.green)
            case .failed(let message):
                Label("Login failed", systemImage: "xmark.circle")
                    .font(.headline)
                Text(message)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                credentialFields
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var credentialFields: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Enter the email address and password of the activated user.")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            TextField("Email address", text: $email)
                .textContentType(.username)
                .keyboardType(.emailAddress)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .textFieldStyle(.roundedBorder)

            SecureField("Password", text: $password)
                .textContentType(.password)
                .textFieldStyle(.roundedBorder)

            Button("Log in") {
                session.login(
                    userId: email.trimmingCharacters(in: .whitespacesAndNewlines),
                    password: password
                )
            }
            .buttonStyle(.borderedProminent)
            .disabled(email.isEmpty || password.isEmpty)
        }
    }
}
