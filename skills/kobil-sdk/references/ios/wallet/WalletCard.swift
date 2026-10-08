//
//  WalletCard.swift
//  KOBIL SDK reference implementation: wallet (app-side; makes no SDK call). See wallet.md.
//
//  A payment card as the wallet keeps it: only what identifies the card to its owner
//  (brand, last four digits, expiry, holder, a label). The full number is checked while it
//  is typed and then discarded; no security code is ever asked for.
//

import Foundation

struct WalletCard: Identifiable, Codable, Equatable, Hashable, Sendable {
    enum Network: String, Codable, Sendable {
        case visa, mastercard, amex, maestro, troy, other

        var name: String {
            switch self {
            case .visa: "Visa"
            case .mastercard: "Mastercard"
            case .amex: "American Express"
            case .maestro: "Maestro"
            case .troy: "Troy"
            case .other: "Card"
            }
        }

        /// Accepted lengths of a complete card number.
        var numberLengths: ClosedRange<Int> {
            switch self {
            case .amex: 15...15
            case .visa: 13...19
            case .mastercard, .troy: 16...16
            case .maestro, .other: 12...19
            }
        }

        /// Recognises the network from the leading digits (issuer identification number).
        static func of(_ digits: String) -> Network {
            func lead(_ count: Int) -> Int? { digits.count >= count ? Int(digits.prefix(count)) : nil }
            if digits.hasPrefix("4") { return .visa }
            if let two = lead(2), two == 34 || two == 37 { return .amex }
            if let two = lead(2), (51...55).contains(two) { return .mastercard }
            if let four = lead(4), (2221...2720).contains(four) { return .mastercard }
            if let four = lead(4), four == 9792 { return .troy }
            if let two = lead(2), [50, 56, 57, 58, 63, 67].contains(two) { return .maestro }
            return .other
        }
    }

    let id: UUID
    let network: Network
    let lastFour: String
    let expiryMonth: Int
    let expiryYear: Int
    var holder: String
    var label: String
    let addedAt: Date

    /// "Everyday •• 4242", or "Visa •• 4242" without a label; also stored on approvals.
    var shortName: String { "\(label.isEmpty ? network.name : label) •• \(lastFour)" }

    var expiryText: String { String(format: "%02d/%02d", expiryMonth, expiryYear % 100) }

    func isExpired(on date: Date = .now) -> Bool {
        let now = Calendar.current.dateComponents([.year, .month], from: date)
        guard let year = now.year, let month = now.month else { return false }
        return expiryYear < year || (expiryYear == year && expiryMonth < month)
    }
}

/// Checks typed card data before anything is kept.
enum CardInput {
    static func digits(_ text: String) -> String { text.filter(\.isASCII).filter(\.isNumber) }

    /// The Luhn checksum every payment card number carries.
    static func passesLuhn(_ digits: String) -> Bool {
        guard !digits.isEmpty else { return false }
        var sum = 0
        for (index, character) in digits.reversed().enumerated() {
            guard var value = character.wholeNumberValue else { return false }
            if index.isMultiple(of: 2) == false {
                value *= 2
                if value > 9 { value -= 9 }
            }
            sum += value
        }
        return sum.isMultiple(of: 10)
    }

    static func isValidNumber(_ digits: String) -> Bool {
        WalletCard.Network.of(digits).numberLengths.contains(digits.count) && passesLuhn(digits)
    }

    /// Groups the digits as printed on the card: 4-6-5 for American Express, else fours.
    static func grouped(_ digits: String) -> String {
        let sizes = WalletCard.Network.of(digits) == .amex ? [4, 6, 5] : [4, 4, 4, 4, 3]
        var groups: [Substring] = []
        var rest = Substring(digits)
        for size in sizes where !rest.isEmpty {
            groups.append(rest.prefix(size))
            rest = rest.dropFirst(size)
        }
        return groups.joined(separator: " ")
    }

    /// "MM/YY" while typing.
    static func groupedExpiry(_ text: String) -> String {
        let value = String(digits(text).prefix(4))
        return value.count > 2 ? "\(value.prefix(2))/\(value.dropFirst(2))" : value
    }

    /// Month and four-digit year of a valid, not yet expired "MM/YY".
    static func expiry(_ text: String, now: Date = .now) -> (month: Int, year: Int)? {
        let value = digits(text)
        guard value.count == 4, let month = Int(value.prefix(2)), let short = Int(value.suffix(2)),
              (1...12).contains(month) else { return nil }
        let year = 2000 + short
        let current = Calendar.current.dateComponents([.year, .month], from: now)
        guard let thisYear = current.year, let thisMonth = current.month else { return nil }
        guard year > thisYear || (year == thisYear && month >= thisMonth), year <= thisYear + 20 else { return nil }
        return (month, year)
    }
}
