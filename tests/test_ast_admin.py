import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from kobil_sdk_integration import ast_admin as a
from kobil_sdk_integration.backend import BackendError


class Registry:
    def __init__(self):
        self.tools = {}
    def tool(self):
        def add(fn):
            self.tools[fn.__name__] = fn
            return fn
        return add


class ASTAdminTests(unittest.TestCase):
    def setUp(self):
        r = Registry()
        a.register(r)
        self.tools = r.tools
        self.b = Mock()
        self.config = patch.object(a, 'configuration', return_value={'environment': 'test'})
        self.factory = patch.object(a, 'AST', return_value=self.b)
        self.config.start()
        self.factory.start()
        self.addCleanup(self.config.stop)
        self.addCleanup(self.factory.stop)

    def call(self, tool_name, **kwargs):
        return self.tools[tool_name](expected_environment='test', **kwargs)

    def test_list_names_pages_and_filters(self):
        self.b.request.return_value = ['Zed', 'Beta', 'Alpha']
        one = self.call('sdk_app_list', page_size=2)
        self.assertEqual([r['appName'] for r in one['items']], ['Alpha', 'Beta'])
        self.assertEqual(one['next_cursor'], '2')
        two = self.call('sdk_app_list', page_size=2, cursor=one['next_cursor'])
        self.assertEqual(two['items'], [{'appName': 'Zed', 'categories': []}])
        self.assertTrue(two['complete'])
        filtered = self.call('sdk_app_list', name='AL')
        self.assertEqual(filtered['total'], 1)
        self.b.request.assert_called_with('GET', '/apps?page=1&pageSize=100')
        self.b.close.assert_called()

    def test_list_excludes_secrets_and_filters_categories(self):
        self.b.request.return_value = {'apps': [{'id': '1', 'appName': 'one', 'secret': 'BAD', 'pushNotificationConfig': {'categories': ['tms'], 'iosApnsPrivateKey': 'BAD'}}]}
        result = self.call('sdk_app_list', category='tms')
        self.assertNotIn('BAD', json.dumps(result))
        self.assertEqual(result['total'], 1)

    def test_incomplete_collection_not_claimed_complete(self):
        for value in ({'data': [], 'totalCount': 8}, {'apps': [], 'last': False}, {'content': []}, {'apps': [], 'nextCursor': '2'}):
            self.b.request.return_value = value
            with self.assertRaises(BackendError):
                self.call('sdk_app_list')

    def test_invalid_page_rejected_before_network(self):
        for kwargs in ({'cursor': '-1'}, {'cursor': 'x'}, {'page_size': 0}, {'page_size': 201}):
            with self.assertRaises(ValueError):
                self.call('sdk_app_list', **kwargs)
        self.b.request.assert_not_called()

    def test_environment_guard_and_close(self):
        with patch.object(a, 'configuration', side_effect=ValueError('Active environment mismatch')):
            with self.assertRaises(ValueError):
                self.call('sdk_ast_device_delete', client_id='id')
        self.b.request.assert_not_called()
        self.b.request.side_effect = BackendError('Backend request failed (HTTP 403)')
        with self.assertRaises(BackendError):
            self.call('sdk_ast_device_get', client_id='id')
        self.b.close.assert_called_once()

    def test_version_delete_checks_app_ownership(self):
        self.b._version_rows.return_value = [{'id': 'v1', 'appName': 'other'}]
        with self.assertRaises(BackendError):
            self.call('sdk_app_version_delete', app_name='app', version_id='v1')
        self.b.request.assert_not_called()
        self.b._version_rows.return_value = [{'id': 'v1', 'appName': 'app', 'platform': 'IOS'}]
        result = self.call('sdk_app_version_delete', app_name='app', version_id='v1')
        self.assertTrue(result['deleted'])
        self.b.request.assert_called_once_with('DELETE', '/versions/v1')

    def test_device_routes_and_uuid_validation(self):
        user = '00000000-0000-0000-0000-000000000001'
        with self.assertRaises(ValueError):
            self.call('sdk_ast_device_unlink', user_uuid='username', client_id='x')
        self.call('sdk_ast_device_unlink', user_uuid=user, client_id='a/b')
        self.b.request.assert_called_with('POST', '/unlink', {'userId': user, 'astClientId': 'a/b'})
        self.call('sdk_ast_device_delete', client_id='a/b')
        self.b.request.assert_called_with('DELETE', '/astclients/a%2Fb')

    def test_push_summary_never_returns_material(self):
        self.b.request.return_value = {'appName': 'app', 'pushNotificationConfig': {'iosApnsPrivateKey': 'BAD', 'fcmServiceAccountJSON': 'BAD', 'iosBundleId': 'org.app'}}
        result = self.call('sdk_ast_push_get', app_name='app')
        self.assertNotIn('BAD', json.dumps(result))
        self.assertTrue(result['push']['configured_material']['iosApnsPrivateKey'])

    def test_push_update_preserves_fields_and_is_idempotent(self):
        config = {'iosApnsPrivateKey': 'SECRET', 'fcmServiceAccountJSON': 'SECRET', 'iosBundleId': 'old'}
        self.b.request.return_value = {'appName': 'app', 'pushNotificationConfig': config}
        result = self.call('sdk_ast_push_update', app_name='app', ios_bundle_id='new')
        self.assertNotIn('SECRET', json.dumps(result))
        self.b.request.assert_called_with('PUT', '/apps/app', {**config, 'iosBundleId': 'new'})
        self.assertEqual(config['iosBundleId'], 'old')
        self.b.request.reset_mock()
        result = self.call('sdk_ast_push_update', app_name='app', ios_bundle_id='old')
        self.assertFalse(result['changed'])
        self.assertEqual(self.b.request.call_count, 1)

    def test_fcm_file_and_apns_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'account.json'
            path.write_text(json.dumps({'type': 'service_account', 'project_id': 'test', 'client_email': 'test@example.com', 'private_key': 'SECRET'}))
            path.chmod(0o600)
            self.b.request.return_value = {'appName': 'app', 'pushNotificationConfig': {'iosApnsPrivateKey': 'APNS'}}
            result = self.call('sdk_ast_push_fcm_set', app_name='app', service_account_file=str(path))
            self.assertTrue(result['changed'])
            self.assertEqual(self.b.request.call_args.args[2]['iosApnsPrivateKey'], 'APNS')
            self.assertNotIn('SECRET', json.dumps(result))
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                self.call('sdk_ast_push_fcm_set', app_name='app', service_account_file=str(path))

    def test_message_does_not_claim_delivery_or_echo_backend_secrets(self):
        self.b.request.return_value = {'id': 'msg', 'token': 'SECRET'}
        result = self.call('sdk_tms_display_message', user_uuid='00000000-0000-0000-0000-000000000001', text='requested message')
        self.assertFalse(result['delivery_verified'])
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertEqual(self.b.request.call_args.args[1], '/display-message')

    def test_local_certificate_validation_and_mismatch(self):
        from datetime import datetime, timedelta, timezone
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, 'test')])
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                .public_key(key.public_key()).serial_number(1)
                .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
                .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
                .sign(key, hashes.SHA256()))
        with tempfile.TemporaryDirectory() as directory:
            certfile = Path(directory) / 'cert.pem'
            keyfile = Path(directory) / 'key.pem'
            certfile.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            certfile.chmod(0o600)
            for private_key, matching in [(key, True), (other, False)]:
                keyfile.write_bytes(private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
                keyfile.chmod(0o600)
                result = self.call('sdk_ast_push_validate', certificate_file=str(certfile), private_key_file=str(keyfile))
                self.assertEqual(result['key_matches'], matching)
                self.assertTrue(result['currently_valid'])
                self.assertNotIn('PRIVATE', json.dumps(result))
            self.b.request.assert_not_called()
            with self.assertRaises(ValueError):
                self.call('sdk_ast_push_update', app_name='app', apns_certificate_file=str(certfile), apns_private_key_file=str(keyfile))
            self.b.request.assert_not_called()

    def test_app_backend_pagination_and_repeat_detection(self):
        first = ['app%03d' % n for n in range(100)]
        self.b.request.side_effect = [first, ['last']]
        result = self.call('sdk_app_list', page_size=200)
        self.assertEqual(result['total'], 101)
        self.assertTrue(result['complete'])
        self.assertEqual(self.b.request.call_args.args[1], '/apps?page=2&pageSize=100')
        self.b.request.side_effect = [first, first]
        with self.assertRaises(BackendError):
            self.call('sdk_app_list')

    def test_app_delete_cascade_inventory(self):
        self.b.request.return_value = {'appName': 'app'}
        self.b._version_rows.return_value = [{'id': 'v1', 'appName': 'app', 'privateKey': 'SECRET'}]
        result = self.call('sdk_app_delete', app_name='app')
        self.assertTrue(result['cascade_versions'])
        self.assertNotIn('SECRET', json.dumps(result))
        self.b.request.assert_called_with('DELETE', '/apps/app')

    def test_version_update_preserves_policy_and_rejects_wrong_app(self):
        row = {'id': 'v1', 'appName': 'app', 'platform': 'IOS', 'versionStr': '1.0.0',
               'registerUserId': 'user', 'versionLock': False, 'isCheckIntegrity': True}
        self.b.request.return_value = row
        result = self.call('sdk_app_version_update', app_name='app', version_id='v1', locked=True)
        self.assertTrue(result['changed'])
        self.b.request.assert_called_with('PUT', '/versions/v1', {k: (True if k == 'versionLock' else v) for k, v in row.items() if k != 'id'})
        self.b.request.reset_mock()
        with self.assertRaises(BackendError):
            self.call('sdk_app_version_update', app_name='wrong', version_id='v1', locked=True)
        self.assertEqual(self.b.request.call_count, 1)
        self.b.request.return_value = {**row, 'policyId': 'policy'}
        with self.assertRaises(ValueError):
            self.call('sdk_app_version_update', app_name='app', version_id='v1', register_user_id='other')

    def test_device_list_requires_complete_count_and_drops_secrets(self):
        user = '00000000-0000-0000-0000-000000000001'
        self.b.request.return_value = [{'id': 'one'}]
        with self.assertRaises(BackendError):
            self.call('sdk_ast_device_list', user_uuid=user)
        self.b.request.return_value = {'data': [{'id': 'one', 'token': 'SECRET'}], 'totalCount': 1}
        result = self.call('sdk_ast_device_list', user_uuid=user)
        self.assertEqual(result['items'], [{'id': 'one'}])
        self.assertTrue(result['complete'])
        self.assertNotIn('SECRET', json.dumps(result))

    def test_real_fastmcp_registration_schema(self):
        from mcp.server.fastmcp import FastMCP
        import asyncio
        server = FastMCP('test')
        a.register(server)
        listed = asyncio.run(server.list_tools())
        self.assertEqual(len(listed), 15)
        for tool in listed:
            self.assertIn('expected_environment', tool.inputSchema['required'])
            self.assertGreater(len(tool.description), 100)


if __name__ == '__main__':
    unittest.main()
