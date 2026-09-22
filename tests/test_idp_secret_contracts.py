"""Review regressions for metadata visibility and uncertain credential rotations."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from kobil_sdk_integration import idp_admin, idp_secrets
from kobil_sdk_integration.backend import BackendError


class Registry:
    def __init__(self): self.tools = {}
    def tool(self):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class SecretContractTests(unittest.TestCase):
    def test_metadata_redaction_keeps_nonsecret_policies_and_mapper_switches(self):
        data = {'accessTokenLifespan': 300, 'passwordPolicy': 'length(12)',
                'config': {'access.token.claim': 'true'},
                'clientSecret': 'sensitive', 'access_token': 'sensitive'}
        cleaned = idp_admin.redact(data)
        self.assertEqual(cleaned['clientSecret'], '[redacted]')
        self.assertEqual(cleaned['access_token'], '[redacted]')
        self.assertEqual(cleaned['accessTokenLifespan'], 300)
        self.assertEqual(cleaned['passwordPolicy'], 'length(12)')
        self.assertEqual(cleaned['config']['access.token.claim'], 'true')

    def test_post_rotation_storage_failure_reports_uncertain_backend_change(self):
        registry=Registry()
        idp_secrets.register(registry)
        with tempfile.TemporaryDirectory() as directory, patch.object(idp_secrets, 'Admin') as admin:
            api=admin.return_value.__enter__.return_value
            api.raw.return_value={'value':'rotated-secret'}
            output=str(Path(directory)/'secret.json')
            with patch.object(idp_secrets,'write_result',side_effect=OSError('No space left on device')):
                with self.assertRaisesRegex(BackendError, '(?i)(rotat|changed|uncertain)'):
                    registry.tools['sdk_idp_client_secret_rotate']('test', 'client', output)
            api.raw.assert_called_once_with('POST','/clients/client/client-secret')

class ActivationCodeTests(unittest.TestCase):
    uid='12345678-1234-4234-8234-123456789abc'

    def setUp(self):
        registry=Registry()
        idp_secrets.register(registry)
        self.generate=registry.tools['sdk_idp_activation_code_generate']

    def test_generate_stores_credential_without_profile_or_flow_changes(self):
        import json
        with patch.object(idp_secrets,'Admin') as admin:
            api=admin.return_value.__enter__.return_value
            api.raw.side_effect=[{'id':self.uid,'attributes':{'keep':['value']}},None,[{'type':'ACTIVATION_CODE'}]]
            result=self.generate('test',self.uid,valid_for='30m',digits=8,realm='chosen')
            admin.assert_called_once_with('test','chosen')
            self.assertRegex(result['activation_code'],r'^[0-9]{8}$')
            body=api.raw.call_args_list[1].args[2]
            self.assertEqual(set(body),{'credentials'})
            self.assertEqual(json.loads(body['credentials'][0]['secretData'])['code'],result['activation_code'])
            self.assertEqual(json.loads(body['credentials'][0]['credentialData']),{'period':'30m'})
            self.assertFalse(result['exact_value_verified'])
            self.assertFalse(result['device_activated'])
            self.assertEqual(api.raw.call_count,3)

    def test_invalid_inputs_never_connect(self):
        with patch.object(idp_secrets,'Admin') as admin:
            for kwargs in [{'user_uuid':'bad'},{'valid_for':'0d'},{'valid_for':'-1d'},{'digits':True},{'digits':13}]:
                args={'user_uuid':self.uid,**kwargs}
                with self.assertRaises(ValueError):self.generate('test',**args)
            admin.assert_not_called()

    def test_wrong_user_never_writes(self):
        with patch.object(idp_secrets,'Admin') as admin:
            api=admin.return_value.__enter__.return_value
            api.raw.return_value={'id':'other'}
            with self.assertRaises(BackendError):self.generate('test',self.uid)
            self.assertEqual(api.raw.call_count,1)

    def test_uncertain_write_and_missing_readback_do_not_retry_or_expose_code(self):
        for responses in [[{'id':self.uid},RuntimeError('secret echoed')],[{'id':self.uid},None,[]]]:
            with patch.object(idp_secrets,'Admin') as admin:
                api=admin.return_value.__enter__.return_value
                api.raw.side_effect=responses
                with self.assertRaisesRegex(BackendError,'Do not automatically retry') as caught:
                    self.generate('test',self.uid)
                self.assertNotIn('secret echoed',str(caught.exception))
                self.assertEqual(sum(c.args[0]=='PUT' for c in api.raw.call_args_list),1)
