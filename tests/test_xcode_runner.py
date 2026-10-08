"""Acceptance harness regressions: false-green prevention and actual manifest launch."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, AsyncMock

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import test_xcode_integration as runner
import os
os.environ.setdefault('KOBIL_SDK_SENTRY_ENVIRONMENT', 'tests')  # test runs report to Sentry, filter on environment
os.environ.setdefault('KOBIL_SDK_USAGE_LOG', '0')


class XcodeRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_generated_manifest_and_failure_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = await runner.run(root / 'pass', development=True)
            self.assertEqual(result['status'], 'PASS')
            self.assertFalse(result['xcode_host_qualified'])
            self.assertTrue(any(row['id'] == 'X03' and row['status'] == 'PASS' for row in result['cases']))
            with patch.object(runner, 'probe', new=AsyncMock(side_effect=AssertionError('fixture failure'))):
                with self.assertRaises(AssertionError):
                    await runner.run(root / 'fail', development=True)
            report = json.loads((root / 'fail/manifest.json').read_text())
            self.assertEqual(report['status'], 'FAIL')
            self.assertTrue((root / 'fail/report.md').is_file())

    async def test_wrong_running_identity_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / '.kobil-sdk').mkdir()
            (root / '.kobil-sdk/credential-request.txt').write_text('fixture')
            adapter = root / 'adapter'
            runner.prepare(root, 'xcode', adapter, development=True)
            expected = runner.identity()
            expected['source_sha256'] = '0' * 64
            with self.assertRaises(ExceptionGroup) as caught:
                await asyncio.wait_for(runner.probe(adapter / '.mcp.json', expected, root / 'stderr.log'), 60)
            errors = [caught.exception]
            leaves = []
            while errors:
                error = errors.pop()
                if isinstance(error, BaseExceptionGroup): errors.extend(error.exceptions)
                else: leaves.append(error)
            self.assertTrue(any(isinstance(e, AssertionError) and 'identity differs' in str(e) for e in leaves))

    def test_fingerprint_detects_renamed_or_changed_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            p = root / 'file.py'
            p.write_text('fixture')
            original = runner.fingerprint(root, ['*.py'])
            p.rename(root / 'other.py')
            self.assertNotEqual(original, runner.fingerprint(root, ['*.py']))
