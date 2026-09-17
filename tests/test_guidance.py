"""The method and the environment facts must be reachable without a skill or admin rights."""
import json
import unittest
from unittest.mock import patch

from kobil_sdk_integration import docs
from kobil_sdk_integration.appconfig import mc_config
from kobil_sdk_integration.discovery import idp_clients, platforms, token_roles
from kobil_sdk_integration.backend import BackendError


class FakeBackend:
    """Minimal stand-in: the real client is exercised by the backend tests."""

    def __init__(self, response=None, token=''):
        self.cfg = {'environment': 'test', 'tenant': 'sample',
                    'oauth': {'token_url': 'https://idp.example/token', 'scope': 'kobil-tms'}}
        self._response = response
        self._token = token

    def request(self, method, path, body=None, allow_not_found=False):
        return self._response

    def token(self):
        return self._token


def jwt_with(claims):
    import base64
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=')
    return 'header.' + body + '.signature'


class DocumentationTests(unittest.TestCase):
    def test_index_and_workflow_are_served_without_a_section(self):
        result = docs.read()
        self.assertIn('workflow', result['returned'])
        self.assertIn('platforms', result['sections_available'])

    def test_named_section_is_served_alone(self):
        result = docs.read('platforms')
        self.assertEqual(list(result['returned']), ['platforms'])

    def test_unknown_section_is_refused(self):
        with self.assertRaises(ValueError):
            docs.read('no-such-section')

    def test_a_full_dump_is_never_returned(self):
        # Clients truncate oversized results silently, leaving a partial method.
        self.assertEqual(len(docs.read()['returned']), 1)


class DiscoveryTests(unittest.TestCase):
    def test_platforms_are_reported_verbatim(self):
        self.assertEqual(platforms(FakeBackend(['Android', 'iOS']))['platforms'], ['Android', 'iOS'])

    def test_unrecognized_platform_listing_is_refused(self):
        for value in ({'unexpected': True}, ['iOS', 2], None):
            with self.assertRaises(BackendError):
                platforms(FakeBackend(value))

    def test_missing_role_in_token_is_visible(self):
        result = token_roles(FakeBackend(token=jwt_with({'resource_access': {}})))
        self.assertEqual(result['client_roles_in_token'], [])
        self.assertEqual(result['scope_requested'], 'kobil-tms')

    def test_granted_role_is_reported(self):
        token = jwt_with({'resource_access': {'ks-management': {'roles': ['Admin']}}})
        self.assertEqual(token_roles(FakeBackend(token=token))['client_roles_in_token'], ['Admin'])

    def test_unreadable_token_is_refused(self):
        with self.assertRaises(BackendError):
            token_roles(FakeBackend(token='not-a-jwt'))

    def test_absent_client_is_detected_without_admin_rights(self):
        class Response:
            status_code = 401
            content = b'{"error":"invalid_client"}'

            def json(self):
                return {'error': 'invalid_client'}

        class Client:
            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def post(self, url, data=None):
                return Response()

        with patch('kobil_sdk_integration.discovery.httpx.Client', Client):
            result = idp_clients({'oauth': {'token_url': 'https://idp.example/token'}}, ['IDPLoginHeadlessV2'])
        self.assertEqual(result['clients_absent'], ['IDPLoginHeadlessV2'])
        self.assertEqual(result['clients_present'], [])

    def test_client_discovery_needs_an_oauth_endpoint(self):
        with self.assertRaises(BackendError):
            idp_clients({'token_env': 'SDK_TOKEN'})


class AppConfigTests(unittest.TestCase):
    def config(self, **updates):
        args = {'idp_url': 'https://idp.example', 'client_id': 'IDPLoginHeadlessV2',
                'certificate_file': 'root.pem', **updates}
        return mc_config({'environment': 'test', 'tenant': 'sample'}, **args)

    def test_generated_config_matches_the_shift_contract(self):
        content = json.loads(self.config()['content'])
        self.assertEqual(content['astServerBackend'], 'maverick')
        self.assertTrue(content['useTokenBasedLogin'])
        self.assertEqual(content['iam']['clientId'], 'IDPLoginHeadlessV2')
        self.assertEqual(content['iam']['trustedSslServerCerts'], ['root.pem'])

    def test_all_three_bundle_files_are_named(self):
        self.assertEqual(self.config()['bundle_with'], ['mc_config.json', 'sdk_config.jwt', 'root.pem'])

    def test_insecure_or_malformed_input_is_refused(self):
        for bad in ({'idp_url': 'http://idp.example'}, {'client_id': 'bad id'},
                    {'certificate_file': '../../etc/passwd\n'}, {'key_policy': 'ANYTHING'}):
            with self.assertRaises(ValueError):
                self.config(**bad)

    def test_key_policy_choices_are_honoured(self):
        content = json.loads(self.config(key_policy='ENFORCE_STRONG_HARDWARE')['content'])
        self.assertEqual(content['maverick']['jwtSignKeySecurityPolicy'], 'ENFORCE_STRONG_HARDWARE')


if __name__ == '__main__':
    unittest.main()
