import unittest
from unittest.mock import Mock
from kobil_sdk_integration.tms import trigger, read, cancel

UID = '00000000-0000-4000-8000-000000000001'

class TmsTests(unittest.TestCase):
    def test_trigger_policy_and_no_payload_echo(self):
        backend = Mock()
        backend.request.return_value = {'id': 'TEST01', 'status': 'PENDING', 'signedData': 'private'}
        self.assertEqual(trigger(backend, UID, 'Synthetic test', 60, 30, False, -1),
                         {'transaction_id': 'TEST01', 'status': 'PENDING'})
        args = backend.request.call_args.args
        self.assertEqual(args[:2], ('POST', '/tms'))
        self.assertEqual(args[2]['push'], {'skip': True})
        self.assertEqual(args[2]['tmsTimeout'], 30)
        self.assertEqual(args[2]['userId'], UID)

    def test_reject_invalid_before_write(self):
        for uid, timeout in [('username', 30), (UID, 0), (UID, True)]:
            backend = Mock()
            with self.assertRaises(ValueError): trigger(backend, uid, 'test', 60, timeout, False, -1)
            backend.request.assert_not_called()

    def test_result_excludes_signature_recipient_and_text(self):
        backend = Mock()
        backend.request.return_value = {'info': {'id': 'TEST01', 'status': 'ACCEPTED', 'userId': UID}, 'signedData': 'private'}
        self.assertEqual(read(backend, 'TEST01', True), {'transaction_id': 'TEST01', 'status': 'ACCEPTED', 'result_available': True})
        backend.request.return_value = None
        self.assertFalse(read(backend, 'TEST01', True)['result_available'])

    def test_read_rejects_missing_status_and_mismatched_id(self):
        from kobil_sdk_integration.backend import BackendError
        for payload in [{}, {'info': {}}, {'info': {'id': 'OTHER', 'status': 'ACCEPTED'}}, {'status': 42}]:
            for result in [False, True]:
                backend = Mock()
                backend.request.return_value = payload
                with self.assertRaises(BackendError): read(backend, 'EXPECTED', result)
        backend.request.return_value = {'status': 'ACCEPTED'}
        self.assertEqual(read(backend, 'EXPECTED', True)['transaction_id'], 'EXPECTED')

    def test_cancel_is_not_final_result(self):
        backend = Mock()
        self.assertFalse(cancel(backend, 'TEST01')['final_result_verified'])
        backend.request.assert_called_once_with('DELETE', '/tms/TEST01')
        with self.assertRaises(ValueError): cancel(backend, '../another')

    def test_default_freshness_is_applied_and_not_warned(self):
        backend = Mock()
        backend.request.return_value = {'id': 'TEST01', 'status': 'PENDING'}
        result = trigger(backend, UID, 'Synthetic test', 60, 30, False)
        self.assertEqual(backend.request.call_args.args[2]['requireFreshnessOfAuthentication'], 3600)
        self.assertNotIn('warning', result)
        for value in (-1, 120, 3600, 86400):
            backend.reset_mock()
            self.assertNotIn('warning', trigger(backend, UID, 'Synthetic test', 60, 30, False, value))
            self.assertEqual(backend.request.call_args.args[2]['requireFreshnessOfAuthentication'], value)

    def test_unconfirmable_freshness_still_creates_but_warns(self):
        # VAL-28 (2026-09-29, iOS MCSDK 15.16.803.3089231): freshness_seconds=0 produced a
        # guaranteed confirmation-time HTTP 403 wrapped as SDK errorCode 516004035.
        for value in (0, 60, 119):
            backend = Mock()
            backend.request.return_value = {'id': 'TEST01', 'status': 'PENDING'}
            result = trigger(backend, UID, 'Synthetic test', 60, 30, False, value)
            backend.request.assert_called_once()
            self.assertEqual(result['transaction_id'], 'TEST01')
            for token in ('516004035', 'HTTP 403', '85 seconds', 'CONFIRMATION', '3600', '-1'):
                self.assertIn(token, result['warning'], token)

    def test_result_http_412_maps_to_explicit_pending(self):
        from kobil_sdk_integration.backend import BackendError
        precondition = BackendError('Backend request failed (HTTP 412; backend_error)')
        precondition.status_code = 412
        backend = Mock()
        backend.request.side_effect = precondition
        result = read(backend, 'TEST01', result=True)
        self.assertEqual(result['status'], 'pending')  # lowercase: distinguishable from backend [A-Z_] statuses
        self.assertFalse(result['result_available'])
        self.assertIn('not a backend error', result['note'].lower())
        self.assertIn('re-trigger', result['note'])
        # the status endpoint has no verified 412 pending semantics; it must still raise
        with self.assertRaises(BackendError): read(backend, 'TEST01', result=False)
        # other statuses and 412 errors without status metadata remain real errors
        for error in (BackendError('Backend request failed (HTTP 403; permission_denied)'),
                      BackendError('Backend request failed (HTTP 412; backend_error)')):
            backend.request.side_effect = error
            with self.assertRaises(BackendError): read(backend, 'TEST01', result=True)


class FreshnessRequirementTests(unittest.TestCase):
    def test_strict_freshness_warning_preserves_requirement(self):
        class Backend:
            def request(self, method, path, payload):
                self.payload = payload
                return {'id': '01TX', 'status': 'STARTED'}
        backend = Backend()
        result = trigger(backend, '00000000-0000-0000-0000-000000000001', 'Test', 120, 90, True, 0)
        self.assertEqual(backend.payload['requireFreshnessOfAuthentication'], 0)
        self.assertIn('Do not relax freshness', result['warning'])
        self.assertIn('preserve that requirement', result['warning'])
