import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx

from kobil_sdk_integration.backend import AST, BackendError, configuration
from kobil_sdk_integration.server import sdk_app_ensure
from kobil_sdk_integration.sdk_config import write_config, certificate_bundle


CFG = {'environment': 'test', 'tenant': 'tenant', 'ast_url': 'https://backend.example', 'token_env': 'TEST_BEARER'}


class BackendTests(unittest.TestCase):
    def client(self, handler):
        backend = AST(CFG)
        backend.client.close()
        backend.client = httpx.Client(transport=httpx.MockTransport(handler))
        self.addCleanup(backend.close)
        self.env = patch.dict(os.environ, {'TEST_BEARER': 'fixture-secret'})
        self.env.start()
        self.addCleanup(self.env.stop)
        return backend

    def test_app_repeat_does_not_write(self):
        apps, writes = [], []
        def handler(req):
            self.assertEqual(req.headers['authorization'], 'Bearer fixture-secret')
            if req.method == 'GET':
                return httpx.Response(200, json=apps[0]) if apps else httpx.Response(404)
            writes.append(json.loads(req.content))
            apps.append({'appName': 'sample'})
            return httpx.Response(200, json={})
        backend = self.client(handler)
        self.assertTrue(backend.ensure_app('sample', ['tms'])['created'])
        self.assertFalse(backend.ensure_app('sample', ['tms'])['created'])
        self.assertEqual(writes, [{'categories': ['tms']}])

    def test_unknown_app_listing_refuses_write(self):
        backend = self.client(lambda req: httpx.Response(200, json={'unexpected': []}))
        with self.assertRaises(BackendError):
            backend.ensure_app('sample', ['tms'])

    def test_versions_reuse_and_conflict(self):
        rows, writes = [], []
        def handler(req):
            if req.method == 'GET':
                return httpx.Response(200, json={'content': rows, 'totalElements': len(rows)})
            body = json.loads(req.content)
            writes.append(body)
            rows.append(body)
            return httpx.Response(200, json={})
        backend = self.client(handler)
        args = ('sample', 'Android', '1.0.0', 'user', True)
        self.assertTrue(backend.ensure_version(*args)['created'])
        self.assertFalse(backend.ensure_version(*args)['created'])
        with self.assertRaises(BackendError):
            backend.ensure_version('sample', 'Android', '1.0.0', 'user', False)
        self.assertEqual(len(writes), 1)
        self.assertTrue(writes[0]['isCheckIntegrity'])

    def test_partial_and_duplicate_versions_refuse_write(self):
        row = {'appName': 'sample', 'platform': 'Android', 'versionStr': '1.0.0', 'isCheckIntegrity': True}
        for result in [{'content': [], 'last': False}, {'content': [], 'totalElements': 5}, {'content': [row, row], 'totalElements': 2}]:
            calls = []
            def handler(req):
                calls.append(req.method)
                return httpx.Response(200, json=result)
            backend = self.client(handler)
            with self.assertRaises(BackendError):
                backend.ensure_version('sample', 'Android', '1.0.0', 'user', True)
            self.assertEqual(calls, ['GET'])

    def test_errors_and_redirects_do_not_expose_secrets_or_retry(self):
        for code in [302, 401, 403, 409, 500]:
            calls = []
            def handler(req):
                calls.append(req)
                return httpx.Response(code, text='fixture-secret', headers={'location': 'https://elsewhere.example'})
            backend = self.client(handler)
            with self.assertRaises(BackendError) as error:
                backend.request('GET', '/apps')
            self.assertNotIn('fixture-secret', str(error.exception))
            self.assertEqual(len(calls), 1)

    def test_oauth_credentials_only_go_to_token_endpoint(self):
        calls = []
        def handler(req):
            calls.append(req)
            if req.url.host == 'identity.example':
                self.assertNotIn('authorization', req.headers)
                return httpx.Response(200, json={'access_token': 'issued-token'})
            self.assertEqual(req.headers['authorization'], 'Bearer issued-token')
            return httpx.Response(200, json=[])
        backend = self.client(handler)
        backend.cfg = {k: v for k, v in CFG.items() if k != 'token_env'}
        backend.cfg['oauth'] = {'token_url': 'https://identity.example/token', 'client_id': 'client', 'client_secret_env': 'TEST_BEARER'}
        backend.request('GET', '/apps')
        self.assertEqual(len(calls), 2)
        self.assertIn(b'client_secret=fixture-secret', calls[0].content)
        self.assertNotIn(b'fixture-secret', calls[1].content)

    def test_paginated_version_reuse(self):
        calls = []
        wanted = {'appName': 'sample', 'platform': 'Android', 'versionStr': '1.0.0', 'isCheckIntegrity': True, 'registerUserId': 'user'}
        def handler(req):
            calls.append(req.method)
            page = req.url.params['page']
            return httpx.Response(200, json={'data': [wanted | {'versionStr': '0.0.1'}] if page == '1' else [wanted], 'totalCount': 2})
        backend = self.client(handler)
        self.assertFalse(backend.ensure_version('sample', 'Android', '1.0.0', 'user', True)['created'])
        self.assertEqual(calls, ['GET', 'GET'])

    def test_auth_not_found_cannot_trigger_app_creation(self):
        backend = self.client(lambda req: httpx.Response(404))
        backend.cfg = {k: v for k, v in CFG.items() if k != 'token_env'}
        backend.cfg['oauth'] = {'token_url': 'https://identity.example/token', 'client_id': 'client', 'client_secret_env': 'TEST_BEARER'}
        with self.assertRaises(BackendError):
            backend.ensure_app('sample', ['tms'])

    def test_connection_rejects_unsafe_or_secret_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'connection.json'
            with patch.dict(os.environ, {'KOBIL_SDK_CONNECTION': str(path)}):
                for change in [{'ast_url': 'http://backend.example'}, {'password': 'hidden'}, {'ast_url': 'https://user:secret@backend.example'}]:
                    path.write_text(json.dumps(CFG | change))
                    with self.assertRaises(BackendError) as error:
                        configuration()
                    self.assertNotIn('hidden', str(error.exception))
                path.write_text(json.dumps(CFG))
                self.assertEqual(configuration('test')['tenant'], 'tenant')
                with patch('kobil_sdk_integration.backend.AST') as cls:
                    with self.assertRaises(ValueError):
                        sdk_app_ensure('different', 'sample', ['tms'])
                    cls.assert_not_called()

    def test_config_tool_supplies_ast_gateway_to_signer(self):
        from kobil_sdk_integration.server import sdk_config_write
        with tempfile.TemporaryDirectory() as directory:
            connection = Path(directory) / 'connection.json'
            connection.write_text(json.dumps(CFG))
            with patch.dict(os.environ, {'KOBIL_SDK_CONNECTION': str(connection)}), \
                 patch('kobil_sdk_integration.backend.AST') as factory, \
                 patch('kobil_sdk_integration.sdk_config.certificate_bundle', return_value=['public-cert']):
                backend = factory.return_value
                backend.cfg = CFG | {'services': [{'name': 'astLogin', 'url': 'https://backend.example'}]}
                backend.request.return_value = {'sdkConfig': 'header.payload.signature'}
                sdk_config_write('test', ['cert.pem'], str(Path(directory) / 'sdk.jwt'))
                backend.request.assert_called_once_with('POST', '/sdkconfig', {
                    'tlsBundle': ['public-cert'], 'astUrl': 'https://backend.example',
                    'services': [{'name': 'astLogin', 'url': 'https://backend.example'}]})
                backend.close.assert_called_once()

    def test_config_tool_refuses_missing_or_invalid_services(self):
        from kobil_sdk_integration.server import sdk_config_write
        with tempfile.TemporaryDirectory() as directory:
            connection = Path(directory) / 'connection.json'
            connection.write_text(json.dumps(CFG))
            for services in [None, [], [{'name': 'astLogin', 'url': 'http://backend.example'}],
                             [{'name': 'astLogin', 'url': 'https://backend.example'}] * 2]:
                with patch.dict(os.environ, {'KOBIL_SDK_CONNECTION': str(connection)}), patch('kobil_sdk_integration.backend.AST') as factory:
                    backend = factory.return_value
                    backend.cfg = CFG | {'services': services}
                    with self.assertRaises(ValueError):
                        sdk_config_write('test', ['missing.pem'], str(Path(directory) / 'sdk.jwt'))
                    backend.request.assert_not_called()
                    self.assertFalse((Path(directory) / 'sdk.jwt').exists())

    def test_missing_secret_fails_before_network(self):
        backend = self.client(lambda req: self.fail('Unexpected network request'))
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(BackendError):
                backend.request('GET', '/apps')


class ConfigTests(unittest.TestCase):
    def test_new_private_file_and_no_token_in_result(self):
        with tempfile.TemporaryDirectory() as directory, patch('kobil_sdk_integration.sdk_config.certificate_bundle', return_value=['cert']):
            path = Path(directory) / 'sdk.jwt'
            calls = []
            def request(body):
                calls.append(body)
                return {'sdkConfig': 'header.payload.signature'}
            result = write_config(['certificate'], str(path), request)
            self.assertEqual(path.read_text(), 'header.payload.signature')
            self.assertNotIn('header.payload.signature', str(result))
            self.assertFalse(result['signature_verified'])
            if os.name != 'nt':
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                write_config(['certificate'], str(path), request)
            self.assertEqual(len(calls), 1)

    def test_invalid_or_failed_response_removes_reserved_file(self):
        with tempfile.TemporaryDirectory() as directory, patch('kobil_sdk_integration.sdk_config.certificate_bundle', return_value=['cert']):
            path = Path(directory) / 'sdk.jwt'
            def failure(body):
                raise RuntimeError('fixture-secret')
            for request in [failure, lambda body: {'sdkConfig': 'not-a-jwt'}]:
                with self.assertRaises(RuntimeError) as error:
                    write_config(['certificate'], str(path), request)
                self.assertNotIn('fixture-secret', str(error.exception))
                self.assertFalse(path.exists())

    def test_certificate_validation(self):
        for paths in [[], ['missing'], ['missing'] * 51]:
            with self.assertRaises(ValueError):
                certificate_bundle(paths)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cert.pem'
            path.write_text('-----BEGIN PRIVATE KEY-----\nfixture\n')
            with self.assertRaises(ValueError):
                certificate_bundle([str(path)])

    def test_public_pem_and_der_certificate_inputs(self):
        import ssl
        der = httpx.create_ssl_context().get_ca_certs(binary_form=True)[0]
        with tempfile.TemporaryDirectory() as directory:
            pem = Path(directory) / 'public.pem'
            binary = Path(directory) / 'public.der'
            pem.write_text(ssl.DER_cert_to_PEM_cert(der))
            binary.write_bytes(der)
            self.assertEqual(certificate_bundle([str(pem)]), certificate_bundle([str(binary)]))
            result = write_config([str(pem)], str(Path(directory) / 'sdk.jwt'), lambda body: {'sdkConfig': 'a.b.c'})
            self.assertFalse(result['signature_verified'])

    def test_symlink_refuses_before_backend(self):
        if os.name == 'nt':
            self.skipTest('Symlink creation depends on host policy')
        with tempfile.TemporaryDirectory() as directory, patch('kobil_sdk_integration.sdk_config.certificate_bundle', return_value=['cert']):
            path = Path(directory) / 'sdk.jwt'
            path.symlink_to(Path(directory) / 'missing')
            with self.assertRaises(FileExistsError):
                write_config(['certificate'], str(path), lambda body: self.fail('Unexpected backend call'))


if __name__ == '__main__':
    unittest.main()
