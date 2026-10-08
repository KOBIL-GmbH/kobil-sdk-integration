//
//  WalletPaymentCard.swift
//  KOBIL SDK reference implementation: wallet (app-side; makes no SDK call). See wallet.md.
//
//  Connects the wallet to the TMS approval sheet: the default card is shown under "Pay with"
//  on a payment and its short name ("Visa •• 4242") is kept on the approval record.
//

import SwiftUI

extension View {
    /// Apply once, on the view that presents `ApprovalSheet`.
    func walletPaymentCard(_ wallet: WalletStore) -> some View {
        environment(\.paymentCard, wallet.defaultCard.map { card in
            PaymentCardDisplay(shortName: card.shortName, face: AnyView(CardFace(card: card)))
        })
    }
}
