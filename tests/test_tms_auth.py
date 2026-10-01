import unittest
from kobil_sdk_integration.tms_auth import diagnose


class TmsAuthTests(unittest.TestCase):
    def test_ordinary_scope_is_not_a_user_failure(self):
        r = diagnose(current_scopes=['openid'])
        self.assertEqual(r['status'], 'needs_evidence')
        self.assertFalse(r['runtime_verified'])

    def test_successful_exchange_can_drop_requested_scope(self):
        r = diagnose(['openid'], ['tms'], 200, ['openid'], 516004034)
        self.assertEqual(r['status'], 'blocked')
        self.assertIn('did not grant', str(r['evidence']))
        self.assertIn('same client', str(r['next_checks']))

    def test_unknown_result_is_not_fabricated_from_http200(self):
        r = diagnose(['openid'], ['tms'], 200)
        self.assertEqual(r['status'], 'needs_evidence')
        self.assertIn('actual exchange result', str(r['next_checks']))

    def test_scope_present_never_proves_backend_success(self):
        r = diagnose(['openid'], ['tms'], 200, ['tms'])
        self.assertEqual(r['status'], 'scope_metadata_checked')
        self.assertFalse(r['runtime_verified'])
        r = diagnose(['openid'], ['tms'], 200, ['tms'], 516004034)
        self.assertEqual(r['status'], 'blocked')
        self.assertIn('token used', str(r['next_checks']))

    def test_exchange_failure_and_ast_rejection_are_distinct(self):
        r = diagnose(exchange_requested_scopes=['tms'], exchange_http_status=403)
        self.assertEqual(r['status'], 'blocked')
        self.assertIn('binding', str(r['next_checks']))
        self.assertEqual(diagnose(ast_error_code=516004034)['status'], 'blocked')

    def test_invalid_metadata_not_echoed(self):
        for kwargs in ({'current_scopes': ['eyJ.secret.token']}, {'exchanged_scopes': 'secret'},
                       {'exchange_http_status': True}, {'exchange_http_status': 600},
                       {'ast_error_code': -1}, {'exchange_requested_scopes': ['a b']}):
            with self.assertRaises(ValueError) as error:
                diagnose(**kwargs)
            self.assertNotIn('secret', str(error.exception))
