//
//  SdkFeatureRequests.swift
//  KOBIL SDK reference implementation: typed async calls for the MCSDK's one-request,
//  one-result events. Every signature below is the SDK's own Swift interface (MCSDK iOS
//  15.16, from swift-synthesize-interface). The guide `sdk-features.md` records which
//  of them were answered on a device and which are only checked by the compiler.
//
//  Never log token or decrypted values; log sizes and statuses only.
//

import Foundation

/// Carries an SDK result object (an Objective-C class, not `Sendable`) from the SDK's
/// callback to the one caller awaiting it. The SDK hands it over once and does not touch it
/// again, so this transfer is safe; it is what lets these calls compile in Swift 6 mode.
nonisolated struct SdkHandover<Value>: @unchecked Sendable {
    let value: Value
}

extension MasterControllerSession {

    // MARK: - SDK and device state

    /// KSMGetSdkStateEvent (new in 15.16). Answers without a login.
    func sdkState() async throws -> KSMSdkState {
        try await awaitResult(of: KSMGetSdkStateEvent(ssmsUserCredentialPath: nil), requiresLogin: false) {
            ($0 as? KSMGetSdkStateResultEvent)?.sdkState
        }
    }

    /// KSMGetUserListEvent: every activated user on this device (Shift and SSMS).
    func activatedUsers() async throws -> [KsUserListEntry] {
        let (status, users) = try await awaitResult(of: KSMGetUserListEvent(ssmsUserCredentialPath: nil), requiresLogin: false) {
            ($0 as? KSMGetUserListResultEvent).map { SdkHandover(value: ($0.status, $0.userList)) }
        }.value
        try Self.require(status, "GetUserList")
        return users
    }

    /// KSMGetLoggedInUserEvent.
    func loggedInUserIdentifier() async throws -> KsUserIdentifier {
        try await awaitResult(of: KSMGetLoggedInUserEvent()) {
            ($0 as? KSMGetLoggedInUserResultEvent).map { SdkHandover(value: $0.userIdentifier) }
        }.value
    }

    /// KSMGetDeviceInformationEvent: the stored device id and name for a user.
    /// SSMS backend only: the value lives in the SSMS user store. With `astServerBackend`
    /// "maverick" the 15.16 lookup finds nothing and the SDK answers KSMInvalidStateEvent
    /// without a network call (device log, 2026-09-27), in every state.
    func deviceInformation(for user: KsUserIdentifier) async throws -> (deviceId: String, deviceName: String) {
        do {
            return try await awaitResult(of: KSMGetDeviceInformationEvent(userIdentifier: user), requiresLogin: false) {
                ($0 as? KSMGetDeviceInformationResultEvent).map { ($0.deviceId, $0.deviceName) }
            }
        } catch SdkRequestError.invalidState {
            throw SdkRequestError.failed("The KOBIL SDK keeps a device id and name only for SSMS users. This user was activated on the Maverick backend.")
        }
    }

    /// KSMSetDeviceNameEvent; needs a logged-in user.
    func setDeviceName(_ name: String) async throws {
        let status = try await awaitResult(of: KSMSetDeviceNameEvent(deviceName: name)) {
            ($0 as? KSMSetDeviceNameResultEvent)?.status
        }
        try Self.require(status, "SetDeviceName")
    }

    /// KSMRequestLicensesEvent: third-party licence name → text, for an About screen.
    func thirdPartyLicenses() async throws -> [String: String] {
        // Converted inside the handler: [AnyHashable: Any] is not Sendable.
        let licenses = try await awaitResult(of: KSMRequestLicensesEvent(), requiresLogin: false) { event -> [String: String]? in
            guard let event = event as? KSMRequestLicensesResultEvent else { return nil }
            var result: [String: String] = [:]
            for (key, value) in event.licenses {
                result["\(key)"] = "\(value)"
            }
            return result
        }
        return licenses
    }

    /// KSMSetLocalesEvent (answered by KSMStatusResultEvent). Header: "supported only for Maverick".
    func setLocales(_ locales: [String]) async throws {
        try await awaitStatus(of: KSMSetLocalesEvent(locales: locales), "SetLocales")
    }

    // MARK: - Authentication mode

    /// KSMEnableAuthenticationModeEvent (answered by KSMStatusResultEvent). `.biometric` needs
    /// NSFaceIDUsageDescription and a backend key policy that allows it.
    func enableAuthenticationMode(_ mode: KSMAuthenticationMode) async throws {
        try await awaitStatus(of: KSMEnableAuthenticationModeEvent(authenticationMode: mode), "EnableAuthenticationMode")
    }

    // MARK: - Push

    /// KSMSetPushTokenEvent after every successful login. The token needs the provider prefix:
    /// "APN:" + hex for native iOS ("FCM:" native Android, "FCMF:" Flutter). Without one the
    /// MasterController prepends "GCM:" and no push arrives (developer.kobil.com, Push Token).
    func setPushToken(_ deviceToken: Data) async throws {
        let token = "APN:" + deviceToken.map { String(format: "%02X", $0) }.joined()
        let status = try await awaitResult(of: KSMSetPushTokenEvent(pushToken: token)) {
            ($0 as? KSMSetPushTokenResultEvent)?.status
        }
        try Self.require(status, "SetPushToken")
    }

    /// KSMVerifyPushContentEvent: verifies a signed push payload; returns the verified content.
    func verifyPushContent(_ content: Data) async throws -> Data {
        let user = try loggedInUser()
        let (status, verified) = try await awaitResult(of: KSMVerifyPushContentEvent(userIdentifier: user, content: content)) {
            ($0 as? KSMVerifyPushContentResultEvent).map { ($0.status, $0.content) }
        }
        try Self.require(status, "VerifyPushContent")
        return verified
    }

    // MARK: - IAM tokens for the app's own backend

    /// KSMExchangeIamTokenEvent: an access token for `audience` (e.g.
    /// "userPortalPublic" for a KOBIL profile service). Never log the token.
    func exchangeIamToken(audience: String, forceUpdate: Bool = false) async throws -> String {
        let (status, token) = try await awaitResult(of: KSMExchangeIamTokenEvent(audience: audience, forceUpdate: forceUpdate)) {
            ($0 as? KSMExchangeIamTokenResultEvent).map { ($0.status, $0.token) }
        }
        try Self.require(status, "ExchangeIamToken")
        return token
    }

    /// KSMGetIamAccessTokenEvent. Returns an *identifier*, not the token: pass it as
    /// `accessTokenIdentifier` to KSMCreateHttpCommonRequestEvent and the SDK adds the token.
    func iamAccessTokenIdentifier(audience: String, scope: String, clientId: String) async throws -> String {
        let (status, identifier) = try await awaitResult(
            of: KSMGetIamAccessTokenEvent(audience: audience, withScope: scope, withClientId: clientId)
        ) {
            ($0 as? KSMGetIamAccessTokenResultEvent).map { ($0.status, $0.accessTokenIdentifier) }
        }
        try Self.require(status, "GetIamAccessToken")
        return identifier
    }

    /// KSMGetIamAuthorizationCodeEvent. Returns an identifier for the code, like the token call.
    func iamAuthorizationCodeIdentifier(audience: String, scope: String, clientId: String) async throws -> String {
        let (status, identifier) = try await awaitResult(
            of: KSMGetIamAuthorizationCodeEvent(audience: audience, withScope: scope, withClientId: clientId)
        ) {
            ($0 as? KSMGetIamAuthorizationCodeResultEvent).map { ($0.status, $0.authCodeIdentifier) }
        }
        try Self.require(status, "GetIamAuthorizationCode")
        return identifier
    }

    /// KSMClearIamTokenCacheEvent for the logged-in user.
    func clearIamTokenCache(_ behavior: KSMClearIamTokenCacheBehavior = .clearAccessAndRefresh) async throws {
        let event = KSMClearIamTokenCacheEvent(clear: behavior, with: try loggedInUser())
        _ = try await awaitResult(of: event) { ($0 as? KSMClearIamTokenCacheResultEvent) != nil ? true : nil }
    }

    /// KSMDeleteIamTokenByAudienceEvent (answered by KSMStatusResultEvent).
    func deleteIamTokens(audiences: [String]) async throws {
        try await awaitStatus(of: KSMDeleteIamTokenByAudienceEvent(audiences: audiences), "DeleteIamTokenByAudience")
    }

    // MARK: - Data

    /// KSMDecryptDataEvent: decrypts data encrypted for this device's public key.
    func decrypt(_ encrypted: Data) async throws -> Data {
        let (status, plain, sslError) = try await awaitResult(of: KSMDecryptDataEvent(encryptedData: encrypted)) {
            ($0 as? KSMDecryptDataResultEvent).map { ($0.status, $0.decryptedData, $0.openSslErrorCode) }
        }
        guard status == .KSMOK else {
            throw SdkRequestError.failed("The KOBIL SDK could not decrypt the data (status \(status.rawValue), OpenSSL \(sslError)).")
        }
        return plain
    }

    /// KSMGetDataEntryEvent: global, unencrypted, shared by all users. nil when absent.
    func globalValue(forKey key: String) async throws -> String? {
        let (status, value) = try await awaitResult(of: KSMGetDataEntryEvent(key: key), requiresLogin: false) {
            ($0 as? KSMGetDataEntryResultEvent).map { ($0.status, $0.value) }
        }
        switch status {
        case .success: return value
        case .notExists: return nil
        default: throw SdkRequestError.failed("GetDataEntry status \(status.rawValue)")
        }
    }

    /// KSMSetDataEntryEvent: global and unencrypted; never store secrets here.
    func setGlobalValue(_ value: String, forKey key: String) async throws {
        let status = try await awaitResult(of: KSMSetDataEntryEvent(key: key, withValue: value), requiresLogin: false) {
            ($0 as? KSMSetDataEntryResultEvent)?.status
        }
        guard status == .success else { throw SdkRequestError.failed("SetDataEntry status \(status.rawValue)") }
    }

    // Muting (KSMMuteCategoryEvent, KSMMuteAllEvent, KSMGetMutedEntriesEvent, …) is declared
    // in the 15.16 headers but not exported by any KSMasterController binary slice: using it
    // fails at link time ("Undefined symbols … KSMMuteCategoryEvent"). Do not wrap it.

    // MARK: - Update check

    struct UpdateInformation: Sendable {
        let status: KSMEventStatusType
        let updateUrl: String
        let infoUrl: String
        let expiresInSeconds: UInt

        var isUpdateAvailable: Bool { status == .KSMUPDATE_AVAILABLE || status == .KSMUPDATE_NECESSARY }
    }

    /// KSMGetUpdateInformationEvent → KSMUpdateInformationEvent. status `.KSMUPDATE_AVAILABLE`
    /// or `.KSMUPDATE_NECESSARY` means the backend wants a newer app version.
    /// SSMS backend only: the SDK hands the request to its SSMS module. With `astServerBackend`
    /// "maverick" that module has no handler ("Executor not exists for event:
    /// GetUpdateInformationEvent") and the SDK answers KSMInvalidStateEvent. No AST setting
    /// changes that; it never reaches the network.
    func updateInformation(requiresLogin: Bool = true) async throws -> UpdateInformation {
        do {
            return try await awaitResult(of: KSMGetUpdateInformationEvent(), requiresLogin: requiresLogin) {
                ($0 as? KSMUpdateInformationEvent).map {
                    UpdateInformation(status: $0.updateStatus, updateUrl: $0.updateUrl, infoUrl: $0.infoUrl, expiresInSeconds: $0.expiresInSeconds)
                }
            }
        } catch SdkRequestError.invalidState {
            throw SdkRequestError.failed("The KOBIL SDK checks for app updates only on the SSMS backend. This app uses the Maverick backend.")
        }
    }

    // MARK: - Helpers

    /// Waits for KSMStatusResultEvent, the SDK's shared status-only answer. Send one such
    /// request at a time: the event does not say which request it answers.
    func awaitStatus(of event: KsMacroEvent, _ name: String) async throws {
        let status = try await awaitResult(of: event) { ($0 as? KSMStatusResultEvent)?.status }
        try Self.require(status, name)
    }

    nonisolated static func require(_ status: KSMEventStatusType, _ name: String) throws {
        guard status == .KSMOK else {
            throw SdkRequestError.failed("\(name) answered status \(status.rawValue).")
        }
    }
}
