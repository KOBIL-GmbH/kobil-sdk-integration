import json
import tempfile
import unittest
from pathlib import Path
from kobil_sdk_integration.deployment_preflight import check, read_config


class DeploymentPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'mc_config.json'
        self.config = {'maverick': {'mTLS': False}, 'iam': {'clientId': 'Enrollment'},
                       'unrelated_secret': 'never-return-this'}
        self.write()

    def write(self):
        self.path.write_text(json.dumps(self.config))

    def test_qualified_deployment_does_not_claim_backend_or_runtime_verification(self):
        result = check(str(self.path), False)
        self.assertEqual(result['status'], 'configuration_checked')
        self.assertFalse(result['backend_capability_verified'])
        self.assertFalse(result['runtime_verified'])
        self.assertFalse(result['token_binding_checked'])
        self.assertNotIn('never-return-this', str(result))

    def test_wrong_sample_mtls_blocks_without_mutating_file(self):
        before = self.path.read_bytes()
        result = check(str(self.path), True)
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('510000015', str(result['errors']))
        self.assertEqual(before, self.path.read_bytes())

    def test_unknown_mtls_and_string_booleans_block(self):
        self.assertEqual(check(str(self.path), None)['status'], 'blocked')
        for value in ('false', 0, None):
            self.config['maverick']['mTLS'] = value
            self.write()
            self.assertEqual(check(str(self.path), False)['status'], 'blocked')

    def test_token_owner_mismatch_even_when_scope_present(self):
        result = check(str(self.path), False, 'Login', ['openid', 'tms'], True)
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('700000022', str(result['errors']))

    def test_missing_actual_scope_not_satisfied_by_known_client(self):
        result = check(str(self.path), False, 'Enrollment', ['openid'], True, 'explicit_auth')
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('516004034', str(result['errors']))
        self.assertNotIn('never-return-this', str(result))

    def test_explicit_auth_requires_metadata_and_no_token_value_echo(self):
        for scopes in (None, 'secret-token', ['openid tms'], [123]):
            result = check(str(self.path), False, None, scopes, True)
            self.assertEqual(result['status'], 'blocked')
            self.assertNotIn('secret-token', str(result))

    def test_scope_presence_only_configuration_evidence(self):
        result = check(str(self.path), False, 'Enrollment', ['openid', 'tms'], True, 'explicit_auth')
        self.assertEqual(result['status'], 'configuration_checked')
        self.assertTrue(result['explicit_tms_scope_checked'])
        self.assertFalse(result['runtime_verified'])
        self.assertIn('necessary but not sufficient', result['limits'])

    def test_invalid_input_returns_sanitized_error(self):
        for raw in ('{"secret":"never-return-this",', '[]'):
            self.path.write_text(raw)
            with self.assertRaises(ValueError) as caught:
                read_config(str(self.path))
            self.assertNotIn('never-return-this', str(caught.exception))

    def test_symlink_and_oversize_rejected(self):
        alias = self.path.with_name('link.json')
        alias.symlink_to(self.path)
        with self.assertRaises(ValueError):
            read_config(str(alias))
        self.path.write_text(' ' * (1024 * 1024 + 1))
        with self.assertRaises(ValueError):
            read_config(str(self.path))

    def test_dynamic_scope_is_not_required_before_exchange(self):
        result = check(str(self.path), False, 'Enrollment', ['openid'], True)
        self.assertEqual(result['status'], 'configuration_checked')
        self.assertFalse(result['explicit_tms_scope_checked'])
        self.assertTrue(result['warnings'])
        after = check(str(self.path), False, 'Enrollment', ['openid', 'tms'], True, 'explicit_auth')
        self.assertTrue(after['explicit_tms_scope_checked'])

    def test_explicit_auth_missing_metadata_and_unknown_stage_block(self):
        self.assertEqual(check(str(self.path), False, 'Enrollment', None, True, 'explicit_auth')['status'], 'blocked')
        self.assertEqual(check(str(self.path), False, 'Enrollment', [], True, 'guess')['status'], 'blocked')

    def test_signed_jwt_missing_policy_blocks_without_config_mutation(self):
        before = self.path.read_bytes()
        result = check(str(self.path), False, require_signed_jwt=True, authentication_mode='biometric')
        self.assertEqual(result['status'], 'blocked')
        self.assertFalse(result['signed_jwt_prerequisites_checked'])
        self.assertIn('jwtSignKeySecurityPolicy', str(result['errors']))
        self.assertNotIn('never-return-this', str(result))
        self.assertEqual(before, self.path.read_bytes())

    def test_signed_jwt_qualified_prerequisites_do_not_prove_grant(self):
        self.config['useTokenBasedLogin'] = True
        for policy in ('ENFORCE_HARDWARE', 'ENFORCE_STRONG_HARDWARE', 'ALLOW_VIRTUAL_SMART_CARD'):
            self.config['maverick']['jwtSignKeySecurityPolicy'] = policy
            self.write()
            result = check(str(self.path), False, require_signed_jwt=True, authentication_mode='biometric')
            self.assertEqual(result['status'], 'configuration_checked')
            self.assertTrue(result['signed_jwt_prerequisites_checked'])
            self.assertFalse(result['runtime_verified'])
            self.assertIn('never use CLEAR_ALL', str(result['warnings']))

    def test_signed_jwt_invalid_metadata_is_not_echoed_or_defaulted(self):
        self.config['useTokenBasedLogin'] = True
        for policy in (None, '', 'secret-policy-value', [], {}):
            self.config['maverick']['jwtSignKeySecurityPolicy'] = policy
            self.write()
            result = check(str(self.path), False, require_signed_jwt=True, authentication_mode='biometric')
            self.assertEqual(result['status'], 'blocked')
            self.assertNotIn('secret-policy-value', str(result))
        self.config['maverick']['jwtSignKeySecurityPolicy'] = 'ENFORCE_HARDWARE'
        self.write()
        for mode in (None, 'password', 'secret-mode', [], {}):
            result = check(str(self.path), False, require_signed_jwt=True, authentication_mode=mode)
            self.assertEqual(result['status'], 'blocked')
            self.assertNotIn('secret-mode', str(result))
        for enabled in (False, 'true', 1, None):
            self.config['useTokenBasedLogin'] = enabled
            self.write()
            self.assertEqual(check(str(self.path), False, require_signed_jwt=True,
                                   authentication_mode='biometric')['status'], 'blocked')
        self.assertEqual(check(str(self.path), False, require_signed_jwt='true')['status'], 'blocked')
