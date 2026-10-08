# In-app PDF signing with the MCSDK (iOS)

Verified 2026-09-26 on an iPhone 15 Pro (iOS 26), MCSDK iOS 15.16, email-code realm on
a KOBIL development environment. The user drew a signature, signed a PDF in the app, and the signed file
copied off the phone passed `pdfsig`: "Signature is Valid", signer `CN=<user email>`, "Total
document signed". The experience: a
hand-drawn signature kept in the user's SDK data store, a PDF viewer with a "Sign here" field,
and a real CMS signature from the SDK embedded in the PDF.

Two kinds of signing exist; pick by what the request says.

| The customer wants | Use |
|---|---|
| A server/back office asks the user to approve or sign something (payment, contract hash) | [TMS](tms.md#document-signing): the backend keeps `TmsResult.signedData` |
| The user signs a PDF **in the app** and gets a signed PDF file  | This guide: `KSMSignDataEvent` on the device plus `PdfSigner` |

Both can live in one app; the reference app has both.

## Copy, do not rewrite

The files in `ios/signing/` and the SDK request section at the end of
`ios/email-code/MasterControllerSession.swift` are copied from the device-verified app and
compile on their own (checked with only the reference files plus the wiring below). Copy them
unchanged; write only the wiring. A rewritten PDF signer is the most likely way to produce a
PDF that looks signed but fails validation.

| File | Role |
|---|---|
| `signing/HandSignature.swift` | The drawn signature: strokes normalised to 0…1, aspect ratio, ink colour; the shared KOBIL JSON (`svgString`, `isSecondaryColor`) plus `strokes`, `aspectRatio`; `SignaturePreview` |
| `signing/SignaturePadView.swift` | Full-screen drawing sheet (Clear, Save). Takes `onSave: (HandSignature) async throws -> Void` |
| `signing/SignatureStore.swift` | `@Observable`; loads/saves the signature in the SDK user data store under key `signature` (encrypted). `init(session:)`, `refresh()`, `save(_:)`, `delete()`, `reset()` |
| `signing/PdfSigner.swift` | UI-free PDF signer: incremental update (signature dictionary, widget, appearance stream of the drawn signature, new page and catalog objects, xref, trailer with `/Prev`), a 16384-byte `/Contents` placeholder, `/ByteRange` padded to fixed width. Falls back to a CoreGraphics redraw for PDFs with xref streams, object streams or an existing AcroForm |
| `signing/DocumentStore.swift` | `@Observable`; per user in `Documents/Signing/<SHA-256 of the user id>/`: `index.json`, `<id>.pdf`, `<id>-signed.pdf`, complete file protection. `load(for:)`, `reset()`, `importPDF(from:)`, `addSampleAgreement(for:)`, `markSigned`, `markDeclined`, `delete`. `SampleAgreement` builds a demo contract (PER APP). `addSignatureRequest(_:signerName:)` and `SignatureRequestPdf` turn an answered TMS signature request into a PDF, so the file needs `ApprovalRecord` from `TransactionCenter.swift` |
| `signing/DocumentsView.swift` | List of pending/signed/declined documents, PDF import (`.fileImporter`), sample document, share of the signed file |
| `signing/SignDocumentView.swift` | PDFKit viewer (`PDFKitView`), the "Sign here" field (`SignatureFieldAnnotation`), tap to place (imported PDFs), Sign/Decline, calls the SDK, saves the signed PDF. Contains `PdfSigner.cms(from:)` |
| `ui/Theme.swift`, `ui/ApprovalSheet.swift` | Shared styling the signing views use (`Theme`, `AvatarView`, `SettingsRow`, buttons). Copy both even if the app has its own theme; restyle afterwards |
| `tests/SigningAndPhotoTests.swift` | Swift Testing unit tests for the signer, the store and the signature format; change `@testable import YourApp` |

## The SDK contract (verified on device)

```swift
let result = try await session.signData(prepared.bytesToSign)   // KSMSignDataEvent(dataToSign:)
let cms = try PdfSigner.cms(from: result)                          // result.signature
let signedPDF = try PdfSigner.embed(cms: cms, into: prepared)
```

- `KSMSignDataEvent(dataToSign:)` answers `KSMSignDataResultEvent`. Its **`signature`** is a
  **detached CMS SignedData** (DER, about 1.5 KB, `30 82 … 06 09 2A 86 48 86 F7 0D 01 07 02`)
  whose signer certificate has `CN=<user email>`. Embed it as-is with
  `/SubFilter /adbe.pkcs7.detached`; do not hash first, do not wrap it.
- Its **`signedData`** only echoes the input bytes (it starts with `%PDF`). Never embed it.
  `PdfSigner.cms(from:)` checks for the CMS OID and rejects anything else.
- Pass the ByteRange bytes themselves (everything except the `/Contents` hex), not a digest.
- The SDK may answer through the send's completion handler **or** the global receiver. The
  session therefore routes results through `SdkResultRouter`; the receiver must offer every
  event to it first:

  ```swift
  func receive(_ event: any KsEvent, withCompletionHandler completionBlock: (((any KsEvent)?) -> Void)?) {
      if SdkResultRouter.shared.offer(event) { completionBlock?(nil); return }
      // … existing handling
  }
  ```

  The reference `email-code/MasterControllerSession.swift` already has this and the helpers
  `signData(_:)`, `storeUserData(_:forKey:)`, `userData(forKey:)` and `awaitResult`. With the
  activation-code variant, port that whole "SDK requests" section plus the one-line hook.
- Signing and user data need `phase == .loggedIn`; the helpers throw otherwise.
- User data: `KSMSetUserDataEntryEvent(encryption: .encrypted, userIdentifier:
  KsUserIdentifier(tenantId:userId:), key:, value:)`; read with `KSMGetUserDataEntryEvent`.
  "Delete" stores an empty string. Status `.notExists` means no signature yet.

### Swift names of SDK enums (compile errors seen)

Swift drops the `KSM` prefix of *some* NS_ENUM cases: `KSMEncryption.encrypted` (not
`.KSMEncryptionEncrypted`), `KSMDataModelRequestStatus.success` / `.notExists`. Others keep
it (`KSMEventStatusType.KSMOK`); see the table in
[sdk-features.md](sdk-features.md#finding-a-swift-name). Check the interface before
guessing and use `XcodeRefreshCodeIssuesInFile` to confirm.

## Wiring (the only code to write)

1. App: create the stores once and inject them.

   ```swift
   @State private var session: MasterControllerSession
   @State private var signatures: SignatureStore
   @State private var documents = DocumentStore()

   init() {
       let session = MasterControllerSession()
       _session = State(initialValue: session)
       _signatures = State(initialValue: SignatureStore(session: session))
   }
   // body: RootView().environment(session).environment(session.transactions)
   //                 .environment(signatures).environment(documents)
   ```

2. Root view: load on login, clear on logout. Documents and the transaction history are kept
   per user, like the wallet and profile photo; without `load(for:)` adding a document throws
   `notSignedIn`.

   ```swift
   .task(id: session.phase == .loggedIn) {
       if session.phase == .loggedIn,
          let user = session.sdkInformation?.loggedInUserId ?? session.currentUserIdentifier {
           documents.load(for: user)
           session.transactions.load(for: user)
           await signatures.refresh()
       } else {
           documents.reset()
           session.transactions.reset()
           signatures.reset()
       }
   }
   ```

3. Profile: a "Signature" section — `SignaturePreview` when set, Change (present
   `SignaturePadView { try await signatures.save($0) }`) and Delete, and a
   `NavigationLink` to `DocumentsView()`.
4. Home (optional): a "Sign" quick action pushing `DocumentsView()`.
5. `SignDocumentView` asks for a signature first if none is stored.
6. A signature request the user accepts on the approval sheet becomes a document on the Sign
   tab. Without this the approval ends in a "Signed" banner and the Sign tab stays empty:

   ```swift
   .onChange(of: transactions.lastFinished?.id) {
       guard let record = transactions.lastFinished, record.isSignature,
             record.outcome == .approved,
             documents.document(forTransaction: record.id) == nil else { return }
       do {
           _ = try documents.addSignatureRequest(record, signerName: userName)
       } catch {
           documentProblem = error.localizedDescription
       }
   }
   .alert("Document not added", isPresented: Binding(
       get: { documentProblem != nil }, set: { if !$0 { documentProblem = nil } })) {
       Button("OK", role: .cancel) {}
   } message: {
       Text(documentProblem ?? "")
   }
   ```

   `userName` stands for the name the app shows for the user (nil prints no name).
   `documentProblem` is a `@State private var documentProblem: String?` in the same view: the
   approval was signed on the server, so the user must be told when its document is missing.

The files compile in Swift 5 and Swift 6, Debug and Release, with
`SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor` (the Xcode 26 default for new projects); that
setting is required. The PDF types are `nonisolated` on purpose; keep them so.

## Verify

1. Unit tests (`tests/SigningAndPhotoTests.swift`) on the simulator.
2. On the device (signing needs a logged-in SDK user): sign the sample agreement.
3. Copy the result off the phone and validate it; the app's word is not evidence:

   ```sh
   xcrun devicectl device copy from --device <id> --domain-type appDataContainer \
     --domain-identifier <bundle id> --source Documents/Signing --destination /tmp/signing
   pdfsig /tmp/signing/<user folder>/<id>-signed.pdf     # brew install poppler
   ```

   Expect "Signature is Valid" and "Total document signed". In DEBUG builds the signing
   screen also writes `sdk-signature.bin` and `sdk-signedData.bin` next to the documents so
   the raw SDK output can be inspected (`openssl cms -inform DER -cmsout -print -in …`).
4. "Signature is Valid" with "Certificate issuer is unknown" is expected: the KOBIL user CA
   is not in poppler's trust store.

## Server-side signing APIs

The separate KOBIL signature service (`/mpower/v1/users/{userId}/signature`) is not part of
AST or the MCSDK. The device-side flow above needs no backend beyond a logged-in user.
