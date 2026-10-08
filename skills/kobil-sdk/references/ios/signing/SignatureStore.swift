//
//  SignatureStore.swift
//  KOBIL SDK reference implementation (email-code variant; verified on device)
//
//  Keeps the user's handwritten signature in the KOBIL SDK's encrypted user store, under
//  the key other KOBIL apps use. Deleting stores an empty value.
//

import Foundation
import Observation

@Observable
final class SignatureStore {
    enum LoadState: Equatable {
        case idle, loading, loaded
        case failed(String)
    }

    /// The SDK user-data key other KOBIL apps store the signature under, so they share it.
    static let storageKey = "signature"

    private(set) var signature: HandSignature?
    private(set) var loadState: LoadState = .idle

    private let load: () async throws -> String?
    private let store: (String) async throws -> Void

    init(load: @escaping () async throws -> String?, store: @escaping (String) async throws -> Void) {
        self.load = load
        self.store = store
    }

    convenience init(session: MasterControllerSession) {
        self.init(
            load: { [weak session] in
                guard let session else { return nil }
                return try await session.userData(forKey: Self.storageKey)
            },
            store: { [weak session] value in
                guard let session else { throw MasterControllerSession.SdkRequestError.notLoggedIn }
                try await session.storeUserData(value, forKey: Self.storageKey)
            }
        )
    }

    /// Reads the stored signature. An unreadable value counts as none.
    func refresh() async {
        loadState = .loading
        do {
            let json = try await load()
            signature = json.flatMap { try? JSONDecoder().decode(HandSignature.self, from: Data($0.utf8)) }
            loadState = .loaded
        } catch {
            loadState = .failed(error.localizedDescription)
        }
    }

    func save(_ signature: HandSignature) async throws {
        let data = try JSONEncoder().encode(signature)
        try await store(String(decoding: data, as: UTF8.self))
        self.signature = signature
        loadState = .loaded
    }

    func delete() async throws {
        try await store("")
        signature = nil
    }

    /// Forgets the signature in memory, when the user signs out.
    func reset() {
        signature = nil
        loadState = .idle
    }
}

#if DEBUG
extension SignatureStore {
    static func preview(_ signature: HandSignature? = nil) -> SignatureStore {
        let box = PreviewBox(value: signature.flatMap { try? JSONEncoder().encode($0) }.map { String(decoding: $0, as: UTF8.self) })
        let store = SignatureStore(load: { box.value }, store: { box.value = $0 })
        store.signature = signature
        store.loadState = .loaded
        return store
    }

    private final class PreviewBox {
        var value: String?
        init(value: String?) { self.value = value }
    }
}
#endif
