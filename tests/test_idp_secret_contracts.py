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
