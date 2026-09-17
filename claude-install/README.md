# KOBIL SDK for Claude

One setup command installs the pinned MCP and guide for Claude Code, Claude
Desktop, or both. Installer preview **0.1.0** uses integration **v0.3.3** at
`6736dc9f8cde8bbc29e4d484575677f86b30e36e`. It never installs from main.
SDK binaries are delivered separately. This is a setup script, not a published
Claude directory extension or a self-contained MCPB bundle.

## Quick start

Install Git, [uv](https://docs.astral.sh/uv/getting-started/installation/), and the
Claude client you want to use. Python 3.9+ is needed to run this installer; uv
prepares Python 3.11 for the pinned server. Claude Code must be signed in.
Download and extract the installer archive, or clone this repository. From its
root, run:

```sh
python3 claude-install/install.py
```

On macOS you can instead double-click **Install Claude.command** in the
`claude-install` folder. It installs both clients by default. For only one:

```sh
python3 claude-install/install.py --client code
python3 claude-install/install.py --client desktop
```

On Windows use `py` instead of `python3`. Claude Desktop configuration is supported
on macOS/Windows; Claude Code also supports Linux. Native Windows/Linux runs still
need separate verification. Supply `--git`, `--uv` or `--claude` with the full
executable path if the tool is unavailable from the terminal's PATH.

The installer downloads and verifies the fixed Git commit, installs dependencies
from its lockfile and tests tool discovery, target listing and guide access.
Then it registers a dedicated local marketplace/plugin for Code and/or adds one
`KOBILSDKRelease` entry to Desktop. Other servers and settings are preserved.
Existing different configurations are refused; Desktop gets a private backup.
Keep `~/.local/share/kobil-sdk-claude/0.1.0`: both clients use its runtime.
Do not share this generated directory. Share the source installer archive.

### Claude Code

Start a fresh session in your app directory and invoke:

```text
/kobil-sdk-release:kobil-sdk-release
```

Then request, for example: “Build a fresh Swift iOS app with activation and login.
Read the SDK guide and ask for missing SDK artifacts and backend setup.”

### Claude Desktop

Quit and reopen Claude Desktop. Enable **KOBILSDKRelease** for the chat and ask:

> Use sdk_guide to read the KOBIL integration skill, then plan my app.

Desktop receives all 13 pinned integration tools plus `sdk_guide`, which reads
the complete skill and its linked public Markdown documents. The extension does
not grant shell/file-edit/build tools. Use Claude Code for building and running
local apps; Desktop chat can plan and perform authorized backend operations.
The guide is exposed as an MCP tool, not installed as a native Desktop skill.

## Backend setup (optional)

Initial installation works without a backend for planning and documentation.
Activation setup and app registration require a customer-provided connection and
service-client credential. See [backend setup](../docs/backend.md).
Do not enter secrets in chat, command arguments or the connection JSON.

For macOS, create a generic-password entry through Keychain Access, then use:

```sh
python3 claude-install/install.py --client desktop \
  --destination "$HOME/.local/share/kobil-sdk-claude/0.1.0-connected" \
  --connection "$HOME/.config/kobil-sdk/connection.json" \
  --keychain-service kobil-sdk-development \
  --keychain-account service-client \
  --secret-env KOBIL_SDK_CLIENT_SECRET
```

Use your actual Keychain identifiers and match the profile's secret-variable
name. The launcher reads the secret at startup and passes it in the MCP process
only. The installer and startup check never read Keychain or contact a backend.
On other platforms, your secret manager must supply the profile's named variable
to the Claude process; a terminal export does not configure an already-running
Desktop app. This installer deliberately rejects unreleased version-2 profiles.

If already installed planning-only, explicitly remove the old KOBIL entry/plugin
before activating a differently configured installation. The installer refuses
to overwrite it automatically. For Code, remove `kobil-sdk-release@kobil-sdk-local`
and its `kobil-sdk-local` marketplace using Claude's plugin commands, then rerun.
For Desktop remove only `mcpServers.KOBILSDKRelease` from its configuration through
Settings → Developer → Edit Config, preserving other entries; then rerun.

After restart, request `sdk_backend_status`. `configured:true` with
`connection_verified:false` means local validation passed and no network check
was attempted. Request `sdk_app_get` for your known app to verify backend access.
No resource is created by these checks. Never import internal admin/deployment
launchers into a customer installation.

## Removal, upgrades and verification

Remove the dedicated Code plugin/marketplace with Claude's plugin commands and/or
only the Desktop `KOBILSDKRelease` config entry. Restart Claude before removing
its installation directory. Credentials and SDK files remain separate.
Use a new destination for a future pinned release and switch both guide and MCP
together. Never `git pull` inside the release checkout.

For verification without modifying your Claude configuration:

```sh
python3 claude-install/install.py --prepare-only
python3 -m unittest discover -s claude-install/tests -v
python3 claude-install/package.py
```

The generated ZIP contains the portable setup scripts and documentation only.
The MCP guide bridge is installer-owned; the tagged integration source remains
unchanged. Local setup checks are not proof of backend access, device activation,
or native Windows/Linux support.

References: [Claude plugin reference](https://code.claude.com/docs/en/plugins-reference),
[Claude Desktop local MCP setup](https://modelcontextprotocol.io/docs/develop/connect-local-servers).
