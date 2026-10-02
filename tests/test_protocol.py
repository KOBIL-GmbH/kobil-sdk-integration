"""Exercise the installed server through the actual MCP stdio protocol."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class ProtocolTests(unittest.TestCase):
    def test_stdio_tools_and_environment_guard(self):
        async def check():
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'connection.json'
                path.write_text(json.dumps({'environment': 'test', 'tenant': 'sample',
                    'ast_url': 'https://backend.example', 'token_env': 'SDK_TEST_TOKEN'}))
                params = StdioServerParameters(command=sys.executable,
                    args=['-c', 'from kobil_sdk_integration.server import main; main()'],
                    env={**os.environ, 'KOBIL_SDK_CONNECTION': str(path), 'SDK_TEST_TOKEN': 'protocol-fixture'})
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        names = {t.name for t in (await session.list_tools()).tools}
                        self.assertEqual(len(names), 196)
                        self.assertIn('sdk_knowledge_bundle', names)
                        self.assertTrue({"sdk_deployment_preflight", "sdk_ios_signing_preflight"} <= names)
                        self.assertIn('sdk_tls_chain_check', names)
                        self.assertIn('sdk_tms_auth_diagnose', names)
                        auth = await session.call_tool('sdk_tms_auth_diagnose', {'exchange_requested_scopes': ['tms'], 'exchange_http_status': 200, 'exchanged_scopes': ['openid'], 'ast_error_code': 516004034})
                        self.assertFalse(auth.isError)
                        auth_payload = auth.structuredContent or json.loads(auth.content[0].text)
                        self.assertEqual(auth_payload['status'], 'blocked')
                        config_path = Path(directory) / 'mc_config.json'
                        config_path.write_text(json.dumps({'maverick': {'mTLS': True}, 'iam': {'clientId': 'Login'}}))
                        checked = await session.call_tool('sdk_deployment_preflight', {
                            'mc_config_path': str(config_path), 'expected_mtls': False,
                            'expected_token_client': 'Enrollment', 'granted_scopes': ['openid'],
                            'require_explicit_authentication': True, 'granted_scope_stage': 'explicit_auth'})
                        self.assertFalse(checked.isError)
                        checked_payload = checked.structuredContent or json.loads(checked.content[0].text)
                        self.assertEqual(checked_payload['status'], 'blocked')
                        self.assertEqual(len(checked_payload['errors']), 3)

                        self.assertTrue({'sdk_sftp_list', 'sdk_sftp_download'} <= names)
                        self.assertFalse({"sdk_idp_journeys", "sdk_activation_flow_ensure", "sdk_activation_client_ensure"} & names)
                        self.assertTrue({"sdk_idp_client_list", "sdk_idp_flow_list", "sdk_app_list"} <= names)
                        self.assertTrue({'sdk_app_get', 'sdk_app_versions'} <= names)
                        for platform in ('android', 'ios'):
                            for topic in ('setup', 'lifecycle', 'activation', 'login', 'multi_step', 'tms', 'diagnostics', 'logs'):
                                result = await session.call_tool('sdk_knowledge_get', {
                                    'topic': topic, 'platform': platform})
                                self.assertFalse(result.isError)
                                payload = result.structuredContent or json.loads(result.content[0].text)
                                self.assertTrue(payload['example']['compile_ready'])
                                self.assertFalse(payload['version_verified'])
                                self.assertEqual(payload['integration_generation'], 'classic_mcsdk_kssidp')
                                self.assertTrue(set(payload['backend_tools']) <= names)
                        gap = await session.call_tool('sdk_knowledge_get', {'topic': 'login', 'platform': 'flutter'})
                        self.assertFalse(gap.isError)
                        payload = gap.structuredContent or json.loads(gap.content[0].text)
                        self.assertEqual(payload['status'], 'knowledge_gap')
                        result = await session.call_tool('sdk_backend_status', {})
                        self.assertFalse(result.isError)
                        self.assertNotIn('protocol-fixture', str(result))
                        result = await session.call_tool('sdk_app_ensure', {
                            'expected_environment': 'wrong', 'app_name': 'sample', 'categories': ['tms']})
                        self.assertTrue(result.isError)
                        self.assertNotIn('protocol-fixture', str(result))
                        target = Path(directory) / 'target.json'
                        target.write_text(json.dumps({'environment': 'target', 'tenant': 'second',
                            'ast_url': 'https://target.example', 'token_env': 'SDK_TEST_TOKEN'}))
                        switched = await session.call_tool('sdk_environment_select', {
                            'connection_path': str(target), 'expected_current_environment': 'test',
                            'expected_environment': 'target'})
                        self.assertFalse(switched.isError)
                        status = await session.call_tool('sdk_backend_status', {})
                        payload = status.structuredContent or json.loads(status.content[0].text)
                        self.assertEqual(payload['environment'], 'target')
                        stale = await session.call_tool('sdk_environment_select', {
                            'connection_path': str(path), 'expected_current_environment': 'test',
                            'expected_environment': 'test'})
                        self.assertTrue(stale.isError)
                        for name in ['sdk_app_get', 'sdk_app_versions']:
                            result = await session.call_tool(name, {'expected_environment': 'wrong', 'app_name': 'sample'})
                            self.assertTrue(result.isError)
        asyncio.run(check())
