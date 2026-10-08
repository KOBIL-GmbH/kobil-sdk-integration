#!/usr/bin/env bash
# One screenshot of the running app, from the Simulator, ready to look at.
#
#   shot.sh <out.png> [--device "iPhone 17"] [--appearance light|dark] [--clean-status-bar]
#           [--launch <bundle id>] [--wait 2]
#
# Boots the device if needed. With --launch it relaunches the app first, so the shot is of a known
# state rather than whatever was left on screen.
set -euo pipefail
die() { echo "error: $*" >&2; exit 1; }

OUT="${1:?usage: shot.sh <out.png> [--device NAME] [--appearance light|dark] [--clean-status-bar] [--launch BUNDLE_ID] [--wait S]}"
shift
DEVICE=""; APPEARANCE=""; CLEAN=0; BUNDLE=""; WAIT="1.5"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --device) DEVICE="${2:?}"; shift 2 ;;
    --appearance) APPEARANCE="${2:?}"; shift 2 ;;
    --clean-status-bar) CLEAN=1; shift ;;
    --launch) BUNDLE="${2:?}"; shift 2 ;;
    --wait) WAIT="${2:?}"; shift 2 ;;
    *) die "unknown option $1" ;;
  esac
done
command -v xcrun >/dev/null || die "xcrun not found: install Xcode command line tools"
[[ -n "$APPEARANCE" && ! "$APPEARANCE" =~ ^(light|dark)$ ]] && die "--appearance must be light or dark"

target="booted"
if [[ -n "$DEVICE" ]]; then
  udid="$(xcrun simctl list devices available | grep -F "$DEVICE (" | head -1 | sed -E 's/.*\(([0-9A-F-]{36})\).*/\1/')"
  [[ -n "$udid" ]] || die "no available simulator called \"$DEVICE\" (xcrun simctl list devices available)"
  target="$udid"
  xcrun simctl list devices | grep -q "$udid.*Booted" || { xcrun simctl boot "$udid"; sleep 6; }
fi
xcrun simctl list devices | grep -q "Booted" || die "no booted simulator: pass --device, or start one in Xcode"

[[ -n "$APPEARANCE" ]] && xcrun simctl ui "$target" appearance "$APPEARANCE" >/dev/null 2>&1
# A clean status bar keeps the clock and battery out of a visual diff, which otherwise flags every
# screenshot as different from the last one.
[[ "$CLEAN" -eq 1 ]] && xcrun simctl status_bar "$target" override --time "9:41" --batteryState charged --batteryLevel 100 --cellularBars 4 --wifiBars 3 >/dev/null 2>&1
if [[ -n "$BUNDLE" ]]; then
  xcrun simctl terminate "$target" "$BUNDLE" >/dev/null 2>&1 || true
  xcrun simctl launch "$target" "$BUNDLE" >/dev/null || die "could not launch $BUNDLE (is it installed on this simulator?)"
fi
sleep "$WAIT"
mkdir -p "$(dirname "$OUT")"
xcrun simctl io "$target" screenshot "$OUT" >/dev/null 2>&1 || die "screenshot failed"
echo "wrote $OUT ($(sips -g pixelWidth -g pixelHeight "$OUT" 2>/dev/null | awk '/pixel/{printf "%s ", $2}'))"
