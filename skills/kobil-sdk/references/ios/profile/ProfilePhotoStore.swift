//
//  ProfilePhotoStore.swift
//  KOBIL SDK reference implementation (email-code variant; verified on device)
//
//  The signed-in user's profile photo. It stays on this iPhone, one file per user, readable
//  only while the device is unlocked. Uploading needs a separate KOBIL profile service
//  instead; this environment has none, so there is no upload.
//

import CryptoKit
import Foundation
import Observation
import UIKit

@Observable
final class ProfilePhotoStore {
    private(set) var image: UIImage?

    /// Side length of the stored square photo, in pixels.
    static let pixelSize: CGFloat = 512

    private let folder: URL?
    private var userID: String?
    private var memoryPhotos: [String: Data] = [:]

    /// `folder` nil keeps photos in memory, for previews and tests.
    init(folder: URL? = ProfilePhotoStore.defaultFolder) {
        self.folder = folder
    }

    static var defaultFolder: URL? {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first?
            .appending(path: "ProfilePhotos", directoryHint: .isDirectory)
    }

    /// Shows the photo of `userID`, or none.
    func load(for userID: String) {
        self.userID = userID
        image = read(fileName(for: userID)).flatMap(UIImage.init(data:))
    }

    /// Stores an already cropped square photo for the current user.
    func save(_ photo: UIImage) throws {
        guard let userID else { throw PhotoError.notSignedIn }
        let square = Self.normalized(photo)
        guard let data = square.jpegData(compressionQuality: 0.85) else { throw PhotoError.unreadable }
        try write(data, as: fileName(for: userID))
        image = square
    }

    func delete() throws {
        guard let userID else { throw PhotoError.notSignedIn }
        try remove(fileName(for: userID))
        image = nil
    }

    /// Forgets the photo in memory, when the user signs out.
    func reset() {
        userID = nil
        image = nil
    }

    enum PhotoError: LocalizedError {
        case notSignedIn, unreadable
        var errorDescription: String? {
            switch self {
            case .notSignedIn: "Sign in first to set a profile photo."
            case .unreadable: "The photo could not be read."
            }
        }
    }

    /// Redrawn upright at the stored size, whatever the source orientation and scale.
    static func normalized(_ photo: UIImage) -> UIImage {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        let size = CGSize(width: pixelSize, height: pixelSize)
        return UIGraphicsImageRenderer(size: size, format: format).image { _ in
            photo.draw(in: CGRect(origin: .zero, size: size))
        }
    }

    // MARK: - Files

    /// The user ID hashed, so file names reveal nothing about the account.
    private func fileName(for userID: String) -> String {
        let digest = SHA256.hash(data: Data(userID.utf8))
        return digest.map { String(format: "%02x", $0) }.joined() + ".jpg"
    }

    private func read(_ name: String) -> Data? {
        guard let folder else { return memoryPhotos[name] }
        return try? Data(contentsOf: folder.appending(path: name))
    }

    private func write(_ data: Data, as name: String) throws {
        guard let folder else {
            memoryPhotos[name] = data
            return
        }
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        try data.write(to: folder.appending(path: name), options: [.atomic, .completeFileProtection])
    }

    private func remove(_ name: String) throws {
        guard let folder else {
            memoryPhotos[name] = nil
            return
        }
        let url = folder.appending(path: name)
        if FileManager.default.fileExists(atPath: url.path(percentEncoded: false)) {
            try FileManager.default.removeItem(at: url)
        }
    }
}

#if DEBUG
extension ProfilePhotoStore {
    static func preview(_ image: UIImage? = nil) -> ProfilePhotoStore {
        let store = ProfilePhotoStore(folder: nil)
        store.load(for: "preview-user")
        if let image { try? store.save(image) }
        return store
    }
}
#endif
