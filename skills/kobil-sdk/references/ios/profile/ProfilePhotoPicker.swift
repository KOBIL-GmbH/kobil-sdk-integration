//
//  ProfilePhotoPicker.swift
//  KOBIL SDK reference implementation (email-code variant; verified on device)
//
//  Choosing a profile photo: from the library or the camera, then positioned and zoomed in a
//  circular crop before it is saved.
//

import PhotosUI
import SwiftUI

extension View {
    /// Offers Choose Photo, Take Photo and Remove Photo while `isPresented`, then crops and saves.
    func profilePhotoPicker(isPresented: Binding<Bool>, store: ProfilePhotoStore) -> some View {
        modifier(ProfilePhotoPickerModifier(isPresented: isPresented, store: store))
    }
}

private struct ProfilePhotoPickerModifier: ViewModifier {
    @Binding var isPresented: Bool
    let store: ProfilePhotoStore

    @State private var showsLibrary = false
    @State private var showsCamera = false
    @State private var libraryItem: PhotosPickerItem?
    @State private var cropping: CropSource?
    @State private var errorMessage: String?

    private struct CropSource: Identifiable {
        let id = UUID()
        let image: UIImage
    }

    func body(content: Content) -> some View {
        content
            .confirmationDialog("Profile photo", isPresented: $isPresented, titleVisibility: .visible) {
                Button("Choose Photo") { showsLibrary = true }
                if UIImagePickerController.isSourceTypeAvailable(.camera) {
                    Button("Take Photo") { showsCamera = true }
                }
                if store.image != nil {
                    Button("Remove Photo", role: .destructive) {
                        run { try store.delete() }
                    }
                }
            }
            .photosPicker(isPresented: $showsLibrary, selection: $libraryItem, matching: .images, preferredItemEncoding: .compatible)
            .onChange(of: libraryItem) { _, item in
                guard let item else { return }
                libraryItem = nil
                Task { await load(item) }
            }
            .fullScreenCover(isPresented: $showsCamera) {
                CameraPicker { image in
                    showsCamera = false
                    if let image { cropping = CropSource(image: Self.downscaled(image)) }
                }
                .ignoresSafeArea()
            }
            .fullScreenCover(item: $cropping) { source in
                PhotoCropView(image: source.image) { cropped in
                    cropping = nil
                    if let cropped { run { try store.save(cropped) } }
                }
            }
            .alert("Photo not saved", isPresented: Binding(get: { errorMessage != nil }, set: { if !$0 { errorMessage = nil } })) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(errorMessage ?? "")
            }
    }

    private func load(_ item: PhotosPickerItem) async {
        do {
            guard let data = try await item.loadTransferable(type: Data.self), let image = UIImage(data: data) else {
                throw ProfilePhotoStore.PhotoError.unreadable
            }
            cropping = CropSource(image: Self.downscaled(image))
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func run(_ action: () throws -> Void) {
        do {
            try action()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    /// Upright and at most 2048 px on the long side, so the crop view stays light.
    static func downscaled(_ image: UIImage) -> UIImage {
        let longSide = max(image.size.width, image.size.height)
        let factor = min(1, 2048 / max(longSide, 1))
        let size = CGSize(width: (image.size.width * factor).rounded(), height: (image.size.height * factor).rounded())
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        return UIGraphicsImageRenderer(size: size, format: format).image { _ in
            image.draw(in: CGRect(origin: .zero, size: size))
        }
    }
}

// MARK: - Crop

/// Drag and pinch the photo under a circular mask; Choose returns the square behind the circle.
struct PhotoCropView: View {
    let image: UIImage
    let onFinish: (UIImage?) -> Void

    @State private var scale: CGFloat = 1
    @State private var committedScale: CGFloat = 1
    @State private var offset: CGSize = .zero
    @State private var committedOffset: CGSize = .zero

    private static let maxScale: CGFloat = 5

    var body: some View {
        GeometryReader { proxy in
            let side = min(proxy.size.width, proxy.size.height) - 48
            let base = baseSize(side: side)
            ZStack {
                Color.black.ignoresSafeArea()
                Image(uiImage: image)
                    .resizable()
                    .frame(width: base.width * scale, height: base.height * scale)
                    .offset(offset)
                    .frame(width: proxy.size.width, height: proxy.size.height)
                    .clipped()
                mask(side: side)
                    .allowsHitTesting(false)
            }
            .contentShape(Rectangle())
            .gesture(
                DragGesture()
                    .onChanged { value in
                        offset = clamped(
                            CGSize(width: committedOffset.width + value.translation.width,
                                   height: committedOffset.height + value.translation.height),
                            scale: scale, base: base, side: side
                        )
                    }
                    .onEnded { _ in committedOffset = offset }
                    .simultaneously(with: MagnifyGesture()
                        .onChanged { value in
                            scale = min(max(committedScale * value.magnification, 1), Self.maxScale)
                            offset = clamped(offset, scale: scale, base: base, side: side)
                        }
                        .onEnded { _ in
                            committedScale = scale
                            committedOffset = offset
                        })
            )
            .overlay(alignment: .top) {
                Text("Move and scale")
                    .font(.kTextMedium)
                    .foregroundStyle(.white)
                    .padding(.top, 16)
            }
            .overlay(alignment: .bottom) {
                HStack {
                    Button("Cancel") { onFinish(nil) }
                    Spacer()
                    Button("Choose") { onFinish(crop(side: side, base: base)) }
                        .fontWeight(.semibold)
                }
                .font(.body)
                .foregroundStyle(.white)
                .padding(.horizontal, Theme.margin)
                .padding(.bottom, 20)
            }
        }
        .statusBarHidden()
        .accessibilityElement(children: .contain)
        .accessibilityHint("Drag to move the photo, pinch to zoom")
    }

    /// The circle cut out of a dimmed layer.
    private func mask(side: CGFloat) -> some View {
        ZStack {
            Rectangle().fill(.black.opacity(0.6))
            Circle()
                .frame(width: side, height: side)
                .blendMode(.destinationOut)
        }
        .compositingGroup()
        .overlay {
            Circle()
                .strokeBorder(.white.opacity(0.8), lineWidth: 1)
                .frame(width: side, height: side)
        }
        .ignoresSafeArea()
    }

    /// The image size that just fills the circle at scale 1.
    private func baseSize(side: CGFloat) -> CGSize {
        let shortSide = max(min(image.size.width, image.size.height), 1)
        let factor = side / shortSide
        return CGSize(width: image.size.width * factor, height: image.size.height * factor)
    }

    /// Keeps the circle fully covered by the photo.
    private func clamped(_ offset: CGSize, scale: CGFloat, base: CGSize, side: CGFloat) -> CGSize {
        let limitX = max((base.width * scale - side) / 2, 0)
        let limitY = max((base.height * scale - side) / 2, 0)
        return CGSize(width: min(max(offset.width, -limitX), limitX), height: min(max(offset.height, -limitY), limitY))
    }

    private func crop(side: CGFloat, base: CGSize) -> UIImage {
        let displayed = CGSize(width: base.width * scale, height: base.height * scale)
        let pointsPerImagePoint = displayed.width / image.size.width
        // The circle's square, in the displayed image's coordinates (origin top-left).
        let square = CGRect(
            x: displayed.width / 2 - offset.width - side / 2,
            y: displayed.height / 2 - offset.height - side / 2,
            width: side, height: side
        )
        let size = CGSize(width: ProfilePhotoStore.pixelSize, height: ProfilePhotoStore.pixelSize)
        let factor = size.width / (square.width / pointsPerImagePoint)
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        return UIGraphicsImageRenderer(size: size, format: format).image { _ in
            let origin = CGPoint(x: -square.minX / pointsPerImagePoint * factor, y: -square.minY / pointsPerImagePoint * factor)
            image.draw(in: CGRect(origin: origin, size: CGSize(width: image.size.width * factor, height: image.size.height * factor)))
        }
    }
}

// MARK: - Camera

/// The system camera, front-facing by default as for a profile photo.
struct CameraPicker: UIViewControllerRepresentable {
    let onFinish: (UIImage?) -> Void

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.cameraDevice = UIImagePickerController.isCameraDeviceAvailable(.front) ? .front : .rear
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ controller: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator(onFinish: onFinish) }

    final class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let onFinish: (UIImage?) -> Void

        init(onFinish: @escaping (UIImage?) -> Void) {
            self.onFinish = onFinish
        }

        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
            onFinish(info[.originalImage] as? UIImage)
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            onFinish(nil)
        }
    }
}


#if DEBUG
#Preview("Crop") {
    PhotoCropView(image: UIImage(systemName: "person.crop.square.fill") ?? UIImage()) { _ in }
}
#endif
