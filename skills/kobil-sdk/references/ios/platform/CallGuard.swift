//
//  CallGuard.swift
//  KOBIL SDK reference implementation: scam-call protection with hnb's CallMonitor
//  (MCSDK 15.16). While a sensitive screen (approval, signing) is open, an active phone
//  call shows a warning. Needs CallKit linked (the hnb header says so).
//

import hnb
import SwiftUI

extension View {
    /// Monitors phone calls while this view is on screen. `.acknowledge` shows a warning the
    /// user dismisses after `seconds`; `.terminate` closes the app after `seconds` if the call
    /// continues. CallMonitor draws its own alert unless a delegate is set.
    func callGuard(_ flow: CallMonitorFlow = .acknowledge, seconds: Int32 = 5) -> some View {
        onAppear {
            let monitor = CallMonitor.sharedInstance()
            switch flow {
            case .terminate: monitor.startMonitoring(withTerminateIn: max(seconds, 1))
            default: monitor.startMonitoring(withAcknowledgeIn: max(seconds, 0))
            }
        }
        .onDisappear {
            CallMonitor.sharedInstance().stopMonitoring()
        }
    }
}
