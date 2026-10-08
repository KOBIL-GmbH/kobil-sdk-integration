# Wallet: payment cards in the app (iOS)

The KOBIL MCSDK has **no wallet, card or payment-method API**. A wallet is app code: it lists
the user's cards, and the TMS approval shows which card a payment is approved with. The SDK
still does the part that matters for security: the user's acceptance of the payment
transaction is signed on the device (`sdk_tms_result` reports `signed_data_present`).

Status: **compiled** (Swift 5 and 6, debug and release, `kobil-sdk-refcheck`). A payment with
this wallet installed was approved on an iPhone (2026-09-28, TMS result ACCEPTED with signed
data), but the "Pay with" row on that approval was not checked on screen: do that on the
first device test and say so until then.

## Rules (keep these whatever the design)

- **Never store or log the full card number (PAN) or the security code (CVV/CVC).** Check the
  typed number (length and Luhn), then keep only the network, the last four digits, the
  expiry, the holder name and a label. Never ask for the security code: nothing here needs it,
  and storing it is forbidden under PCI DSS.
- Keep the wallet in the **Keychain**, one item per signed-in user, with
  `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` (never synced, never in a backup). Load it
  after login, forget it in memory on logout; do not show one user's cards to another.
- Nothing about the card goes to the KOBIL backend. `paidWith` (for example "Visa •• 4242")
  is a local label on the approval record, for the user's history only.
- The card shown on an approval **does not make a payment**. Charging a card needs a payment
  provider: Apple Pay (PassKit) or the provider's own SDK, which returns a token the
  customer's backend charges. Say so when the customer asks for "real" payments; building a
  card-charging flow is outside this plugin.
- Show the card only on requests that carry an amount; never on a signature request.

## Files (`references/ios/wallet/`)

| File | Role |
|---|---|
| `WalletCard.swift` | The card model (network, last four, expiry, holder, label, `shortName`) and `CardInput`: digit filter, Luhn check, network from the leading digits, 4-4-4-4 / 4-6-5 grouping, MM/YY parsing |
| `WalletStore.swift` | `@Observable` store: `load(for:)`, `reset()`, `add`, `rename`, `makeDefault`, `remove`; writes the Keychain first and publishes only what was stored. PER APP: the Logger subsystem |
| `CardFace.swift` | The card visual on `Theme.brandGradient` (Theme colours only, readable in light and dark) |
| `WalletView.swift` | "Wallet" screen: cards, an empty state with **Add Card**, a context menu to make default, rename or remove |
| `AddCardView.swift` | The add form: number, expiry, name, label; no security-code field |
| `WalletPaymentCard.swift` | `.walletPaymentCard(wallet)`: hands the default card to `ApprovalSheet` ("Pay with") |

They need `ui/Theme.swift` and `ui/ApprovalSheet.swift` from the same release, and
`TransactionCenter.swift` (for `paidWith`). No SDK call, no entitlement, no Info.plist key.

## Wiring

1. Create the store once, next to the session, and inject it:

   ```swift
   @State private var wallet = WalletStore()
   // …
   ContentView().environment(wallet)
   ```

2. Load and forget it with the signed-in user (the same place the profile photo and the
   signature are loaded):

   ```swift
   .task(id: session.phase == .loggedIn) {
       if session.phase == .loggedIn,
          let user = session.sdkInformation?.loggedInUserId ?? session.currentUserIdentifier {
           wallet.load(for: user)
       } else {
           wallet.reset()
       }
   }
   ```

   These are the email-code and login-standards sessions' properties; the key only has to be
   stable per user.

3. Where the root view presents the approval, add `.walletPaymentCard(wallet)` so the sheet
   sees the card:

   ```swift
   .fullScreenCover(isPresented: approvalShown) { ApprovalSheet() }
   .walletPaymentCard(wallet)
   ```

   Without this modifier the sheet shows no "Pay with" row and records no card; nothing
   else changes.

4. Put **Wallet** where the design says: on the Pay / Payments tab above the history
   (design-system.md, "Payment, cards and wallet"), or as a row in Profile. A
   `NavigationLink { WalletView() }` is enough.

5. In the payment history, show `record.paidWith` next to the amount when it is set
   ("EUR 24.50 · Visa •• 4242").

## Verify

1. Simulator: open Wallet, add `4242 4242 4242 4242` with a future expiry; the Luhn check
   rejects `4242 4242 4242 4241`. Screenshot light and dark (ios-visual-check).
2. Device: after login, add a card, then send a payment:
   `sdk_tms_trigger(..., text="Approve payment of {{amount}} {{currency}} to {{merchant}}",
   data={"requestType": "payment", "amount": "24.50", "currency": "EUR", "merchant": "Test Shop"})`.
   The approval shows "Pay with" and the card; after accepting, the result says
   "Paid EUR 24.50 with Visa •• 4242" and `sdk_tms_result` reports `signed_data_present`.
3. Sign out and sign in as another user: the first user's cards are not shown.
