//
//  CardFace.swift
//  KOBIL SDK reference implementation: wallet (app-side; makes no SDK call). See wallet.md.
//
//  A card drawn on the brand gradient: label, masked number, holder, expiry. Colours come
//  from Theme only, so a restyled Theme restyles the card.
//

import SwiftUI

struct CardFace: View {
    let card: WalletCard
    var isDefault = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .top) {
                Text(card.label.isEmpty ? card.network.name : card.label)
                    .font(.system(.headline, design: .rounded))
                    .foregroundStyle(.white)
                    .lineLimit(1)
                Spacer()
                if isDefault {
                    Text("Default")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(Theme.brandDeep)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(Capsule().fill(Theme.slider))
                }
            }
            Spacer(minLength: 16)
            Text("••••  ••••  ••••  \(card.lastFour)")
                .font(.system(.title3, design: .monospaced).weight(.medium))
                .foregroundStyle(.white)
                .minimumScaleFactor(0.7)
                .lineLimit(1)
            Spacer(minLength: 14)
            HStack(alignment: .bottom) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(card.holder.isEmpty ? " " : card.holder.uppercased())
                        .font(.caption.weight(.medium))
                        .foregroundStyle(.white.opacity(0.85))
                        .lineLimit(1)
                    Text(card.isExpired() ? "Expired \(card.expiryText)" : "Valid thru \(card.expiryText)")
                        .font(.caption2)
                        .foregroundStyle(card.isExpired() ? Theme.warning : .white.opacity(0.65))
                }
                Spacer()
                Text(card.network.name)
                    .font(.system(.subheadline, design: .rounded).weight(.bold))
                    .foregroundStyle(.white)
                    .lineLimit(1)
            }
        }
        .padding(20)
        .frame(maxWidth: .infinity)
        .aspectRatio(1.586, contentMode: .fit)
        .background(
            ZStack(alignment: .topTrailing) {
                RoundedRectangle(cornerRadius: 20, style: .continuous).fill(Theme.brandGradient)
                Circle()
                    .fill(Theme.slider.opacity(0.18))
                    .frame(width: 180, height: 180)
                    .offset(x: 60, y: -70)
            }
            .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .strokeBorder(.white.opacity(0.12), lineWidth: 1)
        )
        .shadow(color: .black.opacity(0.18), radius: 12, y: 6)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(card.shortName), expires \(card.expiryText)\(isDefault ? ", default card" : "")")
    }
}

#if DEBUG
extension WalletCard {
    static let sample = WalletCard(
        id: UUID(), network: .visa, lastFour: "4242", expiryMonth: 8, expiryYear: 2030,
        holder: "Alex Sample", label: "Everyday", addedAt: .now
    )
}

#Preview {
    CardFace(card: .sample, isDefault: true)
        .padding()
}
#endif
