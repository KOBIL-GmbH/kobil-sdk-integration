//
//  SdkFeatureTests.swift
//  KOBIL SDK reference implementation: Swift Testing unit tests for the transaction PIN/token
//  answer (TransactionCenter.secretRequest) and the sdk-requests helpers. Replace
//  `YourApp` with your app module.
//

import Foundation
import Testing
@testable import YourApp  // PER APP

@MainActor
struct TransactionSecretTests {
    private func center() -> (TransactionCenter, () -> [KsMacroEvent]) {
        let center = TransactionCenter(persisting: false)
        var sent: [KsMacroEvent] = []
        center.sender = { sent.append($0) }
        return (center, { sent })
    }

    @Test func pinIsSentOnceWithOk() throws {
        let (center, sent) = center()
        center.handleSecretRequired(.pin, timerSeconds: 60)
        #expect(center.secretRequest?.kind == .pin)
        center.provideSecret("1234")
        center.provideSecret("1234")
        #expect(sent().count == 1)
        let event = try #require(sent().first as? KSMProvidePinEvent)
        #expect(event.confirmationType == .ok)
        #expect(center.secretRequest?.isSubmitting == true)
    }

    @Test func tokenCancelSendsCancelAndCloses() throws {
        let (center, sent) = center()
        center.handleSecretRequired(.token, timerSeconds: 0)
        center.cancelSecret()
        let event = try #require(sent().first as? KSMProvideTokenEvent)
        #expect(event.confirmationType == .cancel)
        #expect(center.secretRequest == nil)
    }

    @Test func endSessionClearsTheRequest() {
        let (center, _) = center()
        center.handleSecretRequired(.pin, timerSeconds: 30)
        center.endSession()
        #expect(center.secretRequest == nil)
    }
}

@MainActor
struct SdkFeatureTests {
    @Test func updateStatusMeansUpdateAvailable() {
        let make = { (status: KSMEventStatusType) in
            MasterControllerSession.UpdateInformation(status: status, updateUrl: "", infoUrl: "", expiresInSeconds: 0)
        }
        #expect(make(.KSMUPDATE_AVAILABLE).isUpdateAvailable)
        #expect(make(.KSMUPDATE_NECESSARY).isUpdateAvailable)
        #expect(!make(.KSMOK).isUpdateAvailable)
    }

    @Test func sdkStatesHaveNames() {
        #expect(DeviceSecurityView.name(of: .loggedIn) == "Signed in")
        #expect(DeviceSecurityView.name(of: .activationRequired) == "Activation required")
    }
}
