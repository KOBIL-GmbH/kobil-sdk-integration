//
//  EmailCodeActivationView.swift
//  KOBIL SDK iOS reference implementation, email-code variant (verified on a device 2026-09-26)
//
//  The first activation of this device, with the IDP's self-service journeys: the identity
//  server asks for the account's email address and password, emails a one-time code and asks
//  for it on the next page. Every page is drawn natively from the step the server sends
//  (HeadlessIdpFlow), so the fields, texts and validation rules come from the server.
//
//  Present it as a sheet while the session reports `.activationRequired`; it reads the
//  session from the environment (`.environment(session)` at the root). Pairs with
//  email-code/MasterControllerSession.swift.
//

import SwiftUI

struct EmailCodeActivationView: View {
    @Environment(MasterControllerSession.self) private var session
    @Environment(\.dismiss) private var dismiss

    /// What the user typed, keyed by the step's input keys. Kept across steps so a re-served
    /// step (for example after a wrong code) still shows the email address.
    @State private var values: [String: String] = [:]
    @State private var validationMessage: String?
    @State private var resendAvailableAt: Date?
    /// The serving whose notice the user dismissed with "OK" or "Retry".
    @State private var dismissedNotice: UUID?
    @FocusState private var focusedField: String?

    var body: some View {
        NavigationStack {
            VStack {
                switch session.activationStep {
                case .none:
                    waitingForSdkView
                case .userIdAndCode, .loadingPage:
                    progressView(title: "Contacting the identity server…", detail: nil)
                case .form(let form, let message):
                    stepContainer {
                        if let message, dismissedNotice != form.serial {
                            noticeBanner(message, form: form)
                        }
                        formView(form)
                    }
                case .submitting:
                    submittingView
                case .activated:
                    activatedSuccessView
                case .failed(let message):
                    stepContainer {
                        failureBanner(message)
                        retryButton
                    }
                case .password:
                    stepContainer {
                        failureBanner("The SDK asked for a PIN, which this activation does not use. Ask your administrator to check the activation setup.")
                    }
                }
            }
            .navigationTitle("Device Activation")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Close") {
                        dismiss()
                    }
                }
            }
        }
        .task(id: session.activationStep == .userIdAndCode) {
            // The SDK is ready: fetch the journey's first page.
            if session.activationStep == .userIdAndCode {
                session.beginActivation()
            }
        }
        .onDisappear {
            // A half-finished journey is abandoned; reopening the sheet starts a fresh one.
            session.cancelActivation()
        }
    }

    // MARK: - Step Container

    private func stepContainer<Content: View>(@ViewBuilder _ content: () -> Content) -> some View {
        ScrollView {
            VStack(spacing: 24) {
                content()
            }
            .padding()
        }
        .background(Color(.systemGroupedBackground))
    }

    // MARK: - Server-driven form

    private func formView(_ form: HeadlessForm) -> some View {
        VStack(alignment: .leading, spacing: 20) {
            VStack(alignment: .leading, spacing: 8) {
                Text(form.title.isEmpty ? "Activation" : form.title)
                    .font(.title3.bold())
                if !form.description.isEmpty {
                    Text(form.description)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }

            ForEach(form.fields) { field in
                fieldView(field, in: form)
            }

            if !form.unsupportedFields.isEmpty {
                Text("This step asks for something this app cannot show yet (\(form.unsupportedFields.map(\.rawType).joined(separator: ", "))).")
                    .font(.footnote)
                    .foregroundStyle(.red)
            }

            if let validationMessage {
                Text(validationMessage)
                    .font(.footnote)
                    .foregroundStyle(.red)
            }

            Button {
                submit(form)
            } label: {
                Text(form.submitButton?.title ?? "Continue")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
            }
            .buttonStyle(.borderedProminent)
            .disabled(!canSubmit(form))

            if let otpField = form.otpField {
                resendControl(for: otpField, in: form)
            }

            if form.offersResendEmail,
               let button = form.buttons.first(where: { $0.action == "resendEmail" }) {
                Button(button.title) {
                    session.resendActivationEmail(form, values: values)
                }
                .frame(maxWidth: .infinity)
            }

            // Page buttons that name another journey ("log in", "register", "forgot password").
            ForEach(form.buttons, id: \.action) { button in
                if let journey = MasterControllerSession.ActivationJourney(action: button.action) {
                    Button(button.title) {
                        session.switchActivationJourney(to: journey)
                    }
                    .frame(maxWidth: .infinity)
                }
            }
        }
        .padding(20)
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .shadow(color: Color.black.opacity(0.05), radius: 8, x: 0, y: 4)
        .task(id: form.serial) {
            prepare(for: form)
        }
    }

    @ViewBuilder
    private func fieldView(_ field: HeadlessField, in form: HeadlessForm) -> some View {
        switch field.kind {
        case .displayText:
            Text(field.initialValue.isEmpty ? field.title : field.initialValue)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        case .text, .changeText:
            labeledField(field.title) {
                TextField(field.placeholder, text: binding(for: field.key))
                    .textContentType(field.keyboardType == "email" ? .username : nil)
                    .keyboardType(field.keyboardType == "email" ? .emailAddress : .default)
                    .submitLabel(.next)
                    .disabled(!field.isEditable)
                    .focused($focusedField, equals: field.key)
            }
        case .password:
            labeledField(field.title) {
                SecureField(field.placeholder, text: binding(for: field.key))
                    .textContentType(.password)
                    .submitLabel(.go)
                    .focused($focusedField, equals: field.key)
                    .onSubmit { submit(form) }
            }
        case .otp:
            labeledField(field.title) {
                TextField(field.placeholder.isEmpty ? "Code" : field.placeholder, text: otpBinding(for: field, in: form))
                    .textContentType(.oneTimeCode)
                    .keyboardType(.numberPad)
                    .font(.title3.monospacedDigit())
                    .focused($focusedField, equals: field.key)
            }
        case .button:
            if let action = field.actionButton,
               let journey = MasterControllerSession.ActivationJourney(action: action.action) {
                Button(action.title) {
                    session.switchActivationJourney(to: journey)
                }
                .font(.footnote.bold())
                .frame(maxWidth: .infinity, alignment: .trailing)
            }
        case .unsupported:
            EmptyView()
        }
    }

    private func resendControl(for field: HeadlessField, in form: HeadlessForm) -> some View {
        TimelineView(.periodic(from: .now, by: 1)) { context in
            let remaining = max(0, Int(ceil((resendAvailableAt ?? .distantPast).timeIntervalSince(context.date))))
            if remaining > 0 {
                Text("\(field.resendTimerText ?? "Resend code in") \(remaining / 60):\(String(format: "%02d", remaining % 60))")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity)
            } else {
                Button(field.resendButtonText ?? "Resend code") {
                    values[field.key] = ""
                    session.resendActivationCode(form, values: values)
                }
                .frame(maxWidth: .infinity)
            }
        }
    }

    private func binding(for key: String) -> Binding<String> {
        Binding(
            get: { values[key] ?? "" },
            set: {
                values[key] = $0
                validationMessage = nil
            }
        )
    }

    /// Digits only, capped at the code's length; a complete code is submitted at once.
    private func otpBinding(for field: HeadlessField, in form: HeadlessForm) -> Binding<String> {
        let length = field.maxLength.flatMap { $0 > 0 ? $0 : nil } ?? 6
        return Binding(
            get: { values[field.key] ?? "" },
            set: { newValue in
                let digits = String(newValue.filter(\.isNumber).prefix(length))
                values[field.key] = digits
                validationMessage = nil
                if digits.count == length {
                    session.submitActivationForm(form, values: values, onlyKeys: [field.key])
                }
            }
        )
    }

    private func prepare(for form: HeadlessForm) {
        for field in form.fields where (values[field.key] ?? "").isEmpty && !field.initialValue.isEmpty {
            values[field.key] = field.initialValue
        }
        if let otpField = form.otpField {
            // A fresh serving of the code step means a code was just sent.
            values[otpField.key] = ""
            resendAvailableAt = Date().addingTimeInterval(TimeInterval(otpField.resendWaitSeconds ?? 90))
        }
        validationMessage = nil
        focusedField = form.fields.first { $0.requiresInput && (values[$0.key] ?? "").isEmpty }?.key
    }

    private func canSubmit(_ form: HeadlessForm) -> Bool {
        form.unsupportedFields.isEmpty
            && form.fields.allSatisfy { !$0.requiresInput || !(values[$0.key] ?? "").isEmpty }
    }

    private func submit(_ form: HeadlessForm) {
        guard canSubmit(form) else { return }
        var answers: [String: String] = [:]
        for field in form.fields where field.kind != .button && field.kind != .unsupported {
            let raw = values[field.key] ?? ""
            let value = field.kind == .password ? raw : raw.trimmingCharacters(in: .whitespacesAndNewlines)
            if let message = field.validationMessage(for: value) {
                validationMessage = message
                focusedField = field.key
                return
            }
            answers[field.key] = value
        }
        if let otpField = form.otpField {
            session.submitActivationForm(form, values: answers, onlyKeys: [otpField.key])
        } else {
            session.submitActivationForm(form, values: answers)
        }
    }

    private func labeledField<Field: View>(_ title: String, @ViewBuilder field: () -> Field) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption.bold())
                .foregroundStyle(.secondary)
            field()
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .padding(14)
                .background(Color(.secondarySystemGroupedBackground))
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
                )
        }
    }

    private func noticeBanner(_ message: HeadlessPageMessage, form: HeadlessForm) -> some View {
        Label {
            VStack(alignment: .leading, spacing: 4) {
                if !message.title.isEmpty {
                    Text(message.title)
                        .font(.headline)
                }
                if !message.message.isEmpty {
                    Text(message.message)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                HStack(spacing: 12) {
                    ForEach(message.buttons, id: \.action) { button in
                        noticeButton(button, form: form)
                    }
                }
                .padding(.top, 8)
            }
        } icon: {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.orange)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    /// The IDP's own choices for a notice, handled.
    @ViewBuilder
    private func noticeButton(_ button: HeadlessButton, form: HeadlessForm) -> some View {
        if let journey = MasterControllerSession.ActivationJourney(action: button.action) {
            Button(button.title) {
                session.switchActivationJourney(to: journey)
            }
            .buttonStyle(.borderedProminent)
        } else if ["ok", "retry"].contains(button.action) {
            Button(button.title) {
                dismissedNotice = form.serial
            }
            .buttonStyle(.bordered)
        } else if button.action == "exit" {
            Button(button.title) {
                dismiss()
            }
            .buttonStyle(.bordered)
        }
    }

    private func failureBanner(_ message: String) -> some View {
        Label {
            VStack(alignment: .leading, spacing: 4) {
                Text("Activation Failed")
                    .font(.headline)
                Text(message)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        } icon: {
            Image(systemName: "xmark.octagon.fill")
                .foregroundStyle(.red)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private var retryButton: some View {
        Button {
            session.beginActivation()
        } label: {
            Text("Try Again")
                .font(.headline)
                .frame(maxWidth: .infinity)
                .padding()
        }
        .buttonStyle(.borderedProminent)
    }

    // MARK: - Helper Views & Functions

    private func progressView(title: String, detail: String?) -> some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.2)
            Text(title)
                .font(.headline)
                .foregroundStyle(.secondary)
            if let detail {
                Text(detail)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(.systemGroupedBackground))
    }

    private var waitingForSdkView: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.2)
            Text("Waiting for the SDK to be ready…")
                .font(.headline)
                .foregroundStyle(.secondary)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(.systemGroupedBackground))
    }

    private var submittingView: some View {
        VStack(spacing: 24) {
            ProgressView()
                .scaleEffect(1.5)
            VStack(spacing: 8) {
                Text("Activating device…")
                    .font(.title3.bold())
                Text("The security SDK is exchanging the sign-in result for this device's credentials.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding(.horizontal, 32)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(.systemGroupedBackground))
    }

    private var activatedSuccessView: some View {
        VStack(spacing: 24) {
            Spacer()
            
            Image(systemName: "checkmark.seal.fill")
                .font(.system(size: 80))
                .foregroundStyle(.green)
                .shadow(color: .green.opacity(0.3), radius: 10, x: 0, y: 5)
            
            VStack(spacing: 12) {
                Text("Activation Complete!")
                    .font(.title2.bold())
                
                // Where the key lives depends on mc_config.json jwtSignKeySecurityPolicy;
                // ALLOW_VIRTUAL_SMART_CARD permits a software key, so claim no hardware here.
                Text("This device is activated for your account and you are signed in.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)

                VStack(alignment: .leading, spacing: 10) {
                    Label("Device credentials issued by the security SDK", systemImage: "key.fill")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                    // SetAuthorisationCodeResult Ok leaves the SDK logged in; the next launch
                    // reports LoginRequired.
                    Label("Next launch: sign in with your email and password", systemImage: "arrow.right.circle.fill")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                .padding()
                .background(Color(.secondarySystemGroupedBackground))
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .padding(.top, 10)
            }
            
            Spacer()
            
            Button {
                dismiss()
            } label: {
                Text("Done")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
            }
            .buttonStyle(.borderedProminent)
            .padding(.horizontal, 24)
            .padding(.bottom, 20)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(.systemGroupedBackground))
    }

}


#if DEBUG
#Preview("Activation") {
    EmailCodeActivationView()
        .environment(MasterControllerSession())
}
#endif
