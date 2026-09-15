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
                        self.assertEqual(len(names), 11)
                        result = await session.call_tool('sdk_backend_status', {})
                        self.assertFalse(result.isError)
                        self.assertNotIn('protocol-fixture', str(result))
                        result = await session.call_tool('sdk_app_ensure', {
                            'expected_environment': 'wrong', 'app_name': 'sample', 'categories': ['tms']})
                        self.assertTrue(result.isError)
                        self.assertNotIn('protocol-fixture', str(result))
        asyncio.run(check())
