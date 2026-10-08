//
//  BiometricSignIn.swift
//  KOBIL SDK reference implementation: "Sign in with Face ID" for the IDP password login,
//  After a password sign-in the app keeps the password in
//  the Keychain behind Face ID (`.biometryCurrentSet`, this device only). The next sign-in
//  reads it with Face ID and runs the same login journey, so the tokens still belong to
//  mc_config.json iam.clientId and TMS and IAM token exchange keep working. No backend change.
//
//  Wiring: inject one instance with .environment(_:). In the login view call
//  rememberAfterSignIn(userId:password:) before session.login, and show "Sign in with Face ID"
//  when savedUserId is set: password(reason:) then session.login. Call commitPending() on
//  .loggedIn and discardPending() on .failed from an onChange(of: session.loginStep) in a view
//  that stays on screen (the root view), not in the login view: the login view is replaced the
//  moment the phase becomes loggedIn, so its onChange never fires and nothing is saved.
//  Needs NSFaceIDUsageDescription.
//
//  The SDK's own biometric mode (KSMEnableAuthenticationModeEvent(.biometric)) needs IDP
//  client scopes such as bio_auth_grant_SE that a Shift realm does not have; see
//  references/sdk-features.md, "Face ID".
//

import Foundation
import LocalAuthentication
import Observation
import Security

@Observable
final class BiometricSignIn {
    /// The account whose password is kept behind Face ID; nil when none is kept.
    private(set) var savedUserId: String?
    /// "Face ID", "Touch ID" or "Optic ID"; nil when the device has no enrolled biometry.
    private(set) var biometryName: String?

    /// PER APP: any service name unique to the app.
    private let service: String
    /// The account name is kept outside the Keychain item: reading any attribute of an item
    /// protected by `.biometryCurrentSet` without a prompt fails with -25308.
    private var accountKey: String { service + ".account" }
    private var pending: (userId: String, password: String)?

    init(service: String = (Bundle.main.bundleIdentifier ?? "app") + ".biometric-sign-in") {
        self.service = service
        refresh()
    }

    /// Re-reads biometry and the kept account; call when the app comes to the foreground.
    func refresh() {
        biometryName = Self.availableBiometry()
        savedUserId = UserDefaults.standard.string(forKey: accountKey)
    }

    /// Holds a password sign-in until it succeeds; the password is kept only then.
    func rememberAfterSignIn(userId: String, password: String) {
        pending = biometryName == nil ? nil : (userId, password)
    }

    /// Call when the login succeeded: keeps the held password behind Face ID.
    func commitPending() throws {
        guard let pending else { return }
        self.pending = nil
        try Self.save(service: service, userId: pending.userId, password: pending.password)
        UserDefaults.standard.set(pending.userId, forKey: accountKey)
        savedUserId = pending.userId
    }

    /// Call when the login failed or was cancelled.
    func discardPending() {
        pending = nil
    }

    /// Asks for Face ID and returns the kept password; nil when the user cancelled.
    /// Throws when the item is gone, for example after Face ID was re-enrolled.
    func password(reason: String) async throws -> String? {
        guard let userId = savedUserId else { return nil }
        let service = service
        let result = await Task.detached { Self.read(service: service, userId: userId, reason: reason) }.value
        switch result {
        case .success(let password):
            return password
        case .cancelled:
            return nil
        case .missing:
            UserDefaults.standard.removeObject(forKey: accountKey)
            savedUserId = nil
            throw BiometricSignInError.credentialGone
        case .failed(let status):
            throw BiometricSignInError.keychain(status)
        }
    }

    /// Stops signing in with Face ID and deletes the kept password.
    func forget() {
        pending = nil
        Self.delete(service: service)
        UserDefaults.standard.removeObject(forKey: accountKey)
        savedUserId = nil
    }

    // MARK: - Keychain

    private enum ReadResult: Sendable {
        case success(String), cancelled, missing, failed(OSStatus)
    }

    nonisolated private static func availableBiometry() -> String? {
        let context = LAContext()
        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: nil) else { return nil }
        switch context.biometryType {
        case .faceID: return "Face ID"
        case .touchID: return "Touch ID"
        case .opticID: return "Optic ID"
        default: return nil
        }
    }

    nonisolated private static func save(service: String, userId: String, password: String) throws {
        var error: Unmanaged<CFError>?
        guard let access = SecAccessControlCreateWithFlags(
            nil, kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly, .biometryCurrentSet, &error
        ) else {
            throw BiometricSignInError.accessControl(error?.takeRetainedValue().localizedDescription ?? "unknown")
        }
        delete(service: service)
        let item: [CFString: Any] = [
            kSecClass: kSecClassGenericPassword,
            kSecAttrService: service,
            kSecAttrAccount: userId,
            kSecAttrAccessControl: access,
            kSecValueData: Data(password.utf8),
        ]
        let status = SecItemAdd(item as CFDictionary, nil)
        guard status == errSecSuccess else { throw BiometricSignInError.keychain(status) }
    }

    /// Blocks while Face ID runs: call it off the main actor.
    nonisolated private static func read(service: String, userId: String, reason: String) -> ReadResult {
        let context = LAContext()
        context.localizedReason = reason
        context.localizedFallbackTitle = ""
        let query: [CFString: Any] = [
            kSecClass: kSecClassGenericPassword,
            kSecAttrService: service,
            kSecAttrAccount: userId,
            kSecReturnData: true,
            kSecMatchLimit: kSecMatchLimitOne,
            kSecUseAuthenticationContext: context,
        ]
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        switch status {
        case errSecSuccess:
            guard let data = item as? Data, let password = String(data: data, encoding: .utf8) else { return .failed(status) }
            return .success(password)
        case errSecUserCanceled: return .cancelled
        case errSecItemNotFound: return .missing
        default: return .failed(status)
        }
    }

    nonisolated private static func delete(service: String) {
        let query: [CFString: Any] = [kSecClass: kSecClassGenericPassword, kSecAttrService: service]
        SecItemDelete(query as CFDictionary)
    }
}

enum BiometricSignInError: LocalizedError {
    case credentialGone
    case accessControl(String)
    case keychain(OSStatus)

    var errorDescription: String? {
        switch self {
        case .credentialGone: "Face ID sign-in was turned off because Face ID changed on this iPhone. Sign in with your password to turn it on again."
        case .accessControl(let reason): "Face ID sign-in could not be set up: \(reason)"
        case .keychain(let status): "Face ID sign-in failed (Keychain status \(status)). Sign in with your password."
        }
    }
}
