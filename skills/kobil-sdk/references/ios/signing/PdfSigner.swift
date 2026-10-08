//
//  PdfSigner.swift
//  KOBIL SDK reference implementation (email-code variant; verified on device)
//
//  Signs a PDF the way PDF readers verify: an incremental update appends a signature field
//  whose appearance draws the handwritten signature as vector paths, and a signature value
//  (/Type /Sig, adbe.pkcs7.detached) whose /Contents holds the CMS the KOBIL SDK creates over
//  every byte of the file except /Contents itself (the /ByteRange). The original bytes are
//  never changed. PDFs this parser cannot update in place (cross-reference streams, existing
//  forms) are first re-drawn into a plain PDF.
//

import CoreGraphics
import Foundation

/// Where the signature goes: a page and a rectangle in that page's PDF coordinates
/// (points, origin bottom-left).
nonisolated struct PdfSignatureField: Codable, Sendable, Equatable, Hashable {
    var pageIndex: Int
    var rect: CGRect
}

nonisolated enum PdfSigner {
    enum SignError: LocalizedError, Equatable {
        case unreadable(String)
        case unsupported(String)
        case encrypted
        case signatureTooLarge(Int)
        case notCms(String)

        var errorDescription: String? {
            switch self {
            case .unreadable(let detail): "The PDF could not be read (\(detail))."
            case .unsupported(let detail): "This PDF cannot be signed in place (\(detail))."
            case .encrypted: "The PDF is password protected and cannot be signed."
            case .signatureTooLarge(let size): "The signature (\(size) bytes) does not fit the space reserved in the PDF."
            case .notCms(let detail): "The KOBIL SDK returned no CMS signature (\(detail))."
            }
        }
    }

    /// A PDF with the signature field appended and /Contents still empty.
    struct Prepared: Sendable {
        let pdf: Data
        let byteRange: [Int]
        /// The bytes the signature covers: everything but the /Contents hex string.
        var dataToSign: Data {
            pdf.subdata(in: byteRange[0]..<byteRange[1]) + pdf.subdata(in: byteRange[2]..<(byteRange[2] + byteRange[3]))
        }
        /// Room for the DER CMS, in bytes.
        let contentsCapacity: Int
    }

    struct Appearance: Sendable {
        var signature: HandSignature
        var signerName: String
        var reason: String
        var date: Date
    }

    /// Bytes reserved for the CMS: a signature with a certificate chain fits comfortably.
    static let contentsCapacity = 16_384

    /// Signs `pdf`: prepares the update, lets `sign` produce the CMS over the byte range, and
    /// embeds it. Falls back to a re-drawn copy when the original cannot be updated in place.
    static func sign(
        pdf: Data,
        field: PdfSignatureField,
        appearance: Appearance,
        sign: @Sendable (Data) async throws -> Data
    ) async throws -> Data {
        let prepared: Prepared
        do {
            prepared = try prepare(pdf: pdf, field: field, appearance: appearance)
        } catch SignError.unsupported {
            prepared = try prepare(pdf: try redrawn(pdf), field: field, appearance: appearance)
        }
        let cms = try await sign(prepared.dataToSign)
        return try embed(cms: cms, into: prepared)
    }

    // MARK: - Prepare

    static func prepare(pdf: Data, field: PdfSignatureField, appearance: Appearance) throws -> Prepared {
        let bytes = [UInt8](pdf)
        let parser = try Parser(bytes: bytes)
        if parser.trailer.contains("/Encrypt") { throw SignError.encrypted }

        guard let root = Parser.reference(named: "Root", in: parser.trailer) else {
            throw SignError.unreadable("no document catalog")
        }
        let catalog = try parser.dictionary(of: root.number)
        if catalog.contains("/AcroForm") { throw SignError.unsupported("the PDF already has a form") }
        guard let pagesRef = Parser.reference(named: "Pages", in: catalog) else {
            throw SignError.unreadable("no page tree")
        }
        let pages = try parser.pageReferences(from: pagesRef.number)
        guard pages.indices.contains(field.pageIndex) else { throw SignError.unreadable("no page \(field.pageIndex + 1)") }
        let pageRef = pages[field.pageIndex]
        let page = try parser.dictionary(of: pageRef.number)

        guard let size = Parser.integer(named: "Size", in: parser.trailer) else { throw SignError.unreadable("no /Size") }
        let sigNumber = size, widgetNumber = size + 1, appearanceNumber = size + 2

        let updatedPage: String
        if let annots = page.range(of: #"/Annots\s*\["#, options: .regularExpression) {
            updatedPage = page.replacingCharacters(in: annots, with: page[annots] + "\(widgetNumber) 0 R ")
        } else if page.contains("/Annots") {
            throw SignError.unsupported("indirect annotation array")
        } else {
            updatedPage = Parser.adding("/Annots [\(widgetNumber) 0 R]", to: page)
        }
        let updatedCatalog = Parser.adding("/AcroForm << /Fields [\(widgetNumber) 0 R] /SigFlags 3 >>", to: catalog)

        let rect = field.rect.standardized
        let stream = appearanceStream(for: appearance, size: rect.size)
        let byteRangePlaceholder = "/ByteRange [0 0000000000 0000000000 0000000000]"
        let contentsPlaceholder = "/Contents <" + String(repeating: "0", count: contentsCapacity * 2) + ">"

        var update = Data("\n".utf8)
        var offsets: [(number: Int, generation: Int, offset: Int)] = []
        func append(_ number: Int, _ generation: Int, _ body: Data) {
            offsets.append((number, generation, bytes.count + update.count))
            update += Data("\(number) \(generation) obj\n".utf8) + body + Data("\nendobj\n".utf8)
        }

        let sigDictionary = """
            << /Type /Sig /Filter /Adobe.PPKLite /SubFilter /adbe.pkcs7.detached \
            \(byteRangePlaceholder) \(contentsPlaceholder) \
            /M \(pdfString(pdfDate(appearance.date))) /Name \(pdfString(appearance.signerName)) \
            /Reason \(pdfString(appearance.reason)) /Prop_Build << /App << /Name /KOBILSDKApp >> >> >>
            """
        append(sigNumber, 0, Data(sigDictionary.utf8))

        let widget = """
            << /Type /Annot /Subtype /Widget /FT /Sig /T (KOBIL Signature) /V \(sigNumber) 0 R /F 132 \
            /P \(pageRef.number) \(pageRef.generation) R \
            /Rect [\(number(rect.minX)) \(number(rect.minY)) \(number(rect.maxX)) \(number(rect.maxY))] \
            /AP << /N \(appearanceNumber) 0 R >> >>
            """
        append(widgetNumber, 0, Data(widget.utf8))

        let form = """
            << /Type /XObject /Subtype /Form /BBox [0 0 \(number(rect.width)) \(number(rect.height))] \
            /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >> >> >> \
            /Length \(stream.utf8.count) >>
            stream
            \(stream)
            endstream
            """
        append(appearanceNumber, 0, Data(form.utf8))
        append(pageRef.number, pageRef.generation, Parser.latin1(updatedPage))
        append(root.number, root.generation, Parser.latin1(updatedCatalog))

        let xrefOffset = bytes.count + update.count
        var xref = "xref\n"
        for entry in offsets.sorted(by: { $0.number < $1.number }) {
            xref += "\(entry.number) 1\n" + String(format: "%010d %05d n \n", entry.offset, entry.generation)
        }
        var trailer = "trailer\n<< /Size \(size + 3) /Root \(root.number) \(root.generation) R /Prev \(parser.startXref)"
        if let info = Parser.reference(named: "Info", in: parser.trailer) {
            trailer += " /Info \(info.number) \(info.generation) R"
        }
        if let id = parser.trailer.range(of: #"/ID\s*\[[^\]]*\]"#, options: .regularExpression) {
            trailer += " " + parser.trailer[id]
        }
        trailer += " >>\nstartxref\n\(xrefOffset)\n%%EOF\n"
        update += Data((xref + trailer).utf8)

        var output = [UInt8](pdf) + [UInt8](update)

        // Resolve the byte range around the /Contents hex string and write it in place.
        guard let contentsKey = Parser.lastIndex(of: Array("/Contents <".utf8), in: output) else {
            throw SignError.unreadable("placeholder lost")
        }
        let contentsStart = contentsKey + "/Contents ".utf8.count
        let contentsEnd = contentsStart + contentsCapacity * 2 + 2
        let byteRange = [0, contentsStart, contentsEnd, output.count - contentsEnd]
        guard let rangeKey = Parser.lastIndex(of: Array(byteRangePlaceholder.utf8), in: output) else {
            throw SignError.unreadable("placeholder lost")
        }
        let values = byteRange.dropFirst().map { String($0).padding(toLength: 10, withPad: " ", startingAt: 0) }
        let resolved = Array("/ByteRange [0 \(values.joined(separator: " "))]".utf8)
        guard resolved.count == byteRangePlaceholder.utf8.count else { throw SignError.unreadable("byte range too long") }
        output.replaceSubrange(rangeKey..<(rangeKey + resolved.count), with: resolved)

        return Prepared(pdf: Data(output), byteRange: byteRange, contentsCapacity: contentsCapacity)
    }

    // MARK: - Embed

    static func embed(cms: Data, into prepared: Prepared) throws -> Data {
        guard cms.count <= prepared.contentsCapacity else { throw SignError.signatureTooLarge(cms.count) }
        let hex = cms.map { String(format: "%02X", $0) }.joined()
        let padded = hex + String(repeating: "0", count: prepared.contentsCapacity * 2 - hex.count)
        var output = prepared.pdf
        let start = prepared.byteRange[1] + 1
        output.replaceSubrange(start..<(start + padded.utf8.count), with: Data(padded.utf8))
        return output
    }

    /// True when `data` is a DER ContentInfo of type signedData (1.2.840.113549.1.7.2).
    static func isCmsSignedData(_ data: Data) -> Bool {
        let oid: [UInt8] = [0x06, 0x09, 0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x07, 0x02]
        guard data.first == 0x30 else { return false }
        return data.prefix(32).range(of: Data(oid)) != nil
    }

    // MARK: - Appearance

    /// The widget's normal appearance: the signature strokes above a "Signed by" line.
    static func appearanceStream(for appearance: Appearance, size: CGSize) -> String {
        let captionHeight: CGFloat = 11
        let inset: CGFloat = 4
        let box = CGRect(x: inset, y: inset, width: size.width - inset * 2, height: size.height - captionHeight - inset * 2)
        let ink = appearance.signature.inkComponents
        var ops = ["q", "1 J 1 j", "\(number(ink.red)) \(number(ink.green)) \(number(ink.blue)) RG", "1.4 w"]

        // Strokes arrive top-left based; PDF space is bottom-left based.
        let flip: (CGPoint) -> CGPoint = { CGPoint(x: $0.x, y: size.height - $0.y) }
        for stroke in appearance.signature.strokes(fittedInto: box) {
            let points = stroke.map(flip)
            guard let first = points.first, points.count > 1 else { continue }
            ops.append("\(number(first.x)) \(number(first.y)) m")
            if points.count == 2 {
                ops.append("\(number(points[1].x)) \(number(points[1].y)) l")
            } else {
                // The on-screen quadratic midpoint curves, as cubic Béziers.
                var current = first
                for index in 1..<points.count - 1 {
                    let control = points[index]
                    let end = CGPoint(x: (points[index].x + points[index + 1].x) / 2, y: (points[index].y + points[index + 1].y) / 2)
                    let c1 = CGPoint(x: current.x + 2 / 3 * (control.x - current.x), y: current.y + 2 / 3 * (control.y - current.y))
                    let c2 = CGPoint(x: end.x + 2 / 3 * (control.x - end.x), y: end.y + 2 / 3 * (control.y - end.y))
                    ops.append("\(number(c1.x)) \(number(c1.y)) \(number(c2.x)) \(number(c2.y)) \(number(end.x)) \(number(end.y)) c")
                    current = end
                }
                let last = points[points.count - 1]
                ops.append("\(number(last.x)) \(number(last.y)) l")
            }
            ops.append("S")
        }
        ops.append("Q")

        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        let caption = "Signed by \(appearance.signerName) with KOBIL, \(formatter.string(from: appearance.date))"
        ops.append("q 0.45 0.48 0.53 rg 0.45 0.48 0.53 RG 0.5 w \(number(inset)) \(number(captionHeight)) m \(number(size.width - inset)) \(number(captionHeight)) l S")
        ops.append("BT /F1 6 Tf \(number(inset)) 3 Td \(pdfString(caption)) Tj ET Q")
        return ops.joined(separator: "\n")
    }

    // MARK: - Redraw

    /// A plain copy of the PDF drawn page by page, which the parser can always update.
    static func redrawn(_ pdf: Data) throws -> Data {
        guard let provider = CGDataProvider(data: pdf as CFData), let document = CGPDFDocument(provider) else {
            throw SignError.unreadable("not a PDF")
        }
        if document.isEncrypted { throw SignError.encrypted }
        let output = NSMutableData()
        guard let consumer = CGDataConsumer(data: output as CFMutableData), document.numberOfPages > 0,
              let context = CGContext(consumer: consumer, mediaBox: nil, nil) else {
            throw SignError.unreadable("no pages")
        }
        for number in 1...document.numberOfPages {
            guard let page = document.page(at: number) else { continue }
            var box = page.getBoxRect(.mediaBox)
            context.beginPage(mediaBox: &box)
            context.drawPDFPage(page)
            context.endPage()
        }
        context.closePDF()
        return output as Data
    }

    // MARK: - Helpers

    private static func number(_ value: CGFloat) -> String {
        String(format: "%.2f", Double(value))
    }

    /// A literal string, ASCII only so the standard Helvetica encoding shows it.
    static func pdfString(_ text: String) -> String {
        let folded = text.folding(options: [.diacriticInsensitive, .widthInsensitive], locale: Locale(identifier: "en_US_POSIX"))
        let ascii = folded.unicodeScalars.map { $0.isASCII && $0.value >= 0x20 ? String($0) : "?" }.joined()
        let escaped = ascii.replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "(", with: "\\(")
            .replacingOccurrences(of: ")", with: "\\)")
        return "(\(escaped))"
    }

    static func pdfDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = .current
        formatter.dateFormat = "yyyyMMddHHmmss"
        let seconds = TimeZone.current.secondsFromGMT(for: date)
        let sign = seconds >= 0 ? "+" : "-"
        let offset = String(format: "%@%02d'%02d'", sign, abs(seconds) / 3600, abs(seconds) % 3600 / 60)
        return "D:" + formatter.string(from: date) + offset
    }
}

// MARK: - Parser

/// Just enough of a PDF parser for an incremental update: classic cross-reference tables,
/// the trailer, and the dictionaries of the catalog, the page tree and one page.
private nonisolated struct Parser {
    let bytes: [UInt8]
    let startXref: Int
    let trailer: String
    private var offsets: [Int: Int] = [:]

    init(bytes: [UInt8]) throws {
        self.bytes = bytes
        guard let keyword = Self.lastIndex(of: Array("startxref".utf8), in: bytes) else {
            throw PdfSigner.SignError.unreadable("no startxref")
        }
        var cursor = keyword + 9
        guard let start = Self.readInteger(bytes, &cursor) else { throw PdfSigner.SignError.unreadable("bad startxref") }
        startXref = start

        var trailer: String?
        var next: Int? = start
        var visited = Set<Int>()
        while let offset = next, !visited.contains(offset) {
            visited.insert(offset)
            var position = offset
            Self.skipWhitespace(bytes, &position)
            guard Self.matches(Array("xref".utf8), in: bytes, at: position) else {
                throw PdfSigner.SignError.unsupported("cross-reference stream")
            }
            position += 4
            while true {
                Self.skipWhitespace(bytes, &position)
                if Self.matches(Array("trailer".utf8), in: bytes, at: position) { position += 7; break }
                guard let first = Self.readInteger(bytes, &position), let count = Self.readInteger(bytes, &position) else {
                    throw PdfSigner.SignError.unreadable("bad cross-reference table")
                }
                for index in 0..<count {
                    guard let entryOffset = Self.readInteger(bytes, &position), Self.readInteger(bytes, &position) != nil else {
                        throw PdfSigner.SignError.unreadable("bad cross-reference entry")
                    }
                    Self.skipWhitespace(bytes, &position)
                    let kind = position < bytes.count ? bytes[position] : 0
                    position += 1
                    // The newest section is read first, so older entries never override it.
                    if kind == UInt8(ascii: "n"), offsets[first + index] == nil {
                        offsets[first + index] = entryOffset
                    }
                }
            }
            let dictionary = try Self.dictionary(in: bytes, from: position)
            if trailer == nil { trailer = dictionary }
            next = Self.integer(named: "Prev", in: dictionary)
        }
        guard let trailer else { throw PdfSigner.SignError.unreadable("no trailer") }
        self.trailer = trailer
    }

    func dictionary(of number: Int) throws -> String {
        guard let offset = offsets[number] else { throw PdfSigner.SignError.unsupported("object \(number) is compressed") }
        return try Self.dictionary(in: bytes, from: offset)
    }

    /// Page references in document order, walking nested page-tree nodes.
    func pageReferences(from node: Int, depth: Int = 0) throws -> [(number: Int, generation: Int)] {
        guard depth < 32 else { throw PdfSigner.SignError.unreadable("page tree too deep") }
        let dictionary = try dictionary(of: node)
        guard dictionary.range(of: #"/Type\s*/Pages\b"#, options: .regularExpression) != nil else {
            return [(node, 0)]
        }
        guard let kids = dictionary.range(of: #"/Kids\s*\[[^\]]*\]"#, options: .regularExpression) else {
            throw PdfSigner.SignError.unsupported("indirect page list")
        }
        var result: [(number: Int, generation: Int)] = []
        for kid in Self.references(in: String(dictionary[kids])) {
            let child = try self.dictionary(of: kid.number)
            if child.range(of: #"/Type\s*/Pages\b"#, options: .regularExpression) != nil {
                result += try pageReferences(from: kid.number, depth: depth + 1)
            } else {
                result.append(kid)
            }
        }
        return result
    }

    // MARK: Dictionary text

    static func reference(named key: String, in dictionary: String) -> (number: Int, generation: Int)? {
        guard let range = dictionary.range(of: "/\(key)\\s+(\\d+)\\s+(\\d+)\\s+R", options: .regularExpression) else { return nil }
        return references(in: String(dictionary[range])).first
    }

    static func references(in text: String) -> [(number: Int, generation: Int)] {
        let regex = try? NSRegularExpression(pattern: #"(\d+)\s+(\d+)\s+R\b"#)
        let nsText = text as NSString
        return regex?.matches(in: text, range: NSRange(location: 0, length: nsText.length)).compactMap { match in
            guard let number = Int(nsText.substring(with: match.range(at: 1))),
                  let generation = Int(nsText.substring(with: match.range(at: 2))) else { return nil }
            return (number, generation)
        } ?? []
    }

    static func integer(named key: String, in dictionary: String) -> Int? {
        guard let range = dictionary.range(of: "/\(key)\\s+\\d+(?!\\s+\\d+\\s+R)", options: .regularExpression) else { return nil }
        return Int(dictionary[range].split(whereSeparator: \.isWhitespace).last ?? "")
    }

    /// Inserts `entry` before the dictionary's closing `>>`.
    static func adding(_ entry: String, to dictionary: String) -> String {
        String(dictionary.dropLast(2)) + " " + entry + " >>"
    }

    static func latin1(_ text: String) -> Data {
        text.data(using: .isoLatin1) ?? Data(text.utf8)
    }

    // MARK: Bytes

    /// The top-level `<< … >>` starting at or after `start`, skipping strings.
    static func dictionary(in bytes: [UInt8], from start: Int) throws -> String {
        var index = start
        while index + 1 < bytes.count, !(bytes[index] == UInt8(ascii: "<") && bytes[index + 1] == UInt8(ascii: "<")) {
            index += 1
        }
        let open = index
        var depth = 0
        while index < bytes.count {
            let byte = bytes[index]
            if byte == UInt8(ascii: "("), depth > 0 {
                index = skipLiteralString(bytes, from: index)
                continue
            }
            if byte == UInt8(ascii: "<"), index + 1 < bytes.count {
                if bytes[index + 1] == UInt8(ascii: "<") {
                    depth += 1
                    index += 2
                    continue
                }
                while index < bytes.count, bytes[index] != UInt8(ascii: ">") { index += 1 }
                index += 1
                continue
            }
            if byte == UInt8(ascii: ">"), index + 1 < bytes.count, bytes[index + 1] == UInt8(ascii: ">") {
                depth -= 1
                index += 2
                if depth == 0 {
                    return String(bytes: bytes[open..<index], encoding: .isoLatin1) ?? ""
                }
                continue
            }
            index += 1
        }
        throw PdfSigner.SignError.unreadable("unterminated dictionary")
    }

    private static func skipLiteralString(_ bytes: [UInt8], from start: Int) -> Int {
        var index = start + 1
        var depth = 1
        while index < bytes.count, depth > 0 {
            switch bytes[index] {
            case UInt8(ascii: "\\"): index += 1
            case UInt8(ascii: "("): depth += 1
            case UInt8(ascii: ")"): depth -= 1
            default: break
            }
            index += 1
        }
        return index
    }

    static func lastIndex(of pattern: [UInt8], in bytes: [UInt8]) -> Int? {
        guard bytes.count >= pattern.count else { return nil }
        var index = bytes.count - pattern.count
        while index >= 0 {
            if matches(pattern, in: bytes, at: index) { return index }
            index -= 1
        }
        return nil
    }

    static func matches(_ pattern: [UInt8], in bytes: [UInt8], at index: Int) -> Bool {
        guard index >= 0, index + pattern.count <= bytes.count else { return false }
        for offset in 0..<pattern.count where bytes[index + offset] != pattern[offset] { return false }
        return true
    }

    static func skipWhitespace(_ bytes: [UInt8], _ index: inout Int) {
        while index < bytes.count, [0x00, 0x09, 0x0A, 0x0C, 0x0D, 0x20].contains(bytes[index]) { index += 1 }
    }

    static func readInteger(_ bytes: [UInt8], _ index: inout Int) -> Int? {
        skipWhitespace(bytes, &index)
        var value = 0
        var digits = 0
        while index < bytes.count, (0x30...0x39).contains(bytes[index]) {
            value = value * 10 + Int(bytes[index] - 0x30)
            index += 1
            digits += 1
        }
        return digits > 0 ? value : nil
    }
}
