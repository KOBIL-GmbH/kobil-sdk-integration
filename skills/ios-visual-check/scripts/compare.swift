// Compares a build screenshot with a reference image, with numbers, and writes a side-by-side.
//
//   xcrun swift compare.swift <reference.png> <build.png> <out-folder> [--grid 4]
//
// Both images are scaled to the reference's aspect at 390 pt wide. Prints the mean colour
// difference overall and per grid cell (0 = identical, 100 = opposite), marks cells above 12
// as DIFFERENT, and writes <out>/side-by-side.png (reference | build | difference heat map).
// Needs only macOS and Xcode; no packages.

import AppKit
import CoreGraphics
import Foundation

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8))
    exit(1)
}

var arguments = Array(CommandLine.arguments.dropFirst())
var grid = 4
if let index = arguments.firstIndex(of: "--grid") {
    guard index + 1 < arguments.count, let value = Int(arguments[index + 1]), (1...12).contains(value) else {
        fail("--grid takes 1–12")
    }
    grid = value
    arguments.removeSubrange(index...(index + 1))
}
guard arguments.count == 3 else { fail("usage: compare.swift <reference.png> <build.png> <out-folder> [--grid 4]") }

func load(_ path: String) -> CGImage {
    guard let image = NSImage(contentsOfFile: path),
          let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else { fail("cannot read \(path)") }
    return cg
}

let reference = load(arguments[0])
let build = load(arguments[1])
let width = 390
let height = max(1, Int((Double(reference.height) / Double(reference.width) * Double(width)).rounded()))

func pixels(_ image: CGImage) -> [UInt8] {
    var data = [UInt8](repeating: 0, count: width * height * 4)
    let space = CGColorSpaceCreateDeviceRGB()
    data.withUnsafeMutableBytes { buffer in
        let context = CGContext(data: buffer.baseAddress, width: width, height: height, bitsPerComponent: 8,
                                bytesPerRow: width * 4, space: space,
                                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        context.interpolationQuality = .high
        context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
    }
    return data
}

let a = pixels(reference)
let b = pixels(build)
var heat = [UInt8](repeating: 255, count: width * height * 4)
var cellSum = [Double](repeating: 0, count: grid * grid)
var cellCount = [Double](repeating: 0, count: grid * grid)
var total = 0.0
for y in 0..<height {
    for x in 0..<width {
        let i = (y * width + x) * 4
        let d = (abs(Double(a[i]) - Double(b[i])) + abs(Double(a[i + 1]) - Double(b[i + 1]))
                 + abs(Double(a[i + 2]) - Double(b[i + 2]))) / (3 * 255) * 100
        total += d
        // Bitmap memory holds the top row first, so y counts from the top as seen.
        let cell = min(grid - 1, y * grid / height) * grid + min(grid - 1, x * grid / width)
        cellSum[cell] += d
        cellCount[cell] += 1
        let v = UInt8(min(255, d * 5))
        heat[i] = 255; heat[i + 1] = 255 - v; heat[i + 2] = 255 - v; heat[i + 3] = 255
    }
}

let overall = total / Double(width * height)
print(String(format: "overall difference %.1f (0 identical, 100 opposite)", overall))
print("per cell, row by row from the top (DIFFERENT above 12):")
var different: [String] = []
for row in 0..<grid {
    var line = ""
    for column in 0..<grid {
        let value = cellSum[row * grid + column] / max(1, cellCount[row * grid + column])
        line += String(format: "%6.1f", value)
        if value > 12 { different.append("row \(row + 1) col \(column + 1)") }
    }
    print(line)
}
print(different.isEmpty ? "CLOSE BY NUMBERS: still look at the side-by-side yourself"
                        : "DIFFERENT: " + different.joined(separator: ", "))

let out = URL(fileURLWithPath: arguments[2], isDirectory: true)
try? FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)
let space = CGColorSpaceCreateDeviceRGB()
let gap = 12
let sheet = CGContext(data: nil, width: width * 3 + gap * 2, height: height, bitsPerComponent: 8,
                      bytesPerRow: 0, space: space, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
sheet.setFillColor(CGColor(gray: 0.07, alpha: 1))
sheet.fill(CGRect(x: 0, y: 0, width: width * 3 + gap * 2, height: height))
func image(from bytes: [UInt8]) -> CGImage {
    var copy = bytes
    return copy.withUnsafeMutableBytes { buffer in
        CGContext(data: buffer.baseAddress, width: width, height: height, bitsPerComponent: 8, bytesPerRow: width * 4,
                  space: space, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!.makeImage()!
    }
}
for (index, bytes) in [a, b, heat].enumerated() {
    sheet.draw(image(from: bytes), in: CGRect(x: index * (width + gap), y: 0, width: width, height: height))
}
let rep = NSBitmapImageRep(cgImage: sheet.makeImage()!)
guard let png = rep.representation(using: .png, properties: [:]) else { fail("cannot encode the PNG") }
let file = out.appendingPathComponent("side-by-side.png")
do { try png.write(to: file) } catch { fail("cannot write \(file.path)") }
print("wrote \(file.path)")
