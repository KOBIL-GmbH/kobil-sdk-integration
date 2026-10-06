# IDE adapters (development preview)

One installed release supplies the MCP and complete skill for all three hosts.
These adapters are under qualification; generated configuration is not proof of
successful IDE discovery or app runtime behavior. SDK binaries remain separate.

## Prepare

Use the Python interpreter of the installed release, after `uv sync --frozen`:

```sh
/path/to/release/.venv/bin/python /path/to/release/scripts/ide_setup.py \
  --host vscode --project /absolute/app \
  --output /absolute/app/.kobil-sdk/ide/vscode-v1 \
  --expected-commit FULL_VERIFIED_COMMIT
```

Use `xcode` or `android-studio` for the other hosts. Optionally add
`--connection /absolute/connection.json`. Profiles are validated by the core and
referenced without rewriting them. Planning and onboarding work without backend
credentials. An absent connection produces `CONNECTION_NOT_SELECTED` only when
backend operations are requested. For a source-development checkout, explicitly
use `--development` instead of claiming an immutable release.

The output belongs to one project on this machine. Do not distribute it: Android
setup includes a local HTTP access token. Keep the installed release directory
available. Run setup separately on the receiving machine. Private age identities
remain managed by the existing onboarding tools outside the project.

## VS Code / Copilot

Merge the generated `settings-fragment.json` entries into **workspace** settings;
preserve other settings. The native Claude-format plugin contains the MCP and
canonical skill. Do not enable a second KOBIL registration for the same project.
Use the ordinary Agent mode with file/edit/terminal capabilities enabled; this
adapter does not restrict native build tools or change permission policy.

[Native plugin settings](https://code.visualstudio.com/docs/agent-customization/agent-plugins).

## Xcode

Add the generated adapter folder in Xcode's Intelligence plug-in settings. Check
the selected agent actually lists the KOBIL skill and MCP. Start a fresh chat for
qualification; do not assume an existing chat reloads tool schemas or skills.
Use native Xcode editing/build tools. Plugin configuration cannot grant approvals.

## Android Studio / Gemini

Start the generated `start.py` with the release Python in a dedicated terminal.
It runs in the foreground; Ctrl-C stops it. Use a distinct `--port` per concurrent
project. An occupied port must fail rather than selecting another project's server.

Merge `mcp-settings.private.json` into Settings → Tools → AI → MCP Servers,
preserving existing entries. It contains a local access token: do not paste it
into chat or commit it. Android Studio's header configuration is not claimed to be
a secure keychain. Enable MCP and inspect `/mcp`. Google sign-in is required for
an actual Gemini agent test.

For native skill discovery, copy the adapter's complete `skills/kobil-sdk`
directory to `.agents/skills/kobil-sdk` only if that destination is unused. Its
`../../docs` links require the adapter's `docs` directory at `.agents/docs` too;
do not overwrite existing files. Invoke `@kobil-sdk`. Skill installation will be
automated after this layout is verified in the host.

[HTTP setup](https://developer.android.com/studio/gemini/add-mcp-server).

## Verify, update, remove

1. Inspect `installation.json`: package version/commit and project binding.
2. In the actual IDE call `sdk_service_catalog`, `sdk_knowledge_topics`, and
   `sdk_knowledge_get`; load the matching skill. Required capabilities matter,
   not a fixed historical tool count.
3. `sdk_backend_status` validates configuration only. Backend authentication and
   app registration/activation/login/TMS are separate tests.
4. Create/edit a fixture file and run its build using native IDE tools.
5. Prepare a new output directory for an update; select it in the host and
   disable the previous registration. Reinstall/select the previous release's
   adapter to roll back. Existing outputs are never overwritten.
6. Disable/remove the host registration and stop its HTTP terminal to uninstall.
   Preserve project SDKs, encrypted bundles and private identities.

`sdk_environment_select` changes the active MCP process only. It does not change
`installation.json` or the saved startup selector. To persist a choice, prepare
an adapter with the selected connection path and reconnect. Other IDE processes
keep their own selection. On moving/copying a project, regenerate the adapter
with its new explicit path; use existing identity tools to choose identity reuse
or creation, never guess a missing private-key path.
