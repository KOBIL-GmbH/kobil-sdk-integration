#!/bin/sh
# Run once after unzipping or moving this folder. It points .mcp.json at this folder's
# launcher (Xcode needs an absolute path), prepares the Python environment and checks the
# Keychain entries. It prints no secret.
set -eu
ROOT=$(cd "$(dirname "$0")" && pwd -P)
[ -n "${HOME:-}" ] || HOME=$(cd ~ && pwd -P)
export HOME
# Same location the launcher uses: outside this folder, so nothing machine-specific is in it.
UV_PROJECT_ENVIRONMENT="${KOBIL_SDK_VENV:-$HOME/.kobil-sdk/venvs/$(/sbin/md5 -q -s "$ROOT")}"
export UV_PROJECT_ENVIRONMENT
# An older build kept it inside the folder, where Xcode would copy it; it is rebuilt outside.
if [ -d "$ROOT/.venv" ]; then
  rm -rf "$ROOT/.venv"
  echo "Removed the old .venv from this folder"
fi
chmod +x "$ROOT/bin/kobil-sdk-mcp"
cat > "$ROOT/.mcp.json" <<EOF
{
  "mcpServers": {
    "KOBILSDK": {
      "command": "$ROOT/bin/kobil-sdk-mcp",
      "args": []
    }
  }
}
EOF
echo "MCP launcher: $ROOT/bin/kobil-sdk-mcp"

UV=
for CANDIDATE in "$HOME/.local/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv "$HOME/.cargo/bin/uv"; do
  [ -x "$CANDIDATE" ] && { UV="$CANDIDATE"; break; }
done
[ -n "$UV" ] || UV=$(command -v uv 2>/dev/null) || { echo "Install uv first: https://docs.astral.sh/uv/"; exit 1; }
"$UV" sync --quiet --frozen --directory "$ROOT" && echo "Python environment ready: $UV_PROJECT_ENVIRONMENT"

if [ -f "$ROOT/config/connection.json" ]; then
  echo "Backend connection: $ROOT/config/connection.json"
else
  echo "No config/connection.json: copy config/connection.example.json and fill it in"
fi
while read -r NAME SERVICE ACCOUNT; do
  case "$NAME" in ''|'#'*) continue ;; esac
  if /usr/bin/security find-generic-password -s "$SERVICE" ${ACCOUNT:+-a "$ACCOUNT"} >/dev/null 2>&1; then
    echo "Keychain: $NAME found ($SERVICE)"
  else
    echo "Keychain: $NAME missing. Add it with: security add-generic-password -s $SERVICE ${ACCOUNT:+-a $ACCOUNT }-w"
  fi
done < "$ROOT/config/keychain.txt"
echo "Now add this folder in Xcode > Settings > Intelligence and start a new chat."
