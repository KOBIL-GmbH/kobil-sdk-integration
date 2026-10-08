import unittest

from urllib.parse import parse_qs, urlsplit

from kobil_sdk_integration.journeys import classify, discover

BDDK_ENROLL = ['ast-headers-to-session', 'bddk-user-password-reg', 'ast-login-authenticator', 'ast-login-authenticator',
               'kobil-risk-and-policy-evaluator', 'kobil-user-group-authenticator']
BDDK_LOGIN = ['ast-headers-to-session', 'kobil-username-password-form', 'ast-login-authenticator', 'kobil-risk-and-policy-evaluator']
KSSIDP_ENROLL = ['ast-headers-to-session', 'kssidp-activation-code-verifier', 'ast-login-authenticator',
                 'kobil-risk-and-policy-evaluator', 'kssidp-configure-or-verify-password', 'ast-login-authenticator',
                 'kobil-user-group-authenticator', 'kssidp-delete-activation-code', 'kobil-claims-authenticator']
KSSIDP_LOGIN = ['ast-headers-to-session', 'ast-login-authenticator', 'kobil-risk-and-policy-evaluator',
                'kobil-username-password-form', 'kssidp-configure-or-verify-password']


class ClassifyTests(unittest.TestCase):
    def test_official_names(self):
        self.assertEqual(classify('BDDK Enrollment', BDDK_ENROLL)['based_on'], 'bddk')
        self.assertTrue(classify('BDDK Enrollment', BDDK_ENROLL)['official_flow'])
        self.assertTrue(classify('BDDK Enrollment', BDDK_ENROLL)['deprecated'])
        r = classify('KSSIDP Enrollment - Multi form flow', KSSIDP_ENROLL)
        self.assertEqual((r['based_on'], r['role'], r['official_flow']), ('kssidp', 'activation', True))
        self.assertFalse(r['deprecated'])
        r = classify('KSSIDP Mobile App Multi Flow Login', KSSIDP_LOGIN)
        self.assertEqual((r['based_on'], r['role']), ('kssidp', 'login'))

    def test_copy_with_own_name_is_recognised_by_its_steps(self):
        r = classify('KOBIL Mobile Enrollment', BDDK_ENROLL)
        self.assertEqual((r['based_on'], r['role'], r['official_flow']), ('bddk', 'activation', False))
        r = classify('KOBIL Mobile Login', BDDK_LOGIN)
        self.assertEqual((r['based_on'], r['role'], r['official_flow']), ('bddk', 'login', False))

    def test_kssidp_copy_with_own_name(self):
        r = classify('My KSSIDP Enrol', KSSIDP_ENROLL)
        self.assertEqual((r['based_on'], r['role'], r['official_flow']), ('kssidp', 'activation', False))

    def test_unknown_flow_is_other_and_has_no_role_guess(self):
        r = classify('SuperApp Login V2', ['ast-headers-to-session', 'something-else'])
        self.assertEqual((r['based_on'], r['role']), ('other', None))


class Api:
    def __init__(self):
        self.calls = []

    def call(self, method, path, params=None):
        self.calls.append((method, path))
        assert method == 'GET'
        if path == '/authentication/flows':
            return [{'id': 'f1', 'alias': 'KOBIL Mobile Enrollment'}, {'id': 'f2', 'alias': 'KOBIL Mobile Login'},
                    {'id': 'f3', 'alias': 'SuperApp Login V2'}]
        if path == '/clients':
            return [
                {'clientId': 'KobilMobileEnrollment', 'authenticationFlowBindingOverrides': {'browser': 'f1'},
                 'attributes': {'login_theme': 'kobil-mobile'}, 'secret': 'must-not-appear', 'redirectUris': ['https://x']},
                {'clientId': 'KobilMobileLogin', 'authenticationFlowBindingOverrides': {'browser': 'f2'},
                 'attributes': {'login_theme': 'kobil-mobile'}},
                {'clientId': 'Other', 'authenticationFlowBindingOverrides': {'browser': 'f3'}},
                {'clientId': 'NoOverride'}]
        if path.endswith('/executions'):
            alias = path.split('/')[-2].replace('%20', ' ')
            steps = {'KOBIL Mobile Enrollment': BDDK_ENROLL, 'KOBIL Mobile Login': BDDK_LOGIN}.get(alias, ['x'])
            return [{'providerId': s, 'requirement': 'REQUIRED'} for s in steps]
        raise AssertionError(path)


class DiscoverTests(unittest.TestCase):
    def test_discover_lists_only_flow_bound_clients_and_no_secrets(self):
        api = Api()
        r = discover(api)
        by = {c['client_id']: c for c in r['clients']}
        self.assertEqual(set(by), {'KobilMobileEnrollment', 'KobilMobileLogin', 'Other'})
        self.assertEqual(by['KobilMobileEnrollment']['based_on'], 'bddk')
        self.assertEqual(by['KobilMobileEnrollment']['login_theme'], 'kobil-mobile')
        self.assertEqual(by['KobilMobileLogin']['role'], 'login')
        self.assertEqual(r['clients_without_own_flow'], 1)
        self.assertNotIn('must-not-appear', str(r))
        self.assertNotIn('redirectUris', str(r))  # only the one redirect_uri the app needs, not the raw client attributes
        self.assertTrue(all(m == 'GET' for m, _ in api.calls))

    def test_discover_says_when_no_kssidp_standard_exists(self):
        r = discover(Api())
        self.assertFalse(r['has_kssidp_standard'])
        self.assertIn('bddk', r['summary'].lower())
        self.assertIn('No KSSIDP flow', r['summary'])


WELL_KNOWN = {'issuer': 'https://idp.example.test/auth/realms/superapp',
              'authorization_endpoint': 'https://idp.example.test/auth/realms/superapp/protocol/openid-connect/auth',
              'token_endpoint': 'https://idp.example.test/auth/realms/superapp/protocol/openid-connect/token',
              'userinfo_endpoint': 'https://idp.example.test/auth/realms/superapp/protocol/openid-connect/userinfo',
              'jwks_uri': 'https://idp.example.test/auth/realms/superapp/protocol/openid-connect/certs',
              'end_session_endpoint': 'https://idp.example.test/auth/realms/superapp/protocol/openid-connect/logout',
              'secret_like': 'ignored'}


class EndpointTests(unittest.TestCase):
    def test_endpoints_come_from_the_realm_well_known_document(self):
        r = discover(Api(), realm_base='https://idp.example.test/auth/realms/superapp', well_known=lambda url: WELL_KNOWN)
        self.assertEqual(r['endpoints']['authorization'], WELL_KNOWN['authorization_endpoint'])
        self.assertEqual(r['endpoints']['token'], WELL_KNOWN['token_endpoint'])
        self.assertEqual(r['endpoints']['source'], 'well-known')
        self.assertNotIn('secret_like', str(r['endpoints']))
        c = {c['client_id']: c for c in r['clients']}['KobilMobileEnrollment']
        self.assertEqual(c['redirect_uri'], 'https://x')
        q = parse_qs(urlsplit(c['authorization_url_template']).query)
        self.assertEqual((q['client_id'], q['redirect_uri'], q['response_type']), (['KobilMobileEnrollment'], ['https://x'], ['code']))
        self.assertTrue(c['authorization_url_template'].startswith(WELL_KNOWN['authorization_endpoint'] + '?'))

    def test_fetched_url_is_the_well_known_path_of_the_realm(self):
        seen = []
        discover(Api(), realm_base='https://idp.example.test/auth/realms/superapp', well_known=lambda url: seen.append(url) or WELL_KNOWN)
        self.assertEqual(seen, ['https://idp.example.test/auth/realms/superapp/.well-known/openid-configuration'])

    def test_when_the_document_is_unavailable_endpoints_are_derived_and_flagged(self):
        def boom(url):
            raise OSError('down')
        r = discover(Api(), realm_base='https://idp.example.test/auth/realms/superapp', well_known=boom)
        self.assertEqual(r['endpoints']['source'], 'derived')
        self.assertEqual(r['endpoints']['authorization'],
                         'https://idp.example.test/auth/realms/superapp/protocol/openid-connect/auth')
        self.assertIn('not confirmed', r['endpoints']['note'])

    def test_no_realm_base_no_endpoints(self):
        self.assertIsNone(discover(Api())['endpoints'])


if __name__ == '__main__':
    unittest.main()
