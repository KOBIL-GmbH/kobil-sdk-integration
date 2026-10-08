//
//  SdkStatusMonitor.swift
//  KOBIL SDK reference implementation: the notifications the MasterController sends by itself
//  (connection, SSE stream, busy/idle, chat status, migration, IDP login required), published
//  for SwiftUI. It watches the event stream through SdkResultRouter without consuming
//  anything, so the session still sees every event.
//

import Foundation
import Observation

@MainActor
@Observable
final class SdkStatusMonitor {
    static let shared = SdkStatusMonitor()

    enum ChatStatus: String {
        case unknown, initialised, notInitialised, offline
    }

    private(set) var connection: KSMConnectionState = .KSMUndefined
    private(set) var sseStatus: KSMSseStatus?
    /// True between KSMBusyEvent and KSMIdleEvent; drive a spinner with it.
    private(set) var isBusy = false
    private(set) var chat: ChatStatus = .unknown
    /// True between KSMStartMigrationEvent and KSMMigrationFinishedEvent; keep users out of flows.
    private(set) var isMigrating = false
    /// Set by KSMIdpLoginRequiredEvent: the IDP session expired, run the login flow again.
    private(set) var idpLoginRequiredFor: String?

    var isOnline: Bool {
        switch connection {
        case .KSMConnected, .KSMReconnected, .KSMReachable: true
        default: false
        }
    }

    @ObservationIgnored private var started = false

    /// Call once, before the session sends its Start event, so the first notifications arrive.
    func start() {
        guard !started else { return }
        started = true
        SdkResultRouter.shared.register(UUID()) { [weak self] event in
            guard let update = Self.update(for: event) else { return false }
            Task { @MainActor [weak self] in self?.apply(update) }
            return false  // observe only: never take an event from the session
        }
    }

    func acknowledgeIdpLogin() { idpLoginRequiredFor = nil }

    /// Values copied off the SDK thread; the events themselves are not Sendable.
    private enum Update: Sendable {
        case connection(KSMConnectionState), sse(KSMSseStatus), busy(Bool), chat(ChatStatus), migrating(Bool), idpLogin(String)
    }

    nonisolated private static func update(for event: any KsEvent) -> Update? {
        switch event {
        case let e as KSMServerConnectionEvent: .connection(e.connectionStatus)
        case let e as KSMSseStreamStatusEvent: .sse(e.status)
        case is KSMBusyEvent: .busy(true)
        case is KSMIdleEvent: .busy(false)
        case is KSMChatInitialisedEvent: .chat(.initialised)
        case is KSMChatNotInitialisedEvent: .chat(.notInitialised)
        case is KSMChatOfflineInitialisedEvent: .chat(.offline)
        case is KSMStartMigrationEvent: .migrating(true)
        case is KSMMigrationFinishedEvent: .migrating(false)
        case let e as KSMIdpLoginRequiredEvent: .idpLogin(e.userIdentifier.userId)
        default: nil
        }
    }

    private func apply(_ update: Update) {
        switch update {
        case .connection(let state): connection = state
        case .sse(let status): sseStatus = status
        case .busy(let busy): isBusy = busy
        case .chat(let status): chat = status
        case .migrating(let migrating): isMigrating = migrating
        case .idpLogin(let userId): idpLoginRequiredFor = userId
        }
    }
}
