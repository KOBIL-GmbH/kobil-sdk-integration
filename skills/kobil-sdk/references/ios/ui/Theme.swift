//
//  Theme.swift
//  KOBIL SDK reference implementation (email-code variant; verified on device)
//
//  Brand colours and the small set of components every screen is built from.
//

import SwiftUI

enum Theme {
    // KOBIL blue (#2563EB) on calm neutrals. Light values are the brand; dark
    // values keep the same roles legible.

    /// Brand primary: links, focus, active states, outgoing content.
    static let brand = dynamic(light: 0x2563EB, dark: 0x5B8DEF)
    /// The brand blue in every appearance, for fills behind white content.
    static let brandSolid = Color(hex: 0x2563EB)
    /// Near-black ink: secondary buttons, badges, send and scroll buttons.
    static let secondary = dynamic(light: 0x1B1C22, dark: 0xF2F2F5)
    static let brandDeep = Color(hex: 0x0B2A7A)
    static let ink = Color(hex: 0x16171C)
    static let violet = Color(hex: 0x6E56CF)
    static let cyan = Color(hex: 0x0A84FF)
    static let success = Color(hex: 0x1FA463)
    static let warning = Color(hex: 0xF29B38)
    static let danger = Color(hex: 0xD92D20)

    /// Screen background behind white panels.
    static let screen = dynamic(light: 0xF4F4F6, dark: 0x000000)
    /// Panels, cards, sheets and incoming chat bubbles.
    static let panel = dynamic(light: 0xFFFFFF, dark: 0x1C1C1E)
    static let textPrimary = dynamic(light: 0x1B1C22, dark: 0xF4F4F6)
    static let textSecondary = dynamic(light: 0x6E717A, dark: 0x9EA1A8)
    static let hint = dynamic(light: 0xB0B3BB, dark: 0x6B6E75)
    static let iconMuted = dynamic(light: 0x7A7D85, dark: 0x9EA1A8)
    /// 1 pt borders of fields, keypads and cards.
    static let hairline = dynamic(light: 0xE8E8EC, dark: 0x38383A)
    static let fieldFill = dynamic(light: 0xFAFAFB, dark: 0x2C2C2E)
    static let disabledFill = dynamic(light: 0xE8E8EC, dark: 0x2C2C2E)
    /// Borders of the TMS overlay's countdown and transaction card (`miniAppButtonBorder`).
    static let tmsBorder = dynamic(light: 0xD5DBE5, dark: 0x3A3A3C)
    /// Slide-to-accept green of the TMS overlay (`sliderButton`).
    static let slider = Color(hex: 0x0DC5AB)

    /// Card and panel radius (`cardBorder`, `panelBorderRadius`).
    static let cornerRadius: CGFloat = 16
    static let fieldRadius: CGFloat = 12
    static let buttonHeight: CGFloat = 48
    /// Horizontal screen margin used on every page.
    static let margin: CGFloat = 24
    /// The SF Symbol drawn as the product mark (`KOBILMark`, `KOBILShield`).
    static let shieldSymbol = "checkmark.shield.fill"

    /// The brand gradient: bright blue top left to deep blue bottom right.
    static let brandGradient = LinearGradient(
        colors: [Color(hex: 0x4F8DFF), brandSolid, Color(hex: 0x0B3A9E)],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    private static func dynamic(light: UInt32, dark: UInt32) -> Color {
        Color(uiColor: UIColor { traits in
            UIColor(hex: traits.userInterfaceStyle == .dark ? dark : light)
        })
    }

    static func color(for outcome: ApprovalRecord.Outcome) -> Color {
        switch outcome {
        case .approved: success
        case .declined: danger
        case .expired: warning
        case .cancelledByServer: .secondary
        case .failed: danger
        }
    }

    static func symbol(for outcome: ApprovalRecord.Outcome) -> String {
        switch outcome {
        case .approved: "checkmark"
        case .declined: "xmark"
        case .expired: "clock"
        case .cancelledByServer: "arrow.uturn.backward"
        case .failed: "exclamationmark"
        }
    }

}

extension Color {
    init(hex: UInt32) {
        self.init(uiColor: UIColor(hex: hex))
    }
}

extension UIColor {
    convenience init(hex: UInt32) {
        self.init(
            red: CGFloat((hex >> 16) & 0xFF) / 255,
            green: CGFloat((hex >> 8) & 0xFF) / 255,
            blue: CGFloat(hex & 0xFF) / 255,
            alpha: 1
        )
    }
}

// MARK: - Typography

/// A type scale relative to Dynamic Type.
extension Font {
    /// 24/32 semibold: screen titles, welcome, onboarding.
    static let kLargeTitle = Font.system(.title2, design: .default).weight(.semibold)
    /// 18/28 semibold: sheet and status titles.
    static let kSmallTitle = Font.system(.title3).weight(.semibold)
    /// 18/24 medium: section headers, profile name.
    static let kBodyTitle = Font.system(.title3).weight(.medium)
    /// 16/24 medium: buttons, row titles.
    static let kTextMedium = Font.system(.callout).weight(.medium)
    /// 16/24 regular: body text and inputs.
    static let kText = Font.system(.callout)
    /// 14/20 regular: captions, timestamps, secondary lines.
    static let kLabel = Font.system(.footnote)
    /// 14/20 medium.
    static let kLabelMedium = Font.system(.footnote).weight(.medium)
}

// MARK: - Backgrounds

/// The deep brand backdrop of the splash and welcome screens: a slow-moving mesh of blues.
struct BrandBackdrop: View {
    var animated = true

    var body: some View {
        TimelineView(.animation(minimumInterval: 1 / 30, paused: !animated)) { context in
            let t = animated ? context.date.timeIntervalSinceReferenceDate : 0
            let wobble = Float(sin(t / 3)) * 0.08
            let drift = Float(cos(t / 4)) * 0.07
            MeshGradient(
                width: 3,
                height: 3,
                points: [
                    [0, 0], [0.5, 0], [1, 0],
                    [0, 0.5], [0.5 + wobble, 0.45 + drift], [1, 0.5],
                    [0, 1], [0.5, 1], [1, 1],
                ],
                colors: [
                    Color(hex: 0x1747C4), Theme.brandSolid, Color(hex: 0x1440B0),
                    Theme.brandSolid, Color(hex: 0x4A86FF), Color(hex: 0x1747C4),
                    Color(hex: 0x0A2366), Color(hex: 0x0E2F8A), Color(hex: 0x081C52),
                ]
            )
        }
        .ignoresSafeArea()
    }
}

/// The neutral scaffold behind the white panels of the tab screens.
struct AmbientBackground: View {
    var body: some View {
        Theme.screen.ignoresSafeArea()
    }
}

// MARK: - Logo

/// The product word mark, drawn as text so the reference needs no image asset. The plugin
/// ships no logo artwork: to use your own, add it to the asset catalog and swap the Text
/// for `Image("YourLogo").resizable().scaledToFit()`.
struct KOBILLogo: View {
    var height: CGFloat = 32
    var onBrand = false
    var text = "KOBIL"

    var body: some View {
        Text(text)
            .font(.system(size: height * 0.8, weight: .heavy, design: .rounded))
            .tracking(height * 0.04)
            .foregroundStyle(onBrand ? Color.white : Theme.textPrimary)
            .frame(height: height)
            .accessibilityLabel(text)
    }
}

/// A shield on the brand squircle, used as the product mark. The shield is an SF Symbol so
/// the reference needs no image asset; swap `Theme.shieldSymbol` for your own artwork.
struct KOBILMark: View {
    var size: CGFloat = 88
    /// Runs a light sweep across the mark once when it appears.
    var shines = false
    @State private var sheen: CGFloat = -1

    var body: some View {
        RoundedRectangle(cornerRadius: size * 0.26, style: .continuous)
            .fill(Theme.brandGradient)
            .overlay {
                Image(systemName: Theme.shieldSymbol)
                    .resizable()
                    .scaledToFit()
                    .fontWeight(.semibold)
                    .foregroundStyle(.white)
                    .padding(size * 0.2)
            }
            .overlay {
                if shines {
                    LinearGradient(colors: [.clear, .white.opacity(0.45), .clear], startPoint: .leading, endPoint: .trailing)
                        .frame(width: size * 0.5)
                        .rotationEffect(.degrees(20))
                        .offset(x: sheen * size)
                        .blendMode(.plusLighter)
                }
            }
            .overlay(
                RoundedRectangle(cornerRadius: size * 0.26, style: .continuous)
                    .strokeBorder(.white.opacity(0.22), lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: size * 0.26, style: .continuous))
            .frame(width: size, height: size)
            .shadow(color: Color(hex: 0x6E000A).opacity(0.35), radius: size * 0.18, y: size * 0.08)
            .onAppear {
                guard shines else { return }
                withAnimation(.easeInOut(duration: 1.1).delay(0.5)) { sheen = 1 }
            }
            .accessibilityLabel("KOBIL")
    }
}

/// The bare shield, for watermarks and small badges.
struct KOBILShield: View {
    var body: some View {
        Image(systemName: Theme.shieldSymbol)
            .resizable()
            .scaledToFit()
            .accessibilityHidden(true)
    }
}

// MARK: - Motion

/// A soft light sweep for loading placeholders; pair with `.redacted(reason: .placeholder)`.
struct ShimmerModifier: ViewModifier {
    var active = true
    @State private var phase: CGFloat = -1

    func body(content: Content) -> some View {
        content
            .overlay {
                if active {
                    GeometryReader { proxy in
                        LinearGradient(colors: [.clear, .white.opacity(0.55), .clear], startPoint: .leading, endPoint: .trailing)
                            .frame(width: proxy.size.width * 0.6)
                            .offset(x: phase * proxy.size.width * 1.3)
                    }
                    .mask(content)
                    .allowsHitTesting(false)
                }
            }
            .onAppear {
                guard active else { return }
                withAnimation(.linear(duration: 1.3).repeatForever(autoreverses: false)) { phase = 1 }
            }
    }
}

extension View {
    func shimmer(_ active: Bool = true) -> some View {
        modifier(ShimmerModifier(active: active))
    }
}

/// Buttons that sink slightly under the finger.
struct PressableButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.96 : 1)
            .animation(.spring(duration: 0.25, bounce: 0.4), value: configuration.isPressed)
    }
}

// MARK: - Surfaces

struct SurfaceModifier: ViewModifier {
    var padding: CGFloat = 18

    func body(content: Content) -> some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: Theme.cornerRadius, style: .continuous)
                    .fill(Theme.panel)
            )
            .overlay(
                RoundedRectangle(cornerRadius: Theme.cornerRadius, style: .continuous)
                    .strokeBorder(Theme.hairline.opacity(0.7), lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.04), radius: 10, y: 4)
    }
}

extension View {
    func surface(padding: CGFloat = 18) -> some View {
        modifier(SurfaceModifier(padding: padding))
    }
}

struct SectionHeader: View {
    let title: String
    var action: (title: String, run: () -> Void)?

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(title)
                .font(.kBodyTitle)
                .foregroundStyle(Theme.textPrimary)
            Spacer()
            if let action {
                Button(action.title, action: action.run)
                    .font(.kLabelMedium)
                    .foregroundStyle(Theme.brand)
            }
        }
    }
}

/// A rounded symbol tile, used for list icons and quick actions.
struct SymbolTile: View {
    let symbol: String
    var tint: Color = Theme.brand
    var size: CGFloat = 44

    var body: some View {
        Image(systemName: symbol)
            .font(.system(size: size * 0.42, weight: .semibold))
            .foregroundStyle(tint)
            .frame(width: size, height: size)
            .background(
                RoundedRectangle(cornerRadius: size * 0.3, style: .continuous)
                    .fill(tint.opacity(0.1))
            )
    }
}

struct StatusPill: View {
    let text: String
    let color: Color
    var symbol: String?

    var body: some View {
        HStack(spacing: 4) {
            if let symbol {
                Image(systemName: symbol)
                    .font(.caption2.weight(.bold))
            }
            Text(text)
                .font(.caption.weight(.semibold))
        }
        .foregroundStyle(color)
        .padding(.horizontal, 9)
        .padding(.vertical, 4)
        .background(Capsule().fill(color.opacity(0.13)))
    }
}

/// A designed empty state: large glyph, a clear sentence of why it is empty, optional action.
struct EmptyStateCard: View {
    let symbol: String
    let title: String
    let message: String
    var actionTitle: String?
    var action: (() -> Void)?

    var body: some View {
        VStack(spacing: 14) {
            ZStack {
                Circle()
                    .fill(Theme.brand.opacity(0.08))
                    .frame(width: 96, height: 96)
                Image(systemName: symbol)
                    .font(.system(size: 34, weight: .regular))
                    .foregroundStyle(Theme.brand)
            }
            .padding(.bottom, 14)
            Text(title)
                .font(.kSmallTitle)
                .foregroundStyle(Theme.textPrimary)
            Text(message)
                .font(.kText)
                .foregroundStyle(Theme.textSecondary)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
            if let actionTitle, let action {
                Button(actionTitle, action: action)
                    .buttonStyle(PrimaryButtonStyle())
                    .padding(.top, 10)
            }
        }
        .padding(.vertical, 32)
        .padding(.horizontal, Theme.margin)
        .frame(maxWidth: .infinity)
        .surface(padding: 0)
    }
}

/// Initials in a solid brand circle, for chat lists and the profile.
struct AvatarView: View {
    let name: String?
    var size: CGFloat = 56
    /// The profile photo, shown instead of the initials when set.
    var image: UIImage?

    private var initials: String {
        let words = (name ?? "").split(separator: " ").prefix(2)
        let letters = words.compactMap(\.first).map(String.init).joined()
        return letters.isEmpty ? "" : letters.uppercased()
    }

    var body: some View {
        ZStack {
            Circle().fill(Theme.brandGradient)
            if let image {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFill()
                    .clipShape(Circle())
            } else if initials.isEmpty {
                Image(systemName: "person.fill")
                    .font(.system(size: size * 0.42, weight: .medium))
                    .foregroundStyle(.white)
            } else {
                Text(initials)
                    .font(.system(size: size * 0.36, weight: .semibold))
                    .foregroundStyle(.white)
            }
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }
}

/// The primary button: full width, 48 pt, radius 16, KOBIL blue fill with a soft glow.
struct PrimaryButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled
    var onBrand = false

    /// Opaque in every state, so a disabled button never shows the content behind it.
    private var background: Color {
        if !isEnabled {
            return onBrand ? .white.opacity(0.35) : Theme.disabledFill
        }
        return onBrand ? .white : Theme.brandSolid
    }

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.kTextMedium)
            .frame(maxWidth: .infinity, minHeight: Theme.buttonHeight)
            .padding(.horizontal, 16)
            .foregroundStyle(isEnabled ? (onBrand ? Theme.brandSolid : .white) : Theme.hint)
            .background(
                RoundedRectangle(cornerRadius: Theme.cornerRadius, style: .continuous)
                    .fill(background)
            )
            .shadow(color: isEnabled && !onBrand ? Theme.brandSolid.opacity(0.28) : .clear, radius: 10, y: 5)
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
            .opacity(configuration.isPressed ? 0.88 : 1)
            .animation(.spring(duration: 0.25, bounce: 0.3), value: configuration.isPressed)
    }
}

/// A secondary button: transparent with a 1 pt border.
struct SecondaryButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled
    var tint: Color = Theme.secondary

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.kTextMedium)
            .frame(maxWidth: .infinity, minHeight: Theme.buttonHeight)
            .padding(.horizontal, 16)
            .foregroundStyle(isEnabled ? tint : Theme.hint)
            .background(
                RoundedRectangle(cornerRadius: Theme.cornerRadius, style: .continuous)
                    .strokeBorder(isEnabled ? tint.opacity(0.9) : Theme.hairline, lineWidth: 1)
            )
            .contentShape(RoundedRectangle(cornerRadius: Theme.cornerRadius, style: .continuous))
            .opacity(configuration.isPressed ? 0.7 : 1)
    }
}

/// A settings row like the iOS Settings app: white symbol on a coloured tile, title and
/// optional subtitle. The tile colour follows the symbol unless a tint is given; the danger
/// tint also colours the title.
struct SettingsRow<Trailing: View>: View {
    let symbol: String
    let title: String
    var subtitle: String?
    var tint: Color = Theme.iconMuted
    @ViewBuilder var trailing: Trailing

    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: symbol)
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(.white)
                .frame(width: 30, height: 30)
                .background(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .fill(Self.tileColor(for: symbol, tint: tint).gradient)
                )
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.kTextMedium)
                    .foregroundStyle(tint == Theme.danger ? tint : Theme.textPrimary)
                if let subtitle {
                    Text(subtitle)
                        .font(.kLabel)
                        .foregroundStyle(Theme.textSecondary)
                }
            }
            Spacer(minLength: 12)
            trailing
        }
        .frame(minHeight: subtitle == nil ? 48 : 64)
        .contentShape(Rectangle())
    }
}

extension SettingsRow {
    /// Picks a stable tile colour from the symbol, so every screen colours a topic the same way.
    static func tileColor(for symbol: String, tint: Color) -> Color {
        if tint != Theme.iconMuted { return tint }
        let s = symbol
        if s.contains("shield") || s.contains("lock") || s.contains("faceid") || s.contains("touchid") { return Theme.brandSolid }
        if s.contains("key") || s.contains("signature") { return Theme.warning }
        if s.contains("iphone") || s.contains("cpu") || s.contains("number") { return Color(hex: 0x8E8E93) }
        if s.contains("person") || s.contains("envelope") { return Theme.cyan }
        if s.contains("doc") || s.contains("arrow.down") { return Theme.violet }
        if s.contains("card") || s.contains("checkmark") { return Theme.success }
        if s.contains("trash") { return Theme.danger }
        return Theme.cyan
    }
}

extension SettingsRow where Trailing == EmptyView {
    init(symbol: String, title: String, subtitle: String? = nil, tint: Color = Theme.iconMuted) {
        self.init(symbol: symbol, title: title, subtitle: subtitle, tint: tint) { EmptyView() }
    }
}

/// A labelled text-field container shared by the forms.
struct FieldContainer<Field: View>: View {
    let title: String
    var isInvalid = false
    @ViewBuilder var field: Field

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if !title.isEmpty {
                Text(title)
                    .font(.kLabelMedium)
                    .foregroundStyle(Theme.textPrimary)
            }
            field
                .font(.kText)
                .tint(Theme.brand)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .padding(.horizontal, 12)
                .frame(minHeight: Theme.buttonHeight)
                .background(
                    RoundedRectangle(cornerRadius: Theme.fieldRadius, style: .continuous)
                        .fill(Theme.fieldFill)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: Theme.fieldRadius, style: .continuous)
                        .strokeBorder(isInvalid ? Theme.danger : Theme.hairline, lineWidth: 1)
                )
        }
    }
}

/// An inline error or notice.
struct NoticeBanner: View {
    enum Kind { case error, success, info }
    let kind: Kind
    let title: String?
    let message: String

    private var color: Color {
        switch kind {
        case .error: Theme.danger
        case .success: Theme.success
        case .info: Theme.brand
        }
    }

    private var symbol: String {
        switch kind {
        case .error: "exclamationmark.triangle.fill"
        case .success: "checkmark.circle.fill"
        case .info: "info.circle.fill"
        }
    }

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: symbol)
                .foregroundStyle(color)
                .font(.body.weight(.semibold))
            VStack(alignment: .leading, spacing: 3) {
                if let title {
                    Text(title).font(.subheadline.weight(.semibold))
                }
                Text(message)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 0)
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: Theme.fieldRadius, style: .continuous)
                .fill(color.opacity(0.08))
        )
    }
}
