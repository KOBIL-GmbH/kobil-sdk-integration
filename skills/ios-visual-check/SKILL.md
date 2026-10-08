---
name: ios-visual-check
description: See what an iOS app actually looks like and fix what is wrong with it — screenshot the running app in Simulator or on a device, sweep it across light and dark, small and large screens, compare against a design or reference image with measured numbers, and iterate until it matches. Use when the user says a screen looks broken, off, cramped, cut off, misaligned or "not like the design", when reviewing UI work before calling it done, after changing layout, spacing, colours or dark-mode handling, or whenever an agent needs visual feedback on its own iOS UI changes instead of guessing.
---

# iOS visual check

**Looking at the app is the check. Reading the code is not.** SwiftUI compiles and runs while the
text is truncated, the button sits under the Dynamic Island, the dark-mode contrast is unreadable
and the layout collapses on a small phone. None of that appears in a build log.

```
run ─▶ shot.sh ─▶ look at it ─▶ name the defect ─▶ fix ─▶ shot again ─▶ sweep.sh across conditions
```

`V=<this skill's folder>/scripts`: the `skills/ios-visual-check/scripts` folder next to this file,
in the plugin that installed it. Everything below uses only these scripts, Xcode and macOS.

## 1. One screenshot of a known state
```bash
$V/shot.sh /tmp/shots/home.png --launch com.example.App --clean-status-bar
$V/shot.sh /tmp/shots/home-dark.png --launch com.example.App --appearance dark --device "iPhone 17"
```
Boots the device if needed, relaunches the app so the shot is of a known state, and pins the status
bar to 9:41 with full battery — without that, the clock changes every shot and every visual diff
reports a difference.

**Then open the PNG and look at it.** A screenshot nobody looked at proves nothing.

## 2. Sweep the conditions that break layouts
```bash
$V/sweep.sh /tmp/shots --launch com.example.App \
  --devices "iPhone 17,iPhone 17 Pro Max,iPhone SE (3rd generation)" --appearances light,dark
```
Writes one PNG per combination plus `_sheet.png`. Review the sheet, not the files: one look covers
the whole matrix.

## 3. What to look for
Go through this list against the shots — most iOS visual bugs are one of these:

| Check | Symptom in the shot |
|---|---|
| Safe areas | content under the Dynamic Island, home indicator or keyboard |
| Truncation | "Continue with…" tail-truncated, or a number wrapping to two lines |
| Dark mode | grey-on-grey text, a white card on a white sheet, an icon that vanishes |
| Small screens | SE cropping the primary action below the fold |
| Large text | buttons overlapping at accessibility sizes; test one shot at XXL |
| Tap targets | anything under 44×44 pt |
| Alignment | labels off the leading margin, uneven card gaps, a stray 1 pt divider |
| Empty and loading states | a blank screen where the design has placeholder art |

## 4. Compare against the design, with numbers
When there is a reference (a design export, a screenshot of the old build, a frame from a video):
```bash
xcrun swift $V/compare.swift design/home.png /tmp/shots/home.png /tmp/shots/look --grid 4
```
It prints the overall colour difference and a grid of per-cell differences (0 identical, 100
opposite), names the cells above 12 as `DIFFERENT`, and writes `side-by-side.png` (reference, build,
red heat map of the difference). Open that PNG, fix what differs, shoot again, repeat. The same
command on a light and a dark shot of one screen shows where dark mode changes nothing (a cell near
0 that should have changed is often a hard-coded colour). `CLOSE BY NUMBERS` is not done: look at the
sheet yourself, then show it to the user. Only their "close" counts.

## 5. Fix, then prove it
Change one thing at a time and re-shoot; a batch of five changes and one screenshot tells you
nothing about which one worked. Keep the before and after side by side in the final message.

## Notes
- **Simulator screenshots need a booted simulator.** `--device` boots one; otherwise start it in
  Xcode. Device screenshots go through `xcrun devicectl device capture screenshot --device <id>
  --destination shot.png` (the phone must be unlocked), not `simctl`.
- **Metal shaders, CoreHaptics and camera do not run in Simulator** — a shader-heavy screen must be
  checked on hardware.
- **SwiftUI previews are not the app**: they miss real data, safe areas and navigation chrome. Use
  them for iteration speed, not as the check.
- **Inside Xcode's Claude** background tasks are disabled: run these scripts in the foreground and
  keep the sweeps small.
