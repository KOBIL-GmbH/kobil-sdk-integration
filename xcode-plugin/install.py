#!/usr/bin/env python3
"""Install a pinned MCP/skill release and prepare an Xcode 27 import folder."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

VERSION = "0.1.0"
TAG = "v0.3.3"
COMMIT = "6736dc9f8cde8bbc29e4d484575677f86b30e36e"
REPOSITORY = "https://github.com/KOBIL-GmbH/kobil-sdk-integration.git"


def run(args):
    # Do not echo subprocess output: deployment helpers may contain private data.
    try:
        return subprocess.run(args, check=True, capture_output=True, text=True,
                              timeout=300, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}).stdout
    except (subprocess.SubprocessError, OSError) as exc:
        raise RuntimeError(f"{Path(args[0]).name} failed; check installation and network access.") from exc


def verify_release(release, git):
    if release.is_symlink():
        raise RuntimeError("Release directory must not be a symlink.")
    if run([git, "-C", str(release), "rev-parse", "HEAD"]).strip() != COMMIT:
        raise RuntimeError("Release commit does not match the pin.")
    if run([git, "-C", str(release), "status", "--porcelain"]).strip():
        raise RuntimeError("Release checkout has local modifications; restore it before installing.")


def plugin_files(release, connection=None, keychain=None, plugin=None):
    server = {"type": "stdio", "command": str(release / ".venv/bin/kobil-sdk-mcp"),
              "args": [], "tools": ["*"]}
    if connection:
        server["env"] = {"KOBIL_SDK_CONNECTION": str(connection)}
    if keychain:
        server["command"] = str(release / ".venv/bin/python")
        server["args"] = [str(plugin / "launch.py")]
    common = {"name": "kobil-sdk-xcode", "version": VERSION,
              "description": f"KOBIL mobile app integration, MCP and skill pinned to {TAG}."}
    encode = lambda value: json.dumps(value, indent=2) + "\n"
    # Xcode imports the root manifest; agent-specific manifests also declare the MCP.
    files = {
        "plugin.json": encode({**common, "mcpServers": {"KOBILSDK": server}}),
        ".mcp.json": encode({"mcpServers": {"KOBILSDK": server}}),
        ".codex-plugin/plugin.json": encode({**common, "skills": "./skills/", "mcpServers": "./.mcp.json"}),
        ".claude-plugin/plugin.json": encode({**common, "skills": ["./skills/kobil-sdk"], "mcpServers": "./.mcp.json"}),
        "skills/kobil-sdk/SKILL.md": (
            "---\nname: kobil-sdk\ndescription: Build KOBIL Swift iOS, Kotlin Android and Flutter Android/iOS apps with the pinned integration release.\n---\n\n"
            f"Read and follow [the canonical KOBIL SDK skill](<{release}/skills/kobil-sdk/SKILL.md>). "
            "Resolve all references relative to that canonical file; its docs and recipes remain together in the release installation. "
            "Use the KOBILSDK MCP tools. Ask for missing app and deployment choices. "
            "SDK binaries are supplied separately. Never expose credentials, JWTs, PINs or activation codes. "
            "Record build and actual runtime verification separately.\n"
        ),
    }
    if keychain:
        files["launch.py"] = launcher_text(release, keychain)
    return files


def launcher_text(release, keychain):
    service, account, secret_env = keychain
    if not re.fullmatch(r"KOBIL_[A-Z0-9_]+", secret_env):
        raise ValueError("Secret environment variable must use a KOBIL_ prefix.")
    return f'''# Local credential bridge. No secret values are stored here.
import os
import subprocess
import sys

def main():
    try:
        result = subprocess.run(
            ['/usr/bin/security', 'find-generic-password', '-s', {service!r},
             '-a', {account!r}, '-w'], capture_output=True, text=True,
            check=True, timeout=120)
        secret = result.stdout.removesuffix('\\n')
        if not secret:
            raise ValueError('empty credential')
    except (subprocess.SubprocessError, OSError, ValueError):
        print('KOBIL SDK: Keychain credential unavailable. Check the item and macOS access prompt.', file=sys.stderr)
        sys.exit(1)
    env = dict(os.environ)
    env[{secret_env!r}] = secret
    executable = {str(release / '.venv/bin/kobil-sdk-mcp')!r}
    os.execve(executable, [executable], env)

if __name__ == '__main__':
    main()
'''


def write_plugin(destination, files):
    # Idempotent, but never overwrite a user's edited plugin or follow symlinks.
    if destination.is_symlink():
        raise RuntimeError("Plug-in directory must not be a symlink.")
    if destination.exists():
        existing = set()
        for path in destination.rglob("*"):
            if path.is_symlink():
                raise RuntimeError("Existing plug-in contains a symlink.")
            if path.is_file():
                existing.add(path.relative_to(destination).as_posix())
        if existing != set(files) or any((destination / name).read_text() != value for name, value in files.items()):
            raise RuntimeError("Plug-in folder differs; choose a new destination to preserve customizations.")
        return
    destination.mkdir(parents=True, mode=0o700)
    for name, value in files.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x") as handle:
            handle.write(value)


def check_mcp(release):
    # Intentionally no backend env/config: this verifies discovery and a local tool only.
    script = """import asyncio,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def main():
 async with stdio_client(StdioServerParameters(command=sys.argv[1],env={})) as (r,w):
  async with ClientSession(r,w) as s:
   await s.initialize()
   tools=await s.list_tools()
   assert len(tools.tools)==13, 'unexpected tool count'
   result=await s.call_tool('sdk_targets',{})
   assert not result.isError, 'sdk_targets failed'
   print('13 tools; sdk_targets succeeded')
asyncio.run(main())
"""
    return run([str(release / ".venv/bin/python"), "-c", script,
                str(release / ".venv/bin/kobil-sdk-mcp")]).strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=Path.home() / ".local/share/kobil-sdk-xcode" / VERSION)
    parser.add_argument("--git", default="git", help="Git executable name or absolute path")
    parser.add_argument("--uv", default="uv", help="uv executable name or absolute path")
    parser.add_argument("--connection", type=Path, help="Optional private connection JSON path, never a credential")
    parser.add_argument("--keychain-service", help="Existing macOS generic-password item service name")
    parser.add_argument("--keychain-account", help="Existing Keychain item account")
    parser.add_argument("--secret-env", help="KOBIL_ prefixed variable named in the connection JSON")
    parser.add_argument("--check", action="store_true", help="Verify 13 MCP tools and sdk_targets without backend access")
    args = parser.parse_args(argv)
    if sys.platform != "darwin":
        parser.error("Xcode packaging requires macOS.")
    git, uv = shutil.which(args.git), shutil.which(args.uv)
    if not git or not uv:
        parser.error("Install Git and uv, or supply --git and --uv executable paths.")
    destination = args.destination.expanduser().resolve()
    if any(c in str(destination) for c in "\n\r<>"):
        parser.error("Choose a destination without newlines or angle brackets.")
    connection = args.connection.expanduser().resolve() if args.connection else None
    if connection and not connection.is_file():
        parser.error("Connection JSON must be an existing private file.")
    keychain = (args.keychain_service, args.keychain_account, args.secret_env)
    if any(keychain):
        if not all(keychain) or not connection:
            parser.error("Keychain requires --connection, --keychain-service, --keychain-account and --secret-env.")
        if not re.fullmatch(r"KOBIL_[A-Z0-9_]+", args.secret_env):
            parser.error("Secret environment variable must use a KOBIL_ prefix.")
        try:
            cfg = json.loads(connection.read_text())
            expected = cfg.get("token_env") or cfg["oauth"]["client_secret_env"]
            if expected != args.secret_env:
                raise ValueError()
        except (ValueError, KeyError, TypeError, AttributeError):
            parser.error("Connection secret reference must match --secret-env.")
    else:
        keychain = None
    release = destination / "release"
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not release.exists():
        print(f"Downloading {TAG} from GitHub…", flush=True)
        run([git, "clone", "--branch", TAG, "--depth", "1", REPOSITORY, str(release)])
    verify_release(release, git)
    print("Installing locked dependencies…", flush=True)
    run([uv, "sync", "--frozen", "--python", "3.11", "--directory", str(release)])
    verify_release(release, git)
    plugin = destination / "plugin"
    write_plugin(plugin, plugin_files(release, connection, keychain, plugin))
    if args.check:
        print(check_mcp(release))
    print(f"In Xcode: Settings → Intelligence → Plug-ins → Add Plug-in → Add from file\nSelect: {plugin}\nKeep this installation directory: the imported plug-in uses its pinned runtime and skill.")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"Installation stopped: {error}", file=sys.stderr)
        sys.exit(1)
