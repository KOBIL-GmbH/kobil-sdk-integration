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
                    env={**os.environ, 'KOBIL_SDK_CONNECTION': str(path), 'SDK_TEST_TOKEN': 'protocol-fixture', 'KOBIL_SDK_SFTP_CONNECTION': str(Path(directory) / 'missing-sftp.json')})
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        names = {t.name for t in (await session.list_tools()).tools}
                        self.assertGreaterEqual(len(names), 100)
                        self.assertTrue({"sdk_app_list", "sdk_idp_user_list", "sdk_idp_client_list", "sdk_backend_capabilities"} <= names)
                        self.assertTrue({'sdk_sftp_list', 'sdk_sftp_download'} <= names)
                        self.assertTrue({'sdk_app_get', 'sdk_app_versions'} <= names)
                        # method and environment discovery must be reachable as tools, not only
                        # as a skill file: most MCP clients never load a skill.
                        self.assertTrue({'sdk_docs', 'sdk_platforms', 'sdk_idp_clients',
                                         'sdk_backend_verify', 'sdk_mc_config',
                                         'sdk_activation_user_ensure', 'sdk_activation_code_set',
                                         'sdk_activation_flow_ensure', 'sdk_activation_client_ensure',
                                         'sdk_activation_flow_describe', 'sdk_activation_step_config'} <= names)
                        for tool, args in [('sdk_sftp_list', {}), ('sdk_sftp_download', {'relative_path': 'SDK.zip'})]:
                            response = await session.call_tool(tool, args)
                            self.assertTrue(response.isError)
                            self.assertIn('Invalid SFTP configuration', str(response))
                        result = await session.call_tool('sdk_docs', {})
                        self.assertFalse(result.isError)
                        self.assertIn('workflow', str(result))
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
