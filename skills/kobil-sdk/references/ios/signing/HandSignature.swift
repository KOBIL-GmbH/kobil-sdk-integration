//
//  HandSignature.swift
//  KOBIL SDK reference implementation (email-code variant; verified on device)
//
//  The user's handwritten signature as vector strokes. It is drawn on screen, stored in the
//  KOBIL SDK's encrypted user store, and written into signed PDFs as vector paths.
//

import SwiftUI

nonisolated struct HandSignature: Codable, Equatable, Sendable {
    /// Strokes in the pad's coordinates, each point normalised to 0...1 of the pad's size.
    var strokes: [[CGPoint]]
    /// The pad's width divided by its height, so the strokes keep their proportions.
    var aspectRatio: CGFloat
    /// Brand-blue ink instead of black.
    var usesBrandInk: Bool

    var isEmpty: Bool { strokes.allSatisfy { $0.count < 2 } }

    /// The ink as RGB components, for the PDF appearance.
    var inkComponents: (red: CGFloat, green: CGFloat, blue: CGFloat) {
        usesBrandInk ? (0x1D / 255, 0x19 / 255, 1) : (0.1, 0.1, 0.12)
    }

    var inkColor: Color {
        let ink = inkComponents
        return Color(red: ink.red, green: ink.green, blue: ink.blue)
    }

    /// The strokes fitted into `rect` (top-left origin), cropped to their own bounds and
    /// centred, so the signature fills a field whatever part of the pad was used.
    func strokes(fittedInto rect: CGRect) -> [[CGPoint]] {
        let absolute = strokes.map { $0.map { CGPoint(x: $0.x * aspectRatio, y: $0.y) } }
        let points = absolute.flatMap { $0 }
        guard let minX = points.map(\.x).min(), let maxX = points.map(\.x).max(),
              let minY = points.map(\.y).min(), let maxY = points.map(\.y).max() else { return [] }
        let width = max(maxX - minX, 0.001)
        let height = max(maxY - minY, 0.001)
        let scale = min(rect.width / width, rect.height / height)
        let offsetX = rect.minX + (rect.width - width * scale) / 2
        let offsetY = rect.minY + (rect.height - height * scale) / 2
        return absolute.map { stroke in
            stroke.map { CGPoint(x: offsetX + ($0.x - minX) * scale, y: offsetY + ($0.y - minY) * scale) }
        }
    }

    /// A smooth path through the points: quadratic curves between the midpoints.
    static func smoothPath(_ stroke: [CGPoint]) -> Path {
        var path = Path()
        guard let first = stroke.first else { return path }
        path.move(to: first)
        guard stroke.count > 2 else {
            stroke.dropFirst().forEach { path.addLine(to: $0) }
            return path
        }
        for index in 1..<stroke.count - 1 {
            let mid = CGPoint(x: (stroke[index].x + stroke[index + 1].x) / 2, y: (stroke[index].y + stroke[index + 1].y) / 2)
            path.addQuadCurve(to: mid, control: stroke[index])
        }
        path.addLine(to: stroke[stroke.count - 1])
        return path
    }

    /// An SVG rendering, stored alongside the strokes under the `svgString` key other KOBIL apps read.
    var svgString: String {
        let height: CGFloat = 400
        let width = (height * aspectRatio).rounded()
        let paths = strokes.map { stroke -> String in
            let points = stroke.map { String(format: "%.1f %.1f", $0.x * width, $0.y * height) }
            guard let first = points.first else { return "" }
            return "<path d=\"M \(first)" + points.dropFirst().map { " L \($0)" }.joined() + "\"/>"
        }
        let ink = usesBrandInk ? "#1D19FF" : "#1A1A1F"
        return """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 \(Int(width)) \(Int(height))">\
            <g fill="none" stroke="\(ink)" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">\
            \(paths.joined())</g></svg>
            """
    }

    private enum CodingKeys: String, CodingKey {
        case svgString, isSecondaryColor, strokes, aspectRatio
    }

    init(strokes: [[CGPoint]], aspectRatio: CGFloat, usesBrandInk: Bool) {
        self.strokes = strokes
        self.aspectRatio = aspectRatio
        self.usesBrandInk = usesBrandInk
    }

    init(from decoder: any Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        strokes = try container.decode([[CGPoint]].self, forKey: .strokes)
        aspectRatio = try container.decode(CGFloat.self, forKey: .aspectRatio)
        usesBrandInk = try container.decodeIfPresent(Bool.self, forKey: .isSecondaryColor) ?? false
    }

    func encode(to encoder: any Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(svgString, forKey: .svgString)
        try container.encode(usesBrandInk, forKey: .isSecondaryColor)
        try container.encode(strokes, forKey: .strokes)
        try container.encode(aspectRatio, forKey: .aspectRatio)
    }
}

/// Draws a signature fitted into its frame.
nonisolated struct SignatureShape: Shape {
    let signature: HandSignature

    func path(in rect: CGRect) -> Path {
        var path = Path()
        for stroke in signature.strokes(fittedInto: rect) {
            path.addPath(HandSignature.smoothPath(stroke))
        }
        return path
    }
}

/// A signature preview on a white card, as shown in Profile.
struct SignaturePreview: View {
    let signature: HandSignature
    var lineWidth: CGFloat = 2

    var body: some View {
        SignatureShape(signature: signature)
            .stroke(signature.inkColor, style: StrokeStyle(lineWidth: lineWidth, lineCap: .round, lineJoin: .round))
            .padding(10)
            .background(
                RoundedRectangle(cornerRadius: Theme.fieldRadius, style: .continuous)
                    .fill(.white)
            )
            .overlay(
                RoundedRectangle(cornerRadius: Theme.fieldRadius, style: .continuous)
                    .strokeBorder(Theme.hairline, lineWidth: 1)
            )
            .accessibilityLabel("Your signature")
    }
}

#if DEBUG
extension HandSignature {
    /// A looping sample signature for previews and tests.
    static let sample: HandSignature = {
        let loop = stride(from: 0.0, through: 1.0, by: 0.02).map { (t: Double) -> CGPoint in
            let wave: Double = 0.25 * sin(t * Double.pi * 5) * (1 - t * 0.5)
            return CGPoint(x: 0.1 + 0.8 * t, y: 0.5 + wave)
        }
        let underline = [CGPoint(x: 0.15, y: 0.82), CGPoint(x: 0.55, y: 0.8), CGPoint(x: 0.85, y: 0.78)]
        return HandSignature(strokes: [loop, underline], aspectRatio: 2, usesBrandInk: false)
    }()
}
#endif
