//
//  ApprovalSheet.swift
//  KOBIL SDK reference implementation (email-code variant; verified on device)
//
//  The TMS confirmation overlay: a countdown
//  pill, the request as a bordered card of labelled rows, slide to accept, decline, and a
//  result screen the user closes with Done. Shown full screen over whatever is open.
//

import SwiftUI

/// The card a payment is approved with, shown under "Pay with" and recorded on the approval
/// as `ApprovalRecord.paidWith`. Nil (the default) hides the row. The wallet reference sets
/// it from the default card with `.walletPaymentCard(wallet)`; see wallet.md. Display only:
/// nothing about the card reaches the SDK or the backend.
struct PaymentCardDisplay {
    /// A short, non-sensitive name such as "Visa •• 4242".
    let shortName: String
    let face: AnyView
}

extension EnvironmentValues {
    @Entry var paymentCard: PaymentCardDisplay? = nil
}

struct ApprovalSheet: View {
    @Environment(TransactionCenter.self) private var transactions

    var body: some View {
        ZStack {
            Theme.panel.ignoresSafeArea()
            if let pending = transactions.pending {
                RequestView(pending: pending)
                    .transition(.opacity)
            } else if let record = transactions.lastFinished {
                ResultView(record: record) {
                    transactions.acknowledgeLastFinished()
                }
                .transition(.opacity.combined(with: .scale(scale: 0.98)))
            }
        }
        .animation(.smooth(duration: 0.35), value: transactions.pending?.id)
        .animation(.smooth(duration: 0.35), value: transactions.lastFinished?.id)
    }
}

// MARK: - Request

private struct RequestView: View {
    @Environment(TransactionCenter.self) private var transactions
    @Environment(\.paymentCard) private var card
    let pending: PendingApproval

    /// Only a payment that carries an amount is paid with a card.
    private var paymentCard: PaymentCardDisplay? {
        pending.isSignature || pending.content.amount == nil ? nil : card
    }

    var body: some View {
        TimelineView(.periodic(from: .now, by: 1)) { context in
            let expired = pending.deadline.map { context.date >= $0 } ?? false
            VStack(spacing: 16) {
                if let deadline = pending.deadline {
                    CountdownPill(remaining: max(0, deadline.timeIntervalSince(context.date)))
                }
                ScrollView {
                    VStack(spacing: 16) {
                        TransactionCard(pending: pending)
                        if let paymentCard {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Pay with")
                                    .font(.kLabelMedium)
                                    .foregroundStyle(Theme.textSecondary)
                                paymentCard.face
                                    .frame(maxWidth: 320)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .accessibilityElement(children: .combine)
                        }
                        Text(pending.isSignature
                             ? "Your signature is created on this iPhone and bound to this document."
                             : "Only accept requests you started yourself.")
                            .font(.kLabel)
                            .foregroundStyle(Theme.textSecondary)
                            .multilineTextAlignment(.center)
                    }
                }
                .scrollBounceBehavior(.basedOnSize)
                actions(expired: expired)
            }
            .padding(.horizontal, Theme.margin)
            .padding(.top, 24)
            .padding(.bottom, 20)
        }
    }

    @ViewBuilder
    private func actions(expired: Bool) -> some View {
        VStack(spacing: 8) {
            SlideToConfirm(
                title: pending.isSignature ? "Slide to sign" : "Slide to accept",
                isBusy: pending.decision == .approve
            ) {
                transactions.decide(approve: true, paidWith: paymentCard?.shortName)
            }
            .disabled(expired || pending.decision != nil)
            .sensoryFeedback(.success, trigger: pending.decision == .approve)

            Group {
                switch pending.decision {
                case .decline:
                    HStack(spacing: 8) {
                        ProgressView()
                        Text("Declining…")
                    }
                case .timeout:
                    Text("Time is up. Closing the request…")
                default:
                    Button {
                        transactions.decide(approve: false)
                    } label: {
                        Text("DECLINE")
                            .frame(maxWidth: .infinity, minHeight: 44)
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(Theme.danger)
                    .disabled(expired || pending.decision != nil)
                    .sensoryFeedback(.warning, trigger: pending.decision == .decline)
                }
            }
            .font(.kTextMedium)
            .foregroundStyle(pending.decision == nil ? Theme.danger : Theme.textSecondary)
            .frame(minHeight: 44)
        }
    }
}

/// Full-width bordered pill with a clock and the time left as mm:ss.
private struct CountdownPill: View {
    let remaining: TimeInterval

    private var text: String {
        let seconds = Int(remaining.rounded(.up))
        return String(format: "%02d:%02d", seconds / 60, seconds % 60)
    }

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: "clock")
                .font(.system(size: 16, weight: .regular))
            Text(text)
                .font(.kText.monospacedDigit())
                .contentTransition(.numericText(countsDown: true))
        }
        .foregroundStyle(remaining <= 10 ? Theme.danger : Theme.textPrimary)
        .frame(maxWidth: .infinity, minHeight: 40)
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .strokeBorder(Theme.tmsBorder, lineWidth: 1)
        )
        .animation(.default, value: text)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(Int(remaining.rounded(.up))) seconds left")
    }
}

/// The request: a centred header, then one labelled row per detail, in a bordered card.
private struct TransactionCard: View {
    let pending: PendingApproval

    private var header: String {
        pending.content.title ?? (pending.isSignature ? "Sign document" : "Confirm transaction")
    }

    private var rows: [TransactionContent.Detail] {
        let content = pending.content
        var rows: [TransactionContent.Detail] = []
        if pending.isSignature {
            if let name = content.documentName { rows.append(.init(label: "Document", value: name)) }
            if let hash = content.documentHash { rows.append(.init(label: "SHA-256 fingerprint", value: hash)) }
        }
        if let amount = content.amount, !content.details.contains(where: { $0.value == amount }) {
            rows.append(.init(label: "Amount", value: amount))
        }
        rows += content.details.filter { detail in
            !rows.contains { $0.value == detail.value }
        }
        rows.append(.init(label: "Received", value: pending.receivedAt.formatted(date: .abbreviated, time: .standard)))
        return rows
    }

    var body: some View {
        VStack(spacing: 0) {
            VStack(spacing: 4) {
                Text(header)
                    .font(.kTextMedium)
                    .foregroundStyle(Theme.textPrimary)
                Text(pending.content.text)
                    .font(.kLabel)
                    .foregroundStyle(Theme.textPrimary.opacity(0.64))
                    .textSelection(.enabled)
            }
            .multilineTextAlignment(.center)
            .frame(maxWidth: .infinity)
            .padding(.horizontal, 19)
            .padding(.top, 12)
            .padding(.bottom, 14)
            .overlay(alignment: .bottom) {
                Rectangle().fill(Theme.tmsBorder).frame(height: 1)
            }

            ForEach(Array(rows.enumerated()), id: \.offset) { index, row in
                VStack(alignment: .leading, spacing: 2) {
                    Text(row.label)
                        .font(.kLabel)
                        .foregroundStyle(Theme.textSecondary)
                    Text(row.value)
                        .font(row.label.hasPrefix("SHA-256") ? .footnote.monospaced() : .kText)
                        .foregroundStyle(Theme.textPrimary)
                        .textSelection(.enabled)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.leading, 13)
                .padding(.trailing, 13)
                .padding(.top, 11)
                .padding(.bottom, 13)
                .overlay(alignment: .bottom) {
                    if index < rows.count - 1 {
                        Rectangle().fill(Theme.tmsBorder).frame(height: 1)
                    }
                }
                .accessibilityElement(children: .combine)
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .strokeBorder(Theme.tmsBorder, lineWidth: 1)
        )
    }
}

/// Slide the thumb to the end to confirm; released early, it springs back. A deliberate
/// gesture, so a payment is never accepted by a stray tap. VoiceOver gets a plain action.
struct SlideToConfirm: View {
    @Environment(\.isEnabled) private var isEnabled
    let title: String
    var tint: Color = Theme.slider
    var isBusy = false
    let action: () -> Void

    @State private var offset: CGFloat = 0
    @State private var completed = false

    private let height: CGFloat = 52
    private let thumb: CGFloat = 46

    var body: some View {
        GeometryReader { proxy in
            let travel = max(0, proxy.size.width - thumb - 6)
            let progress = travel > 0 ? offset / travel : 0
            ZStack(alignment: .leading) {
                Capsule()
                    .strokeBorder(tint, lineWidth: 2)
                Text(title.uppercased())
                    .font(.system(size: 16, weight: .medium))
                    .tracking(0.5)
                    .foregroundStyle(tint)
                    .frame(maxWidth: .infinity)
                    .padding(.leading, thumb)
                    .opacity(1 - progress * 1.4)
                Capsule()
                    .fill(tint.opacity(0.08))
                    .frame(width: offset + thumb)
                    .padding(3)
                Circle()
                    .fill(tint)
                    .frame(width: thumb, height: thumb)
                    .overlay {
                        if isBusy || completed {
                            ProgressView().tint(.white)
                        } else {
                            Image(systemName: "arrow.right")
                                .font(.system(size: 20, weight: .semibold))
                                .foregroundStyle(.white)
                        }
                    }
                    .offset(x: 3 + offset)
                    .gesture(
                        DragGesture(minimumDistance: 2)
                            .onChanged { value in
                                guard isEnabled, !completed else { return }
                                offset = min(max(0, value.translation.width), travel)
                            }
                            .onEnded { _ in
                                guard isEnabled, !completed else { return }
                                if offset >= travel * 0.92 {
                                    withAnimation(.snappy(duration: 0.2)) { offset = travel }
                                    completed = true
                                    action()
                                } else {
                                    withAnimation(.spring(duration: 0.5)) { offset = 0 }
                                }
                            }
                    )
            }
        }
        .frame(height: height)
        .opacity(isEnabled || isBusy || completed ? 1 : 0.45)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(title)
        .accessibilityAddTraits(.isButton)
        .accessibilityAction {
            guard isEnabled, !completed else { return }
            completed = true
            action()
        }
    }
}

// MARK: - Result

private struct ResultView: View {
    let record: ApprovalRecord
    let done: () -> Void

    private var subject: String { record.isSignature ? "Document" : "Transaction" }

    private var title: String {
        switch record.outcome {
        case .approved: record.isSignature ? "Document signed" : "Transaction accepted"
        case .declined: "\(subject) declined"
        case .expired: "\(subject) timed out"
        case .cancelledByServer: "\(subject) withdrawn"
        case .failed: "\(subject) failed"
        }
    }

    private var message: String {
        switch record.outcome {
        case .approved: record.isSignature
            ? "Your signature was created on this iPhone and sent securely."
            : record.paidWith.map { "Paid \(record.amount.map { "\($0) " } ?? "")with \($0). Confirmed securely from this iPhone." }
                ?? "You accepted the request. It was confirmed securely from this iPhone."
        case .declined: "You declined the request. Nothing was confirmed."
        case .expired: "The time to answer ran out. Start the request again if you still need it."
        case .cancelledByServer: "The service withdrew the request before you answered."
        case .failed: "The answer could not be confirmed. Please try again."
        }
    }

    private var symbol: String {
        switch record.outcome {
        case .approved: "checkmark"
        case .declined: "xmark"
        case .expired: "clock.badge.exclamationmark"
        case .cancelledByServer: "arrow.uturn.backward"
        case .failed: "exclamationmark"
        }
    }

    var body: some View {
        GeometryReader { proxy in
            VStack(spacing: 0) {
                ZStack {
                    Circle()
                        .fill(Theme.color(for: record.outcome).opacity(0.1))
                        .frame(width: 132, height: 132)
                    Circle()
                        .fill(Theme.color(for: record.outcome))
                        .frame(width: 84, height: 84)
                    Image(systemName: symbol)
                        .font(.system(size: 36, weight: .semibold))
                        .foregroundStyle(.white)
                }
                .accessibilityHidden(true)
                Text(title)
                    .font(.kBodyTitle)
                    .foregroundStyle(Theme.textPrimary)
                    .padding(.top, 15)
                Text(message)
                    .font(.kText)
                    .foregroundStyle(Theme.textSecondary)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: proxy.size.width * 0.73)
                    .padding(.top, 8)
                Spacer()
                Button("Done", action: done)
                    .font(.kTextMedium)
                    .foregroundStyle(Theme.textPrimary)
                    .frame(maxWidth: .infinity, minHeight: 52)
                    .overlay(Capsule().strokeBorder(Theme.hairline, lineWidth: 1))
                    .contentShape(Capsule())
                    .buttonStyle(.plain)
            }
            .padding(.top, min(216, proxy.size.height * 0.2))
            .padding(.horizontal, Theme.margin)
            .padding(.bottom, 20)
            .frame(maxWidth: .infinity)
        }
        .sensoryFeedback(record.outcome == .approved ? .success : .warning, trigger: record.id)
    }
}


#if DEBUG
#Preview("Request") {
    ApprovalSheet()
        .environment(TransactionCenter.preview(pendingInformation: "Payment of EUR 249.90 to Apple Store, Munich", timerSeconds: 60))
}

#Preview("Signature") {
    ApprovalSheet()
        .environment(TransactionCenter.preview(pendingInformation: #"{"text":"Sign Rental-Contract.pdf","requestType":"signature","documentName":"Rental-Contract.pdf","documentSha256":"9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"}"#, timerSeconds: 90))
}
#endif
