//
//  MasterControllerSession.swift
//  KOBIL SDK iOS reference implementation, login-standards variant (kssidp / bddk)
//
//  Starts the KOBIL MasterController SDK and reports the SDK state it returns.
//
//  Use this file INSTEAD OF ../MasterControllerSession.swift when sdk_idp_journeys tags a
//  client with `login_standard`. First activation runs the official enrollment client through
//  KSSIDP (user ID + admin-issued activation code, for kssidp also the admin-issued temporary
//  password, then the user's new password; KssidpFormFlow.swift posts pages 2 and 3). Returning
//  login runs the standard's login client through KSSIDP with IdpActivation.swift. The user
//  types a user ID, not an email address. It also keeps a session event log and reads
//  KSMGetInformationEvent and the user's token claims (name, email).
//

import Foundation
import os
import Synchronization

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
    /// The SDK information the app requested after login.
    case information(SdkInformation)
    /// The MasterController's answer to an authorisation code the app handed over itself.
    case authorisationCodeResult(status: KSMEventStatusType, astClientId: String)
    /// The result of a KSMCreateHttpCommonRequestEvent, used by the headless activation.
    case httpResult(HeadlessHttpResponse)
    /// The IAM access token claims of the logged-in user: pushed by the SDK at login
    /// (KSMLoginTokenClaimsAvailableEvent, no status) or answered to KSMGetIamAccessTokenClaimsEvent.
    case tokenClaims(status: KSMEventStatusType?, claims: [String: String])
    /// KSMTriggerBannerEvent: the backend queued a transaction or a display message.
    case banner(type: KSMBannerType, payload: String, timerSeconds: Int)
    /// KSMDisplayConfirmationRequestEvent: a transaction waits for the user's decision.
    case confirmationRequested(timerSeconds: Int, information: String)
    /// KSMDisplayConfirmationResultEvent: the SDK's answer to the decision.
    case confirmationResult(status: KSMEventStatusType)
    /// KSMTransactionFinishedEvent: the terminal event of a transaction.
    case transactionFinished(status: KSMEventStatusType)
    /// KSMTransactionPinRequiredRequestEvent: the transaction needs the user's SDK PIN.
    case transactionPinRequired(timerSeconds: Int)
    /// KSMTransactionTokenRequiredRequestEvent: the transaction needs a token (OTP) instead.
    case transactionTokenRequired(timerSeconds: Int)
    /// KSMDisplayMessageEvent: a message the backend sent to this device.
    case displayMessage(information: String, type: KSMMessageType)

    struct SdkInformation: Sendable {
        let sdkVersion: String
        let certificateSerialNumber: String
        let loggedInUserId: String
    }

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
nonisolated final class MasterControllerEventReceiver: NSObject, KSAsyncEventReceiver {
    private let deliver: @Sendable (MasterControllerEvent) -> Void

    init(deliver: @escaping @Sendable (MasterControllerEvent) -> Void) {
        self.deliver = deliver
        super.init()
    }

    func receive(
        _ event: any KsEvent,
        withCompletionHandler completionBlock: (((any KsEvent)?) -> Void)?
    ) {
        // A result someone awaits with awaitResult(of:) goes to that caller only.
        if SdkResultRouter.shared.offer(event) {
            completionBlock?(nil)
            return
        }
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
        case let event as KSMSetAuthorisationCodeResultEvent:
            return .authorisationCodeResult(status: event.status, astClientId: event.astClientId)
        case let event as KSMCreateHttpCommonRequestResultEvent:
            return .httpResult(HeadlessHttpResponse(event))
        case let event as KSMLoginTokenClaimsAvailableEvent:
            return .tokenClaims(status: nil, claims: stringClaims(event.claims))
        case let event as KSMGetIamAccessTokenClaimsResultEvent:
            return .tokenClaims(status: event.status, claims: stringClaims(event.claims))
        case let event as KSMTriggerBannerEvent:
            return .banner(type: event.bannerType, payload: event.payload, timerSeconds: Int(event.timer))
        case let event as KSMDisplayConfirmationRequestEvent:
            return .confirmationRequested(timerSeconds: Int(event.timerValue), information: event.transactionInformation)
        case let event as KSMDisplayConfirmationResultEvent:
            return .confirmationResult(status: event.status)
        case let event as KSMTransactionFinishedEvent:
            return .transactionFinished(status: event.status)
        case let event as KSMTransactionPinRequiredRequestEvent:
            return .transactionPinRequired(timerSeconds: Int(event.timerValue))
        case let event as KSMTransactionTokenRequiredRequestEvent:
            return .transactionTokenRequired(timerSeconds: Int(event.timerValue))
        case let event as KSMDisplayMessageEvent:
            return .displayMessage(information: event.messageInformation, type: event.messageType)
        case let event as KSMGetInformationResultEvent:
            return .information(MasterControllerEvent.SdkInformation(
                sdkVersion: event.sdkVersion,
                certificateSerialNumber: event.serialNumber,
                loggedInUserId: event.loggedInUser.userId
            ))
        default:
            return .unhandled(name: event.getName())
        }
    }

    /// The SDK documents the claim values as stringified; anything else is described.
    private static func stringClaims(_ claims: [AnyHashable: Any]) -> [String: String] {
        var result: [String: String] = [:]
        for (key, value) in claims {
            guard let name = key as? String else { continue }
            result[name] = (value as? String) ?? String(describing: value)
        }
        return result
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
        /// KSMStartActivationUserIdAndCodeOnlyEvent arrived: the SDK is ready to be activated.
        case userIdAndCode
        /// KSMStartActivationSetPINEvent arrived.
        case password
        /// The headless activation journey is fetching or posting a page.
        case loadingPage
        /// The IDP rendered a step of the activation journey and waits for the user.
        case form(HeadlessForm, message: HeadlessPageMessage?)
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
        /// The headless email + emailed-code journey, run natively by HeadlessIdpFlow.
        case activation
        /// The KSSIDP or BDDK enrollment, run by KSSIDP: user id, admin-issued activation code,
        /// the admin-issued temporary password (KSSIDP only) and the password the user chooses.
        case bddkEnrollment(userId: String, activationCode: String, temporaryPassword: String?, password: String)
        /// The one-page login journey, run by KSSIDP.
        case login(userId: String, password: String)

        var isLogin: Bool {
            if case .login = self { return true }
            return false
        }
    }

    /// The AST app name, which is not necessarily the Xcode product name.
    // PER APP: fill in both values below, then delete this #error. The build fails until you do,
    // so a copied reference can never run against another app's backend registration.
    #error("PER APP: set appName to the AST app registered for THIS app with sdk_app_ensure, and tenantId to the tenant sdk_backend_status reports")
    static let appName = "<AST_APP_NAME>"  // PER APP: the AST app name registered with sdk_app_ensure for this app
    /// The AST tenant the app and its users belong to.
    static let tenantId = "<TENANT>"  // PER APP: the tenant from sdk_backend_status
    /// The IDP client whose journey logs an activated user in. Its flow asks for
    /// the user ID and password on a single page. mc_config.json
    /// iam.clientId must name this same client: the SDK exchanges the login tokens as
    /// iam.clientId (explicit-authentication TMS, ExchangeIamToken), and Keycloak lets a
    /// public client exchange only tokens it holds. The activation journeys pass their
    /// own client explicitly, so they do not depend on iam.clientId.
    static var loginClientId: String { loginStandard.loginClientId }
    /// The enrollment client, run by KSSIDP. Native KSSIDP apps never use the self-service V2 flows.
    static var enrollmentClientId: String { loginStandard.enrollmentClientId }

    /// The official KOBIL enrollment and login standards a native KSSIDP app can use.
    enum LoginStandard {
        /// "KSSIDP Enrollment - Multi form flow" / "KSSIDP Mobile App Multi Flow Login".
        /// Enrollment asks for the activation code, the temporary password, then a new password.
        case kssidp
        /// "BDDK Enrollment" / "BDDK Login"; the IDP deprecates its BDDK authenticators in 6.0.
        case bddk

        var loginClientId: String { self == .kssidp ? "KSSIDPWebBasedLogin" : "BDDKLogin" }
        var enrollmentClientId: String { self == .kssidp ? "KSSIDPWebBasedEnrollment" : "BDDKEnrollment" }
        var needsTemporaryPassword: Bool { self == .kssidp }
    }

    /// PER APP: must match the clients in mc_config.json iam.clientId and on the IDP.
    static let loginStandard: LoginStandard = .kssidp
    /// Both login flows bind the login to the activated user through this header.
    static let loginUserIdHeader = "X-KOBIL-ASTUSERID"
    /// Not used by the login standards (kept for apps that also offer self-service email sign-up).
    /// The self-service first-activation journeys, all headless-v2 pages that KSSIDP cannot run
    /// (their second page is dropped), so HeadlessIdpFlow runs them. Activation starts with
    /// registration; the IDP's own buttons switch between them, e.g.
    /// "log in" when the email already belongs to an account.
    enum ActivationJourney: String, Sendable {
        /// Email, then an emailed eTAN code; a new account also chooses its password.
        case registration
        /// Existing account: email + password, then the emailed code.
        case login
        /// Existing account without a known password: email, emailed code, new password.
        case forgotPassword

        var clientId: String {
            switch self {
            case .registration: return "IDPRegistrationHeadlessV2"  // PER REALM
            case .login: return "IDPLoginHeadlessV2"  // PER REALM
            case .forgotPassword: return "IDPForgotPasswordHeadlessV2"  // PER REALM
            }
        }

        /// The journey a headless button action names, if this app runs it.
        init?(action: String) {
            switch action {
            case "registration": self = .registration
            case "login": self = .login
            case "forgotPassword", "forgotPasswordActivation": self = .forgotPassword
            default: return nil
            }
        }
    }
    private static let appVersion = (major: 1, minor: 0, build: 0)  // PER APP: equals the version registered with sdk_app_version_ensure and the Xcode marketing version

    private static let mcConfigResource = (name: "mc_config", extension: "json")
    private static let sdkConfigResource = (name: "sdk_config", extension: "jwt")
    private static let certificateResource = (name: "isrg-root-x1", extension: "pem")  // PER APP: the file named in mc_config.json trustedSslServerCerts

    private static let log = Logger(subsystem: "com.example.kobilsdk", category: "MCSDK")  // PER APP: your bundle identifier

    private(set) var phase: Phase = .notStarted
    /// User identifiers the SDK reports as activated on this device.
    private(set) var activatedUserIdentifiers: [String] = []
    /// Last warning, runtime or fatal event, kept for on-screen diagnostics.
    private(set) var lastDiagnostic: String?
    /// The activation input the SDK is currently waiting for.
    private(set) var activationStep: ActivationStep = .none
    /// Where the login of an activated user stands.
    private(set) var loginStep: LoginStep = .none
    /// Every SDK event observed this session, newest last, shown on the Home screen.
    private(set) var sessionEvents: [SessionLogEntry] = []
    /// The activation journey that is running or ran last.
    private(set) var activationJourney: ActivationJourney = .registration
    /// What KSMGetInformationResultEvent reported after login.
    private(set) var sdkInformation: MasterControllerEvent.SdkInformation?
    /// The logged-in user's IAM access token claims, as the SDK reports them.
    private(set) var tokenClaims: [String: String] = [:]
    /// Why the claims could not be read, when the SDK refused them.
    private(set) var tokenClaimsError: String?

    /// The user's full name from the token: `name`, else given and family name.
    var userDisplayName: String? {
        if let name = tokenClaims["name"]?.trimmingCharacters(in: .whitespaces), !name.isEmpty {
            return name
        }
        let parts = [tokenClaims["given_name"], tokenClaims["family_name"]]
            .compactMap { $0?.trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
        return parts.isEmpty ? nil : parts.joined(separator: " ")
    }

    /// The user's email address from the token.
    var userEmail: String? {
        guard let email = tokenClaims["email"], !email.isEmpty else { return nil }
        return email
    }

    /// Transaction confirmations (payment approvals) and display messages for this device.
    let transactions: TransactionCenter

    init(transactions: TransactionCenter? = nil) {
        let transactions = transactions ?? TransactionCenter()
        self.transactions = transactions
        transactions.sender = { [weak self] event in
            self?.sendToController(event)
        }
    }

    /// Sends an event on behalf of a feature outside this class, such as the TMS handling.
    /// Refused while the SDK is not logged in, because its state machine answers with
    /// KSMInvalidStateEvent then.
    func sendToController(_ event: KsMacroEvent) {
        guard let controller, phase == .loggedIn else {
            Self.log.error("Event \(event.getName(), privacy: .public) not sent: the SDK is not logged in")
            return
        }
        send(event, through: controller)
    }

    /// Sends an event the SDK answers with no result event, or with notifications only
    /// (tracing, IsChatInitialised, LoginWithToken). `requiresLogin: false` once Start succeeded.
    func post(_ event: KsMacroEvent, requiresLogin: Bool = true) throws {
        guard let controller, !requiresLogin || phase == .loggedIn else { throw SdkRequestError.notLoggedIn }
        send(event, through: controller)
    }

    /// When the user's own logout was confirmed by the SDK's restart result.
    private(set) var loggedOutAt: Date?
    /// The SDK user identifier the device holds, once one is activated.
    var currentUserIdentifier: String? { activatedUserIdentifiers.first }

    struct SessionLogEntry: Identifiable, Equatable {
        let id = UUID()
        let date: Date
        let name: String
        let detail: String?
    }

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
    /// The native activation journey and the HTTP channel it runs over.
    private var headlessFlow: HeadlessIdpFlow?
    private var headlessTransport: HeadlessHttpTransport?
    private var kssidpFormFlow: KssidpFormFlow?
    private var headlessTask: Task<Void, Never>?
    /// Set while the activation's own KSMSetAuthorisationCodeEvent awaits its result, so a
    /// result KSSIDP triggered during a login is not taken for it.
    private var awaitsActivationCodeResult = false
    private var hasAppliedStartResult = false
    /// Kept from the start event, because the IDP enrolment needs the same chain.
    /// The bundled trust chain; KSMCreateHttpCommonRequestEvent needs it as `certificate`.
    private(set) var certificateChain: Data?

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
        cancelHeadlessActivation()
        releaseController()
        phase = .notStarted
        hasAppliedStartResult = false
        activationStep = .none
        loginStep = .none
    }

    /// Starts the first activation of this device. The MasterController refuses
    /// KSMProvideActivationCodeAndUserIdEvent with token based login, so the activation is an
    /// IDP journey whose authorisation code the app hands to the MasterController.
    ///
    /// The self-service journey: the IDP asks for email and password, emails a code and
    /// asks for it on a second page. Each page arrives as `activationStep = .form`; answer it
    /// with `submitActivationForm`. The AST client data comes first because the authorisation
    /// request must carry the PKCE challenge the MasterController derived from its verifier.
    func beginActivation(journey: ActivationJourney? = nil) {
        guard let controller else { return }
        switch activationStep {
        case .userIdAndCode, .failed: break
        default: return
        }
        activationJourney = journey ?? activationJourney
        guard certificateChain != nil else {
            activationStep = .failed(message: "The trusted certificate was not loaded at start.")
            return
        }
        pendingIdpRequest = .activation
        activationStep = .loadingPage
        Self.log.info("Requesting AST client data for the activation journey")
        send(KSMGetAstClientDataEvent(tenantId: Self.tenantId), through: controller)
    }

    /// Activates this device through the enrollment: the user id, one-time activation code and
    /// (KSSIDP) temporary password the administrator issued, and the password the user chooses.
    func activate(userId: String, activationCode: String, temporaryPassword: String? = nil, password: String) {
        guard let controller else { return }
        switch activationStep {
        case .userIdAndCode, .failed: break
        default: return
        }
        guard !userId.isEmpty, !activationCode.isEmpty else {
            activationStep = .failed(message: "Enter the user ID and the activation code.")
            return
        }
        guard Self.passwordMeetsPolicy(password) else {
            activationStep = .failed(message: Self.passwordPolicyDescription)
            return
        }
        guard certificateChain != nil else {
            activationStep = .failed(message: "The trusted certificate was not loaded at start.")
            return
        }
        if Self.loginStandard.needsTemporaryPassword, (temporaryPassword ?? "").isEmpty {
            activationStep = .failed(message: "Enter the temporary password you received.")
            return
        }
        pendingIdpRequest = .bddkEnrollment(
            userId: userId,
            activationCode: activationCode,
            temporaryPassword: Self.loginStandard.needsTemporaryPassword ? temporaryPassword : nil,
            password: password
        )
        activationStep = .submitting
        Self.log.info("Requesting AST client data for the enrollment")
        send(KSMGetAstClientDataEvent(tenantId: Self.tenantId), through: controller)
    }

    /// Leaves the running journey for another one the IDP offered. The new journey starts with fresh AST client data.
    func switchActivationJourney(to journey: ActivationJourney) {
        switch activationStep {
        case .form, .failed: break
        default: return
        }
        Self.log.info("Switching the activation journey to \(journey.rawValue, privacy: .public)")
        cancelHeadlessActivation()
        activationStep = .userIdAndCode
        beginActivation(journey: journey)
    }

    /// Answers the step the IDP rendered. `values` is keyed by the step's input keys.
    /// `onlyKeys` limits the answer to those inputs; the code step posts only the code.
    func submitActivationForm(_ form: HeadlessForm, values: [String: String], onlyKeys: Set<String>? = nil) {
        runHeadlessStep(from: form) { flow in
            try await flow.submit(form, values: values, onlyKeys: onlyKeys)
        }
    }

    /// Asks the IDP to email a new code, as the code step's resend action does.
    func resendActivationCode(_ form: HeadlessForm, values: [String: String]) {
        guard let otpField = form.otpField else { return }
        runHeadlessStep(from: form) { flow in
            try await flow.submit(form, values: values, resendKey: otpField.key)
        }
    }

    /// Answers a step's "resend email" button: only the user identity is posted, flagged.
    func resendActivationEmail(_ form: HeadlessForm, values: [String: String]) {
        let identityKey = "userIdentity"
        runHeadlessStep(from: form) { flow in
            try await flow.submit(form, values: values, action: "resendEmail", resendKey: identityKey, onlyKeys: [identityKey])
        }
    }

    private func runHeadlessStep(
        from form: HeadlessForm,
        _ operation: @escaping @MainActor (HeadlessIdpFlow) async throws -> HeadlessIdpFlow.Step
    ) {
        guard let headlessFlow, case .form(let current, _) = activationStep, current == form else { return }
        activationStep = .loadingPage
        headlessTask = Task { [weak self] in
            do {
                let step = try await operation(headlessFlow)
                self?.applyHeadlessStep(step)
            } catch {
                self?.failHeadlessActivation(error)
            }
        }
    }

    private func startHeadlessActivation(with clientData: MasterControllerEvent.AstClientData) {
        guard let controller, let certificateChain else { return }
        guard let mcConfig = try? loadConfigurationText(Self.mcConfigResource),
              let redirectUri = Self.redirectUri(inMcConfig: mcConfig),
              let url = Self.idpAuthorizationUrl(
                  inMcConfig: mcConfig,
                  clientId: activationJourney.clientId,
                  tenantId: Self.tenantId,
                  codeChallenge: clientData.codeChallenge,
                  codeChallengeMethod: clientData.codeChallengeMethod,
                  nonce: UUID().uuidString,
                  // These journeys activate the AST client inside their verify-identity or eTAN
                  // step and put the minted id into the token themselves, so the acr_values
                  // bypass is not needed; none is sent. Never add it here.
                  includesAcrBypass: false
              )
        else {
            activationStep = .failed(message: "The IDP client configuration is missing from mc_config.json.")
            return
        }
        let astClientId = clientData.astClientId.isEmpty
            ? IdpActivationRunner.nullAstClientId
            : clientData.astClientId
        Self.log.info("""
            Starting the \(self.activationJourney.rawValue, privacy: .public) journey \
            as AST client \(astClientId, privacy: .public)
            """)

        let transport = HeadlessHttpTransport(controller: controller, certificate: certificateChain)
        let flow = HeadlessIdpFlow(
            transport: transport,
            redirectUri: redirectUri,
            headers: [
                "Accept-Language": Self.locale(),
                "X-KOBIL-ASTCLIENTDATA": clientData.clientData,
                "X-KOBIL-ASTCLIENTID": astClientId,
            ]
        )
        headlessTransport = transport
        headlessFlow = flow
        headlessTask = Task { [weak self] in
            do {
                let step = try await flow.start(authorizationUrl: url)
                self?.applyHeadlessStep(step)
            } catch {
                self?.failHeadlessActivation(error)
            }
        }
    }

    private func applyHeadlessStep(_ step: HeadlessIdpFlow.Step) {
        headlessTask = nil
        switch step {
        case .form(let form, let message):
            if let message {
                Self.log.info("IDP notice on step \(form.formId, privacy: .public), code \(message.code ?? "none", privacy: .public)")
            }
            activationStep = .form(form, message: message)
        case .authorisationCode(let code):
            guard let controller else { return }
            releaseHeadlessFlow()
            activationStep = .submitting
            awaitsActivationCodeResult = true
            Self.log.info("Handing the activation authorisation code to the MasterController")
            send(
                KSMSetAuthorisationCodeEvent(
                    tenantId: Self.tenantId,
                    authenticationMode: .no,
                    authorisationCode: code,
                    clientId: activationJourney.clientId
                ),
                through: controller
            )
        }
    }

    private func failHeadlessActivation(_ error: any Error) {
        headlessTask = nil
        if case HeadlessIdpError.cancelled = error { return }
        Self.log.error("Headless activation failed: \(error.localizedDescription, privacy: .public)")
        releaseHeadlessFlow()
        activationStep = .failed(message: IdpErrorText.plain(
            error.localizedDescription,
            fallback: "Activation failed. Check what you entered and try again."
        ))
    }

    private func releaseHeadlessFlow() {
        headlessFlow = nil
        headlessTransport = nil
        kssidpFormFlow = nil
    }

    /// Posts the KSSIDP enrollment's pages natively (see KssidpFormFlow) and hands the
    /// authorisation code to the MasterController, which activates the device with it.
    private func startKssidpFormEnrollment(
        with clientData: MasterControllerEvent.AstClientData,
        credentials: KssidpFormFlow.Credentials
    ) {
        guard let controller, let certificateChain else { return }
        guard let mcConfig = try? loadConfigurationText(Self.mcConfigResource),
              let redirectUri = Self.redirectUri(inMcConfig: mcConfig),
              let url = Self.idpAuthorizationUrl(
                  inMcConfig: mcConfig,
                  clientId: Self.enrollmentClientId,
                  tenantId: Self.tenantId,
                  codeChallenge: clientData.codeChallenge,
                  codeChallengeMethod: clientData.codeChallengeMethod,
                  nonce: UUID().uuidString
              )
        else {
            activationStep = .failed(message: "The IDP client configuration is missing from mc_config.json.")
            return
        }
        let astClientId = clientData.astClientId.isEmpty
            ? IdpActivationRunner.nullAstClientId
            : clientData.astClientId
        Self.log.info("Starting the KSSIDP enrollment as AST client \(astClientId, privacy: .public)")

        let transport = HeadlessHttpTransport(controller: controller, certificate: certificateChain)
        let flow = KssidpFormFlow(
            transport: transport,
            redirectUri: redirectUri,
            headers: [
                "Accept-Language": Self.locale(),
                "X-KOBIL-ASTCLIENTDATA": clientData.clientData,
                "X-KOBIL-ASTCLIENTID": astClientId,
            ],
            credentials: credentials
        )
        headlessTransport = transport
        kssidpFormFlow = flow
        headlessTask = Task { [weak self] in
            do {
                let code = try await flow.run(authorizationUrl: url)
                guard let self, let controller = self.controller else { return }
                self.headlessTask = nil
                self.releaseHeadlessFlow()
                self.awaitsActivationCodeResult = true
                Self.log.info("Handing the KSSIDP enrollment's authorisation code to the MasterController")
                self.send(
                    KSMSetAuthorisationCodeEvent(
                        tenantId: Self.tenantId,
                        authenticationMode: .no,
                        authorisationCode: code,
                        clientId: Self.enrollmentClientId
                    ),
                    through: controller
                )
            } catch {
                self?.failHeadlessActivation(error)
            }
        }
    }

    /// Logs an activated user in. Token based login runs the same KSSIDP exchange
    /// as the activation, against the login client: the IDP authenticates the
    /// user, KSSIDP hands the authorisation code to the MasterController, and the
    /// MasterController exchanges it for the tokens it keeps for the session.
    /// `userId` is what the login journey asks for: the user ID the administrator issued.
    func login(userId: String, password: String) {
        guard let controller, phase == .loginRequired, loginStep != .submitting else { return }
        guard !userId.isEmpty, !password.isEmpty else {
            loginStep = .failed(message: "Enter the user ID and the password.")
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
        var extraHeaders: [String: String] = [:]
        switch request {
        case .activation:
            // The activation runs natively in HeadlessIdpFlow, never through KSSIDP.
            return
        case .bddkEnrollment(let userId, let activationCode, let temporaryPassword, let password):
            if Self.loginStandard == .kssidp {
                // The KSSIDP enrollment spans several pages, which KSSIDP cannot run.
                startKssidpFormEnrollment(
                    with: clientData,
                    credentials: .init(
                        userId: userId,
                        activationCode: activationCode,
                        temporaryPassword: temporaryPassword,
                        newPassword: password
                    )
                )
                return
            }
            clientIdOverride = Self.enrollmentClientId
            runner = IdpActivationRunner(
                userId: userId,
                activationCode: activationCode,
                temporaryPassword: temporaryPassword,
                password: password,
                deliver: deliverIdpEventOnMainActor()
            )
        case .login(let userId, let password):
            clientIdOverride = Self.loginClientId
            extraHeaders[Self.loginUserIdHeader] = userId
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
            tenantId: Self.tenantId,
            extraHeaders: extraHeaders
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
                The identity server did not answer. Check the user ID and password \
                and try again.
                """)
        }
    }

    /// Records a failure on the step the request belongs to.
    private func fail(_ request: PendingIdpRequest, with message: String) {
        switch request {
        case .activation, .bddkEnrollment:
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

    /// Abandons the activation journey and returns to the start, so the next attempt runs a
    /// fresh journey with fresh AST client data. Nothing is cancelled in the SDK: until the
    /// authorisation code is handed over, the journey only talks to the IDP. Once it has been
    /// handed over the MasterController's answer is awaited instead.
    func cancelActivation() {
        switch activationStep {
        case .loadingPage, .form, .failed: break
        default: return
        }
        Self.log.info("Cancelling the activation journey")
        cancelHeadlessActivation()
        activationJourney = .registration
        activationStep = .userIdAndCode
    }

    private func cancelHeadlessActivation() {
        if case .activation = pendingIdpRequest { pendingIdpRequest = nil }
        headlessTask?.cancel()
        headlessTask = nil
        headlessFlow?.cancel()
        kssidpFormFlow?.cancel()
        releaseHeadlessFlow()
    }

    /// Logs the user out. The SDK has no logout event: closing the session and
    /// re-authenticating is done by a restart, after which it reports login
    /// required again. Shift Lite would log the user in again from its cached IAM
    /// tokens, so the cache is cleared first (official docs: Logout). Nothing else
    /// may be sent to the SDK until the restart result has arrived.
    func logout() {
        guard controller != nil, phase == .loggedIn else { return }
        let user = try? loggedInUser()
        phase = .loggingOut
        loginStep = .none
        transactions.endSession()
        tokenClaims = [:]
        tokenClaimsError = nil
        sdkInformation = nil
        // The restart result is delivered like the start result, and the first
        // copy of it must be applied again.
        hasAppliedStartResult = false

        Task {
            if let user {
                do {
                    _ = try await awaitResult(
                        of: KSMClearIamTokenCacheEvent(userIdentifier: user),
                        timeout: .seconds(10),
                        requiresLogin: false
                    ) { ($0 as? KSMClearIamTokenCacheResultEvent) != nil ? true : nil }
                } catch {
                    // Restart anyway: staying in .loggingOut would block the app.
                    Self.log.error("Logging out: clearing the IAM token cache failed: \(String(describing: error), privacy: .public)")
                }
            }
            restartAfterLogout()
        }
    }

    private func restartAfterLogout() {
        guard let controller else { return }
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
            fail(request, with: IdpErrorText.plain(
                outcome.errorDescription,
                fallback: request.isLogin
                    ? "Sign-in failed. Check the user ID and password and try again."
                    : "Activation failed. Check what you entered and try again."
            ))
            return
        }

        switch request {
        case .activation:
            Self.log.info("Activation succeeded for the SDK user the IDP returned")
            activationStep = .activated
        case .bddkEnrollment:
            // KSSIDP's nested SetAuthorisationCode is OK: the device is activated and the SDK
            // holds this user's session tokens, as after the headless activation.
            Self.log.info("BDDK enrollment succeeded for the SDK user the IDP returned")
            activationStep = .activated
            loginStep = .loggedIn
            phase = .loggedIn
            requestInformation()
        case .login:
            Self.log.info("Login succeeded for the SDK user the IDP returned")
            loginStep = .loggedIn
            phase = .loggedIn
            requestInformation()
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
        logEvent(event)
        switch event {
        case .startResult(let outcome), .restartResult(let outcome):
            // The result can arrive both through the completion handler and
            // through the delegate; the first one wins.
            guard !hasAppliedStartResult else { return }
            hasAppliedStartResult = true
            if case .restartResult = event, phase == .loggingOut {
                loggedOutAt = Date()
            }
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
            switch request {
            case .activation:
                pendingIdpRequest = nil
                startHeadlessActivation(with: clientData)
            case .bddkEnrollment, .login:
                startIdpExchange(with: clientData)
            }
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
        case .information(let information):
            sdkInformation = information
        case .authorisationCodeResult(let status, _):
            applyActivationCodeResult(status)
        case .httpResult(let response):
            headlessTransport?.deliver(response)
        case .tokenClaims(let status, let claims):
            if let status, status != .KSMOK {
                Self.log.error("Access token claims refused: \(Self.statusName(status), privacy: .public)")
                tokenClaimsError = "The SDK did not return the account details: \(Self.statusName(status))."
            } else {
                tokenClaims = claims
                tokenClaimsError = nil
            }
        case .banner(let type, let payload, let timerSeconds):
            transactions.handleBanner(type: type, payload: payload, timerSeconds: timerSeconds)
        case .confirmationRequested(let timerSeconds, let information):
            transactions.handleConfirmationRequest(timerSeconds: timerSeconds, information: information)
        case .confirmationResult(let status):
            transactions.handleConfirmationResult(status)
        case .transactionFinished(let status):
            transactions.handleTransactionFinished(status)
        case .transactionPinRequired(let timerSeconds):
            transactions.handleSecretRequired(.pin, timerSeconds: timerSeconds)
        case .transactionTokenRequired(let timerSeconds):
            transactions.handleSecretRequired(.token, timerSeconds: timerSeconds)
        case .displayMessage(let information, let type):
            transactions.handleDisplayMessage(information: information, type: type)
        case .unhandled(let name):
            Self.log.debug("Unhandled SDK event \(name, privacy: .public)")
        }
    }

    /// The MasterController exchanged the activation's authorisation code for tokens, which
    /// activates the device and links it to the user the IDP authenticated.
    private func applyActivationCodeResult(_ status: KSMEventStatusType) {
        guard awaitsActivationCodeResult else { return }
        awaitsActivationCodeResult = false
        guard status == .KSMOK else {
            Self.log.error("Activation authorisation code rejected: \(Self.statusName(status), privacy: .public)")
            activationStep = .failed(message: """
                The identity server confirmed you, but the security SDK rejected the result \
                (SetAuthorisationCode \(Self.statusName(status))). Try again; if it repeats, \
                the device log names the cause.
                """)
            return
        }
        Self.log.info("Activation succeeded: SetAuthorisationCode OK")
        activationStep = .activated
        // The SDK logs the new user in with the tokens from this code (state Running), so the app continues signed in.
        loginStep = .loggedIn
        phase = .loggedIn
        requestInformation()
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
            requestInformation()
        default:
            phase = .notReady(stateValue: outcome.sdkState.rawValue)
        }
    }

    /// Asks the SDK for its version, certificate serial and logged-in user, and for the
    /// user's access token claims (name, email).
    func requestInformation() {
        guard let controller else { return }
        send(KSMGetInformationEvent(), through: controller)
        send(KSMGetIamAccessTokenClaimsEvent(), through: controller)
    }

    private func logEvent(_ event: MasterControllerEvent) {
        let entry: (name: String, detail: String?)
        switch event {
        case .startResult(let outcome):
            entry = ("StartResult", "\(Self.statusName(outcome.status)), SDK state \(outcome.sdkState.rawValue)")
        case .restartResult(let outcome):
            entry = ("RestartResult", "\(Self.statusName(outcome.status)), SDK state \(outcome.sdkState.rawValue)")
        case .warning(let diagnostic):
            entry = ("Warning", "code \(diagnostic.errorCode): \(diagnostic.errorDescription)")
        case .runtimeError(let diagnostic):
            entry = ("RuntimeError", "code \(diagnostic.errorCode): \(diagnostic.errorDescription)")
        case .fatalError(let diagnostic):
            entry = ("FatalError", "code \(diagnostic.errorCode): \(diagnostic.errorDescription)")
        case .activationCredentialsRequested:
            entry = ("StartActivationUserIdAndCodeOnly", "SDK asked for a user ID and activation code")
        case .activationPasswordRequested:
            entry = ("StartActivationSetPIN", "SDK asked for the activation credential")
        case .activationResult(let outcome):
            entry = ("ActivationResult", Self.statusName(outcome.status))
        case .invalidState(let message):
            entry = ("InvalidState", message)
        case .astClientData(let clientData):
            entry = ("GetAstClientDataResult", Self.statusName(clientData.status))
        case .loginOffered:
            entry = ("StartLogin", "SDK offered login for an activated user")
        case .information(let information):
            entry = ("GetInformationResult", "SDK version \(information.sdkVersion)")
        case .authorisationCodeResult(let status, _):
            entry = ("SetAuthorisationCodeResult", Self.statusName(status))
        case .httpResult(let response):
            entry = ("CreateHttpCommonRequestResult", "HTTP \(response.httpStatus)")
        case .tokenClaims(let status, let claims):
            // Claim names only: the values are personal data.
            let name = status == nil ? "LoginTokenClaimsAvailable" : "GetIamAccessTokenClaimsResult"
            let prefix = status.map { "\(Self.statusName($0)), " } ?? ""
            entry = (name, "\(prefix)\(claims.count) claims")
        case .banner(let type, _, let timerSeconds):
            entry = ("TriggerBanner", "\(type == .transaction ? "transaction" : "display message"), \(timerSeconds) s")
        case .confirmationRequested(let timerSeconds, _):
            entry = ("DisplayConfirmationRequest", "\(timerSeconds) s to decide")
        case .confirmationResult(let status):
            entry = ("DisplayConfirmationResult", Self.statusName(status))
        case .transactionFinished(let status):
            entry = ("TransactionFinished", Self.statusName(status))
        case .transactionPinRequired(let timerSeconds):
            entry = ("TransactionPinRequiredRequest", "\(timerSeconds) s")
        case .transactionTokenRequired(let timerSeconds):
            entry = ("TransactionTokenRequiredRequest", "\(timerSeconds) s")
        case .displayMessage(_, let type):
            entry = ("DisplayMessage", "type \(type.rawValue)")
        case .unhandled(let name):
            entry = (name, nil)
        }
        sessionEvents.append(SessionLogEntry(date: Date(), name: entry.name, detail: entry.detail))
        // The log is for diagnostics; the newest entries are enough.
        if sessionEvents.count > Self.sessionEventLimit {
            sessionEvents.removeFirst(sessionEvents.count - Self.sessionEventLimit)
        }
    }

    private static let sessionEventLimit = 200

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
    /// `clientId` overrides the client named in mc_config.json, which names the
    /// login client; the enrollment passes the enrollment client here.
    private static func idpAuthorizationUrl(
        inMcConfig mcConfig: String,
        clientId clientIdOverride: String? = nil,
        tenantId: String,
        codeChallenge: String,
        codeChallengeMethod: String,
        nonce: String,
        includesAcrBypass: Bool = true
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
        if !includesAcrBypass {
            components.queryItems?.removeAll { $0.name == "acr_values" }
        }
        return components.url?.absoluteString
    }

    /// The redirect URI named in mc_config.json; a journey ends when it is reached.
    private static func redirectUri(inMcConfig mcConfig: String) -> String? {
        (jsonObject(inMcConfig: mcConfig)?["iam"] as? [String: Any])?["redirectUri"] as? String
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

// MARK: - Request and result

/// Hands a result event to the caller that awaits it. The SDK may answer through the
/// send's completion handler or through the event receiver, so both ask the router first.
nonisolated final class SdkResultRouter: Sendable {
    static let shared = SdkResultRouter()

    private struct Waiter: Sendable {
        let id: UUID
        let take: @Sendable (any KsEvent) -> Bool
    }

    private let waiters = Mutex<[Waiter]>([])

    func register(_ id: UUID, take: @escaping @Sendable (any KsEvent) -> Bool) {
        waiters.withLock { $0.append(Waiter(id: id, take: take)) }
    }

    func remove(_ id: UUID) {
        waiters.withLock { $0.removeAll { $0.id == id } }
    }

    /// True when a waiter took the event.
    func offer(_ event: any KsEvent) -> Bool {
        let current = waiters.withLock { $0 }
        return current.contains { $0.take(event) }
    }
}

/// Resumes a continuation exactly once, whichever of result, error or timeout comes first.
nonisolated final class ResumeOnce<T: Sendable>: Sendable {
    private let continuation: Mutex<CheckedContinuation<T, any Error>?>

    init(_ continuation: CheckedContinuation<T, any Error>) {
        self.continuation = Mutex(continuation)
    }

    func resume(with result: Result<T, any Error>) {
        let pending = continuation.withLock { value -> CheckedContinuation<T, any Error>? in
            defer { value = nil }
            return value
        }
        pending?.resume(with: result)
    }
}

extension MasterControllerSession {
    enum SdkRequestError: LocalizedError {
        case notLoggedIn
        case timedOut(String)
        case refused(String)
        case invalidState(String)
        case failed(String)

        var errorDescription: String? {
            switch self {
            case .notLoggedIn: "Sign in first: the KOBIL SDK only does this for a signed-in user."
            case .timedOut(let name): "The KOBIL SDK did not answer \(name) in time."
            case .refused(let name): "The KOBIL SDK refused the request (\(name))."
            case .invalidState(let message): "The KOBIL SDK cannot do this right now: \(message) Try again when it is idle."
            case .failed(let message): message
            }
        }
    }

    /// What KSMSignDataResultEvent returns.
    struct SdkSignature: Sendable {
        let signedData: Data
        let signature: Data
    }

    /// Signs data with the logged-in user's KOBIL key (KSMSignDataEvent).
    func signData(_ data: Data) async throws -> SdkSignature {
        let result = try await awaitResult(of: KSMSignDataEvent(dataToSign: data), timeout: .seconds(60)) { event in
            (event as? KSMSignDataResultEvent).map { SdkSignature(signedData: $0.signedData, signature: $0.signature) }
        }
        Self.log.info("""
            SignData: \(data.count, privacy: .public) bytes in, signedData \(result.signedData.count, privacy: .public) \
            bytes, signature \(result.signature.count, privacy: .public) bytes
            """)
        return result
    }

    /// Stores a value in the SDK's encrypted per-user store (KSMSetUserDataEntryEvent).
    func storeUserData(_ value: String, forKey key: String) async throws {
        let user = try loggedInUser()
        let event = KSMSetUserDataEntryEvent(encryption: .encrypted, userIdentifier: user, key: key, value: value)
        let status = try await awaitResult(of: event) { event in
            (event as? KSMSetUserDataEntryResultEvent)?.status.rawValue
        }
        guard status == KSMDataModelRequestStatus.success.rawValue else {
            throw SdkRequestError.failed("The KOBIL SDK could not store the data (status \(status)).")
        }
    }

    /// Reads a value from the SDK's encrypted per-user store; nil when none is stored.
    func userData(forKey key: String) async throws -> String? {
        let user = try loggedInUser()
        let event = KSMGetUserDataEntryEvent(encryption: .encrypted, userIdentifier: user, key: key)
        let (status, value) = try await awaitResult(of: event) { event in
            (event as? KSMGetUserDataEntryResultEvent).map { ($0.status.rawValue, $0.value) }
        }
        switch status {
        case KSMDataModelRequestStatus.success.rawValue: return value.isEmpty ? nil : value
        case KSMDataModelRequestStatus.notExists.rawValue: return nil
        default: throw SdkRequestError.failed("The KOBIL SDK could not read the data (status \(status)).")
        }
    }

    /// The logged-in user as the SDK identifies it; throws before login.
    func loggedInUser() throws -> KsUserIdentifier {
        guard phase == .loggedIn, let userId = sdkInformation?.loggedInUserId ?? currentUserIdentifier else {
            throw SdkRequestError.notLoggedIn
        }
        return KsUserIdentifier(tenantId: Self.tenantId, userId: userId)
    }

    /// Sends one event and waits for the result event `extract` recognises.
    /// `requiresLogin: false` is for queries the SDK answers once Start has succeeded
    /// (state, user list, licences).
    func awaitResult<T: Sendable>(
        of event: KsMacroEvent,
        timeout: Duration = .seconds(20),
        requiresLogin: Bool = true,
        extract: @escaping @Sendable (any KsEvent) -> T?
    ) async throws -> T {
        guard let controller, !requiresLogin || phase == .loggedIn else { throw SdkRequestError.notLoggedIn }
        let name = event.getName()
        let id = UUID()
        defer { SdkResultRouter.shared.remove(id) }
        return try await withCheckedThrowingContinuation { continuation in
            let once = ResumeOnce(continuation)
            SdkResultRouter.shared.register(id) { event in
                // The SDK answers a request it will not run in its current state with
                // KSMInvalidStateEvent on the event channel instead of the result event (seen on
                // 15.16 for GetDeviceInformation and GetUpdateInformation). It names no request,
                // so keep one request in flight; without this the waiter only times out.
                if let invalid = event as? KSMInvalidStateEvent {
                    once.resume(with: .failure(SdkRequestError.invalidState(invalid.errorMessage)))
                    return true
                }
                guard let value = extract(event) else { return false }
                once.resume(with: .success(value))
                return true
            }
            controller.receive(event, withCompletionHandler: Self.resultHandler(once: once))
            Task {
                try? await Task.sleep(for: timeout)
                once.resume(with: .failure(SdkRequestError.timedOut(name)))
            }
        }
    }

    /// Built outside the main actor: the SDK calls it on its own thread.
    nonisolated private static func resultHandler<T: Sendable>(once: ResumeOnce<T>) -> @Sendable ((any KsEvent)?) -> Void {
        { result in
            guard let result, !SdkResultRouter.shared.offer(result) else { return }
            let name = result.getName()
            if name.contains("InvalidState") || name.contains("Error") {
                once.resume(with: .failure(SdkRequestError.refused(name)))
            }
        }
    }
}
