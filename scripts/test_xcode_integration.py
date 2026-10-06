#!/usr/bin/env python3
"""Automated Xcode adapter package lane; does not claim Xcode UI qualification."""
import argparse
import asyncio
from datetime import timedelta, datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ide_setup import prepare, RELEASE
from kobil_sdk_integration.runtime_info import identity, fingerprint

REQUIRED = {'sdk_runtime_info', 'sdk_service_catalog', 'sdk_backend_status',
            'sdk_knowledge_topics', 'sdk_knowledge_get', 'sdk_environment_select'}


def decode(result):
    if result.isError:
        raise AssertionError('MCP tool returned an error')
    return json.loads(result.content[0].text)


async def probe(manifest, expected_identity, log_path):
    """Launch exactly the generated definition in a credential-free child context."""
    definition = next(iter(json.loads(manifest.read_text())['mcpServers'].values()))
    # Host environment is intentionally not inherited: fixture backend only.
    env = {key: os.environ[key] for key in ('PATH', 'SYSTEMROOT', 'WINDIR') if key in os.environ}
    env.update(definition['env'])
    with tempfile.TemporaryDirectory(prefix='kobil-ide-home-') as home:
        env['HOME'] = home
        params = StdioServerParameters(command=definition['command'], args=definition['args'], env=env)
        with log_path.open('w') as error_log:
            async with stdio_client(params, errlog=error_log) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)) as session:
                    await session.initialize()
                    names = {tool.name for tool in (await session.list_tools()).tools}
                    if not REQUIRED <= names:
                        raise AssertionError('Required MCP capabilities missing')
                    actual = decode(await session.call_tool('sdk_runtime_info', {}))
                    if actual != expected_identity:
                        raise AssertionError('Running MCP identity differs from candidate')
                    topics = decode(await session.call_tool('sdk_knowledge_topics', {'platform': 'ios'}))
                    if not topics.get('topics'):
                        raise AssertionError('No iOS knowledge topics')
                    knowledge = decode(await session.call_tool('sdk_knowledge_get', {'topic': 'setup', 'platform': 'ios'}))
                    if not knowledge:
                        raise AssertionError('Empty iOS setup knowledge')
                    missing = await session.call_tool('sdk_backend_status', {})
                    if not missing.isError or 'CONNECTION_NOT_SELECTED' not in str(missing.content):
                        raise AssertionError('Missing connection was not diagnosed')
                    return {'runtime': actual, 'required_tools': sorted(REQUIRED),
                            'observed_calls': ['sdk_runtime_info', 'sdk_knowledge_topics',
                                               'sdk_knowledge_get', 'sdk_backend_status']}


async def run(output, commit=None, development=False):
    output = output.expanduser().absolute()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    cases = []
    metadata = {'lane': 'package', 'started_at': datetime.now(timezone.utc).isoformat(),
                'requested_commit': commit, 'development': development,
                'xcode_host_qualified': False, 'cases': cases}
    def record(case, status, detail):
        cases.append({'id': case, 'status': status, 'detail': detail})
    try:
        with tempfile.TemporaryDirectory(prefix='kobil-xcode-fixture-') as temporary:
            project = Path(temporary).resolve() / 'App with spaces'
            (project / '.kobil-sdk').mkdir(parents=True)
            # Existing-onboarding fixture avoids user identity creation. X04 is a separate gate.
            (project / '.kobil-sdk/credential-request.txt').write_text('Fixture already onboarded\n')
            sentinel = project / 'README.md'
            sentinel.write_text('Existing app sentinel\n')
            adapter = project / '.kobil-sdk/adapter'
            setup = prepare(project, 'xcode', adapter, expected_commit=commit, development=development)
            metadata['candidate_commit'] = setup['commit']
            record('X01', 'PASS', 'Explicit project binding; setup pin/development policy accepted')
            for name in ['skills', 'docs']:
                if fingerprint(RELEASE / name, ['**/*']) != fingerprint(adapter / name, ['**/*']):
                    raise AssertionError('Copied skill/documentation differs from candidate')
            record('X02-content', 'PASS', 'Full skill/reference/docs trees match candidate by content hash')
            metadata['skill_sha256'] = fingerprint(adapter / 'skills', ['**/*'])
            root_definition = json.loads((adapter / 'plugin.json').read_text())['mcpServers']
            if root_definition != json.loads((adapter / '.mcp.json').read_text())['mcpServers']:
                raise AssertionError('Plugin manifests disagree on runtime')
            metadata['protocol'] = await asyncio.wait_for(probe(adapter / '.mcp.json', identity(), output / 'mcp-stderr.log'), timeout=90)
            record('X03', 'PASS', 'Actual generated manifest launched; initialize, discovery and knowledge calls succeeded')
            record('X05-missing', 'PASS', 'No connection produces CONNECTION_NOT_SELECTED')
            record('X09-runtime', 'PASS', 'Running source/package/knowledge identity matches candidate')
            try:
                prepare(project, 'xcode', adapter, expected_commit=commit, development=development)
            except ValueError as error:
                if 'already exists' not in str(error): raise
            else:
                raise AssertionError('Existing output was overwritten')
            if sentinel.read_text() != 'Existing app sentinel\n':
                raise AssertionError('Existing app file changed')
            record('X08-repeat', 'PASS', 'Existing output refused and app sentinel preserved')
            record('X15-X19', 'NOT_RUN', 'Xcode UI import/chat/update/removal require the host lane')
        metadata['status'] = 'PASS'
    except BaseException as error:
        metadata['status'] = 'FAIL'
        # No raw exception/profile/agent content in summary. Fixture stderr stays local.
        record('runner', 'FAIL', type(error).__name__)
        raise
    finally:
        metadata['finished_at'] = datetime.now(timezone.utc).isoformat()
        (output / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
        (output / 'manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
        lines = ['# Xcode adapter package lane', '', 'Status: ' + metadata.get('status', 'FAIL'),
                 '', 'Xcode host qualification: NOT RUN', '', '| Case | Status | Evidence |', '|---|---|---|']
        lines += [f"| {row['id']} | {row['status']} | {row['detail']} |" for row in cases]
        (output / 'report.md').write_text('\n'.join(lines) + '\n')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lane', choices=['package'], default='package')
    parser.add_argument('--output', required=True, type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--commit')
    group.add_argument('--development', action='store_true')
    args = parser.parse_args()
    try:
        result = asyncio.run(run(args.output, args.commit, args.development))
    except Exception:
        print('Package lane FAILED; inspect the local report.', file=sys.stderr)
        return 1
    print(json.dumps({'status': result['status'], 'report': str(args.output / 'report.md'), 'xcode_host_qualified': False}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
