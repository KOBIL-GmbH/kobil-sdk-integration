"""Contract replay: real recorded AST behaviour for TMS reads and the explicit-preflight client shapes.

``tests/fixtures/ast_tms_replay.json`` was recorded read-only on 2026-10-05
against terminal transactions (ACCEPTED, REJECTED, TIMEOUT, CANCELLED,
explicit ACCEPTED) roughly 2.5 h after completion: both the status and the
result endpoint answered 404. The tools must report unknown/possibly retained state, not infer a
failure or establish retention from 404 alone, and never re-trigger. The preflight shapes mirror the live
``sdk_tms_explicit_preflight`` response of the same day (optional scopes
``address, microprofile-jwt, offline_access, phone, tms``; browser override
"KOBIL Mobile Login") with the scope or the override removed.
"""
import json
import unittest
from pathlib import Path

import httpx

from kobil_sdk_integration import tms
from kobil_sdk_integration.backend import AST, BackendError
from kobil_sdk_integration.tms_auth import explicit_preflight

FIX = Path(__file__).parent / 'fixtures'
REPLAY = json.loads((FIX / 'ast_tms_replay.json').read_text(encoding='utf-8'))
TX = '01TXREPLAYFIXTURE0000000000'


def _backend(handler):
    cfg = {'environment': 'test', 'tenant': 'realm-a', 'ast_url': 'https://ast.example.test',
           'token_env': 'KOBIL_TEST_TOKEN', 'auth': {'type': 'static'}}
    b = AST.__new__(AST)
    b.cfg = cfg
    b.root = '/v1'
    b.client = httpx.Client(transport=httpx.MockTransport(handler), timeout=5)
    b.token = lambda: 'tok'
    return b


class PurgedTransactionReplayTests(unittest.TestCase):
    def test_every_recorded_case_drives_status_and_result_http_reads(self):
        for name, record in REPLAY['cases'].items():
            for endpoint in ('status', 'result'):
                with self.subTest(case=name, endpoint=endpoint):
                    calls = []
                    def handler(request):
                        calls.append((request.method, request.url.path))
                        return httpx.Response(record[endpoint]['http'])
                    backend = _backend(handler)
                    try:
                        actual = tms.read(backend, TX, result=endpoint == 'result')
                    finally:
                        backend.client.close()
                    self.assertEqual(calls, [('GET', '/v1/tms/' + TX + '/' + endpoint)])
                    self.assertEqual(actual['status'], 'not_found')
                    self.assertFalse(actual['result_available'])
                    self.assertNotIn(actual['status'], ('ACCEPTED', 'REJECTED', 'CANCELLED', 'TIMEOUT'))
                    self.assertIn('deployment', actual['note'])

    def test_status_404_is_reported_as_not_found_not_raised(self):
        b = _backend(lambda req: httpx.Response(404))
        r = tms.read(b, TX)
        self.assertEqual(r['status'], 'not_found')
        self.assertFalse(r['result_available'])
        self.assertIn('Not evidence of failure', r['note'])
        self.assertIn('Do not re-trigger', r['note'])

    def test_result_404_is_reported_as_not_found(self):
        b = _backend(lambda req: httpx.Response(404))
        r = tms.read(b, TX, result=True)
        self.assertEqual(r['status'], 'not_found')
        self.assertFalse(r['result_available'])

    def test_result_412_stays_pending_and_other_errors_still_raise(self):
        self.assertEqual(tms.read(_backend(lambda req: httpx.Response(412)), TX, result=True)['status'], 'pending')
        with self.assertRaises(BackendError):
            tms.read(_backend(lambda req: httpx.Response(500)), TX)

    def test_auth_and_status_precondition_errors_are_not_pending(self):
        for code, result_endpoint in ((401, False), (403, False), (401, True), (403, True), (412, False)):
            with self.subTest(code=code, result=result_endpoint):
                calls = []
                def handler(request):
                    calls.append(request.method)
                    return httpx.Response(code)
                backend = _backend(handler)
                try:
                    with self.assertRaises(BackendError):
                        tms.read(backend, TX, result=result_endpoint)
                finally:
                    backend.client.close()
                self.assertEqual(calls, ['GET'])

    def test_pending_is_implementation_output_not_terminal_success(self):
        backend = _backend(lambda request: httpx.Response(412))
        try:
            actual = tms.read(backend, TX, result=True)
        finally:
            backend.client.close()
        self.assertEqual(actual['status'], 'pending')
        self.assertFalse(actual['result_available'])
        self.assertIn('do not re-trigger', actual['note'])


class ExplicitPreflightReplayTests(unittest.TestCase):
    """Client shapes as returned by the IDP admin API on the measured day."""
    FLOWS = [{'id': 'flow-mobile', 'alias': 'KOBIL Mobile Login'}, {'id': 'flow-browser', 'alias': 'browser'}]
    OPTIONAL = [{'name': n} for n in ('address', 'microprofile-jwt', 'offline_access', 'phone', 'tms')]
    DEFAULT = [{'name': n} for n in ('acr', 'ast', 'email', 'profile', 'roles', 'web-origins')]

    def client(self, override='flow-mobile'):
        c = {'clientId': 'token-client', 'enabled': True, 'protocol': 'openid-connect',
             'authenticationFlowBindingOverrides': {}}
        if override:
            c['authenticationFlowBindingOverrides']['browser'] = override
        return c

    def test_measured_live_shape_is_client_checked_with_holder_warning(self):
        r = explicit_preflight(self.client(), self.DEFAULT, self.OPTIONAL, self.FLOWS, enrollment_client_id='enrollment-client')
        self.assertEqual(r['status'], 'client_checked')
        self.assertEqual(r['optional_scopes'], ['address', 'microprofile-jwt', 'offline_access', 'phone', 'tms'])
        self.assertEqual(r['browser_flow_override'], 'KOBIL Mobile Login')
        self.assertEqual(r['errors'], [])
        self.assertTrue(any('cold start with OfflineLogin' in w and 'azp' in w for w in r['warnings']), r['warnings'])

    def test_customer_login_client_without_tms_scope_is_blocked_with_the_measured_signature(self):
        optional = [s for s in self.OPTIONAL if s['name'] != 'tms']
        r = explicit_preflight(self.client(), self.DEFAULT, optional, self.FLOWS)
        self.assertEqual(r['status'], 'blocked')
        self.assertTrue(any('403 / 516004034' in e for e in r['errors']), r['errors'])
        self.assertNotIn('tms', r['optional_scopes'])

    def test_realm_default_browser_flow_is_blocked_with_cannot_acquire_hint(self):
        r = explicit_preflight(self.client(override=None), self.DEFAULT, self.OPTIONAL, self.FLOWS)
        self.assertEqual(r['status'], 'blocked')
        self.assertTrue(any('CANNOT_ACQUIRE_TOKEN_DATA' in e for e in r['errors']), r['errors'])

    def test_wrong_flow_variant_warns_but_does_not_block(self):
        r = explicit_preflight(self.client(override='flow-browser'), self.DEFAULT, self.OPTIONAL, self.FLOWS)
        self.assertEqual(r['status'], 'client_checked')
        self.assertTrue(any("'browser'" in w for w in r['warnings']), r['warnings'])

    def test_preflight_never_mutates_or_claims_runtime(self):
        r = explicit_preflight(self.client(), self.DEFAULT, self.OPTIONAL, self.FLOWS)
        self.assertFalse(r['runtime_verified'])
        self.assertFalse(r['backend_modified'])


if __name__ == '__main__':
    unittest.main()
