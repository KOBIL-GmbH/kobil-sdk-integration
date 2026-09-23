import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kobil_sdk_integration import backend
from kobil_sdk_integration.server import mcp, sdk_backend_status, sdk_environment_select


class EnvironmentSelectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.a = self.profile('first')
        self.b = self.profile('second')
        env = patch.dict(os.environ, KOBIL_SDK_CONNECTION=str(self.a))
        env.start()
        self.addCleanup(env.stop)
        state = patch.object(backend, '_connection_override', None)
        state.start()
        self.addCleanup(state.stop)

    def profile(self, name):
        path = self.root / (name + '.json')
        path.write_text(json.dumps({'environment': name, 'tenant': name,
            'ast_url': 'https://' + name + '.example', 'token_env': 'FIXTURE_TOKEN'}))
        return path

    def select(self, path=None, current='first', target='second'):
        return sdk_environment_select(str(path or self.b), current, target)

    def test_select_reload_and_old_client_snapshot(self):
        original = self.a.read_bytes()
        client = backend.AST(backend.configuration())
        self.addCleanup(client.close)
        result = self.select()
        self.assertEqual(sdk_backend_status()['environment'], 'second')
        self.assertEqual(client.cfg['environment'], 'first')
        self.assertFalse(result['connection_verified'])
        self.assertFalse(result['persists_after_restart'])
        self.assertEqual(self.a.read_bytes(), original)
        self.assertEqual(os.environ['KOBIL_SDK_CONNECTION'], str(self.a))
        self.assertEqual(backend.configuration(path=str(self.a))['environment'], 'first')
        data = json.loads(self.b.read_text()); data['tenant'] = 'updated'
        self.b.write_text(json.dumps(data))
        self.assertEqual(sdk_backend_status()['tenant'], 'updated')
        with self.assertRaises(ValueError): backend.configuration('first')
        with patch.object(backend, '_connection_override', None):
            self.assertEqual(sdk_backend_status()['environment'], 'first')

    def test_failure_keeps_current_environment(self):
        invalid = self.root / 'invalid.json'; invalid.write_text('{secret malformed')
        for path, current, target in [(invalid, 'first', 'second'),
                (self.root / 'missing.json', 'first', 'second'),
                (self.b, 'stale', 'second'), (self.b, 'first', 'wrong'),
                (Path('relative.json'), 'first', 'second')]:
            with self.subTest(path=path, current=current, target=target):
                with self.assertRaises((ValueError, backend.BackendError)) as raised:
                    self.select(path, current, target)
                self.assertNotIn('secret malformed', str(raised.exception))
                self.assertEqual(sdk_backend_status()['environment'], 'first')

    def test_concurrent_stale_switches_only_one_wins(self):
        third = self.profile('third')
        def attempt(path, target):
            try: return self.select(path, target=target)['environment']
            except ValueError: return 'rejected'
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(attempt, self.b, 'second'), pool.submit(attempt, third, 'third')]
            results = [f.result() for f in futures]
        self.assertEqual(results.count('rejected'), 1)
        self.assertIn(sdk_backend_status()['environment'], ['second', 'third'])

    def test_encrypted_selector_and_decrypt_failure(self):
        selector = self.root / 'selector.json'
        selector.write_text(json.dumps({'age_environment': {
            'store': 'fixture.age', 'identity': 'fixture.key', 'environment': 'second'}}))
        with patch('kobil_sdk_integration.age_store.read_document',
                   return_value={'environments': {'second': json.loads(self.b.read_text())}}):
            self.select(selector)
            self.assertEqual(sdk_backend_status()['environment'], 'second')
        # A fresh process retains its original selection if target decrypt fails.
        with patch.object(backend, '_connection_override', None), patch(
                'kobil_sdk_integration.age_store.read_document', side_effect=RuntimeError('private detail')):
            with self.assertRaises(backend.BackendError) as raised: self.select(selector)
            self.assertNotIn('private detail', str(raised.exception))
            self.assertEqual(sdk_backend_status()['environment'], 'first')

    def test_mcp_dispatch_and_schema(self):
        async def check():
            tool = next(t for t in await mcp.list_tools() if t.name == 'sdk_environment_select')
            self.assertEqual(set(tool.inputSchema['required']),
                {'connection_path', 'expected_current_environment', 'expected_environment'})
            await mcp.call_tool('sdk_environment_select', {
                'connection_path': str(self.b), 'expected_current_environment': 'first',
                'expected_environment': 'second'})
            self.assertEqual(sdk_backend_status()['environment'], 'second')
        asyncio.run(check())
