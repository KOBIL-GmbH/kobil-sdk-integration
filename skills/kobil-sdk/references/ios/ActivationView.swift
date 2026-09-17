//
//  ActivationView.swift
//  KOBIL SDK iOS reference implementation (verified on a device 2026-09-16/17)
//
//  Collects what the SDK asks for during a first activation.
//

import SwiftUI

/// Drives the four activation events: the SDK asks for a user identifier and an
/// activation code, then for the credential that completes the activation, and
/// this screen answers each ask in turn.
struct ActivationView: View {
    let session: MasterControllerSession

    @State private var userId = ""
    @State private var activationCode = ""
    @State private var password = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            switch session.activationStep {
            case .none:
                Text("Waiting for the SDK to ask for activation input.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            case .userIdAndCode:
                userIdAndCodeFields
            case .password:
                passwordFields
            case .submitting:
                HStack(spacing: 8) {
                    ProgressView()
                    Text("Sending to the SDK…")
                        .font(.subheadline)
                }
            case .activated:
                Label("Activated", systemImage: "checkmark.circle")
                    .font(.headline)
                    .foregroundStyle(.green)
                Text("Relaunch the app: the SDK should report login required.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            case .failed(let message):
                Label("Activation failed", systemImage: "xmark.circle")
                    .font(.headline)
                Text(message)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                // The message stays readable and the form is right here for the retry.
                userIdAndCodeFields
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var userIdAndCodeFields: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Enter the user and the activation code issued for this version.")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            // The IDP's first step asks for the user's identity as an email address.
            TextField("User ID or email", text: $userId)
                .textContentType(.username)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .textFieldStyle(.roundedBorder)

            TextField("Activation code", text: $activationCode)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .textFieldStyle(.roundedBorder)

            // No password here: this deployment's activation journey sets none, and the
            // login password is issued by the backend tooling. A field marked as a new
            // password also draws iOS's strong-password overlay, which blocks input.
            HStack {
                Button("Activate") {
                    session.activate(
                        userId: userId.trimmingCharacters(in: .whitespacesAndNewlines),
                        activationCode: activationCode.trimmingCharacters(in: .whitespacesAndNewlines)
                    )
                }
                .buttonStyle(.borderedProminent)
                .disabled(userId.isEmpty || activationCode.isEmpty)

                Button("Cancel") {
                    session.cancelActivation()
                }
                .buttonStyle(.bordered)
            }
        }
    }

    /// The policy is stated as text with its own symbol, so the hint does not rely
    /// on colour alone to say the password is not acceptable yet.
    private var passwordPolicyHint: some View {
        Label {
            Text(MasterControllerSession.passwordPolicyDescription)
        } icon: {
            Image(systemName: passwordIsAcceptable ? "info.circle" : "exclamationmark.triangle")
        }
        .font(.footnote)
        .foregroundStyle(passwordIsAcceptable ? Color.secondary : Color.red)
    }

    private var passwordIsAcceptable: Bool {
        password.isEmpty || MasterControllerSession.passwordMeetsPolicy(password)
    }

    private var passwordFields: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Set the password for this user.")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            SecureField("Password", text: $password)
                .textContentType(.newPassword)
                .textFieldStyle(.roundedBorder)

            passwordPolicyHint

            HStack {
                Button("Activate") {
                    session.submitActivationPassword(password)
                }
                .buttonStyle(.borderedProminent)
                .disabled(!MasterControllerSession.passwordMeetsPolicy(password))

                Button("Cancel") {
                    session.cancelActivation()
                }
                .buttonStyle(.bordered)
            }
        }
    }
}

#Preview("Activation") {
    ActivationView(session: MasterControllerSession())
        .padding()
}
