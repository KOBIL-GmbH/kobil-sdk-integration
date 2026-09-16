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
