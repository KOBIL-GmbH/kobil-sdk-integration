#!/usr/bin/env python3
"""Prepare a project-bound IDE adapter without editing IDE/user settings."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import tomllib

RELEASE = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')
    path.chmod(0o600)


def prepare(project, host, output, connection=None, port=8765, expected_commit=None, development=False):
    project = Path(project).expanduser().resolve(strict=True)
    if not project.is_dir():
        raise ValueError('Project must be an existing directory')
    if host not in {'vscode', 'xcode', 'android-studio'}:
        raise ValueError('Unsupported IDE')
    if not 1024 <= port <= 65535:
        raise ValueError('Choose a port between 1024 and 65535')
    commit = subprocess.check_output(['git', '-C', str(RELEASE), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = bool(subprocess.check_output(['git', '-C', str(RELEASE), 'status', '--porcelain'], text=True).strip())
    if not development and (dirty or not expected_commit or expected_commit != commit):
        raise ValueError('Use a clean checkout and its full --expected-commit, or explicitly --development')
    # A runtime from another checkout must not silently serve a different MCP.
    from kobil_sdk_integration import server
    if Path(server.__file__).resolve().parent != RELEASE / 'src/kobil_sdk_integration':
        raise ValueError('Run with this release installation Python interpreter')
    if connection:
        from kobil_sdk_integration.backend import _read_configuration
        connection = str(Path(connection).expanduser().resolve(strict=True))
        _read_configuration(path=connection)
    output = Path(output).expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('Output already exists; prepare a new adapter directory for update or rollback')
    output.parent.mkdir(parents=True, exist_ok=True)
    version = tomllib.loads((RELEASE / 'pyproject.toml').read_text())['project']['version']
    with tempfile.TemporaryDirectory(prefix='.ide-prepare-', dir=output.parent) as directory:
        stage = Path(directory) / 'adapter'
        stage.mkdir(mode=0o700)
        shutil.copytree(RELEASE / 'skills', stage / 'skills')
        shutil.copytree(RELEASE / 'docs', stage / 'docs')
        # Keep the complete skill/reference/docs relative layout, paired with this runtime.
        env = {'KOBIL_SDK_PROJECT': str(project), 'KOBIL_SDK_CONNECTION': connection or ''}
        definition = {'command': sys.executable, 'args': ['-m', 'kobil_sdk_integration.ide_stdio'], 'env': env}
        name = 'kobil-sdk-' + hashlib.sha256(str(project).encode()).hexdigest()[:10]
        common = {'name': name, 'version': version, 'description': 'Project-bound KOBIL SDK integration'}
        metadata = {'adapter_schema': 1, 'host': host, 'project': str(project), 'runtime_release': str(RELEASE),
                    'runtime_commit': commit, 'development': development, 'dirty': dirty,
                    'mcp_version': version, 'mobile_sdk_version': 'supplied separately',
                    'saved_connection': connection, 'active_connection': 'query sdk_backend_status in the IDE'}
        if host in {'vscode', 'xcode'}:
            write_json(stage / '.mcp.json', {'mcpServers': {name: definition}})
            if host == 'vscode':
                (stage / '.claude-plugin').mkdir()
                write_json(stage / '.claude-plugin/plugin.json', {**common, 'skills': ['./skills/kobil-sdk'], 'mcpServers': './.mcp.json'})
                write_json(stage / 'settings-fragment.json', {'chat.plugins.enabled': True, 'chat.pluginLocations': {str(output): True}})
            else:
                write_json(stage / 'plugin.json', {**common, 'mcpServers': {name: definition}})
                (stage / '.codex-plugin').mkdir()
                write_json(stage / '.codex-plugin/plugin.json', {**common, 'skills': './skills/', 'mcpServers': './.mcp.json'})
        else:
            token = secrets.token_urlsafe(48)
            token_path = stage / 'http-token'
            token_path.write_text(token + '\n')
            token_path.chmod(0o600)
            write_json(stage / 'mcp-settings.private.json', {'mcpServers': {name: {
                'httpUrl': f'http://127.0.0.1:{port}/mcp', 'headers': {'Authorization': 'Bearer ' + token}}}})
            argv = [sys.executable, '-m', 'kobil_sdk_integration.ide_http', '--project', str(project),
                    '--token-file', str(output / 'http-token'), '--port', str(port)]
            if connection:
                argv += ['--connection', connection]
            # Python launcher avoids shell quoting and remains foreground for explicit lifecycle ownership.
            (stage / 'start.py').write_text('import os\nos.execv(' + repr(sys.executable) + ', ' + repr(argv) + ')\n')
            (stage / 'start.py').chmod(0o700)
        write_json(stage / 'installation.json', metadata)
        (stage / '.gitignore').write_text('*\n')
        os.rename(stage, output)
    return {'adapter': str(output), 'host': host, 'mcp_version': version,
            'commit': commit, 'development': development, 'installed_in_host': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--host', required=True, choices=['vscode', 'xcode', 'android-studio'])
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--connection', type=Path)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--expected-commit')
    parser.add_argument('--development', action='store_true')
    args = parser.parse_args()
    try:
        result = prepare(**vars(args))
    except ValueError as error:
        parser.exit(2, str(error) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
