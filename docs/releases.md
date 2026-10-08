# Versioned installation and releases

## Install v0.4.0

Requires Git, Python 3.11+ and uv. While this repository is private, Git must
already be authenticated with an account that has access. Never put an access
token in the clone URL or MCP configuration. SDK binaries are supplied separately.

Install each release into its own directory; do not reuse a development checkout:

```sh
git clone --branch v0.4.0 --depth 1 https://github.com/KOBIL-GmbH/kobil-sdk-integration.git /absolute/path/kobil-sdk/releases/v0.4.0
cd /absolute/path/kobil-sdk/releases/v0.4.0
git describe --tags --exact-match
uv sync --frozen --python 3.11
```

The checkout is detached at the release tag. Record `git rev-parse HEAD` in your
installation record. Compare it with the release's commit; for stricter pinning,
use that full commit when checking out. Published version tags must never move.
`uv sync --frozen` uses the committed dependency lockfile. Tool installation from
a Git URL alone does not enforce this project's transitive dependency lock.

## VS Code / GitHub Copilot

Add this entry to the user MCP configuration with **MCP: Open User Configuration**.
Replace all paths with your installation's absolute paths; GUI applications may
need the absolute path to the uv executable as well.

```json
{
  "servers": {
    "KOBILSDK": {
      "type": "stdio",
      "command": "/absolute/path/to/uv",
      "args": ["run", "--frozen", "--directory", "/absolute/path/kobil-sdk/releases/v0.4.0", "kobil-sdk-mcp"],
      "env": {
        "KOBIL_SDK_CONNECTION": "/absolute/path/private/kobil-sdk/connection.json"
      }
    }
  }
}
```

Merge the server entry with existing configuration. Do not replace other servers.
Without backend configuration the planning/artifact tools still work. Follow
[backend setup](backend.md) for a connection and secrets provided by your runtime
or secret manager. A local secret-manager launcher may wrap the pinned executable;
it must stay outside the source and release checkout, and must not follow `main`.
No account, backend URL, SDK binary or credential is included in a release.

Use the skill from the **same** release:
`/absolute/path/kobil-sdk/releases/v0.4.0/skills/kobil-sdk/SKILL.md`.
For Copilot with a release checkout (not the plugin folder, which Copilot installs itself),
create a personal `~/.copilot/skills/kobil-sdk/SKILL.md` with frontmatter
`name: kobil-sdk` and a concise integration description. Its body should instruct
the agent to read that absolute canonical skill path and resolve references from
there. Custom agents should point at the same canonical path. Do not copy just
the skill folder: it also references the release's docs directory.

Start KOBILSDK in the MCP server list. Verify discovery of 41 tools and call
`sdk_targets`. Test backend access separately with authorized read-only operations.
A running MCP does not prove native activation or login passed.

## Xcode 27 (Claude and Codex agents)

### Self-contained plugin folder (hand-over)

The builder `scripts/build_plugin.py` is part of the source repository
(https://github.com/KOBIL-GmbH/kobil-sdk-integration), not of the plugin folder it writes. It
writes one folder that carries everything: skills, docs, the MCP server code with `uv.lock`, a
launcher (`bin/kobil-sdk-mcp`), `setup.sh`, `INSTALL.md` and `config/`. Only listed files are
copied; `.git`, `.venv`, tests and assistant folders never are. Run it from a clean, committed
checkout (ideally the release tag); it refuses uncommitted changes unless `--allow-dirty` is
given for a development copy.

```sh
python3 scripts/build_plugin.py --out /absolute/path/kobil-sdk \
  --connection /absolute/path/connection.json \
  --keychain KOBIL_SDK_CLIENT_SECRET=<keychain service>[:<account>] \
  --keychain KOBIL_SDK_ADMIN_PASSWORD=<keychain service> \
  --zip /absolute/path/kobil-sdk.zip
```

- `config/connection.json` is the given connection. It may name only variables for secrets
  (`*_env`); a literal secret is refused. `config/connection.example.json` shows the fields.
  Name one `--keychain ENV=SERVICE[:ACCOUNT]` per secret variable the connection names.
- `config/keychain.txt` maps each variable to a login-Keychain entry; the launcher reads them
  at every start. No secret is written anywhere.
- `setup.sh` (run by the builder, and by the recipient after unzipping) writes the folder's
  absolute launcher path into `.mcp.json`, prepares the Python environment in
  `~/.kobil-sdk/venvs/` (outside the folder) with `uv sync --frozen` and reports missing
  Keychain entries.
- The zip is portable: it leaves out `.venv`, `*.egg-info` and caches, and its `.mcp.json`
  names `${CLAUDE_PLUGIN_ROOT}/bin/kobil-sdk-mcp` instead of the builder's folder. The recipient
  installs uv, unzips, runs `./setup.sh`, adds the folder in Xcode ▸ Settings ▸ Intelligence and
  starts a new chat. The folder must stay where `setup.sh` ran: the MCP runs from it.
- `release.json` records version, tag, commit, whether the checkout was dirty, and build time.
- An existing output folder is kept as `<folder>.previous`.
- GitHub Copilot (the CLI and Copilot inside Xcode) ignores Xcode's plugin import. The folder
  carries `.github/plugin/marketplace.json`, so `copilot plugin marketplace add <folder>` and
  `copilot plugin install kobil-sdk@kobil-sdk-local` load it live (no copy): skills and the
  same MCP launcher. Remove an older `KOBILSDK` entry from `~/.copilot/mcp-config.json`.

In Xcode ▸ Settings ▸ Intelligence remove an older KOBIL SDK plugin, add the folder, and
start a new agent chat. After an upgrade, rebuild the folder from the new release and
import it again: Xcode keeps its own copy.

## Upgrade and rollback

Install the new tag in a new version directory, review CHANGELOG.md, run discovery
and relevant tests, then switch **both** MCP and skill paths to the new release (for Xcode, rebuild and
re-import the plugin).
Restart the MCP and start a fresh agent session to avoid mixed skill versions.
Keep the old installation until verification passes; rollback by restoring both
paths. Do not copy credentials into version directories. A rollback does not undo
backend mutations. Never run `git pull` in a release installation.

## Version policy

MCP package, plugin manifest, skill recipes and dependency lock ship together.
Versions follow MAJOR.MINOR.PATCH:

- PATCH: compatible fixes, documentation and packaging corrections.
- MINOR: new tools or compatible capabilities. Before 1.0, breaking changes may
  occur in a minor release and must be called out in the changelog.
- MAJOR: incompatible public contracts after 1.0.

Each release has an annotated `vX.Y.Z` Git tag and a GitHub Release with changes,
compatibility notes, known limits and commit identity. Never overwrite a released
tag or artifact. SDK binary versions are independent of this integration version.

## Maintainer checklist

1. Work on a feature branch. Update pyproject.toml and .codex-plugin/plugin.json
   to the same version; update CHANGELOG.md and installation examples.
2. Run `uv lock`, `uv sync --frozen`, and
   `uv run --frozen python -m unittest discover -s tests -v`.
3. Verify manifest/package/lock versions match, run an MCP stdio discovery check,
   and inspect the diff for secrets, binaries and internal information.
4. Merge the tested change to main; create an annotated version tag on that exact
   commit. Push the tag and publish a GitHub Release with its commit and notes.
5. Install from GitHub into a new directory and verify it independently of the
   development tree before migrating consumers. Keep backend-specific evidence
   private and distinguish startup, backend and app-runtime verification.
