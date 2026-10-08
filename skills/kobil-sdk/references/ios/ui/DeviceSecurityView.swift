//
//  DeviceSecurityView.swift
//  KOBIL SDK reference implementation: the "Device and security" settings a banking app
//  needs, on top of SdkFeatureRequests / SdkFlows / SdkStatusMonitor: connection and SDK
//  state, device name, the users on this device (delete = deactivate), sign-in mode, change
//  PIN, app update and third-party licences. Push it from the profile screen.
//

import SwiftUI

struct DeviceSecurityView: View {
    @Environment(MasterControllerSession.self) private var session
    @Environment(BiometricSignIn.self) private var biometric
    private let monitor = SdkStatusMonitor.shared

    @State private var sdkState: KSMSdkState?
    @State private var deviceName = ""
    @State private var users: [UserRow] = []
    @State private var turnsOnBiometric = false
    @State private var update: String?
    @State private var licenses: [String: String] = [:]
    @State private var problem: String?
    @State private var editsName = false
    @State private var newName = ""
    @State private var userToDelete: UserRow?
    @State private var changesPin = false

    struct UserRow: Identifiable, Hashable {
        let id: String
        let name: String
    }

    var body: some View {
        List {
            Section("Status") {
                row("Connection", monitor.isOnline ? "Online" : "Offline", symbol: "antenna.radiowaves.left.and.right")
                row("SDK state", sdkState.map { Self.name(of: $0) } ?? "—", symbol: "cpu")
                if monitor.isMigrating {
                    row("Update", "Migrating data…", symbol: "arrow.triangle.2.circlepath")
                }
            }

            Section("This device") {
                Button {
                    newName = deviceName
                    editsName = true
                } label: {
                    SettingsRow(symbol: "iphone", title: "Device name", subtitle: deviceName.isEmpty ? "—" : deviceName)
                }
            }

            Section {
                ForEach(users) { user in
                    SettingsRow(symbol: "person.fill", title: user.name, subtitle: user.id == session.currentUserIdentifier ? "Signed in" : nil)
                        .swipeActions {
                            Button("Remove", role: .destructive) { userToDelete = user }
                        }
                }
            } header: {
                Text("Users on this iPhone")
            } footer: {
                Text("Removing the last user deactivates KOBIL on this iPhone.")
            }

            Section {
                if let name = biometric.biometryName {
                    Toggle(isOn: Binding(
                        get: { biometric.savedUserId != nil },
                        set: { on in
                            if on { turnsOnBiometric = true } else { biometric.forget() }
                        }
                    )) {
                        SettingsRow(symbol: name == "Touch ID" ? "touchid" : "faceid", title: "Sign in with \(name)", subtitle: biometric.savedUserId)
                    }
                } else {
                    SettingsRow(symbol: "faceid", title: "Face ID unavailable", subtitle: "Set up Face ID in Settings to sign in with it")
                }
                Button { changesPin = true } label: {
                    SettingsRow(symbol: "lock.rotation", title: "Change PIN", subtitle: "Only for accounts that use a KOBIL PIN")
                }
            } header: {
                Text("Sign-in")
            } footer: {
                if biometric.biometryName != nil {
                    Text("Your password is kept on this iPhone, protected by \(biometric.biometryName ?? "Face ID"). It is removed when Face ID changes.")
                }
            }

            Section("App") {
                Button {
                    run {
                        let info = try await session.updateInformation()
                        update = info.isUpdateAvailable ? "A newer version is available" : "Up to date"
                    }
                } label: {
                    SettingsRow(symbol: "arrow.down.app", title: "Check for updates", subtitle: update)
                }
                NavigationLink {
                    List(licenses.keys.sorted(), id: \.self) { name in
                        DisclosureGroup(name) { Text(licenses[name] ?? "").font(.kLabel) }
                    }
                    .navigationTitle("Licences")
                } label: {
                    SettingsRow(symbol: "doc.plaintext", title: "Third-party licences", subtitle: "\(licenses.count)")
                }
            }
        }
        .navigationTitle("Device and security")
        .task { await load() }
        .refreshable { await load() }
        .alert("Device name", isPresented: $editsName) {
            TextField("Name", text: $newName)
            Button("Save") {
                run {
                    try await session.setDeviceName(newName)
                    deviceName = newName
                }
            }
            Button("Cancel", role: .cancel) {}
        }
        .confirmationDialog("Remove \(userToDelete?.name ?? "")?", isPresented: Binding(get: { userToDelete != nil }, set: { if !$0 { userToDelete = nil } }), titleVisibility: .visible) {
            Button("Remove", role: .destructive) {
                guard let user = userToDelete else { return }
                run {
                    _ = try await session.deleteUser(userId: user.id)
                    await load()
                }
            }
        } message: {
            Text("Its keys are deleted from this iPhone. It has to be activated again to sign in.")
        }
        .sheet(isPresented: $changesPin) { ChangePinSheet() }
        .alert("Sign in with \(biometric.biometryName ?? "Face ID")", isPresented: $turnsOnBiometric) {
            Button("OK", role: .cancel) {}
        } message: {
            Text("Sign out, then sign in with your password and keep \"Sign in with \(biometric.biometryName ?? "Face ID") next time\" on.")
        }
        .alert("Not done", isPresented: Binding(get: { problem != nil }, set: { if !$0 { problem = nil } }), presenting: problem) { _ in
            Button("OK", role: .cancel) {}
        } message: { Text($0) }
    }

    private func load() async {
        sdkState = try? await session.sdkState()
        if let list = try? await session.activatedUsers() {
            users = list.map { UserRow(id: $0.userDetails.userIdentifier.userId, name: $0.userDetails.displayUsername.isEmpty ? $0.userDetails.userIdentifier.userId : $0.userDetails.displayUsername) }
        }
        if let user = try? session.loggedInUser(), let info = try? await session.deviceInformation(for: user) {
            deviceName = info.deviceName
        }
        licenses = (try? await session.thirdPartyLicenses()) ?? [:]
    }

    private func run(_ work: @escaping () async throws -> Void) {
        Task {
            do { try await work() } catch { problem = error.localizedDescription }
        }
    }

    private func row(_ title: String, _ value: String, symbol: String) -> some View {
        SettingsRow(symbol: symbol, title: title) {
            Text(value).font(.kText).foregroundStyle(Theme.textSecondary)
        }
    }

    static func name(of state: KSMSdkState) -> String {
        switch state {
        case .activationRequired: "Activation required"
        case .loginRequired: "Sign-in required"
        case .loggedIn: "Signed in"
        case .uninitialised: "Not started"
        case .unidentified: "Unidentified"
        @unknown default: "Unknown (\(state.rawValue))"
        }
    }
}

/// Change PIN (KSMStartChangePinEvent flow). The PINs are handed to the SDK and forgotten.
struct ChangePinSheet: View {
    @Environment(MasterControllerSession.self) private var session
    @Environment(\.dismiss) private var dismiss
    @State private var current = ""
    @State private var new = ""
    @State private var repeated = ""
    @State private var problem: String?
    @State private var isSubmitting = false

    var body: some View {
        NavigationStack {
            Form {
                SecureField("Current PIN", text: $current)
                SecureField("New PIN", text: $new)
                SecureField("Repeat new PIN", text: $repeated)
                if let problem {
                    Text(problem).foregroundStyle(Theme.danger)
                }
            }
            .keyboardType(.numberPad)
            .navigationTitle("Change PIN")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        isSubmitting = true
                        Task {
                            defer { isSubmitting = false }
                            do {
                                try await session.changePin(current: current, new: new)
                                dismiss()
                            } catch {
                                problem = error.localizedDescription
                            }
                        }
                    }
                    .disabled(current.isEmpty || new.isEmpty || new != repeated || isSubmitting)
                }
            }
        }
    }
}
