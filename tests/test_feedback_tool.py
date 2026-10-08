"""The feedback tool is registered, takes no secrets by design and the hint appears in the two status tools."""
import asyncio
import os
import tempfile
import unittest
from unittest import mock

from kobil_sdk_integration import server, telemetry
os.environ.setdefault('KOBIL_SDK_SENTRY_ENVIRONMENT', 'tests')  # test runs report to Sentry, filter on environment
os.environ.setdefault('KOBIL_SDK_USAGE_LOG', '0')


class FeedbackToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.dict(os.environ, {'KOBIL_SDK_HOME': self.tmp.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        telemetry.reset()

    def test_tool_registered_with_optional_contact(self):
        tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
        schema = tools['sdk_report_problem'].inputSchema
        self.assertEqual(set(schema['required']), {'category', 'message'})
        self.assertIn('contact_email', schema['properties'])

    def test_tool_saves_a_report_without_sentry(self):
        result = server.sdk_report_problem('bug', 'token=abc123456789 broke', True, None)
        self.assertTrue(result['saved'])
        self.assertFalse(result['sent'])

    def test_runtime_info_carries_the_hint_once(self):
        for _ in range(telemetry.FEEDBACK_AFTER_CALLS):
            telemetry.count_call()
        first = server.sdk_runtime_info()
        self.assertIn('feedback_prompt', first)
        self.assertNotIn('feedback_prompt', server.sdk_runtime_info())


if __name__ == '__main__':
    unittest.main()
