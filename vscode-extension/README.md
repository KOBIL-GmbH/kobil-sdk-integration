# KOBIL SDK Integration for VS Code

A guided setup dashboard for building Kotlin Android, Swift iOS and Flutter
Android/iOS apps with GitHub Copilot.

1. Install this VSIX using **Extensions: Install from VSIX**.
2. Open **KOBIL SDK: Open Setup** from the command palette or the KOBIL activity icon.
3. Choose **Install integration**. Git and uv must be available; configurable paths
   are available under **Tool paths & settings**. The private GitHub repository
   currently requires an already-authenticated Git installation.
4. Optionally import your deployment connection JSON and enter its credential in
   the secure prompt. The dashboard provides a template; its example URLs must
   be replaced with your complete deployment service map.
5. Choose **Check setup**, then **Open Copilot**. Select **KOBIL Release Builder**
   in the agent picker and send your app request.

The extension installs MCP and skill release **v0.3.3**, checks its exact commit,
and uses the committed uv dependency lock. No main-branch installation or silent
version upgrade. Credentials are stored with VS Code SecretStorage and passed
only to the MCP process. Config JSON is copied to extension storage, never the
project. No binaries, SDK download credentials or backend defaults are bundled.

The new MCP is named **KOBIL SDK Release**; existing user MCP entries and agents
are preserved. The release agent/skill use distinct names to avoid overwriting
manual installations. These files live in your personal `.copilot` directory
and continue to exist when the extension is uninstalled; remove
`agents/kobil-release-builder.agent.md` and `skills/kobil-sdk-release` if no longer
needed. Reinstalling repairs managed files; custom files are not overwritten.

Setup checks verify MCP startup, 13-tool discovery and local config parsing.
They do not certify backend authentication, activation or device behavior.
Backend access is exercised when you request an operation through Copilot.
SDK binaries arrive separately; app compilation requires Android/iOS/Flutter
build tools. Only the local desktop extension host is supported in this preview.

## Development

Node.js 22+:

```sh
npm ci
npm test
npm run package
```

Extension version 0.1.0 is independent of its pinned MCP/skill release 0.3.3.
This is a local VSIX preview, not a published Marketplace extension. Marketplace
publication requires an authorized publisher account and distribution approval.
