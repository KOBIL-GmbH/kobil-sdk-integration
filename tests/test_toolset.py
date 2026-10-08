"""IDE hosts get a small tool set by default; the full catalog stays available.

Optional small tool set (KOBIL_SDK_TOOLSET=start); the default stays the full catalog. Subprocess tests
keep the global server object untouched.
"""
import asyncio
import json
import os
import subprocess
import sys
import unittest

PROBE = r"""
import asyncio, json, os, sys
from kobil_sdk_integration import server
from kobil_sdk_integration.toolset import apply
mode = os.environ.get('MODE', 'full')
apply(server.mcp, mode)
tools = asyncio.run(server.mcp.list_tools())
print(json.dumps({'names': sorted(t.name for t in tools), 'bytes': len(json.dumps([t.model_dump(mode='json') for t in tools]))}))
"""


def probe(mode):
    env = {**os.environ, 'MODE': mode}
    out = subprocess.run([sys.executable, '-c', PROBE], capture_output=True, text=True, env=env, check=True).stdout
    return json.loads(out.strip().splitlines()[-1])


class ToolsetTests(unittest.TestCase):
    def test_full_keeps_the_whole_catalog(self):
        full = probe('full')
        self.assertGreaterEqual(len(full['names']), 190)

    def test_start_is_small_and_covers_the_standard_journey(self):
        from kobil_sdk_integration.toolset import START
        full, start = probe('full'), probe('start')
        self.assertLessEqual(len(start['names']), 60)
        self.assertLess(start['bytes'], 60 * 1024)
        self.assertEqual(sorted(START), start['names'])
        self.assertTrue(set(START) <= set(full['names']), 'unknown tool name in START: ' + str(set(START) - set(full['names'])))

    def test_start_hides_administration_tools(self):
        start = probe('start')
        self.assertNotIn('sdk_idp_policy_create', start['names'])
        self.assertIn('sdk_runtime_info', start['names'])
        self.assertIn('sdk_tms_trigger', start['names'])

    def test_unknown_mode_is_rejected(self):
        from kobil_sdk_integration import toolset
        with self.assertRaises(ValueError):
            toolset.apply(object(), 'everything')

    def test_ide_entry_point_keeps_the_full_catalog_by_default(self):
        import tempfile
        from unittest.mock import patch
        from kobil_sdk_integration import ide_stdio
        seen = {}
        with tempfile.TemporaryDirectory() as project, patch.dict(os.environ, {'KOBIL_SDK_PROJECT': project}):
            os.environ.pop('KOBIL_SDK_TOOLSET', None)
            with patch('kobil_sdk_integration.server.main', lambda: seen.update(mode=os.environ.get('KOBIL_SDK_TOOLSET'))):
                ide_stdio.main()
        self.assertIsNone(seen['mode'])


if __name__ == '__main__':
    unittest.main()
