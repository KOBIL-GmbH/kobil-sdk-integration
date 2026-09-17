//
//  MasterControllerStatusView.swift
//  KOBIL SDK iOS reference implementation (verified on a device 2026-09-16/17)
//
//  Shows what the KOBIL SDK reported after its start event.
//

import SwiftUI

struct MasterControllerStatusView: View {
    @State private var session = MasterControllerSession()

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(title, systemImage: symbolName)
                .font(.headline)

            if let detail {
                Text(detail)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            if session.phase == .activationRequired {
                ActivationView(session: session)
                    .padding(.top, 4)
            }

            if session.phase == .loginRequired {
                LoginView(session: session)
                    .padding(.top, 4)
            }

            if session.phase == .loggedIn {
                Button("Log out") {
                    session.logout()
                }
                .buttonStyle(.bordered)
            }

            if let diagnostic = session.lastDiagnostic {
                Text(diagnostic)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if case .failed = session.phase {
                Button("Retry SDK start") {
                    session.start()
                }
                .buttonStyle(.bordered)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .task {
            if session.phase == .notStarted {
                session.start()
            }
        }
    }

    private var title: String {
        switch session.phase {
        case .notStarted:
            return "SDK not started"
        case .starting:
            return "Starting SDK…"
        case .activationRequired:
            return "Activation required"
        case .loginRequired:
            return "Login required"
        case .loggedIn:
            return "Logged in"
        case .loggingOut:
            return "Logging out…"
        case .notReady:
            return "SDK not ready"
        case .failed:
            return "SDK start failed"
        }
    }

    private var symbolName: String {
        switch session.phase {
        case .notStarted, .starting, .loggingOut:
            return "hourglass"
        case .activationRequired:
            return "person.badge.plus"
        case .loginRequired:
            return "person.crop.circle.badge.questionmark"
        case .loggedIn:
            return "person.crop.circle.badge.checkmark"
        case .notReady:
            return "exclamationmark.circle"
        case .failed:
            return "xmark.circle"
        }
    }

    private var detail: String? {
        switch session.phase {
        case .notStarted, .starting, .loggingOut:
            return nil
        case .activationRequired:
            return "No user is activated on this device."
        case .loginRequired, .loggedIn:
            let users = session.activatedUserIdentifiers
            guard !users.isEmpty else { return nil }
            return "Activated: \(users.joined(separator: ", "))"
        case .notReady(let stateValue):
            return "SDK state \(stateValue)."
        case .failed(let message):
            return message
        }
    }
}

#Preview("SDK status") {
    MasterControllerStatusView()
        .padding()
}
