#!/usr/bin/env python3
"""Install the pinned KOBIL MCP and guide for Claude Code and/or Claude Desktop."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('pinned_installer', ROOT / 'xcode-plugin/install.py')
pinned = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pinned)
NAME = 'KOBILSDKRelease'


def desktop_path():
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/Claude/claude_desktop_config.json'
    if sys.platform == 'win32' and os.environ.get('APPDATA'):
        return Path(os.environ['APPDATA']) / 'Claude/claude_desktop_config.json'
    raise RuntimeError('Claude Desktop setup supports macOS and Windows only.')


def merge_desktop(path, server):
    """Preserve unrelated settings and refuse to replace an existing custom server."""
    if path.is_symlink():
        raise RuntimeError('Desktop configuration must not be a symlink.')
    original = path.read_bytes() if path.exists() else None
    try:
        cfg = json.loads(original) if original is not None else {}
        if not isinstance(cfg, dict) or not isinstance(cfg.get('mcpServers', {}), dict):
            raise ValueError()
    except ValueError:
        raise RuntimeError('Desktop configuration is invalid; no changes made.') from None
    servers = cfg.setdefault('mcpServers', {})
    if NAME in servers:
        if servers[NAME] == server:
            return
        raise RuntimeError('KOBILSDKRelease already has a different setup; no changes made.')
    servers[NAME] = server
    path.parent.mkdir(parents=True, exist_ok=True)
    # Unique backup, retained for explicit rollback. Never print its contents.
    if original is not None:
        fd, backup = tempfile.mkstemp(prefix=path.name + '.backup-', dir=path.parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(original)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.new-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(cfg, stream, indent=2)
            stream.write('\n')
        # Refuse a detected concurrent edit rather than overwriting it.
        if (path.read_bytes() if path.exists() else None) != original:
            raise RuntimeError('Desktop configuration changed during setup; retry.')
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def generated_files(release, destination, connection=None, keychain=None):
    python = release / ('.venv/Scripts/python.exe' if os.name == 'nt' else '.venv/bin/python')
    server = {'command': str(python), 'args': [str(destination / 'bridge.py'), str(destination / 'runtime.json')]}
    skill = '''---
name: kobil-sdk-release
description: Integrate KOBIL SDK features into Kotlin Android, Swift iOS and Flutter Android/iOS apps with the fixed release.
---

Call sdk_guide to read the canonical integration skill and its linked references.
Use the KOBILSDKRelease MCP tools. SDK binaries are supplied separately.
A successful sdk_backend_status with configured:true and connection_verified:false
means configuration is valid but the backend has not been contacted. Continue
with an authorized read-only app lookup when backend verification is requested.
Do not request secrets in chat. App building requires local build tools.
'''
    files = {
        'bridge.py': (ROOT / 'claude-install/bridge.py').read_text(),
        'runtime.json': json.dumps({'release': str(release), 'connection': str(connection) if connection else None,
                                    'keychain': keychain}, indent=2) + '\n',
        'plugin/.claude-plugin/plugin.json': json.dumps({'name': 'kobil-sdk-release', 'version': '0.1.0',
            'description': 'KOBIL SDK integration pinned to v0.3.3.'}),
        'plugin/.mcp.json': json.dumps({'mcpServers': {NAME: server}}, indent=2),
        'plugin/skills/kobil-sdk-release/SKILL.md': skill,
        '.claude-plugin/marketplace.json': json.dumps({'name': 'kobil-sdk-local', 'owner': {'name': 'KOBIL'},
            'plugins': [{'name': 'kobil-sdk-release', 'source': './plugin', 'description': 'Pinned KOBIL MCP and skill.'}]}, indent=2),
    }
    return files, server


def check(release, server):
    python = release / ('.venv/Scripts/python.exe' if os.name == 'nt' else '.venv/bin/python')
    script = '''import asyncio,json,sys
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def main():
 p=StdioServerParameters(**json.loads(sys.argv[1]))
 async with stdio_client(p) as (r,w):
  async with ClientSession(r,w) as s:
   await s.initialize()
   names={t.name for t in (await s.list_tools()).tools}
   assert len(names)==14 and 'sdk_guide' in names
   for tool,args in [('sdk_targets',{}),('sdk_guide',{}),('sdk_guide',{'document':'docs/backend.md'})]:
    result=await s.call_tool(tool,args)
    assert not result.isError, tool
   print('14 tools; targets and pinned guide verified')
asyncio.run(main())
'''
    # Check never uses the connected runtime: no credential access or network.
    with tempfile.TemporaryDirectory() as folder:
        cfg = Path(folder) / 'runtime.json'
        cfg.write_text(json.dumps({'release': str(release)}))
        probe = dict(server, args=[server['args'][0], str(cfg)])
        return pinned.run([str(python), '-c', script, json.dumps(probe)]).strip()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--client', choices=['code','desktop','both'], default='both')
    p.add_argument('--destination', type=Path, default=Path.home()/'.local/share/kobil-sdk-claude/0.1.0')
    p.add_argument('--git', default='git'); p.add_argument('--uv', default='uv')
    p.add_argument('--claude', default='claude')
    p.add_argument('--connection', type=Path)
    p.add_argument('--keychain-service'); p.add_argument('--keychain-account'); p.add_argument('--secret-env')
    p.add_argument('--prepare-only', action='store_true', help='Prepare and verify without changing either Claude client.')
    a=p.parse_args(argv)
    git,uv=shutil.which(a.git),shutil.which(a.uv)
    if not git or not uv:
        p.error('Install Git and uv first, or pass their absolute executable paths.')
    cli=shutil.which(a.claude)
    if a.client in ('code','both') and not a.prepare_only and not cli:
        p.error('Claude Code is missing. Install it first or choose --client desktop.')
    target=desktop_path() if a.client in ('desktop','both') and not a.prepare_only else None
    connection=a.connection.expanduser().resolve() if a.connection else None
    keychain=(a.keychain_service,a.keychain_account,a.secret_env)
    if any(keychain):
        if sys.platform!='darwin' or not all(keychain) or not connection:
            p.error('Keychain needs macOS, a connection and all three Keychain options.')
        if not pinned.re.fullmatch(r'KOBIL_[A-Z0-9_]+',a.secret_env):
            p.error('Secret variable must use a KOBIL_ prefix.')
    else:keychain=None
    if connection:
        try:
            cfg=json.loads(connection.read_text())
            if cfg.get('schema_version') is not None:raise ValueError()
            expected=cfg.get('token_env') or cfg['oauth']['client_secret_env']
            if keychain and expected!=a.secret_env:raise ValueError()
        except (OSError,ValueError,KeyError,TypeError,AttributeError):
            p.error('Provide a legacy v0.3.3 profile with a matching secret reference; v2 is not released.')
    destination=a.destination.expanduser().resolve()
    release=destination/'release'; setup=destination/'setup'
    destination.mkdir(parents=True,exist_ok=True,mode=0o700)
    if not release.exists():
        print('Downloading pinned v0.3.3…',flush=True)
        pinned.run([git,'clone','--branch',pinned.TAG,'--depth','1',pinned.REPOSITORY,str(release)])
    pinned.verify_release(release,git)
    pinned.run([uv,'sync','--frozen','--python','3.11','--directory',str(release)])
    pinned.verify_release(release,git)
    files,server=generated_files(release,setup,connection,keychain)
    pinned.write_plugin(setup,files)
    print(check(release,server))
    if not a.prepare_only:
        if a.client in ('code','both'):
            marketplaces = json.loads(pinned.run([cli,'plugin','marketplace','list','--json']))
            for market in marketplaces:
                if market.get('name') == 'kobil-sdk-local' and market.get('path') != str(setup):
                    raise RuntimeError('kobil-sdk-local already uses another installation; remove it explicitly before switching.')
            pinned.run([cli,'plugin','marketplace','add',str(setup)])
            pinned.run([cli,'plugin','install','kobil-sdk-release@kobil-sdk-local','--scope','user'])
            print('Claude Code: plugin installed. Start a fresh session and use /kobil-sdk-release:kobil-sdk-release.')
        if target:
            merge_desktop(target,server)
            print('Claude Desktop: MCP configured. Quit and reopen Claude, enable KOBILSDKRelease, then ask it to read sdk_guide.')
    print('Setup:',setup)
    print('Backend: '+('configured; authentication not tested' if connection else 'not configured (planning and guide available)'))
    print('SDK binaries and mobile build tools are supplied separately.')


if __name__=='__main__':
    try:main()
    except RuntimeError as e:
        print('Installation stopped: '+str(e),file=sys.stderr);sys.exit(1)
