//
//  MasterControllerSession.swift
//  KOBIL SDK iOS reference implementation (verified on a device 2026-09-16/17)
//
//  Starts the KOBIL MasterController SDK and reports the SDK state it returns.
//

import Foundation
import os

/// Facts extracted from an SDK event while still on the SDK's own thread, so the
/// UI layer never has to reach into a non-Sendable Objective-C event object.
enum MasterControllerEvent: Sendable {
    case startResult(StartOutcome)
    case restartResult(StartOutcome)
    case warning(Diagnostic)
    case runtimeError(Diagnostic)
    case fatalError(Diagnostic)
    /// The SDK asks the app for a user identifier and an activation code.
    case activationCredentialsRequested
    /// The SDK asks the app for the credential that finishes the activation.
    case activationPasswordRequested
    /// The outcome of the activation the SDK was asked to perform.
    case activationResult(ActivationOutcome)
    /// The SDK refused an event because its state machine cannot accept it yet.
    case invalidState(message: String)
    /// The AST client data the authorisation request has to carry.
    case astClientData(AstClientData)
    /// The SDK offers login for an already activated user.
    case loginOffered
    case unhandled(name: String)

    struct StartOutcome: Sendable {
        let status: KSMEventStatusType
        let sdkState: KSMSdkState
        let userIdentifiers: [String]
        let errorCode: Int
        let reportId: Int
        let errorDescription: String
    }

    struct AstClientData: Sendable {
        let status: KSMEventStatusType
        /// The payload KSSIDP sends as X-KOBIL-ASTCLIENTDATA. Handing it over explicitly
        /// stops KSSIDP fetching its own, which would replace the PKCE pair below.
        let clientData: String
        /// The device's AST client id: the null ULID before activation, the minted
        /// id afterwards. A login presents it in X-KOBIL-ASTCLIENTID.
        let astClientId: String
        let codeChallenge: String
        let codeChallengeMethod: String
        let errorCode: Int
        let errorDescription: String
    }

    struct ActivationOutcome: Sendable {
        let status: KSMEventStatusType
        let errorCode: Int
        let reportId: Int
        let errorDescription: String
    }

    /// Warning, runtime-error and fatal-error events all carry these three fields.
    struct Diagnostic: Sendable {
        let errorType: KSMErrorType
        let errorCode: Int
        let errorDescription: String
        /// Only the warning event carries a separate representation string.
        let errorRepresentation: String?
    }
}

/// Receives the MasterController's asynchronous events and forwards the values
/// they carry. The SDK calls `receiveEvent` on its own threads, so this object
/// stays free of actor isolation and hands Sendable values to its consumer.
final class MasterControllerEventReceiver: NSObject, KSAsyncEventReceiver {
    private let deliver: @Sendable (MasterControllerEvent) -> Void

    init(deliver: @escaping @Sendable (MasterControllerEvent) -> Void) {
        self.deliver = deliver
        super.init()
    }

    func receive(
        _ event: any KsEvent,
        withCompletionHandler completionBlock: (((any KsEvent)?) -> Void)?
    ) {
        deliver(Self.value(of: event))
        completionBlock?(nil)
    }

    /// Maps an SDK event onto the subset of events this integration acts on.
    static func value(of event: any KsEvent) -> MasterControllerEvent {
        switch event {
        case let event as KSMStartResultEvent:
            return .startResult(outcome(
                status: event.status,
                sdkState: event.sdkState,
                userDetailsList: event.userDetailsList,
                userList: event.userList,
                errorCode: event.errorCode,
                reportId: event.reportId,
                errorDescription: event.errorDescription
            ))
        case let event as KSMRestartResultEvent:
            return .restartResult(outcome(
                status: event.status,
                sdkState: event.sdkState,
                userDetailsList: event.userDetailsList,
                userList: event.userList,
                errorCode: event.errorCode,
                reportId: event.reportId,
                errorDescription: event.errorDescription
            ))
        case let event as KSMWarningEvent:
            return .warning(MasterControllerEvent.Diagnostic(
                errorType: event.errorStatus,
                errorCode: Int(event.errorCode),
                errorDescription: event.errorDescription,
                errorRepresentation: event.errorRepresentation
            ))
        case let event as KSMErrorRuntimeEvent:
            return .runtimeError(MasterControllerEvent.Diagnostic(
                errorType: event.errorType,
                errorCode: Int(event.errorCode),
                errorDescription: event.errorDescription,
                errorRepresentation: nil
            ))
        case let event as KSMErrorFatalEvent:
            return .fatalError(MasterControllerEvent.Diagnostic(
                errorType: event.errorType,
                errorCode: Int(event.errorCode),
                errorDescription: event.errorDescription,
                errorRepresentation: nil
            ))
        case let event as KSMActivationResultEvent:
            return .activationResult(MasterControllerEvent.ActivationOutcome(
                status: event.activationStatus,
                errorCode: event.errorCode,
                reportId: event.reportId,
                errorDescription: event.errorDescription
            ))
        case let event as KSMInvalidStateEvent:
            return .invalidState(message: event.errorMessage)
        case let event as KSMGetAstClientDataResultEvent:
            return .astClientData(MasterControllerEvent.AstClientData(
                status: event.status,
                clientData: event.clientData,
                astClientId: event.astClientId,
                codeChallenge: event.codeChallange,
                codeChallengeMethod: event.codeChallangeMethod,
                errorCode: event.errorCode,
                errorDescription: event.errorDescription
            ))
        case is KSMStartActivationUserIdAndCodeOnlyEvent:
            return .activationCredentialsRequested
        case is KSMStartActivationSetPINEvent:
            return .activationPasswordRequested
        case is KSMStartLoginEvent:
            return .loginOffered
        default:
            return .unhandled(name: event.getName())
        }
    }

    private static func outcome(
        status: KSMEventStatusType,
        sdkState: KSMSdkState,
        userDetailsList: [KsUserDetails],
        userList: [KsUserIdentifier],
        errorCode: Int,
        reportId: Int,
        errorDescription: String
    ) -> MasterControllerEvent.StartOutcome {
        let identifiers = userDetailsList.isEmpty
            ? userList.map(\.userId)
            : userDetailsList.map { $0.userIdentifier.userId }
        return MasterControllerEvent.StartOutcome(
            status: status,
            sdkState: sdkState,
            userIdentifiers: identifiers,
            errorCode: errorCode,
            reportId: reportId,
            errorDescription: errorDescription
        )
    }
}

/// Failures that stop the SDK from being started at all.
enum MasterControllerStartupError: LocalizedError {
    case resourceMissingFromBundle(name: String)
    case resourceUnreadable(name: String, underlying: any Error)
    case configurationNotUTF8(name: String)
    case controllerUnavailable
    case moduleStartupRefused(KS_Result)
    case moduleNotRunning(KSMRunningStatus)

    var errorDescription: String? {
        switch self {
        case .resourceMissingFromBundle(let name):
            return "\(name) is not in the app bundle. Add it to Build Phases → Copy Bundle Resources."
        case .resourceUnreadable(let name, let underlying):
            return "\(name) could not be read: \(underlying.localizedDescription)"
        case .configurationNotUTF8(let name):
            return "\(name) is not valid UTF-8 text. Re-copy the file issued by the backend."
        case .controllerUnavailable:
            return "KSMasterControllerFactory returned no controller. Check that the KSMasterController framework is embedded and signed."
        case .moduleStartupRefused(let result):
            return "MasterController startup was refused with KS_Result \(result.rawValue)."
        case .moduleNotRunning(let status):
            return "MasterController did not start; running status is \(status.rawValue)."
        }
    }
}

/// Owns the MasterController instance and exposes the SDK state the start event
/// reports back, so the UI can branch between activation and login.
@MainActor
@Observable
final class MasterControllerSession {
    /// What the SDK has told us so far.
    enum Phase: Equatable {
        case notStarted
        case starting
        /// No user is activated on this device yet.
        case activationRequired
        /// At least one user is activated and must log in.
        case loginRequired
        case loggedIn
        /// A restart event is in flight; the SDK closes the session and reports
        /// its state again.
        case loggingOut
        /// The SDK reached a state this integration does not act on yet.
        case notReady(stateValue: Int)
        case failed(message: String)
    }

    /// Which activation input the SDK is waiting for, if any.
    enum ActivationStep: Equatable {
        case none
        /// KSMStartActivationUserIdAndCodeOnlyEvent arrived.
        case userIdAndCode
        /// KSMStartActivationSetPINEvent arrived.
        case password
        /// An event was sent to the SDK and its result has not arrived yet.
        case submitting
        case activated
        case failed(message: String)
    }

    /// Where a login of an activated user stands.
    enum LoginStep: Equatable {
        case none
        /// The IDP exchange is running and its result has not arrived yet.
        case submitting
        case loggedIn
        case failed(message: String)
    }

    /// The IDP request the app is about to run once the AST client data arrives.
    private enum PendingIdpRequest {
        case activation(userId: String, activationCode: String, password: String)
        case login(userId: String, password: String)

        var isLogin: Bool {
            if case .login = self { return true }
            return false
        }
    }

    /// The AST app name, which is not necessarily the Xcode product name.
    static let appName = "KOBILAPP"  // PER APP: the AST app name registered with sdk_app_ensure
    /// The AST tenant the app and its users belong to.
    static let tenantId = "superapp"  // PER APP: the tenant from the connection file
    /// The IDP client whose journey logs an activated user in. Its flow asks for
    /// the user's email address and password on a single page; mc_config.json
    /// names the activation client, which runs the activation-code journey instead.
    static let loginClientId = "IDPSubsequentLoginHeadlessV2"  // PER REALM: the subsequent-login client, see sdk_idp_clients
    private static let appVersion = (major: 1, minor: 0, build: 0)

    private static let mcConfigResource = (name: "mc_config", extension: "json")
    private static let sdkConfigResource = (name: "sdk_config", extension: "jwt")
    private static let certificateResource = (name: "isrg-root-x1", extension: "pem")  // PER APP: the file named in mc_config.json trustedSslServerCerts

    private static let log = Logger(subsystem: "com.example.kobilsdk", category: "MCSDK")

    private(set) var phase: Phase = .notStarted
    /// User identifiers the SDK reports as activated on this device.
    private(set) var activatedUserIdentifiers: [String] = []
    /// Last warning, runtime or fatal event, kept for on-screen diagnostics.
    private(set) var lastDiagnostic: String?
    /// The activation input the SDK is currently waiting for.
    private(set) var activationStep: ActivationStep = .none
    /// Where the login of an activated user stands.
    private(set) var loginStep: LoginStep = .none

    private var controller: (any KSAsyncEventReceiver & KSEcoModulInterface & KSEventSource)?
    private var eventReceiver: MasterControllerEventReceiver?
    private var idpRunner: IdpActivationRunner?
    /// The request held between the AST client data request and the IDP exchange.
    private var pendingIdpRequest: PendingIdpRequest?
    /// The request the running IDP exchange belongs to, so its result lands on the
    /// right step.
    private var runningIdpRequest: PendingIdpRequest?
    /// Ends an exchange that KSSIDP silently abandoned. On this IDP a rejected credential
    /// re-renders the form after the POST, and Keycloak writes an unescaped URL into that
    /// page's script, so KSSIDP discards it as malformed XML: no delegate call, no result,
    /// no error, ever. Without a deadline the app would show a spinner forever.
    private var idpDeadline: Task<Void, Never>?
    /// Long enough for the IDP round trips of a slow network, well under KSSIDP's own
    /// 60-second HTTP timeout so a genuine network stall is still reported by KSSIDP.
    private static let idpExchangeDeadlineSeconds: UInt64 = 40
    private var hasAppliedStartResult = false
    /// Kept from the start event, because the IDP enrolment needs the same chain.
    private var certificateChain: Data?

    /// Starts the SDK and sends the start event. Safe to call again after a failure.
    func start() {
        guard phase != .starting else { return }
        phase = .starting
        hasAppliedStartResult = false

        do {
            try sendStartEvent()
        } catch {
            releaseController()
            Self.log.error("SDK start failed before the start event: \(error.localizedDescription, privacy: .public)")
            phase = .failed(message: error.localizedDescription)
        }
    }

    /// Shuts the SDK down and forgets the controller.
    func shutDown() {
        releaseController()
        phase = .notStarted
        hasAppliedStartResult = false
        activationStep = .none
        loginStep = .none
    }

    /// Activates the user the SDK asked for. This AST backend uses token based
    /// login, so the enrolment runs through KSSIDP, which hands the resulting
    /// authorisation code to the MasterController itself. The MasterController
    /// refuses KSMProvideActivationCodeAndUserIdEvent in this configuration:
    /// its Maverick state machine is still uninitialised at this point and
    /// answers with KSMInvalidStateEvent.
    /// `password` is only forwarded if the IDP journey renders a password page; this
    /// deployment's journey does not, so it defaults to empty and is never sent.
    func activate(userId: String, activationCode: String, password: String = "") {
        guard let controller else { return }
        switch activationStep {
        case .userIdAndCode, .failed: break
        default: return
        }
        guard password.isEmpty || Self.passwordMeetsPolicy(password) else {
            activationStep = .failed(message: Self.passwordPolicyDescription)
            return
        }
        guard certificateChain != nil else {
            activationStep = .failed(message: "The trusted certificate was not loaded at start.")
            return
        }

        // The authorisation request has to carry the PKCE challenge the
        // MasterController derived from the code verifier it stores, so ask for
        // the AST client data first and build the URL from its result.
        pendingIdpRequest = .activation(userId: userId, activationCode: activationCode, password: password)
        activationStep = .submitting
        Self.log.info("Requesting AST client data for the authorisation request")
        send(KSMGetAstClientDataEvent(tenantId: Self.tenantId), through: controller)
    }

    /// Logs an activated user in. Token based login runs the same KSSIDP exchange
    /// as the activation, against the login client: the IDP authenticates the
    /// user, KSSIDP hands the authorisation code to the MasterController, and the
    /// MasterController exchanges it for the tokens it keeps for the session.
    /// `userId` is what the login journey asks for, the user's email address here.
    func login(userId: String, password: String) {
        guard let controller, phase == .loginRequired, loginStep != .submitting else { return }
        guard !userId.isEmpty, !password.isEmpty else {
            loginStep = .failed(message: "Enter the email address and the password.")
            return
        }
        guard certificateChain != nil else {
            loginStep = .failed(message: "The trusted certificate was not loaded at start.")
            return
        }

        pendingIdpRequest = .login(userId: userId, password: password)
        loginStep = .submitting
        Self.log.info("Requesting AST client data for the login request")
        send(KSMGetAstClientDataEvent(tenantId: Self.tenantId), through: controller)
    }

    private func startIdpExchange(with clientData: MasterControllerEvent.AstClientData) {
        guard let controller,
              let certificateChain,
              let request = pendingIdpRequest
        else {
            return
        }
        pendingIdpRequest = nil

        let clientIdOverride: String?
        let runner: IdpActivationRunner
        switch request {
        case .activation(let userId, let activationCode, let password):
            clientIdOverride = nil
            runner = IdpActivationRunner(
                userId: userId,
                activationCode: activationCode,
                password: password,
                deliver: deliverIdpEventOnMainActor()
            )
        case .login(let userId, let password):
            clientIdOverride = Self.loginClientId
            runner = IdpActivationRunner(
                userId: userId,
                password: password,
                deliver: deliverIdpEventOnMainActor()
            )
        }

        guard let mcConfig = try? loadConfigurationText(Self.mcConfigResource),
              let idpUrl = Self.idpAuthorizationUrl(
                  inMcConfig: mcConfig,
                  clientId: clientIdOverride,
                  tenantId: Self.tenantId,
                  codeChallenge: clientData.codeChallenge,
                  codeChallengeMethod: clientData.codeChallengeMethod,
                  nonce: UUID().uuidString
              )
        else {
            fail(request, with: "The IDP client configuration is missing from mc_config.json.")
            return
        }

        // Before activation the SDK reports no client id; AST then expects the
        // null ULID, which is also what its own client data blob declares.
        let astClientId = clientData.astClientId.isEmpty
            ? IdpActivationRunner.nullAstClientId
            : clientData.astClientId
        Self.log.info("""
            Starting IDP exchange for \(request.isLogin ? "login" : "activation", privacy: .public) \
            as AST client \(astClientId, privacy: .public)
            """)

        runningIdpRequest = request
        idpRunner = runner
        armIdpDeadline(for: request)
        runner.start(
            masterController: controller,
            url: idpUrl,
            certificateChain: certificateChain,
            astClientData: clientData.clientData,
            astClientId: astClientId,
            tenantId: Self.tenantId
        )
    }

    private func armIdpDeadline(for request: PendingIdpRequest) {
        idpDeadline?.cancel()
        idpDeadline = Task { [weak self] in
            try? await Task.sleep(nanoseconds: Self.idpExchangeDeadlineSeconds * 1_000_000_000)
            guard !Task.isCancelled, let self, self.idpRunner != nil else { return }
            Self.log.error("IDP exchange gave no result within \(Self.idpExchangeDeadlineSeconds, privacy: .public) s; cancelling")
            self.idpRunner?.cancel()
            self.idpRunner = nil
            self.runningIdpRequest = nil
            if let controller = self.controller {
                self.send(KSMCancelEvent(direction: .fromView), through: controller)
            }
            self.fail(request, with: """
                The IDP gave no answer within \(Self.idpExchangeDeadlineSeconds) seconds. On this IDP a \
                rejected credential is answered with a page the SDK cannot read, so a wrong \
                password looks exactly like this. Check the credentials and try again.
                """)
            // The failed state keeps the message on screen; the form is shown beneath it.
        }
    }

    /// Records a failure on the step the request belongs to.
    private func fail(_ request: PendingIdpRequest, with message: String) {
        switch request {
        case .activation:
            activationStep = .failed(message: message)
        case .login:
            loginStep = .failed(message: message)
        }
    }

    /// Answers KSMStartActivationSetPINEvent with the credential the backend policy expects.
    func submitActivationPassword(_ password: String) {
        guard let controller, activationStep == .password else { return }
        // The SDK calls this field a PIN; this deployment expects the backend
        // password, so the backend's policy is enforced before anything is sent.
        guard Self.passwordMeetsPolicy(password) else {
            activationStep = .failed(message: Self.passwordPolicyDescription)
            return
        }
        let event = KSMProvideSetPinEvent(pin: password, andEnableAutLogin: false)
        Self.log.info("Providing activation credential")
        activationStep = .submitting
        send(event, through: controller)
    }

    /// Cancels the activation, both the IDP enrolment and the SDK's own flow.
    func cancelActivation() {
        idpDeadline?.cancel()
        idpDeadline = nil
        idpRunner?.cancel()
        idpRunner = nil
        runningIdpRequest = nil
        pendingIdpRequest = nil
        guard let controller else { return }
        Self.log.info("Cancelling the running activation")
        send(KSMCancelEvent(direction: .fromView), through: controller)
        activationStep = .userIdAndCode
    }

    /// Logs the user out. The SDK has no logout event: closing the session and
    /// re-authenticating is done by a restart, after which it reports login
    /// required again. Nothing may be sent to the SDK until the restart result
    /// has arrived.
    func logout() {
        guard let controller, phase == .loggedIn else { return }
        phase = .loggingOut
        loginStep = .none
        // The restart result is delivered like the start result, and the first
        // copy of it must be applied again.
        hasAppliedStartResult = false

        let version = KSMVersion(
            majorVersion: Int32(Self.appVersion.major),
            minorVersion: Int32(Self.appVersion.minor),
            build: Int32(Self.appVersion.build)
        )
        let restartEvent = KSMRestartEvent(locale: Self.locale(), version: version, appName: Self.appName)
        if let mcConfig = try? loadConfigurationText(Self.mcConfigResource),
           let serverBackend = Self.astServerBackend(inMcConfig: mcConfig) {
            restartEvent.serverBackend = serverBackend
        }
        Self.log.info("Logging out: restarting the SDK")
        send(restartEvent, through: controller)
    }

    /// Cancels a running login and returns to the login form.
    func cancelLogin() {
        idpDeadline?.cancel()
        idpDeadline = nil
        idpRunner?.cancel()
        idpRunner = nil
        runningIdpRequest = nil
        pendingIdpRequest = nil
        guard let controller else { return }
        Self.log.info("Cancelling the running login")
        send(KSMCancelEvent(direction: .fromView), through: controller)
        loginStep = .none
    }

    /// The backend realm requires at least eight characters with an upper-case
    /// letter, a lower-case letter and a digit.
    static let passwordPolicyDescription =
        "The password needs at least eight characters, including an upper-case letter, a lower-case letter and a digit."

    /// The KSMEventStatusType cases an activation or login can return, named so a
    /// diagnostic reads "FAILED (39)" rather than a bare number.
    static func statusName(_ status: KSMEventStatusType) -> String {
        let name: String
        switch status {
        case .KSMOK: name = "OK"
        case .KSMUSER_CANCEL: name = "USER_CANCEL"
        case .KSMUSER_CONFIRMATION_TIMEOUT: name = "USER_CONFIRMATION_TIMEOUT"
        case .KSMINVALID_PIN: name = "INVALID_PIN"
        case .KSMUNKNOWN_VERSION: name = "UNKNOWN_VERSION"
        case .KSMUNKNOWN_CLIENT_TYPE: name = "UNKNOWN_CLIENT_TYPE"
        case .KSMWRONG_CREDENTIALS: name = "WRONG_CREDENTIALS"
        case .KSMUNKNOWN_CERTIFICATE: name = "UNKNOWN_CERTIFICATE"
        case .KSMINTERNAL_ERROR: name = "INTERNAL_ERROR"
        case .KSMACTIVATION_CODE_EXPIRED: name = "ACTIVATION_CODE_EXPIRED"
        case .KSMLOCKED_CERTIFICATE: name = "LOCKED_CERTIFICATE"
        case .KSMLOCKED_USER: name = "LOCKED_USER"
        case .KSMINVALID_STATE: name = "INVALID_STATE"
        case .KSMINVALID_PARAMETER: name = "INVALID_PARAMETER"
        case .KSMINVALID_USER_ID: name = "INVALID_USER_ID"
        case .KSMUSER_ID_ALREADY_EXISTS: name = "USER_ID_ALREADY_EXISTS"
        case .KSMREGISTER_APP: name = "REGISTER_APP"
        case .KSMMISMATCHED_USER: name = "MISMATCHED_USER"
        case .KSMTEMPORARY_LOCKED: name = "TEMPORARY_LOCKED"
        case .KSMINVALID_PASSWORD: name = "INVALID_PASSWORD"
        case .KSMPASSWORD_BLOCKED: name = "PASSWORD_BLOCKED"
        case .KSMNOT_REACHABLE: name = "NOT_REACHABLE"
        case .KSMPIN_BLOCKED: name = "PIN_BLOCKED"
        case .KSMACCESS_DENIED: name = "ACCESS_DENIED"
        case .KSMTENANT_ID_ALREADY_SET: name = "TENANT_ID_ALREADY_SET"
        case .KSMUNINITIALIZED: name = "UNINITIALIZED"
        case .KSMFAILED: name = "FAILED"
        case .KSMLOGIN_REQUIRED: name = "LOGIN_REQUIRED"
        case .KSMINVALID_TOKEN: name = "INVALID_TOKEN"
        case .KSMNOT_SUPPORTED: name = "NOT_SUPPORTED"
        case .KSMCONNECTION_LOST: name = "CONNECTION_LOST"
        case .KSMSERVER_CANCEL: name = "SERVER_CANCEL"
        default: name = "status"
        }
        return "\(name) (\(status.rawValue))"
    }

    static func passwordMeetsPolicy(_ password: String) -> Bool {
        password.count >= 8
            && password.contains(where: \.isUppercase)
            && password.contains(where: \.isLowercase)
            && password.contains(where: \.isNumber)
    }

    private func send(
        _ event: KsMacroEvent,
        through controller: any KSAsyncEventReceiver & KSEcoModulInterface & KSEventSource
    ) {
        let deliver = deliverOnMainActor()
        controller.receive(event) { resultEvent in
            guard let resultEvent else { return }
            deliver(MasterControllerEventReceiver.value(of: resultEvent))
        }
    }

    private func sendStartEvent() throws {
        let mcConfig = try loadConfigurationText(Self.mcConfigResource)
        let sdkConfig = try loadResource(Self.sdkConfigResource)
        let certificateChain = try loadResource(Self.certificateResource)
        self.certificateChain = certificateChain

        // The receiver has to exist before the start event is sent: the factory
        // registers it as an event delegate, so fatal errors raised during start
        // are delivered rather than lost.
        let receiver = MasterControllerEventReceiver(deliver: deliverOnMainActor())
        eventReceiver = receiver

        guard let controller = KSMasterControllerFactory.getMasterController(
            withParmeter: Self.appName,
            andConsumer: receiver
        ) else {
            throw MasterControllerStartupError.controllerUnavailable
        }
        self.controller = controller

        let startupResult = controller.startup(withParam: nil)
        guard startupResult == KS_Success else {
            throw MasterControllerStartupError.moduleStartupRefused(startupResult)
        }

        let runningStatus = controller.start()
        guard runningStatus == .running || runningStatus == .startInProgress else {
            throw MasterControllerStartupError.moduleNotRunning(runningStatus)
        }

        let version = KSMVersion(
            majorVersion: Int32(Self.appVersion.major),
            minorVersion: Int32(Self.appVersion.minor),
            build: Int32(Self.appVersion.build)
        )
        let appConfiguration = KSMSsmsAppConfiguration(
            locale: Self.locale(),
            version: version,
            name: Self.appName,
            sdkconfig: sdkConfig
        )
        // Category and tag name select SCP message categories. mc_config.json has
        // useScp disabled here, and the SDK only requires the two to be set
        // together, so both stay empty.
        let configurationData = KSMConfigurationData(category: "", tagName: "")
        let startEvent = KSMStartEventEx(
            ssmsAppConfiguration: appConfiguration,
            mcConfig: mcConfig,
            certificateChain: certificateChain,
            configurationData: configurationData,
            // The IAM chain must be passed explicitly; the SDK does not fall back
            // to certificateChain for it. Both endpoints are served off the same
            // Let's Encrypt root, and so is SmartScreen when it is enabled.
            iamCertificateChain: certificateChain,
            smartScreenCertificateChain: certificateChain
        )
        if let serverBackend = Self.astServerBackend(inMcConfig: mcConfig) {
            startEvent.serverBackend = serverBackend
        }

        let deliver = deliverOnMainActor()
        controller.receive(startEvent) { resultEvent in
            guard let resultEvent else { return }
            deliver(MasterControllerEventReceiver.value(of: resultEvent))
        }
    }

    /// A Sendable entry point KSSIDP's threads can use to reach this session.
    private func deliverIdpEventOnMainActor() -> @Sendable (IdpActivationEvent) -> Void {
        { [weak self] event in
            let session = self
            Task { @MainActor in
                session?.apply(event)
            }
        }
    }

    private func apply(_ event: IdpActivationEvent) {
        idpDeadline?.cancel()
        idpDeadline = nil
        idpRunner = nil
        guard let request = runningIdpRequest else {
            Self.log.error("An IDP result arrived with no request running; ignored")
            return
        }
        runningIdpRequest = nil
        let kind = request.isLogin ? "login" : "activation"

        switch event {
        case .formNotFillable(let unfilledKeys, let allKeys):
            Self.log.error("""
                IDP \(kind, privacy: .public) cancelled, unmapped fields: \
                \(unfilledKeys.joined(separator: ", "), privacy: .public) \
                of \(allKeys.joined(separator: ", "), privacy: .public)
                """)
            fail(request, with: """
                The IDP form asked for fields this app cannot fill \
                (\(unfilledKeys.joined(separator: ", "))). Nothing was submitted.
                """)
        case .finished(let outcome):
            applyIdpOutcome(outcome, for: request)
        }
    }

    private func applyIdpOutcome(_ outcome: IdpActivationEvent.Outcome, for request: PendingIdpRequest) {
        let kind = request.isLogin ? "Login" : "Activation"
        // KSSIDP reports its own status and nests the SetAuthorisationCode result
        // the MasterController returned; both have to be OK.
        let authorisationCodeAccepted = outcome.authorisationCodeStatus == .KSMOK
        guard outcome.status == .KSMOK, authorisationCodeAccepted else {
            let nested = outcome.authorisationCodeStatus.map { Self.statusName($0) } ?? "not reached"
            Self.log.error("""
                \(kind, privacy: .public) rejected: KSSIDP status \(outcome.status.rawValue, privacy: .public), \
                errorCode \(outcome.errorCode, privacy: .public), \
                reportId \(outcome.reportId, privacy: .public), \
                setAuthorisationCode status \(nested, privacy: .public)
                """)
            let explanation = outcome.errorDescription ?? "no explanation returned"
            fail(request, with: """
                \(kind) failed: KSSIDP \(Self.statusName(outcome.status)), \
                SetAuthorisationCode \(nested), code \(outcome.errorCode). \(explanation)
                """)
            return
        }

        switch request {
        case .activation:
            Self.log.info("Activation succeeded for the SDK user the IDP returned")
            activationStep = .activated
        case .login:
            Self.log.info("Login succeeded for the SDK user the IDP returned")
            loginStep = .loggedIn
            phase = .loggedIn
        }
    }

    /// A Sendable entry point the SDK's threads can use to reach this session.
    private func deliverOnMainActor() -> @Sendable (MasterControllerEvent) -> Void {
        { [weak self] event in
            // An immutable binding, so the hop to the main actor captures a value
            // rather than the weak reference itself.
            let session = self
            Task { @MainActor in
                session?.apply(event)
            }
        }
    }

    private func apply(_ event: MasterControllerEvent) {
        switch event {
        case .startResult(let outcome), .restartResult(let outcome):
            // The result can arrive both through the completion handler and
            // through the delegate; the first one wins.
            guard !hasAppliedStartResult else { return }
            hasAppliedStartResult = true
            applyStartOutcome(outcome)
        case .warning(let diagnostic):
            record(diagnostic, kind: "warning")
        case .runtimeError(let diagnostic):
            // A runtime error precedes the SDK's own restart, so readiness is gone.
            record(diagnostic, kind: "runtime error")
            hasAppliedStartResult = false
            phase = .starting
        case .fatalError(let diagnostic):
            record(diagnostic, kind: "fatal error")
            phase = .failed(message: "\(diagnostic.errorDescription) (code \(diagnostic.errorCode))")
        case .activationCredentialsRequested:
            Self.log.info("SDK requested a user identifier and an activation code")
            activationStep = .userIdAndCode
        case .activationPasswordRequested:
            Self.log.info("SDK requested the credential that completes the activation")
            activationStep = .password
        case .activationResult(let outcome):
            applyActivationOutcome(outcome)
        case .astClientData(let clientData):
            guard let request = pendingIdpRequest else { return }
            guard clientData.status == .KSMOK else {
                Self.log.error("""
                    AST client data rejected: \(Self.statusName(clientData.status), privacy: .public), \
                    errorCode \(clientData.errorCode, privacy: .public)
                    """)
                pendingIdpRequest = nil
                fail(request, with: """
                    Could not get the AST client data: \(Self.statusName(clientData.status)) \
                    (code \(clientData.errorCode)). \(clientData.errorDescription)
                    """)
                return
            }
            startIdpExchange(with: clientData)
        case .invalidState(let message):
            // The SDK refused the last event outright, so the step it was
            // answering has to become answerable again instead of waiting.
            Self.log.error("SDK refused the event: \(message, privacy: .public)")
            lastDiagnostic = "SDK refused the event: \(message)"
            if activationStep == .submitting {
                activationStep = .failed(message: "The SDK refused the request: \(message)")
            }
            if loginStep == .submitting {
                loginStep = .failed(message: "The SDK refused the request: \(message)")
            }
        case .loginOffered:
            Self.log.info("SDK offered login for an activated user")
        case .unhandled(let name):
            Self.log.debug("Unhandled SDK event \(name, privacy: .public)")
        }
    }

    private func applyActivationOutcome(_ outcome: MasterControllerEvent.ActivationOutcome) {
        guard outcome.status == .KSMOK else {
            Self.log.error("""
                Activation rejected: status \(outcome.status.rawValue, privacy: .public), \
                errorCode \(outcome.errorCode, privacy: .public), \
                reportId \(outcome.reportId, privacy: .public)
                """)
            Self.log.error("Activation rejection explanation: \(outcome.errorDescription)")
            let explanation = outcome.errorDescription.isEmpty
                ? "\(Self.statusName(outcome.status)), code \(outcome.errorCode)"
                : "\(outcome.errorDescription) (\(Self.statusName(outcome.status)), code \(outcome.errorCode))"
            activationStep = .failed(message: "Activation failed: \(explanation)")
            return
        }

        Self.log.info("Activation succeeded")
        activationStep = .activated
    }

    private func applyStartOutcome(_ outcome: MasterControllerEvent.StartOutcome) {
        activatedUserIdentifiers = outcome.userIdentifiers

        guard outcome.status == .KSMOK else {
            Self.log.error("""
                Start rejected: status \(outcome.status.rawValue, privacy: .public), \
                errorCode \(outcome.errorCode, privacy: .public), \
                reportId \(outcome.reportId, privacy: .public)
                """)
            Self.log.error("Start rejection explanation: \(outcome.errorDescription)")
            phase = .failed(
                message: "Start returned \(Self.statusName(outcome.status)) (code \(outcome.errorCode)): \(outcome.errorDescription)"
            )
            return
        }

        Self.log.info("""
            Start OK, sdkState \(outcome.sdkState.rawValue, privacy: .public), \
            \(outcome.userIdentifiers.count, privacy: .public) activated user(s)
            """)

        switch outcome.sdkState {
        case .activationRequired:
            phase = .activationRequired
        case .loginRequired:
            phase = .loginRequired
        case .loggedIn:
            phase = .loggedIn
        default:
            phase = .notReady(stateValue: outcome.sdkState.rawValue)
        }
    }

    private func record(_ diagnostic: MasterControllerEvent.Diagnostic, kind: String) {
        Self.log.error("""
            SDK \(kind, privacy: .public): errorType \(diagnostic.errorType.rawValue, privacy: .public), \
            errorCode \(diagnostic.errorCode, privacy: .public)
            """)
        Self.log.error("SDK \(kind, privacy: .public) explanation: \(diagnostic.errorDescription)")
        if let representation = diagnostic.errorRepresentation {
            Self.log.error("SDK \(kind, privacy: .public) representation: \(representation)")
        }
        lastDiagnostic = "\(kind) \(diagnostic.errorCode): \(diagnostic.errorDescription)"
    }

    private func releaseController() {
        guard controller != nil else { return }
        KSMasterControllerFactory.releaseMasterController()
        controller = nil
        eventReceiver = nil
    }

    private func loadResource(_ resource: (name: String, extension: String)) throws -> Data {
        let fileName = "\(resource.name).\(resource.extension)"
        guard let url = Bundle.main.url(forResource: resource.name, withExtension: resource.extension) else {
            throw MasterControllerStartupError.resourceMissingFromBundle(name: fileName)
        }
        do {
            return try Data(contentsOf: url)
        } catch {
            throw MasterControllerStartupError.resourceUnreadable(name: fileName, underlying: error)
        }
    }

    private func loadConfigurationText(_ resource: (name: String, extension: String)) throws -> String {
        let data = try loadResource(resource)
        guard let text = String(data: data, encoding: .utf8) else {
            throw MasterControllerStartupError.configurationNotUTF8(name: "\(resource.name).\(resource.extension)")
        }
        return text
    }

    /// The complete IDP authorisation request.
    ///
    /// KSSIDP sends this URL unchanged — it validates that the parameters are
    /// present but adds none of them — so the whole OAuth request has to be built
    /// here, including the PKCE challenge the MasterController derived. A request
    /// missing `response_type` is answered with a 302 to the redirect URI rather
    /// than the login form.
    /// `clientId` overrides the client named in mc_config.json; a login uses the
    /// login client while the configuration keeps naming the activation client.
    private static func idpAuthorizationUrl(
        inMcConfig mcConfig: String,
        clientId clientIdOverride: String? = nil,
        tenantId: String,
        codeChallenge: String,
        codeChallengeMethod: String,
        nonce: String
    ) -> String? {
        guard let iam = jsonObject(inMcConfig: mcConfig)?["iam"] as? [String: Any],
              let serverUrl = iam["serverUrl"] as? String,
              let configuredClientId = iam["clientId"] as? String,
              let redirectUri = iam["redirectUri"] as? String,
              var components = URLComponents(string: serverUrl)
        else {
            return nil
        }
        let clientId = clientIdOverride ?? configuredClientId
        components.path = "/auth/realms/\(tenantId)/protocol/openid-connect/auth"
        components.queryItems = [
            URLQueryItem(name: "client_id", value: clientId),
            URLQueryItem(name: "redirect_uri", value: redirectUri),
            URLQueryItem(name: "response_type", value: "code"),
            URLQueryItem(name: "scope", value: "openid"),
            // The IDP posts the result back as a form, which KSSIDP parses.
            URLQueryItem(name: "response_mode", value: "form_post"),
            URLQueryItem(name: "nonce", value: nonce),
            // Safe to send again: the AST client data is now handed to KSSIDP explicitly,
            // so it no longer fetches its own and no longer replaces this pair. Omitting
            // the challenge is not an option either, because KSSIDP always presents a
            // verifier at the token endpoint.
            URLQueryItem(name: "code_challenge", value: codeChallenge),
            URLQueryItem(name: "code_challenge_method", value: codeChallengeMethod),
            // Keycloak stores acr_values as a client note and copies it into the client
            // session at login. The IDP's AST token mapper only performs its token-time AST
            // login when that note is absent; with it present the mapper copies the client
            // id the activate step minted (user session note "astClientId") straight into
            // the token. That token-time login is what fails with 513_4036 on a first
            // activation, because it authenticates with the pre-activation client data blob.
            URLQueryItem(name: "acr_values", value: "1"),
        ]
        return components.url?.absoluteString
    }

    /// The backend named in mc_config.json, passed back to the SDK explicitly.
    private static func astServerBackend(inMcConfig mcConfig: String) -> String? {
        guard let backend = jsonObject(inMcConfig: mcConfig)?["astServerBackend"] as? String,
              !backend.isEmpty
        else {
            return nil
        }
        return backend
    }

    private static func jsonObject(inMcConfig mcConfig: String) -> [String: Any]? {
        guard let data = mcConfig.data(using: .utf8) else { return nil }
        return try? JSONSerialization.jsonObject(with: data) as? [String: Any]
    }

    /// The SDK expects a two-letter language code for its user-facing messages.
    private static func locale() -> String {
        guard let code = Locale.current.language.languageCode?.identifier, code.count == 2 else {
            return "en"
        }
        return code
    }
}
