import asyncio
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from kobil_sdk_integration import code_samples, server

ROOT = Path(code_samples.ROOT)
FORBIDDEN = re.compile(r'(?i)/Users/|@kobil\.com|password\s*=|Johannes|Created by')


class CodeSamplesTest(unittest.TestCase):
    def test_tool_registered(self):
        tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
        self.assertEqual(tools['sdk_code_samples'].inputSchema['required'], ['platform'])

    def test_every_platform_and_topic(self):
        for platform in ('ios', 'android', 'flutter'):
            got = code_samples.get(platform)
            topics = {s['topic'] for s in got['samples']}
            self.assertTrue({'adapter', 'start', 'errors', 'timeout'} <= topics, platform)
            if platform == 'ios':
                self.assertIn('debug', topics)
            for s in got['samples']:
                self.assertTrue(s['code'].strip() and s['source'] and s['about'])
        self.assertEqual(len(code_samples.get('swift', 'errors')['samples']), 1)
        with self.assertRaises(ValueError):
            code_samples.get('windows')
        with self.assertRaises(ValueError):
            code_samples.get('ios', 'nothing')

    def test_index_files_exist_and_no_strays(self):
        index = json.loads((ROOT / 'code_samples' / 'index.json').read_text())
        listed = {s['file'] for p in index['platforms'].values() for s in p['samples']}
        on_disk = {str(p.relative_to(ROOT / 'code_samples')) for p in (ROOT / 'code_samples').glob('*/*') if p.is_file()}
        self.assertEqual(listed, on_disk)

    def test_no_personal_or_internal_references(self):
        for p in (ROOT / 'code_samples').glob('*/*'):
            self.assertIsNone(FORBIDDEN.search(p.read_text()), p.name)

    def test_brackets_balance(self):
        for p in list((ROOT / 'code_samples').glob('kotlin/*')) + list((ROOT / 'code_samples').glob('dart/*')):
            text = re.sub(r'//.*', '', p.read_text())
            for a, b in ('()', '{}', '[]'):
                self.assertEqual(text.count(a), text.count(b), p.name)

    def test_completion_handler_lists_never_overlap_and_cover_start(self):
        data = json.loads((ROOT / 'code_samples' / 'index.json').read_text())['completion_handler']
        needed = set(data['handler_required_examples'])
        allowed = {n.split(' ')[0] for n in data['nil_allowed']}
        self.assertFalse(needed & allowed)
        self.assertTrue({'Start', 'Restart', 'Activate', 'OfflineLogin'} <= needed)
        skill = (Path(__file__).parent.parent / 'skills' / 'kobil-sdk' / 'SKILL.md').read_text()
        self.assertIn('When the completion handler may be nil', skill)

    def test_event_result_lookup(self):
        self.assertEqual(code_samples.event_result('KSMStartEvent')['completion_handler'], 'handler_required')
        self.assertEqual(code_samples.event_result('Start')['result_event'], 'StartResult')
        self.assertEqual(code_samples.event_result('startTransactionEvent')['completion_handler'], 'nil_allowed')
        self.assertEqual(code_samples.event_result('ProvidePIN')['completion_handler'], 'nil_allowed')
        self.assertGreater(len(code_samples.event_result()['events']), 100)
        with self.assertRaises(ValueError):
            code_samples.event_result('Warning')
        self.assertIn('sdk_event_result', {t.name for t in asyncio.run(server.mcp.list_tools())})

    def test_reply_rule_and_restart_rule_are_stated(self):
        rules = ' '.join(code_samples.get('ios')['rules'])
        self.assertIn('Start', code_samples.get('ios')['completion_handler']['handler_required_examples'])
        self.assertIn('RuntimeErrorEvent', rules)
        self.assertIn('timeout', rules)

    @unittest.skipUnless(shutil.which('xcrun') and (Path.home() / '.kobil-sdk' / 'sdk-delivery').exists(), 'needs Xcode and a delivery')
    def test_swift_samples_compile_against_the_sdk(self):
        d = Path((Path.home() / '.kobil-sdk' / 'sdk-delivery').read_text().strip())
        slice_ = 'ios-arm64_x86_64-simulator'
        frames = [d / f'{n}.xcframework' / slice_ for n in ('KSMasterController', 'hnb', 'kssidp', 'KSTrustedWebView')]
        if not all(f.is_dir() for f in frames):
            self.skipTest('delivery has no simulator slices')
        cmd = ['xcrun', '--sdk', 'iphonesimulator', 'swiftc', '-typecheck', '-swift-version', '5',
               '-target', 'arm64-apple-ios17.0-simulator']
        for f in frames:
            cmd += ['-F', str(f)]
        cmd += sorted(str(p) for p in (ROOT / 'code_samples' / 'swift').glob('*.swift'))
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        self.assertEqual(done.returncode, 0, done.stderr[-2000:])


if __name__ == '__main__':
    unittest.main()
