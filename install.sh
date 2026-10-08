#!/bin/sh
# One-line install for Claude Code: fetch this repository into a fixed folder, run setup.sh
# there and register the plugin. Safe to run again; it updates the same folder.
#   curl -fsSL https://raw.githubusercontent.com/KOBIL-GmbH/kobil-sdk-integration/<branch>/install.sh | sh
# KOBIL_SDK_REF picks another branch or tag, KOBIL_SDK_DIR another folder.
set -eu
REPO=https://github.com/KOBIL-GmbH/kobil-sdk-integration.git
REF="${KOBIL_SDK_REF:-feature/xcode-plugin-0.4.2}"
[ -n "${HOME:-}" ] || HOME=$(cd ~ && pwd -P)
export HOME
DEST="${KOBIL_SDK_DIR:-$HOME/.kobil-sdk/plugin}"
MARKETPLACE=kobil-sdk-local

# setup.sh and the launcher read secrets from the macOS Keychain.
[ "$(uname)" = Darwin ] || { echo "kobil-sdk: this installer runs on macOS only" >&2; exit 1; }
for TOOL in git uv claude; do
  command -v "$TOOL" >/dev/null 2>&1 || { echo "kobil-sdk: $TOOL not found; install it and run this again" >&2; exit 1; }
done

if [ -d "$DEST/.git" ]; then
  git -C "$DEST" fetch --quiet --depth 1 origin "$REF"
  # setup.sh rewrites the tracked .mcp.json, so the checkout has to overwrite it.
  git -C "$DEST" checkout --quiet --force FETCH_HEAD
elif [ -e "$DEST" ]; then
  echo "kobil-sdk: $DEST exists and is not a clone of this repository; move it away or set KOBIL_SDK_DIR" >&2
  exit 1
else
  mkdir -p "$(dirname "$DEST")"
  git clone --quiet --depth 1 --branch "$REF" "$REPO" "$DEST"
fi
echo "Plugin folder: $DEST ($REF)"

# Before the plugin commands: the host copies .mcp.json, which must already name this folder.
"$DEST/setup.sh"

if claude plugin marketplace list 2>/dev/null | grep -q "$MARKETPLACE"; then
  claude plugin marketplace update "$MARKETPLACE"
else
  claude plugin marketplace add "$DEST"
fi
claude plugin install "kobil-sdk@$MARKETPLACE"
echo "Installed for Claude Code. Start a new session or run /reload-plugins; ignore the Xcode line above unless you use Xcode."
