#!/bin/sh
# One-line install: fetch this repository into a fixed folder, run setup.sh there and register
# the plugin with every supported agent found on this Mac: Claude Code, Codex CLI, Gemini CLI.
# Safe to run again; it updates the same folder.
#   curl -fsSL https://raw.githubusercontent.com/KOBIL-GmbH/kobil-sdk-integration/<branch>/install.sh | sh
# KOBIL_SDK_REF picks another branch or tag, KOBIL_SDK_DIR another folder, KOBIL_SDK_REPO another source.
set -eu
REPO="${KOBIL_SDK_REPO:-https://github.com/KOBIL-GmbH/kobil-sdk-integration.git}"
REF="${KOBIL_SDK_REF:-feature/xcode-plugin-0.4.2}"
[ -n "${HOME:-}" ] || HOME=$(cd ~ && pwd -P)
export HOME
DEST="${KOBIL_SDK_DIR:-$HOME/.kobil-sdk/plugin}"
PLUGIN=kobil-sdk
MARKETPLACE=kobil-sdk-local

# setup.sh and the launcher read secrets from the macOS Keychain.
[ "$(uname)" = Darwin ] || { echo "kobil-sdk: this installer runs on macOS only" >&2; exit 1; }
for TOOL in git uv; do
  command -v "$TOOL" >/dev/null 2>&1 || { echo "kobil-sdk: $TOOL not found; install it and run this again" >&2; exit 1; }
done
AGENTS=
for AGENT in claude codex gemini; do
  if command -v "$AGENT" >/dev/null 2>&1; then AGENTS="$AGENTS $AGENT"; fi
done
[ -n "$AGENTS" ] || { echo "kobil-sdk: no agent found; install Claude Code, Codex CLI or Gemini CLI and run this again" >&2; exit 1; }

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

# Before the agents: Claude Code and Codex copy .mcp.json, which must already name this folder.
"$DEST/setup.sh" </dev/null

register_claude() {
  if claude plugin marketplace list 2>/dev/null | grep -q "$MARKETPLACE"; then
    claude plugin marketplace update "$MARKETPLACE"
  else
    claude plugin marketplace add "$DEST"
  fi
  claude plugin install "$PLUGIN@$MARKETPLACE"
}

# Both commands replace an earlier registration, so a second run refreshes Codex's cached copy.
register_codex() {
  codex plugin marketplace add "$DEST"
  codex plugin add "$PLUGIN@$MARKETPLACE"
}

# A link reads this folder in place. Gemini refuses to link over an existing extension, so an
# earlier one is removed first; that fails harmlessly on a first install.
register_gemini() {
  gemini extensions uninstall "$PLUGIN" >/dev/null 2>&1 || true
  gemini extensions link --consent "$DEST"
}

# Under "curl | sh" stdin is this script, so no agent command may read from it.
for AGENT in $AGENTS; do
  echo "Registering with $AGENT"
  "register_$AGENT" </dev/null
done
echo "Installed for:$AGENTS. Start a new agent session to load it; ignore the Xcode line above unless you use Xcode."
