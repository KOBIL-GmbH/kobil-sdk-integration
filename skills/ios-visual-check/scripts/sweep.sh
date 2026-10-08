#!/usr/bin/env bash
# The screenshots a visual review actually needs: the same screen across the conditions that break
# layouts. One contact sheet, so a whole pass costs one look instead of twelve.
#
#   sweep.sh <out dir> --launch <bundle id> [--devices "iPhone 17,iPhone 17 Pro Max,iPhone SE (3rd generation)"]
#            [--appearances light,dark] [--wait 2]
set -euo pipefail
die() { echo "error: $*" >&2; exit 1; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

OUT="${1:?usage: sweep.sh <out dir> --launch <bundle id> [--devices ...] [--appearances light,dark]}"
shift
BUNDLE=""; DEVICES="iPhone 17"; APPEARANCES="light,dark"; WAIT="2"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --launch) BUNDLE="${2:?}"; shift 2 ;;
    --devices) DEVICES="${2:?}"; shift 2 ;;
    --appearances) APPEARANCES="${2:?}"; shift 2 ;;
    --wait) WAIT="${2:?}"; shift 2 ;;
    *) die "unknown option $1" ;;
  esac
done
[[ -n "$BUNDLE" ]] || die "--launch <bundle id> is required"
mkdir -p "$OUT"
IFS=',' read -r -a device_list <<< "$DEVICES"
IFS=',' read -r -a appearance_list <<< "$APPEARANCES"
for device in "${device_list[@]}"; do
  for appearance in "${appearance_list[@]}"; do
    name="$(echo "${device}-${appearance}" | tr ' ()' '-' | tr -s '-' | sed 's/-$//')"
    "$HERE/shot.sh" "$OUT/$name.png" --device "$device" --appearance "$appearance" \
      --clean-status-bar --launch "$BUNDLE" --wait "$WAIT" || echo "skipped $name"
  done
done
sheet="$OUT/_sheet.png"
if command -v magick >/dev/null; then
  magick montage "$OUT"/*.png -tile 4x -geometry 240x+6+6 -background '#111' "$sheet" && echo "wrote $sheet"
else
  echo "(install ImageMagick for the contact sheet; the shots are in $OUT)"
fi
