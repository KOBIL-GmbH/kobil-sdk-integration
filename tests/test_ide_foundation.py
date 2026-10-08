import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from mcp.server.fastmcp import FastMCP
from kobil_sdk_integration.backend import _read_configuration, ConfigurationError
from kobil_sdk_integration.ide_http import build_app, read_token
os.environ.setdefault('KOBIL_SDK_SENTRY_ENVIRONMENT', 'tests')  # test runs report to Sentry, filter on environment
os.environ.setdefault('KOBIL_SDK_USAGE_LOG', '0')


class DiagnosticsTests(unittest.TestCase):
    def test_configuration_diagnostics_redact_values(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'secret-profile.json'
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ConfigurationError, 'CONNECTION_NOT_SELECTED'):
                    _read_configuration()
            with self.assertRaisesRegex(ConfigurationError, 'CONNECTION_FILE_NOT_FOUND'):
                _read_configuration(path=str(p))
            for text, code in [('private-secret', 'JSON_INVALID'),
                               (json.dumps({'schema_version': 99, 'secret': 'private-secret'}), 'SCHEMA_UNSUPPORTED'),
                               (json.dumps({'secret': 'private-secret'}), 'FIELDS_INVALID')]:
                p.write_text(text)
                with self.assertRaises(ConfigurationError) as caught:
                    _read_configuration(path=str(p))
                self.assertIn(code, str(caught.exception))
                self.assertNotIn('private-secret', str(caught.exception))
                self.assertNotIn(str(p), str(caught.exception))

    def test_profile_is_preserved(self):
        cfg = {'environment': 'fixture', 'tenant': 'test', 'ast_url': 'https://example.com',
               'schema_version': 2, 'auth': {'type': 'oauth_password', 'username': 'test',
               'client_id': 'client', 'token_url': 'https://example.com/token', 'scope': 'openid custom',
               'credential': {'provider': 'env', 'name': 'TEST_PASSWORD'}},
               'admin': {'idp_url': 'https://example.com', 'realm': 'test', 'client_id': 'admin',
                         'username': 'admin', 'password_env': 'TEST_ADMIN_PASSWORD'}}
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'profile.json'
            p.write_text(json.dumps(cfg))
            self.assertEqual(_read_configuration(path=str(p)), cfg)

    def test_private_token_file(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'token'
            p.write_text('a' * 48)
            p.chmod(0o600)
            self.assertEqual(read_token(p), 'a' * 48)
            link = Path(directory) / 'link'
            link.symlink_to(p)
            with self.assertRaises(ValueError): read_token(link)
            p.chmod(0o644)
            with self.assertRaises(ValueError): read_token(p)


class HttpBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_auth_host_origin_and_real_protocol(self):
        mcp = FastMCP('fixture', stateless_http=True, json_response=True)
        @mcp.tool()
        def fixture(): return {'ok': True}
        app = build_app(mcp, 'a' * 48, 8765)
        async with mcp.session_manager.run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://127.0.0.1:8765') as client:
                headers = {'Authorization': 'Bearer ' + 'a' * 48,
                           'Accept': 'application/json, text/event-stream'}
                request = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                           'params': {'protocolVersion': '2025-03-26', 'capabilities': {},
                                      'clientInfo': {'name': 'test', 'version': '1'}}}
                self.assertEqual((await client.post('/mcp', json=request)).status_code, 401)
                self.assertEqual((await client.post('/mcp', json=request, headers={**headers, 'Authorization': 'wrong'})).status_code, 401)
                self.assertEqual((await client.post('/mcp', json=request, headers={**headers, 'Host': 'evil.example'})).status_code, 421)
                self.assertEqual((await client.post('/mcp', json=request, headers={**headers, 'Origin': 'https://evil.example'})).status_code, 403)
                response = await client.post('/mcp', json=request, headers=headers)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['result']['serverInfo']['name'], 'fixture')
                response = await client.post('/mcp', json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'fixture', 'arguments': {}}}, headers=headers)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.json()['result'].get('isError', False))


class AdapterTests(unittest.TestCase):
    def test_three_hosts_are_project_bound_and_preserve_existing_files(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('ide_setup', Path(__file__).resolve().parents[1] / 'scripts/ide_setup.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory).resolve() / 'App with spaces'
            project.mkdir()
            sentinel = project / 'README.md'
            sentinel.write_text('customer file')
            for host in ['vscode', 'xcode', 'android-studio']:
                out = project / host
                result = module.prepare(project, host, out, development=True)
                self.assertFalse(result['installed_in_host'])
                info = json.loads((out / 'installation.json').read_text())
                self.assertEqual(info['project'], str(project))
                self.assertTrue((out / 'skills/kobil-sdk/SKILL.md').is_file())
                self.assertTrue((out / 'docs/backend.md').is_file())
                if host != 'android-studio':
                    definition = next(iter(json.loads((out / '.mcp.json').read_text())['mcpServers'].values()))
                    self.assertEqual(definition['env']['KOBIL_SDK_PROJECT'], str(project))
                    self.assertEqual(definition['env']['KOBIL_SDK_CONNECTION'], '')
                else:
                    self.assertEqual((out / 'http-token').stat().st_mode & 0o777, 0o600)
                    self.assertEqual((out / 'mcp-settings.private.json').stat().st_mode & 0o777, 0o600)
                with self.assertRaisesRegex(ValueError, 'already exists'):
                    module.prepare(project, host, out, development=True)
            self.assertEqual(sentinel.read_text(), 'customer file')
            with self.assertRaisesRegex(ValueError, 'clean checkout'):
                module.prepare(project, 'vscode', project / 'invalid-pin', expected_commit='0' * 40)


class ProcessTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_two_projects_keep_separate_connections(self):
        import sys
        from contextlib import AsyncExitStack
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            async with AsyncExitStack() as stack:
                sessions = []
                profiles = []
                for name in ['first', 'second']:
                    project = root / name
                    (project / '.kobil-sdk').mkdir(parents=True)
                    # Fixture already onboarded; no identity creation in a user's home.
                    (project / '.kobil-sdk/credential-request.txt').write_text('fixture')
                    profile = project / 'connection.json'
                    profile.write_text(json.dumps({'environment': name, 'tenant': 'fixture',
                                                  'ast_url': 'https://example.test', 'token_env': 'FIXTURE_TOKEN'}))
                    profiles.append(profile)
                    params = StdioServerParameters(command=sys.executable,
                        args=['-m', 'kobil_sdk_integration.ide_stdio'],
                        env={**os.environ, 'KOBIL_SDK_PROJECT': str(project), 'KOBIL_SDK_CONNECTION': str(profile)})
                    read, write = await stack.enter_async_context(stdio_client(params))
                    session = await stack.enter_async_context(ClientSession(read, write))
                    await session.initialize()
                    sessions.append(session)
                first = await sessions[0].call_tool('sdk_backend_status', {})
                self.assertEqual(json.loads(first.content[0].text)['environment'], 'first')
                changed = await sessions[0].call_tool('sdk_environment_select', {
                    'connection_path': str(profiles[1]), 'expected_current_environment': 'first',
                    'expected_environment': 'second'})
                self.assertFalse(changed.isError)
                changed = await sessions[1].call_tool('sdk_environment_select', {
                    'connection_path': str(profiles[0]), 'expected_current_environment': 'second',
                    'expected_environment': 'first'})
                self.assertFalse(changed.isError)
                first = await sessions[0].call_tool('sdk_backend_status', {})
                second = await sessions[1].call_tool('sdk_backend_status', {})
                self.assertEqual(json.loads(first.content[0].text)['environment'], 'second')
                self.assertEqual(json.loads(second.content[0].text)['environment'], 'first')
                knowledge = await sessions[0].call_tool('sdk_knowledge_topics', {})
                self.assertFalse(knowledge.isError)

    async def test_http_process_start_call_stop_and_port_collision(self):
        import asyncio
        import socket
        import sys
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / '.kobil-sdk').mkdir()
            (project / '.kobil-sdk/credential-request.txt').write_text('fixture')
            token = project / 'token'
            token.write_text('b' * 48)
            token.chmod(0o600)
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            command = [sys.executable, '-m', 'kobil_sdk_integration.ide_http', '--project', str(project),
                       '--token-file', str(token), '--port', str(port)]
            process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            try:
                async with httpx.AsyncClient() as client:
                    for _ in range(100):
                        if process.returncode is not None: self.fail('HTTP process exited during startup')
                        try:
                            response = await client.post(f'http://127.0.0.1:{port}/mcp')
                            if response.status_code == 401: break
                        except httpx.ConnectError: pass
                        await asyncio.sleep(0.05)
                    else: self.fail('HTTP process did not become ready')
                async with streamablehttp_client(f'http://127.0.0.1:{port}/mcp', headers={'Authorization': 'Bearer ' + 'b' * 48}) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool('sdk_knowledge_topics', {})
                        self.assertFalse(result.isError)
                collision = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                try:
                    self.assertNotEqual(await asyncio.wait_for(collision.wait(), 10), 0)
                finally:
                    if collision.returncode is None:
                        collision.terminate()
                        await collision.wait()
            finally:
                if process.returncode is None: process.terminate()
                await asyncio.wait_for(process.wait(), 10)
