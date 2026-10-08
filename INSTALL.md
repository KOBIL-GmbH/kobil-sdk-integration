# KOBIL SDK plugin: install

1. Install [uv](https://docs.astral.sh/uv/) once.
2. Put this folder where it will stay, then run `./setup.sh` in it. Run it again after moving
   the folder: `.mcp.json` names the folder's absolute path.
3. Backend: `config/connection.json` holds the connection (environment, tenant, URLs,
   clients). To use another backend, edit it or replace it; `config/connection.example.json`
   shows the fields. A backend behind a VPN needs the VPN connected.
4. Secrets are never in a file. `config/keychain.txt` lists which Keychain entry fills which
   variable (`NAME service [account]`); `setup.sh` says which are missing and how to add them.
5. Xcode > Settings > Intelligence: remove an older kobil-sdk plugin, add this folder, start a
   new chat. It should list two skills and the `KOBILSDK` server. This covers Xcode's Claude and
   Codex agents and needs nothing from steps 6-7. Xcode keeps its own copy of the folder, so
   import it again after an update, and after **moving** the folder import it again as well as
   re-running `./setup.sh`: Xcode's copy still names the launcher's old absolute path.

Command-line agents, if you use them. Run `./setup.sh` (step 2) **before** these, so the
launcher path in `.mcp.json` is already absolute in whatever copy the host takes. Codex does not
expand `${CLAUDE_PLUGIN_ROOT}`, so installing it before `setup.sh` leaves it a path it cannot run.

6. GitHub Copilot (also Copilot inside Xcode), once:
   `copilot plugin marketplace add <this folder>` then
   `copilot plugin install kobil-sdk@kobil-sdk-local`. It loads the folder live, so a rebuild
   takes effect in the next session. Remove any older `KOBILSDK` entry from
   `~/.copilot/mcp-config.json` first, or Copilot starts two.
7. Claude Code: `claude plugin marketplace add <this folder>` then
   `claude plugin install kobil-sdk@kobil-sdk-local`. Codex CLI is the same two commands with
   `codex plugin marketplace add` and `codex plugin add`. Check with `claude plugin details
   kobil-sdk`: it lists `Skills (2)` and `MCP servers (1) KOBILSDK`.

`setup.sh` downloads the Python packages (public PyPI) into
`~/.kobil-sdk/venvs/`, outside this folder, so the folder stays small and holds nothing
specific to this Mac. If that environment is missing, the first MCP start creates it.
