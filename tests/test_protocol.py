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
                        self.assertEqual(len(names), 179)
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
                        for name in ['sdk_app_get', 'sdk_app_versions']:
                            result = await session.call_tool(name, {'expected_environment': 'wrong', 'app_name': 'sample'})
                            self.assertTrue(result.isError)
        asyncio.run(check())
