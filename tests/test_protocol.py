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
                idp_path = Path(directory) / 'idp.json'
                idp_path.write_text(json.dumps({'schema_version': 2, 'environment': 'test',
                    'realm': 'sample', 'admin_url': 'https://idp.example/admin',
                    'allow_test_provisioning': True, 'auth': {'type': 'bearer',
                    'credential': {'provider': 'keyring', 'service': 'fixture', 'account': 'missing'}}}))
                params = StdioServerParameters(command=sys.executable,
                    args=['-c', 'from kobil_sdk_integration.server import main; main()'],
                    env={**os.environ, 'KOBIL_SDK_CONNECTION': str(path), 'KOBIL_SDK_IDP_CONNECTION': str(idp_path), 'SDK_TEST_TOKEN': 'protocol-fixture'})
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        names = {t.name for t in (await session.list_tools()).tools}
                        self.assertEqual(len(names), 17)
                        self.assertTrue({'sdk_app_get', 'sdk_app_versions'} <= names)
                        result = await session.call_tool('sdk_idp_status', {})
                        self.assertFalse(result.isError)  # No access to the absent Keychain item.
                        for name, args in [
                            ('sdk_idp_user_get', {'username': 'fixture'}),
                            ('sdk_idp_test_user_create', {'username': 'fixture'}),
                            ('sdk_idp_activation_write', {'username': 'fixture', 'user_id': 'fixture', 'output_path': '/unused'})]:
                            result = await session.call_tool(name, dict(args, expected_environment='wrong'))
                            self.assertTrue(result.isError)
                            self.assertIn('IDP_ENVIRONMENT_MISMATCH', str(result))
                        result = await session.call_tool('sdk_backend_status', {})
                        self.assertFalse(result.isError)
                        self.assertNotIn('protocol-fixture', str(result))
                        result = await session.call_tool('sdk_app_ensure', {
                            'expected_environment': 'wrong', 'app_name': 'sample', 'categories': ['tms']})
                        self.assertTrue(result.isError)
                        self.assertNotIn('protocol-fixture', str(result))
                        for name in ['sdk_app_get', 'sdk_app_versions']:
                            result = await session.call_tool(name, {'expected_environment': 'wrong', 'app_name': 'sample'})
                            self.assertTrue(result.isError)
        asyncio.run(check())
