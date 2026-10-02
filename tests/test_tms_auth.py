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


class ExplicitPreflightTests(unittest.TestCase):
    FLOWS = [{'id': 'f-login', 'alias': 'KOBIL Mobile Login'}, {'id': 'f-browser', 'alias': 'browser'}]

    def client(self, override='f-login', enabled=True):
        c = {'id': 'uuid-1', 'clientId': 'app-login', 'enabled': enabled}
        if override:
            c['authenticationFlowBindingOverrides'] = {'browser': override}
        return c

    def test_measured_good_configuration_passes(self):
        from kobil_sdk_integration.tms_auth import explicit_preflight
        r = explicit_preflight(self.client(), [{'name': 'ast'}], [{'name': 'tms'}], self.FLOWS)
        self.assertEqual(r['status'], 'client_checked')
        self.assertEqual(r['browser_flow_override'], 'KOBIL Mobile Login')
        self.assertFalse(r['runtime_verified'])

    def test_missing_optional_scope_blocks_with_516004034_hint(self):
        from kobil_sdk_integration.tms_auth import explicit_preflight
        r = explicit_preflight(self.client(), [], [{'name': 'phone'}], self.FLOWS)
        self.assertEqual(r['status'], 'blocked')
        self.assertIn('516004034', str(r['errors']))

    def test_default_scope_is_a_warning_not_a_pass_through(self):
        from kobil_sdk_integration.tms_auth import explicit_preflight
        r = explicit_preflight(self.client(), [{'name': 'tms'}], [], self.FLOWS)
        self.assertEqual(r['status'], 'client_checked')
        self.assertIn('DEFAULT', str(r['warnings']))

    def test_missing_flow_override_blocks_with_cannot_acquire_hint(self):
        from kobil_sdk_integration.tms_auth import explicit_preflight
        r = explicit_preflight(self.client(override=None), [], [{'name': 'tms'}], self.FLOWS)
        self.assertEqual(r['status'], 'blocked')
        self.assertIn('CANNOT_ACQUIRE_TOKEN_DATA', str(r['errors']))

    def test_separate_enrollment_client_warns_about_token_holder(self):
        from kobil_sdk_integration.tms_auth import explicit_preflight
        r = explicit_preflight(self.client(), [], [{'name': 'tms'}], self.FLOWS, enrollment_client_id='app-enrollment')
        self.assertEqual(r['status'], 'client_checked')
        self.assertIn('token holder', str(r['warnings']))

    def test_tool_reads_client_scopes_and_flows_read_only(self):
        from unittest.mock import patch
        from kobil_sdk_integration import tms_auth

        class Registry:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(function):
                    self.tools[function.__name__] = function
                    return function
                return register

        registry = Registry()
        tms_auth.register(registry)
        with patch.object(tms_auth, 'Admin') as admin:
            api = admin.return_value.__enter__.return_value
            api.page.return_value = {
                'items': [self.client()], 'first': 0, 'next_offset': None,
                'complete': True, 'environment': 'test', 'realm': 'superapp'
            }
            api.call.side_effect = lambda method, path, **kw: (
                [{'name': 'tms'}] if path.endswith('/optional-client-scopes') else
                [{'name': 'ast'}] if path.endswith('/default-client-scopes') else self.FLOWS)
            r = registry.tools['sdk_tms_explicit_preflight']('test', 'app-login', 'app-enrollment', 'superapp')
        admin.assert_called_once_with('test', 'superapp')
        api.page.assert_called_once_with('/clients', 0, 50, params={'clientId': 'app-login'})
        self.assertEqual(r['status'], 'client_checked')
        self.assertEqual({c.args[0] for c in api.call.call_args_list}, {'GET'})
        with self.assertRaises(ValueError):
            registry.tools['sdk_tms_explicit_preflight']('test', 'eyJ.a.b c')
