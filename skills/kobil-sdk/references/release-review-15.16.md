# MCSDK 15.16 delivery review

Reviewed 2026-09-16 from separately delivered Android/iOS README and CHANGELOG
files. This is release-specific source evidence, not a general statement about
all SDK versions. No existing app was upgraded or runtime-tested with this release.

## Verified acquisition

Downloaded Android libraries 15.16.3088426, iOS XCFrameworks
15.16.803.3089231, standalone KSSIDP Android 1.8 and standalone KSSIDP iOS 1.10.
All four ZIPs passed CRC validation and artifact metadata/hash inspection.
Supplier SHA-512 files matched the first three; no supplier checksum was present
for standalone KSSIDP iOS. Binaries and complete release documents stay in
private local storage. No standalone Flutter package was visible in this account;
that observation must not be generalized to other customer accounts.

## Integration consequences

- The MCSDK changelog lists Android wrapper 189.0, iOS wrapper 195.1 and KSSIDP
  1.11 for both platforms. Both downloaded MCSDK archives contain KSSIDP
  components. Standalone 1.8/1.10 are not the documented 15.16 combination.
- Android minimum API becomes 24. The README separately describes standard and
  extended OS support; check the delivery's dated support policy for the customer.
- The Android README names AGP 8.12.1 and Java 17 minimum; the iOS README names
  Xcode 26.1. Both name Shift charts 0.208.0+ and IDP core 5.2.1+ / 4.29.0+.
  Confirm the exact backend branch; do not interpret two version lines as a
  guarantee for every intermediate release.
- Automatic suspend/resume handling is added. Review existing lifecycle hooks
  before retaining manual events and test background/foreground behavior.
- New SDK-state query events expose logged-in state. Resolve exact wrapper APIs
  before use; previous integration code may target an older wrapper.
- TLS changes remove SHA-1 support and CCM-8 suites. Check server compatibility;
  do not weaken TLS configuration to bypass an upgrade failure.
- The HTTP stack changes connection reuse; the README says MCSDK is explicitly
  tested against HTTP/2. Include connection changes/restarts in regression tests.
- Shift fixes cover TMS signature handling when switching key types and iOS
  network-change socket detection. Include those cases when applicable.
- Standalone Android 1.8 notes logging/certificate and socket.io fixes. iOS 1.10
  notes secure-field character encoding and initial-request failure handling;
  the preceding 1.9 notes encoding, nonce/state and diagnostic improvements.
- The changelog says no known issues, while the Android README documents a
  biometric-keystore limitation and a Digitanium offline-function restart issue.
  Read both documents; do not report the release as issue-free.

## Required before adoption

Verify the supplied component tuple and target architectures, then build and
exercise SDK Start, activation, returning login, fatal/error diagnostics, log
export, lifecycle/network transitions and any selected TMS flows. Preserve the
previously validated app/version tuple until an upgrade is explicitly performed.
