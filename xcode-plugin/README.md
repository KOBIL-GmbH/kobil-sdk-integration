# KOBIL SDK for Xcode 27

This installer prepares a combined skill and MCP plug-in for Xcode's coding
agents. Packaging version **0.1.0** pins integration release **v0.3.3** to commit
`6736dc9f8cde8bbc29e4d484575677f86b30e36e`. SDK binaries are supplied separately.
This is an agent plug-in, not a VS Code webview or a source-editor extension.

## Install

Requires macOS, Xcode 27 with a signed-in coding agent, Python 3.11+, Git and
[uv](https://docs.astral.sh/uv/getting-started/installation/). Download or clone
this public repository, then run from its root:

```sh
python3 xcode-plugin/install.py --check
```

If Git or uv is absent from your PATH, pass `--git /absolute/path/to/git` or
`--uv /absolute/path/to/uv`. No GitHub sign-in is required. The installer clones
the pinned tag, verifies its commit and clean checkout **before** installing
dependencies with `uv sync --frozen --python 3.11`.

1. Open **Xcode → Settings → Intelligence → Plug-ins → Add Plug-in**.
2. Select **Add from file**, then the `plugin` folder printed by the installer.
3. Confirm the preview contains **1 skill and 1 MCP server**, then import it.
4. Start a new conversation and ask: “Use the KOBIL SDK skill. Call sdk_targets
   and report its supported platforms.” Allow the server for that session.

The default installation is `~/.local/share/kobil-sdk-xcode/0.1.0`. Use
`--destination /absolute/path/to/installation` to change it. Keep that directory:
Xcode copies the plug-in but its runtime and canonical skill reference this
installation. Paths are resolved for each Mac; neither another user's home
directory nor shell-variable expansion is assumed. **Do not share the generated
folder**; share this installer. Run it on each recipient's Mac.

`--check` verifies 13-tool discovery and the local `sdk_targets` tool. It does
not use Keychain, authenticate to your backend, build an app or test activation.
The skill loads the complete pinned recipe and its relative documentation from
the release directory, rather than an incomplete copied skill folder.

## Backend credentials

Planning works without credentials. For backend operations, create a private
[connection JSON](../docs/backend.md) outside the repository. It contains service
URLs, tenant, client ID and a **secret environment-variable name**, not a secret.
Obtain a service client authorized for your tenant and the needed operations
from your backend administrator. This plug-in does not create credentials.

For Xcode's GUI, use an existing **generic-password** item in macOS Keychain.
You can create it in Keychain Access using **File → New Password Item**. Set the
item name (service) and account to your chosen identifiers and enter your client
secret in its password field. Do not paste that secret into chat or a command.
Then prepare a separate connected installation:

```sh
python3 xcode-plugin/install.py \
  --destination "$HOME/.local/share/kobil-sdk-xcode/0.1.0-connected" \
  --connection "$HOME/.config/kobil-sdk/connection.json" \
  --keychain-service kobil-sdk-development \
  --keychain-account service-client \
  --secret-env KOBIL_SDK_CLIENT_SECRET \
  --check
```

Use your own item identifiers; `--secret-env` must match the connection JSON's
`oauth.client_secret_env` (or `token_env` for a bearer token). The local launcher
reads the item at MCP startup, captures it without logging, and passes it only
in the MCP process environment. macOS may request permission to read the item.
No password is embedded in manifests, command-line arguments or the skill.
An OAuth client secret is exchanged for a token by the MCP; supplied bearer
tokens must be renewed by their owner. Restart the MCP after rotation.

Import this folder instead of enabling both the planning-only and connected
copies. Existing preview KOBIL plug-ins may also cause duplicate skills/tools;
disable or remove those entries in Xcode when switching. The installer does not
edit Xcode preferences, grant permissions or overwrite existing customizations.

Alternatively `--connection` alone can be used if your agent launch environment
already supplies the named secret. A shell `export` does not reliably reach an
already-running GUI application. Missing secrets cause backend calls to fail.

## Updates, removal and verification limits

Use a new installation directory for changed configuration or future versions;
the installer refuses to overwrite modified generated files. Re-running an
unchanged installation is safe. Review changes before reimporting into Xcode.
Never `git pull` inside the pinned release. Remove the plug-in in Xcode before
removing its local installation; Keychain items and private connection files
remain under your control. Removing files does not undo backend operations.

Xcode 27 import and `sdk_targets` were tested with a local coding agent. Backend
authentication and native app flows require separate deployment/device checks.
If Codex reports an expired token, sign out/in under Intelligence settings.
This login is separate from KOBIL backend credentials.

Apple reference: [Extending and customizing agents](https://developer.apple.com/documentation/xcode/extending-and-customizing-agents).

Run packaging tests with `python3 -m unittest discover -s xcode-plugin/tests -v`.
Build a shareable installer archive with `python3 xcode-plugin/package.py`.
The archive and SHA-256 file appear in `dist/`; the archive contains only the
installer and documentation. Extract it and run `python3 xcode-plugin/install.py
--check` from the extracted directory. Do not zip a locally generated plug-in or
installation directory: those contain machine-specific paths and may reference
private connection details.

Keychain handoff and failure redaction have automated tests using a dummy
credential. Live Keychain access prompts and customer backend authentication
must be checked separately; the installer never reads a credential during setup.
