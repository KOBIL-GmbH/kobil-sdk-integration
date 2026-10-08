//
//  PushRegistration.swift
//  KOBIL SDK reference implementation: the APNs device token for KSMSetPushTokenEvent.
//
//  Follows the official "Push Token" page: register for remote notifications at launch, keep
//  the device token, and send it with SetPushTokenEvent after every successful login
//  (`setPushToken(_:)` in sdk-requests/SdkFeatureRequests.swift adds the "APN:" prefix).
//
//  Wiring:
//    - In the App: `@UIApplicationDelegateAdaptor(PushAppDelegate.self) private var pushDelegate`
//    - On the root view: `.sendsPushToken(to: session)`
//    - Signing & Capabilities: add Push Notifications (entitlement `aps-environment`).
//  Delivery also needs the app's APNs key in the KOBIL push service (backend setup).
//

import Observation
import SwiftUI
import UIKit
import UserNotifications
import os

@MainActor
@Observable
final class PushRegistration {
    static let shared = PushRegistration()

    /// The APNs device token; nil until iOS delivered one.
    private(set) var deviceToken: Data?

    private static let log = Logger(subsystem: Bundle.main.bundleIdentifier ?? "app", category: "Push")

    /// Asks for permission to show alerts, then registers with APNs. iOS hands out a token
    /// even when the user declines alerts, so registration runs either way.
    func register() async {
        do {
            let granted = try await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound])
            Self.log.info("Notification permission granted: \(granted, privacy: .public)")
        } catch {
            Self.log.error("Notification permission request failed: \(String(describing: error), privacy: .public)")
        }
        UIApplication.shared.registerForRemoteNotifications()
    }

    func didRegister(_ token: Data) {
        deviceToken = token
        Self.log.info("APNs device token received")
    }

    func didFail(_ error: Error) {
        Self.log.error("APNs registration failed: \(String(describing: error), privacy: .public)")
    }
}

/// The UIKit callbacks that deliver the APNs token to a SwiftUI app.
final class PushAppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        Task { await PushRegistration.shared.register() }
        return true
    }

    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        PushRegistration.shared.didRegister(deviceToken)
    }

    func application(_ application: UIApplication, didFailToRegisterForRemoteNotificationsWithError error: Error) {
        PushRegistration.shared.didFail(error)
    }
}

/// Sends the token after every successful login, and again when iOS issues a new token
/// while the user is logged in.
private struct PushTokenSender: ViewModifier {
    let session: MasterControllerSession
    private let push = PushRegistration.shared
    private static let log = Logger(subsystem: Bundle.main.bundleIdentifier ?? "app", category: "Push")

    private struct Trigger: Equatable {
        let loggedIn: Bool
        let token: Data?
    }

    func body(content: Content) -> some View {
        content.task(id: Trigger(loggedIn: session.phase == .loggedIn, token: push.deviceToken)) {
            guard session.phase == .loggedIn, let token = push.deviceToken else { return }
            do {
                try await session.setPushToken(token)
                Self.log.info("SetPushToken OK")
            } catch {
                Self.log.error("SetPushToken failed: \(String(describing: error), privacy: .public)")
            }
        }
    }
}

extension View {
    func sendsPushToken(to session: MasterControllerSession) -> some View {
        modifier(PushTokenSender(session: session))
    }
}
