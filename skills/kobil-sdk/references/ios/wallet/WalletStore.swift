//
//  WalletStore.swift
//  KOBIL SDK reference implementation: wallet (app-side; makes no SDK call). See wallet.md.
//
//  The signed-in user's cards, kept in the Keychain on this device only (readable while the
//  device is unlocked, never synced). One item per user; load after sign-in, reset on sign-out.
//

import Foundation
import Observation
import OSLog
import Security

@Observable
final class WalletStore {
    enum WalletError: LocalizedError {
        case notSignedIn
        case invalidNumber
        case invalidExpiry
        case duplicate
        case keychain(OSStatus)

        var errorDescription: String? {
            switch self {
            case .notSignedIn: "Sign in to use your wallet."
            case .invalidNumber: "This card number isn't valid. Check the digits and try again."
            case .invalidExpiry: "Enter the expiry date as MM/YY. The card must not be expired."
            case .duplicate: "This card is already in your wallet."
            case .keychain(let status): "The wallet couldn't be saved on this device (error \(status))."
            }
        }
    }

    private(set) var cards: [WalletCard] = []
    /// The card payments are approved with.
    private(set) var defaultCardID: UUID?

    var defaultCard: WalletCard? {
        cards.first { $0.id == defaultCardID } ?? cards.first
    }

    @ObservationIgnored private var account: String?
    @ObservationIgnored private let persists: Bool
    private static let service = (Bundle.main.bundleIdentifier ?? "app") + ".wallet"
    private static let log = Logger(subsystem: "com.example.kobilsdk", category: "Wallet")  // PER APP: your bundle identifier

    private struct Stored: Codable {
        var cards: [WalletCard]
        var defaultCardID: UUID?
    }

    init(persisting: Bool = true) {
        persists = persisting
    }

    /// Reads the wallet of the user who just signed in.
    func load(for userID: String) {
        account = userID
        guard persists else { return }
        do {
            let stored = try Self.read(account: userID)
            cards = stored?.cards ?? []
            defaultCardID = stored?.defaultCardID
        } catch {
            Self.log.error("Wallet read failed: \(error.localizedDescription, privacy: .public)")
            cards = []
            defaultCardID = nil
        }
    }

    /// Forgets the cards in memory after sign-out; the Keychain item stays for the next sign-in.
    func reset() {
        account = nil
        cards = []
        defaultCardID = nil
    }

    @discardableResult
    func add(number: String, expiry: String, holder: String, label: String) throws -> WalletCard {
        let digits = CardInput.digits(number)
        guard CardInput.isValidNumber(digits) else { throw WalletError.invalidNumber }
        guard let date = CardInput.expiry(expiry) else { throw WalletError.invalidExpiry }
        let network = WalletCard.Network.of(digits)
        let lastFour = String(digits.suffix(4))
        guard !cards.contains(where: {
            $0.network == network && $0.lastFour == lastFour && $0.expiryMonth == date.month && $0.expiryYear == date.year
        }) else { throw WalletError.duplicate }

        let card = WalletCard(
            id: UUID(),
            network: network,
            lastFour: lastFour,
            expiryMonth: date.month,
            expiryYear: date.year,
            holder: holder.trimmingCharacters(in: .whitespacesAndNewlines),
            label: label.trimmingCharacters(in: .whitespacesAndNewlines),
            addedAt: .now
        )
        try commit(cards: cards + [card], defaultCardID: defaultCardID ?? card.id)
        return card
    }

    func rename(_ card: WalletCard, to label: String) throws {
        let updated = cards.map { entry in
            guard entry.id == card.id else { return entry }
            var copy = entry
            copy.label = label.trimmingCharacters(in: .whitespacesAndNewlines)
            return copy
        }
        try commit(cards: updated, defaultCardID: defaultCardID)
    }

    func makeDefault(_ card: WalletCard) throws {
        try commit(cards: cards, defaultCardID: card.id)
    }

    func remove(_ card: WalletCard) throws {
        let remaining = cards.filter { $0.id != card.id }
        let newDefault = defaultCardID == card.id ? remaining.first?.id : defaultCardID
        try commit(cards: remaining, defaultCardID: newDefault)
    }

    /// Writes first and publishes only what was stored.
    private func commit(cards newCards: [WalletCard], defaultCardID newDefault: UUID?) throws {
        if persists {
            guard let account else { throw WalletError.notSignedIn }
            try Self.write(Stored(cards: newCards, defaultCardID: newDefault), account: account)
        }
        cards = newCards
        defaultCardID = newDefault
    }

    // MARK: - Keychain

    private static func query(account: String) -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }

    private static func read(account: String) throws -> Stored? {
        var query = query(account: account)
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = result as? Data else { throw WalletError.keychain(status) }
        return try JSONDecoder().decode(Stored.self, from: data)
    }

    private static func write(_ stored: Stored, account: String) throws {
        let data = try JSONEncoder().encode(stored)
        let base = query(account: account)
        let attributes: [String: Any] = [
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
        ]
        var status = SecItemUpdate(base as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            status = SecItemAdd(base.merging(attributes) { $1 } as CFDictionary, nil)
        }
        guard status == errSecSuccess else { throw WalletError.keychain(status) }
    }
}

#if DEBUG
extension WalletStore {
    static func preview(_ cards: [WalletCard] = []) -> WalletStore {
        let store = WalletStore(persisting: false)
        store.cards = cards
        store.defaultCardID = cards.first?.id
        return store
    }
}
#endif
