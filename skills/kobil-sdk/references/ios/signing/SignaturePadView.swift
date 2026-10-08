//
//  SignaturePadView.swift
//  KOBIL SDK reference implementation (email-code variant; verified on device)
//
//  The hand-signature canvas: a white pad with a guide
//  line, black or brand-blue ink, Clear and Save.
//

import SwiftUI

struct SignaturePadView: View {
    /// Called with the drawn signature; the sheet closes once it returns without error.
    let onSave: (HandSignature) async throws -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var strokes: [[CGPoint]] = []
    @State private var currentStroke: [CGPoint] = []
    @State private var usesBrandInk = false
    @State private var isSaving = false
    @State private var errorMessage: String?

    private static let aspectRatio: CGFloat = 2

    private var signature: HandSignature {
        HandSignature(strokes: strokes, aspectRatio: Self.aspectRatio, usesBrandInk: usesBrandInk)
    }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 20) {
                Text("Draw your signature with your finger. It is stored encrypted on this iPhone and used to sign documents.")
                    .font(.kText)
                    .foregroundStyle(Theme.textSecondary)

                pad

                HStack(spacing: 14) {
                    inkSwatch(brand: false)
                    inkSwatch(brand: true)
                    Spacer()
                    Button("Clear", systemImage: "arrow.counterclockwise") {
                        strokes = []
                        currentStroke = []
                    }
                    .font(.kTextMedium)
                    .foregroundStyle(Theme.brand)
                    .disabled(strokes.isEmpty)
                }

                if let errorMessage {
                    NoticeBanner(kind: .error, title: nil, message: errorMessage)
                }

                Spacer()

                Button {
                    save()
                } label: {
                    if isSaving {
                        ProgressView().tint(.white)
                    } else {
                        Text("Save")
                    }
                }
                .buttonStyle(PrimaryButtonStyle())
                .disabled(signature.isEmpty || isSaving)
            }
            .padding(Theme.margin)
            .background(Theme.screen)
            .navigationTitle("Your Signature")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel", systemImage: "xmark") { dismiss() }
                }
            }
        }
        .interactiveDismissDisabled(!strokes.isEmpty)
    }

    private var pad: some View {
        GeometryReader { proxy in
            let size = proxy.size
            ZStack(alignment: .bottomLeading) {
                RoundedRectangle(cornerRadius: Theme.cornerRadius, style: .continuous)
                    .fill(.white)
                // The guide line and its cross, a quarter from the bottom.
                Path { path in
                    path.move(to: CGPoint(x: 24, y: size.height * 0.75))
                    path.addLine(to: CGPoint(x: size.width - 24, y: size.height * 0.75))
                }
                .stroke(Theme.tmsBorder, style: StrokeStyle(lineWidth: 1, dash: [4, 4]))
                Image(systemName: "xmark")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(Theme.hint)
                    .position(x: 30, y: size.height * 0.75 - 12)
                if strokes.isEmpty && currentStroke.isEmpty {
                    Text("Sign here")
                        .font(.kText)
                        .foregroundStyle(Theme.hint)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
                Canvas { context, canvasSize in
                    for stroke in strokes + [currentStroke] {
                        let points = stroke.map { CGPoint(x: $0.x * canvasSize.width, y: $0.y * canvasSize.height) }
                        context.stroke(
                            HandSignature.smoothPath(points),
                            with: .color(signature.inkColor),
                            style: StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round)
                        )
                    }
                }
            }
            .overlay(
                RoundedRectangle(cornerRadius: Theme.cornerRadius, style: .continuous)
                    .strokeBorder(Theme.hairline, lineWidth: 1)
            )
            .contentShape(Rectangle())
            .gesture(
                DragGesture(minimumDistance: 0, coordinateSpace: .local)
                    .onChanged { value in
                        let point = CGPoint(
                            x: min(max(value.location.x / size.width, 0), 1),
                            y: min(max(value.location.y / size.height, 0), 1)
                        )
                        currentStroke.append(point)
                    }
                    .onEnded { _ in
                        if currentStroke.count == 1, let dot = currentStroke.first {
                            currentStroke.append(CGPoint(x: dot.x + 0.003, y: dot.y))
                        }
                        strokes.append(currentStroke)
                        currentStroke = []
                    }
            )
        }
        .aspectRatio(Self.aspectRatio, contentMode: .fit)
        .accessibilityLabel("Signature pad")
        .accessibilityHint("Draw your signature with one finger")
    }

    private func inkSwatch(brand: Bool) -> some View {
        let selected = usesBrandInk == brand
        return Button {
            usesBrandInk = brand
        } label: {
            Circle()
                .fill(brand ? Theme.brandSolid : Color(red: 0.1, green: 0.1, blue: 0.12))
                .frame(width: 28, height: 28)
                .padding(4)
                .overlay(Circle().strokeBorder(selected ? Theme.brand : .clear, lineWidth: 2))
        }
        .accessibilityLabel(brand ? "Blue ink" : "Black ink")
        .accessibilityAddTraits(selected ? .isSelected : [])
    }

    private func save() {
        isSaving = true
        errorMessage = nil
        Task {
            do {
                try await onSave(signature)
                dismiss()
            } catch {
                errorMessage = error.localizedDescription
            }
            isSaving = false
        }
    }
}


#if DEBUG
#Preview {
    SignaturePadView { _ in }
}
#endif
