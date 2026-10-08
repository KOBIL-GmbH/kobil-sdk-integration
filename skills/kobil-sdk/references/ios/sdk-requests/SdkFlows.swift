//
//  SdkFlows.swift
//  KOBIL SDK reference implementation: the MCSDK's multi-step and administrative calls
//  (users, PIN, alternative logins, workspace, properties, endpoints, tracing, SSMS OTP,
//  anonymous users, app-initiated transactions, app update, HTTP and file upload).
//  Signatures are the SDK's own Swift interface (MCSDK iOS 15.16). `sdk-features.md`
//  records which ones ran on a device; the others compile and link only.
//
//  Never log PINs, tokens, OTPs, activation codes or response bodies.
//

import Foundation
import Synchronization

extension MasterControllerSession {

    // MARK: - PIN

    /// Change PIN: KSMStartChangePinEvent → MC asks with KSMStartSetNewPinEvent →
    /// KSMProvideSetNewPinEvent → KSMChangePinResultEvent. Only for PIN mode; an IDP-login
    /// user has no SDK PIN. Returns the SDK's retry counter on a wrong current PIN.
    func changePin(current: String, new: String) async throws {
        _ = try await awaitResult(of: KSMStartChangePinEvent()) { $0 is KSMStartSetNewPinEvent ? true : nil }
        let (status, retries) = try await awaitResult(of: KSMProvideSetNewPinEvent(currentPin: current, andPin: new)) {
            ($0 as? KSMChangePinResultEvent).map { ($0.status, $0.retryCounter) }
        }
        if status == .KSMINVALID_PIN {
            throw SdkRequestError.failed("The current PIN is wrong; \(retries) attempts left.")
        }
        try Self.require(status, "ChangePin")
    }

    // MARK: - Users on this device

    /// Activates another user next to the existing ones (KSMAddUserEvent → KSMAddUserResultEvent).
    /// The code comes from `sdk_activation_code_set`; the PIN is the new user's SDK PIN.
    func addUser(userId: String, activationCode: String, pin: String, autoLogin: Bool = true) async throws {
        let user = KsUserIdentifier(tenantId: Self.tenantId, userId: userId)
        let event = KSMAddUserEvent(userIdentifier: user, activationCode: activationCode, pin: pin, enableAutoLogin: autoLogin)
        let status = try await awaitResult(of: event, timeout: .seconds(60), requiresLogin: false) {
            ($0 as? KSMAddUserResultEvent)?.status
        }
        try Self.require(status, "AddUser")
    }

    /// KSMAddUserWithTokenEvent: adds a user with a token instead of a code and PIN.
    func addUser(userId: String, token: String, autoLogin: Bool = true) async throws {
        let user = KsUserIdentifier(tenantId: Self.tenantId, userId: userId)
        let status = try await awaitResult(
            of: KSMAddUserWithTokenEvent(userIdentifier: user, token: token, enableAutoLogin: autoLogin),
            timeout: .seconds(60), requiresLogin: false
        ) { ($0 as? KSMAddUserResultEvent)?.status }
        try Self.require(status, "AddUserWithToken")
    }

    /// Re-activates a user whose keys were revoked (KSMReactivationEvent → KSMReactivationResultEvent).
    func reactivate(userId: String, activationCode: String, pin: String, autoLogin: Bool = true) async throws {
        let user = KsUserIdentifier(tenantId: Self.tenantId, userId: userId)
        let event = KSMReactivationEvent(userIdentifier: user, activationCode: activationCode, pin: pin, enableAutoLogin: autoLogin)
        let status = try await awaitResult(of: event, timeout: .seconds(60), requiresLogin: false) {
            ($0 as? KSMReactivationResultEvent)?.reactivationStatus
        }
        try Self.require(status, "Reactivation")
    }

    /// Removes a user and its keys from this device (KSMDeleteUserEvent → KSMDeleteUserResultEvent).
    /// Deleting the last user is how a device is deactivated: the SDK returns to
    /// `.activationRequired`. Returns the new SDK state and the remaining user ids.
    func deleteUser(userId: String) async throws -> (sdkState: KSMSdkState, remainingUserIds: [String]) {
        let user = KsUserIdentifier(tenantId: Self.tenantId, userId: userId)
        let (status, state, remaining) = try await awaitResult(of: KSMDeleteUserEvent(userIdentifier: user), requiresLogin: false) {
            ($0 as? KSMDeleteUserResultEvent).map { ($0.status, $0.sdkState, $0.userList.map(\.userId)) }
        }
        try Self.require(status, "DeleteUser")
        return (state, remaining)
    }

    // MARK: - Other ways to log in

    /// KSMOfflineLoginEvent → KSMOfflineLoginResultEvent: log in without a network, with the
    /// offline tokens of an earlier online login. Returns the AST client id.
    func offlineLogin(userId: String) async throws -> String {
        let user = KsUserIdentifier(tenantId: Self.tenantId, userId: userId)
        let (status, clientId) = try await awaitResult(of: KSMOfflineLoginEvent(userIdentifier: user), requiresLogin: false) {
            ($0 as? KSMOfflineLoginResultEvent).map { ($0.status, $0.astClientId) }
        }
        try Self.require(status, "OfflineLogin")
        return clientId
    }

    /// KSMLoginWithTokenEvent: log in with an IAM access token and/or authorisation code your
    /// own IDP issued. It has no result event; the normal login result events follow.
    func loginWithToken(userId: String, mode: KSMAuthenticationMode, accessToken: String, authorizationCode: String) throws {
        let user = KsUserIdentifier(tenantId: Self.tenantId, userId: userId)
        try post(
            KSMLoginWithTokenEvent(parameters: user, authenticationMode: mode, iamAccessToken: accessToken, authorizationCode: authorizationCode),
            requiresLogin: false
        )
    }

    // MARK: - Anonymous users (needs backend support)

    /// KSMCreateAnonymousUserEvent: a temporary user id and activation code; the SDK deletes the
    /// user locally at the next restart. Never log the returned code.
    func createAnonymousUser(tenantId: String) async throws -> (userId: String, activationCode: String) {
        try await awaitResult(of: KSMCreateAnonymousUserEvent(tenantId: tenantId), requiresLogin: false) {
            ($0 as? KSMCreateAnonymousUserResultEvent).map { ($0.userId, $0.activationCode) }
        }
    }

    /// KSMEnrollAnonymousUserEvent (answered by KSMStatusResultEvent).
    func enrollAnonymousUser(tenantId: String, mode: KSMAuthenticationMode, clientId: String) async throws {
        try await awaitStatus(of: KSMEnrollAnonymousUserEvent(tenantId: tenantId, authenticationMode: mode, clientId: clientId), "EnrollAnonymousUser")
    }

    // MARK: - Workspace, nonce, properties

    /// KSMSwitchWorkspaceEvent (answered by KSMStatusResultEvent): move to another tenant.
    func switchWorkspace(tenantId: String) async throws {
        try await awaitStatus(of: KSMSwitchWorkspaceEvent(tenantId: tenantId), "SwitchWorkspace")
    }

    /// KSMProvideNonceEvent (answered by KSMStatusResultEvent): hands a nonce to the
    /// ast-webhooks service. Header: "supported only for Maverick".
    func provideNonce(_ nonce: String, action: String) async throws {
        try await awaitStatus(of: KSMProvideNonceEvent(nonce: nonce, action: action), "ProvideNonce")
    }

    struct SdkProperty: Sendable {
        let data: Data
        let type: KSMPropertyType
        let ttl: Int
        let flags: Int
    }

    /// KSMGetPropertyEvent → KSMGetPropertyResultEvent: a property the backend keeps for the
    /// device, the user or the group.
    func property(_ key: String, owner: KSMPropertyOwnerType) async throws -> SdkProperty {
        let (status, property) = try await awaitResult(of: KSMGetPropertyEvent(propertyKey: key, with: owner)) {
            ($0 as? KSMGetPropertyResultEvent).map {
                ($0.status, SdkProperty(data: $0.propertyData, type: $0.propertyType, ttl: $0.propertyTtl, flags: $0.propertyFlags))
            }
        }
        try Self.require(status, "GetProperty")
        return property
    }

    /// KSMSetPropertyEvent → KSMSetPropertyResultEvent.
    func setProperty(_ key: String, data: Data, type: KSMPropertyType, owner: KSMPropertyOwnerType, ttl: Int = 0, flags: Int = 0) async throws {
        let event = KSMSetPropertyEvent(propertyKey: key, withPropertyData: data, with: type, with: owner, withPropertyTtl: ttl, withPropertyFlags: flags)
        let status = try await awaitResult(of: event) { ($0 as? KSMSetPropertyResultEvent)?.status }
        try Self.require(status, "SetProperty")
    }

    // MARK: - Endpoints and tracing

    /// KSMConfigureRestEndpointEvent → KSMAcknowledgeEvent: points one SDK service (IAM, smart
    /// screen, AST, push) at another URL. Send before the feature is used, one at a time.
    func configureRestEndpoint(_ service: KSMRestEndpointIdentifier, url: String, certificateChain: Data) async throws {
        let data = KsRestEndpointData(restEndpointIdentifier: service, serverUrl: url, certificateChain: certificateChain)
        _ = try await awaitResult(of: KSMConfigureRestEndpointEvent(restEndpointData: data), requiresLogin: false) {
            $0 is KSMAcknowledgeEvent ? true : nil
        }
    }

    /// KSMEnableServerTracingEvent / KSMDisableServerTracingEvent: adds or removes the tracing
    /// header on the SDK's HTTP requests. No result event.
    func setServerTracing(_ enabled: Bool) throws {
        try post(enabled ? KSMEnableServerTracingEvent() : KSMDisableServerTracingEvent(), requiresLogin: false)
    }

    /// KSMEnableOpenCensusTracingEvent → KSMAcknowledgeEvent.
    func setOpenCensusTracing(_ enabled: Bool) async throws {
        _ = try await awaitResult(of: KSMEnableOpenCensusTracingEvent(tracingEnabled: enabled), requiresLogin: false) {
            $0 is KSMAcknowledgeEvent ? true : nil
        }
    }

    // MARK: - SSMS one-time password (needs an SSMS backend)

    /// KSMGenerateOtpEvent → KSMGenerateOtpResultEvent. Never log the OTP.
    func generateOtp(optionalData: Data = Data(), pin: String) async throws -> String {
        let (status, otp, retries) = try await awaitResult(of: KSMGenerateOtpEvent(optionalData: optionalData, pin: pin)) {
            ($0 as? KSMGenerateOtpResultEvent).map { ($0.status, $0.otp, $0.retry_counter) }
        }
        if status == .KSMINVALID_PIN {
            throw SdkRequestError.failed("Wrong PIN; \(retries) attempts left.")
        }
        try Self.require(status, "GenerateOtp")
        return otp
    }

    // MARK: - App-initiated transactions

    /// KSMInitiateTransactionEvent → KSMInitiateTransactionResultEvent: opens a secure channel to
    /// your server (the app starts it, not the backend). Returns the handle for the data calls.
    func initiateTransaction(url: String, certificates: Data, headers: [String: String] = [:], content: String, timeoutSeconds: Int32 = 30) async throws -> Int32 {
        let event = KSMInitiateTransactionEvent(fullUrl: url, certificates: certificates, httpHeaders: headers, content: content, timeout: timeoutSeconds)
        let (status, handle) = try await awaitResult(of: event, timeout: .seconds(Int(timeoutSeconds) + 10)) {
            ($0 as? KSMInitiateTransactionResultEvent).map { ($0.status, $0.handle) }
        }
        guard status == .ok else { throw SdkRequestError.failed("The transaction channel was not opened (status \(status.rawValue)).") }
        return handle
    }

    /// KSMInitiatedTransactionDataSendEvent → KSMAcknowledgeEvent, then waits for the server's
    /// KSMInitiatedTransactionDataReceivedEvent on the same handle (unless `closeSocket`).
    func sendOnTransaction(handle: Int32, content: String, closeSocket: Bool = false, timeout: Duration = .seconds(30)) async throws -> String? {
        let id = UUID()
        let reply = ReplyBox()
        SdkResultRouter.shared.register(id) { event in
            guard let data = event as? KSMInitiatedTransactionDataReceivedEvent, data.handle == handle else { return false }
            reply.set(status: data.status, content: data.content)
            return true
        }
        defer { SdkResultRouter.shared.remove(id) }
        _ = try await awaitResult(of: KSMInitiatedTransactionDataSendEvent(handle: handle, content: content, closeSocket: closeSocket)) {
            $0 is KSMAcknowledgeEvent ? true : nil
        }
        guard !closeSocket else { return nil }
        let deadline = ContinuousClock.now + timeout
        while ContinuousClock.now < deadline {
            if let (status, content) = reply.value {
                guard status == .ok else { throw SdkRequestError.failed("The server closed the transaction (status \(status.rawValue)).") }
                return content
            }
            try await Task.sleep(for: .milliseconds(100))
        }
        throw SdkRequestError.timedOut("InitiatedTransactionDataReceived")
    }

    // MARK: - App update

    /// KSMUpdateEvent → KSMUpdateResultEvent: runs the update `updateInformation()` announced.
    func performUpdate() async throws -> KSMUpdateStatus {
        try await awaitResult(of: KSMUpdateEvent(), timeout: .seconds(60)) { ($0 as? KSMUpdateResultEvent)?.updateStatus }
    }

    /// KSMOpenInfoUrlEvent → KSMOpenInfoUrlResultEvent: opens the update's info page in Safari.
    func openUpdateInfo() async throws -> KSMUpdateStatus {
        try await awaitResult(of: KSMOpenInfoUrlEvent()) { ($0 as? KSMOpenInfoUrlResultEvent)?.status }
    }

    // MARK: - HTTP through the SDK (your own backend, file upload)

    struct SdkHttpResponse: Sendable {
        let status: KSMCreateHttpCommonRequestStatus
        let httpStatus: Int
        let body: Data
    }

    /// KSMCreateHttpCommonRequestEvent → KSMCreateHttpCommonRequestResultEvent. With an
    /// `accessTokenIdentifier` from `iamAccessTokenIdentifier(...)` the SDK adds the user's
    /// bearer token itself, so the token never reaches app code. `certificate` is the server's
    /// trust chain (PEM); by default the chain the session was started with.
    func httpRequest(
        _ url: String,
        method: KSMCreateHttpCommonRequestHttpMethod = .get,
        body: String = "",
        contentType: String = "application/json",
        headers: [String: String] = [:],
        accessTokenIdentifier: String = "",
        certificate: Data? = nil
    ) async throws -> SdkHttpResponse {
        let event = KSMCreateHttpCommonRequestEvent(
            fullUrl: url, httpMethod: method, content: body, contentType: contentType,
            userName: "", password: "", certificate: certificate ?? certificateChain ?? Data(),
            httpHeaders: headers, cookieIdentifier: "", accessTokenIdentifier: accessTokenIdentifier
        )
        return try await awaitHttp(event)
    }

    /// File upload. `KsHttpMultiPart` (the SDK's multipart type) is declared in the 15.16 headers
    /// but missing from the binary, so a multipart request fails to link. Upload through the
    /// SDK as a JSON body with the file base64-encoded instead (your server must accept it),
    /// or with URLSession and a token from `exchangeIamToken(audience:)`.
    func upload(
        _ url: String,
        fileName: String,
        data: Data,
        mimeType: String,
        accessTokenIdentifier: String = "",
        certificate: Data? = nil
    ) async throws -> SdkHttpResponse {
        let payload = ["fileName": fileName, "contentType": mimeType, "content": data.base64EncodedString()]
        let body = String(decoding: try JSONSerialization.data(withJSONObject: payload), as: UTF8.self)
        return try await httpRequest(url, method: .post, body: body, accessTokenIdentifier: accessTokenIdentifier, certificate: certificate)
    }

    private func awaitHttp(_ event: KSMCreateHttpCommonRequestEvent) async throws -> SdkHttpResponse {
        let response = try await awaitResult(of: event, timeout: .seconds(60)) {
            ($0 as? KSMCreateHttpCommonRequestResultEvent).map {
                SdkHttpResponse(status: $0.status, httpStatus: Int($0.httpStatus), body: $0.response)
            }
        }
        guard response.status == .success else {
            throw SdkRequestError.failed("The request did not reach the server (status \(response.status.rawValue)).")
        }
        return response
    }
}

/// Holds the server's reply to an initiated transaction until the caller reads it.
nonisolated private final class ReplyBox: Sendable {
    private let stored = Mutex<(KSMInitiateTransactionStatus, String)?>(nil)

    var value: (KSMInitiateTransactionStatus, String)? { stored.withLock { $0 } }

    func set(status: KSMInitiateTransactionStatus, content: String) {
        stored.withLock { $0 = (status, content) }
    }
}
