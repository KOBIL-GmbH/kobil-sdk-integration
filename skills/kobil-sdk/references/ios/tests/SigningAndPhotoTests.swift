//
//  SigningAndPhotoTests.swift
//  KOBIL SDK reference implementation: unit tests for signing/ and profile/.
//  Add to the unit test target; they need no device and no SDK session.
//

import CoreGraphics
import Foundation
import Testing
import UIKit
@testable import YourApp  // PER APP: the app module name

struct PdfSigningTests {
    private func sample() -> (pdf: Data, field: PdfSignatureField, appearance: PdfSigner.Appearance) {
        let sample = SampleAgreement.make(signerName: "Test Signer")
        let appearance = PdfSigner.Appearance(signature: .sample, signerName: "Test Signer", reason: "Test", date: .now)
        return (sample.pdf, sample.field, appearance)
    }

    @Test func byteRangeCoversEverythingButTheContents() throws {
        let (pdf, field, appearance) = sample()
        let prepared = try PdfSigner.prepare(pdf: pdf, field: field, appearance: appearance)
        let range = prepared.byteRange
        #expect(range[0] == 0)
        #expect(range[2] - range[1] == PdfSigner.contentsCapacity * 2 + 2)
        #expect(range[2] + range[3] == prepared.pdf.count)
        #expect(prepared.pdf.prefix(pdf.count) == pdf, "the original bytes stay untouched")
        #expect(prepared.pdf[range[1]] == UInt8(ascii: "<"))
        #expect(prepared.pdf[range[2] - 1] == UInt8(ascii: ">"))
    }

    @Test func embedsTheCmsAndStaysReadable() throws {
        let (pdf, field, appearance) = sample()
        let prepared = try PdfSigner.prepare(pdf: pdf, field: field, appearance: appearance)
        let fakeCms = Data([0x30, 0x82, 0x01, 0x00, 0x06, 0x09, 0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x07, 0x02]) + Data(repeating: 0xAB, count: 200)
        #expect(PdfSigner.isCmsSignedData(fakeCms))
        let signed = try PdfSigner.embed(cms: fakeCms, into: prepared)
        #expect(signed.count == prepared.pdf.count)
        #expect(signed.subdata(in: 0..<prepared.byteRange[1]) == prepared.pdf.subdata(in: 0..<prepared.byteRange[1]))
        let hex = String(decoding: signed.subdata(in: (prepared.byteRange[1] + 1)..<(prepared.byteRange[1] + 31)), as: UTF8.self)
        #expect(hex == "3082010006092A864886F70D010702")
        let document = try #require(CGPDFDocument(CGDataProvider(data: signed as CFData)!))
        #expect(document.numberOfPages == 1)
    }

    @Test func rejectsOversizedAndNonCmsSignatures() throws {
        let (pdf, field, appearance) = sample()
        let prepared = try PdfSigner.prepare(pdf: pdf, field: field, appearance: appearance)
        #expect(throws: PdfSigner.SignError.signatureTooLarge(PdfSigner.contentsCapacity + 1)) {
            try PdfSigner.embed(cms: Data(count: PdfSigner.contentsCapacity + 1), into: prepared)
        }
        #expect(!PdfSigner.isCmsSignedData(Data(repeating: 0x01, count: 256)))
    }

    @Test func resignsASignedPdfFromARedrawnCopy() async throws {
        let (pdf, field, appearance) = sample()
        let cms = Data([0x30, 0x03, 0x06, 0x09, 0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x07, 0x02])
        let once = try await PdfSigner.sign(pdf: pdf, field: field, appearance: appearance) { _ in cms }
        let twice = try await PdfSigner.sign(pdf: once, field: field, appearance: appearance) { _ in cms }
        #expect(CGPDFDocument(CGDataProvider(data: twice as CFData)!)?.numberOfPages == 1)
    }

    @Test func signatureRoundTripsInTheSharedFormat() throws {
        let data = try JSONEncoder().encode(HandSignature.sample)
        let object = try #require(try JSONSerialization.jsonObject(with: data) as? [String: Any])
        #expect((object["svgString"] as? String)?.hasPrefix("<svg") == true)
        #expect(object["isSecondaryColor"] as? Bool == false)
        #expect(try JSONDecoder().decode(HandSignature.self, from: data) == HandSignature.sample)
    }

    @Test func documentStoreTracksDecisions() throws {
        let store = DocumentStore(folder: nil)
        let document = try store.addSampleAgreement(for: "Test Signer")
        #expect(store.pendingCount == 1)
        try store.markSigned(document, signedPDF: Data("signed".utf8))
        #expect(store.documents.first?.status == .signed)
        #expect(store.signedPDF(of: document) == Data("signed".utf8))
        #expect(store.pendingCount == 0)
    }
}

@MainActor
struct ProfilePhotoTests {
    @Test func photosAreKeptPerUserAndStoredSquare() throws {
        let folder = FileManager.default.temporaryDirectory.appending(path: UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: folder) }
        let wide = UIGraphicsImageRenderer(size: CGSize(width: 300, height: 100)).image { context in
            UIColor.red.setFill()
            context.fill(CGRect(x: 0, y: 0, width: 300, height: 100))
        }
        let store = ProfilePhotoStore(folder: folder)
        store.load(for: "user-a")
        try store.save(wide)
        #expect(store.image?.size == CGSize(width: ProfilePhotoStore.pixelSize, height: ProfilePhotoStore.pixelSize))

        let reopened = ProfilePhotoStore(folder: folder)
        reopened.load(for: "user-a")
        #expect(reopened.image != nil)
        reopened.load(for: "user-b")
        #expect(reopened.image == nil)

        store.load(for: "user-a")
        try store.delete()
        reopened.load(for: "user-a")
        #expect(reopened.image == nil)
    }

    @Test func savingNeedsASignedInUser() {
        let store = ProfilePhotoStore(folder: nil)
        #expect(throws: ProfilePhotoStore.PhotoError.self) { try store.save(UIImage()) }
    }
}
