import unittest

from kobil_sdk_integration.backend import BackendError
from kobil_sdk_integration.themecheck import check_login_page, idp_base_url

GOOD = ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
        '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
        '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>x</title></head>'
        '<body><form><input id="jsonInput" type="text" name="jsonInput" value="{}" /></form></body></html>')
BAD = GOOD.replace('</body>', '</body></body>')
NO_TYPE = GOOD.replace(' type="text"', '')


class FakeBackend:
    def __init__(self, status=200, body=GOOD, admin=True):
        self.cfg = {'environment': 'test', 'tenant': 'sample',
                    'oauth': {'token_url': 'https://idp.example/auth/realms/sample/protocol/openid-connect/token',
                              'client_id': 'c', 'client_secret_env': 'X'}}
        if admin:
            self.cfg['admin'] = {'idp_url': 'https://idp.example'}
        self.status, self.body, self.urls = status, body, []

    def fetch_text(self, url, headers=None):
        self.urls.append(url)
        return self.status, self.body


class ThemeCheckTests(unittest.TestCase):
    def test_a_readable_page_passes_and_the_request_is_a_browser_one(self):
        backend = FakeBackend()
        result = check_login_page(backend, 'IDPSubsequentLoginHeadlessV2')
        self.assertTrue(result['well_formed'])
        self.assertTrue(result['json_input_has_type'])
        self.assertTrue(result['checked'])
        self.assertIn('client_id=IDPSubsequentLoginHeadlessV2', backend.urls[0])
        self.assertIn('response_mode=form_post', backend.urls[0])
        self.assertTrue(backend.urls[0].startswith('https://idp.example/auth/realms/sample/'))

    def test_a_malformed_page_is_reported_with_the_parser_error(self):
        result = check_login_page(FakeBackend(body=BAD), 'IDPSubsequentLoginHeadlessV2')
        self.assertFalse(result['well_formed'])
        self.assertTrue(result['error'])
        self.assertIn('reapply', result['note'])

    def test_a_json_input_without_type_is_flagged(self):
        result = check_login_page(FakeBackend(body=NO_TYPE), 'IDPSubsequentLoginHeadlessV2')
        self.assertTrue(result['well_formed'])
        self.assertFalse(result['json_input_has_type'])
        self.assertIn('type attribute', result['note'])

    def test_an_activation_client_is_not_checkable_from_a_browser(self):
        result = check_login_page(FakeBackend(status=406, body=''), 'KOBILAPPActivation')
        self.assertFalse(result['checked'])
        self.assertIsNone(result['well_formed'])

    def test_other_statuses_are_errors(self):
        with self.assertRaises(BackendError):
            check_login_page(FakeBackend(status=500, body='boom'), 'IDPSubsequentLoginHeadlessV2')

    def test_the_host_comes_from_the_token_url_without_an_admin_block(self):
        backend = FakeBackend(admin=False)
        self.assertEqual(idp_base_url(backend.cfg), 'https://idp.example')
        check_login_page(backend, 'IDPSubsequentLoginHeadlessV2')
        self.assertTrue(backend.urls[0].startswith('https://idp.example/auth/realms/sample/'))

    def test_malformed_arguments_are_refused(self):
        with self.assertRaises(ValueError):
            check_login_page(FakeBackend(), 'bad client')
        with self.assertRaises(ValueError):
            check_login_page(FakeBackend(), 'ok', redirect_uri='http://plain')
