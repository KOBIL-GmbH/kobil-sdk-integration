"""A realm without an activation journey cannot activate a device, however correct the app is."""
import unittest

from kobil_sdk_integration.backend import BackendError
from kobil_sdk_integration.idpflow import (DEFAULT_STEP_CONFIG, DEFAULT_STEPS, attach_client_scope, discover_journeys,
                                           configure_step, describe_flow, ensure_client, ensure_flow)

ADMIN = {'idp_url': 'https://idp.example', 'realm': 'master', 'client_id': 'admin-cli',
         'username': 'admin', 'password_env': 'KOBIL_TEST_ADMIN_PASSWORD'}


class FakeBackend:
    def __init__(self, flows=(), clients=(), offered=DEFAULT_STEPS, admin=ADMIN,
                 unconfigurable=(), stored_override=None, realm_scopes=('ast',)):
        self.cfg = {'environment': 'test', 'tenant': 'sample'}
        if admin:
            self.cfg['admin'] = admin
        self.flows = [dict(f) for f in flows]
        self.clients = [dict(c) for c in clients]
        self.offered = list(offered)
        self.unconfigurable = set(unconfigurable)
        self.stored_override = stored_override
        self.configs = {}
        self.realm_scopes = list(realm_scopes)
        self.attached_scopes = ['profile', 'roles']
        self.steps = []
        self.calls = []

    def send(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        body = kwargs.get('json')
        if url.endswith('/protocol/openid-connect/token'):
            return {'access_token': 'admin-token'}
        if url.endswith('/authentication/authenticator-providers'):
            return [{'id': p} for p in self.offered]
        if url.endswith('/authentication/flows') and method == 'GET':
            return list(self.flows)
        if url.endswith('/authentication/flows') and method == 'POST':
            self.flows.append({'alias': body['alias'], 'id': 'flow-uuid'})
            return {}
        if url.endswith('/executions/execution') and method == 'POST':
            self.steps.append({'providerId': body['provider'], 'requirement': 'DISABLED',
                               'id': 'e%d' % len(self.steps), 'index': len(self.steps),
                               'configurable': body['provider'] not in self.unconfigurable})
            return {}
        if '/executions/' in url and url.endswith('/config') and method == 'POST':
            exec_id = url.rsplit('/', 2)[1]
            step = next(s for s in self.steps if s['id'] == exec_id)
            step['authenticationConfig'] = 'cfg-' + step['id']
            self.configs[step['authenticationConfig']] = dict(body['config'])
            return {}
        if '/authentication/config/' in url and method == 'PUT':
            self.configs[url.rsplit('/', 1)[1]] = dict(body['config'])
            return {}
        if '/authentication/config/' in url and method == 'GET':
            stored = self.configs.get(url.rsplit('/', 1)[1], {})
            return {'config': dict(self.stored_override or stored)}
        if url.endswith('/executions') and method == 'GET':
            return list(self.steps)
        if url.endswith('/executions') and method == 'PUT':
            for step in self.steps:
                if step['id'] == body['id']:
                    step['requirement'] = body['requirement']
            return {}
        # Checked before '/client-scopes', which it also ends with.
        if '/default-client-scopes' in url and method == 'PUT':
            self.attached_scopes.append(next(s for s in self.realm_scopes if s in url or True))
            return {}
        if url.endswith('/default-client-scopes') and method == 'GET':
            return [{'name': n} for n in self.attached_scopes]
        if url.endswith('/client-scopes') and method == 'GET':
            return [{'id': 'scope-%s' % n, 'name': n} for n in self.realm_scopes]
        if url.endswith('/clients') and method == 'GET':
            wanted = (kwargs.get('params') or {}).get('clientId')
            if wanted is None:
                return list(self.clients)
            return [c for c in self.clients if c['clientId'] == wanted]
        if url.endswith('/clients') and method == 'POST':
            self.clients.append({'clientId': body['clientId'], 'id': 'client-uuid',
                                 'attributes': body['attributes'], 'redirectUris': body['redirectUris'],
                                 'authenticationFlowBindingOverrides': body['authenticationFlowBindingOverrides']})
            return {}
        return {}


class FlowTests(unittest.TestCase):
    def setUp(self):
        import os
        os.environ['KOBIL_TEST_ADMIN_PASSWORD'] = 'not-the-real-one'

    def test_flow_is_created_with_its_steps_in_order_and_required(self):
        backend = FakeBackend()
        result = ensure_flow(backend, 'KOBILAPP Device Activation')
        self.assertTrue(result['created'])
        self.assertEqual([s['provider'] for s in result['steps']], list(DEFAULT_STEPS))
        self.assertEqual({s['requirement'] for s in result['steps']}, {'REQUIRED'})

    def test_existing_flow_is_never_rewritten(self):
        backend = FakeBackend(flows=[{'alias': 'KOBILAPP Device Activation', 'id': 'flow-uuid'}])
        result = ensure_flow(backend, 'KOBILAPP Device Activation')
        self.assertFalse(result['created'])
        self.assertEqual([c for c in backend.calls if c[0] == 'POST' and c[1].endswith('/flows')], [])

    def test_authenticator_absent_from_this_build_is_refused_before_any_write(self):
        backend = FakeBackend(offered=('ast-login-authenticator',))
        with self.assertRaises(BackendError):
            ensure_flow(backend, 'KOBILAPP Device Activation')
        self.assertEqual([c for c in backend.calls if c[0] == 'POST' and 'authentication' in c[1]], [])

    def test_malformed_arguments_are_refused(self):
        for bad in ({'alias': 'ab'}, {'alias': 'bad/alias'}, {'steps': []},
                    {'steps': ['x'] * 13}, {'requirement': 'MAYBE'}):
            with self.assertRaises((ValueError, BackendError)):
                ensure_flow(FakeBackend(), **{'alias': 'KOBILAPP Device Activation', **bad})

    def test_describe_reports_a_missing_flow_rather_than_inventing_one(self):
        self.assertEqual(describe_flow(FakeBackend(), 'Nothing Here')['exists'], False)


class StepConfigTests(unittest.TestCase):
    def setUp(self):
        import os
        os.environ['KOBIL_TEST_ADMIN_PASSWORD'] = 'not-the-real-one'

    def test_a_new_flow_carries_the_activation_configuration(self):
        backend = FakeBackend()
        result = ensure_flow(backend, 'KOBILAPP Device Activation')
        self.assertEqual(result['step_config_applied'],
                         ['ast-login-authenticator#1', 'ast-login-authenticator#2'])
        first = backend.configs['cfg-e0']
        # Unconfigured, this step demands a client id header a fresh device cannot have.
        self.assertEqual(first['ast_clientid_required'], 'true')
        self.assertEqual(first['Action'], 'activate')
        # The second AST step binds the minted client to the user.
        second = backend.configs['cfg-e2']
        self.assertEqual(second['Action'], 'link')
        self.assertEqual(second['read_ast_data_from_session'], 'true')
        self.assertNotIn('cfg-e1', backend.configs)

    def test_each_ast_step_is_configured_separately(self):
        backend = FakeBackend()
        ensure_flow(backend, 'KOBILAPP Device Activation', step_config={})
        configure_step(backend, 'KOBILAPP Device Activation', 'ast-login-authenticator',
                       {'Action': 'link'}, occurrence=2)
        self.assertNotIn('cfg-e0', backend.configs)
        self.assertEqual(backend.configs['cfg-e2'], {'Action': 'link'})
        with self.assertRaises(BackendError):
            configure_step(backend, 'KOBILAPP Device Activation', 'ast-login-authenticator',
                           {'Action': 'x'}, occurrence=3)
        with self.assertRaises(ValueError):
            configure_step(backend, 'KOBILAPP Device Activation', 'ast-login-authenticator',
                           {'Action': 'x'}, occurrence=0)
        with self.assertRaises(ValueError):
            ensure_flow(backend, 'Other Flow', step_config={'ast-login-authenticator#x': {'a': 'b'}})

    def test_configuration_is_verified_by_reading_it_back(self):
        backend = FakeBackend(stored_override={'Action': 'link'})
        ensure_flow(backend, 'KOBILAPP Device Activation', steps=['ast-login-authenticator'],
                    step_config={})
        with self.assertRaises(BackendError):
            configure_step(backend, 'KOBILAPP Device Activation', 'ast-login-authenticator',
                           {'Action': 'activate'})

    def test_step_absent_from_the_flow_is_refused(self):
        backend = FakeBackend()
        ensure_flow(backend, 'KOBILAPP Device Activation')
        with self.assertRaises(BackendError):
            configure_step(backend, 'KOBILAPP Device Activation', 'kobil-create-account',
                           {'Action': 'activate'})

    def test_a_step_that_cannot_be_configured_is_refused(self):
        backend = FakeBackend(unconfigurable=('kssidp-verify-act-code',))
        ensure_flow(backend, 'KOBILAPP Device Activation')
        with self.assertRaises(BackendError):
            configure_step(backend, 'KOBILAPP Device Activation', 'kssidp-verify-act-code',
                           {'anything': 'true'})

    def test_malformed_configuration_is_refused(self):
        backend = FakeBackend()
        ensure_flow(backend, 'KOBILAPP Device Activation')
        for bad in ({}, {'bad key': 'x'}, {'Action': 42}, {'a%d' % i: 'x' for i in range(31)}):
            with self.assertRaises(ValueError):
                configure_step(backend, 'KOBILAPP Device Activation', 'ast-login-authenticator', bad)

    def test_the_documented_default_is_what_the_device_test_used(self):
        self.assertEqual(DEFAULT_STEP_CONFIG['ast-login-authenticator#1'],
                         {'Action': 'activate', 'ast_clientid_required': 'true', 'MLoA': 'none'})
        self.assertEqual(DEFAULT_STEP_CONFIG['ast-login-authenticator#2'],
                         {'Action': 'link', 'ast_clientid_required': 'false',
                          'read_ast_data_from_session': 'true', 'MLoA': 'none'})

    def test_only_kssidp_authenticators_render_the_activation(self):
        # The kobil-* equivalents render templates a KSSIDP theme does not ship: the IDP
        # then answers HTTP 500 with a FreeMarker TemplateNotFoundException.
        rendering = [p for p in DEFAULT_STEPS if p != 'ast-login-authenticator']
        self.assertTrue(all(p.startswith('kssidp-') for p in rendering), rendering)

    def test_the_code_step_is_the_one_that_has_a_form(self):
        # kssidp-verify-act-code renders nothing and rejects with "Missing parameter: username".
        self.assertIn('kssidp-activation-code-verifier', DEFAULT_STEPS)
        self.assertNotIn('kssidp-verify-act-code', DEFAULT_STEPS)

    def test_the_default_renders_one_page_and_links_after_the_code(self):
        steps = list(DEFAULT_STEPS)
        # Only the code page renders: a second rendered page is dropped by KSSIDP.
        self.assertNotIn('kssidp-configure-or-verify-password', steps)
        self.assertEqual(steps.count('ast-login-authenticator'), 2)
        self.assertEqual(steps, ['ast-login-authenticator', 'kssidp-activation-code-verifier',
                                 'ast-login-authenticator', 'kssidp-delete-activation-code'])


class ClientTests(unittest.TestCase):
    def setUp(self):
        import os
        os.environ['KOBIL_TEST_ADMIN_PASSWORD'] = 'not-the-real-one'

    def test_client_is_bound_to_the_flow_and_carries_the_theme(self):
        backend = FakeBackend(flows=[{'alias': 'KOBILAPP Device Activation', 'id': 'flow-uuid'}])
        result = ensure_client(backend, 'KOBILAPPActivation', 'KOBILAPP Device Activation',
                               'kobil-lite', 'https://kobil/OpenIdRedirectUri')
        self.assertTrue(result['created'])
        self.assertEqual(result['login_theme'], 'kobil-lite')
        self.assertEqual(result['bound_flow'], 'KOBILAPP Device Activation')

    def test_the_client_gets_the_scope_that_carries_the_ast_client_id(self):
        backend = FakeBackend(flows=[{'alias': 'KOBILAPP Device Activation', 'id': 'flow-uuid'}])
        result = ensure_client(backend, 'KOBILAPPActivation', 'KOBILAPP Device Activation',
                               'kobil-lite', 'https://kobil/OpenIdRedirectUri')
        # Without it the SDK refuses the last step: "AST client id is not set in IAM access token".
        self.assertIn('ast', result['default_client_scopes'])

    def test_a_realm_without_that_scope_is_refused(self):
        backend = FakeBackend(flows=[{'alias': 'KOBILAPP Device Activation', 'id': 'flow-uuid'}],
                              realm_scopes=('profile',))
        with self.assertRaises(BackendError):
            ensure_client(backend, 'KOBILAPPActivation', 'KOBILAPP Device Activation',
                          'kobil-lite', 'https://kobil/OpenIdRedirectUri')

    def test_a_malformed_scope_name_is_refused(self):
        with self.assertRaises(ValueError):
            attach_client_scope(FakeBackend(), 'client-uuid', 'bad scope name')

    def test_client_without_its_flow_is_refused(self):
        with self.assertRaises(BackendError):
            ensure_client(FakeBackend(), 'KOBILAPPActivation', 'Missing Flow',
                          'kobil-lite', 'https://kobil/OpenIdRedirectUri')

    def test_existing_client_is_reused_unmodified(self):
        backend = FakeBackend(flows=[{'alias': 'KOBILAPP Device Activation', 'id': 'flow-uuid'}],
                              clients=[{'clientId': 'KOBILAPPActivation', 'id': 'client-uuid',
                                        'attributes': {'login_theme': 'kobil-headless-v2'}}])
        result = ensure_client(backend, 'KOBILAPPActivation', 'KOBILAPP Device Activation', 'kobil-lite',
                               'https://kobil/OpenIdRedirectUri')
        self.assertFalse(result['created'])
        self.assertEqual([c for c in backend.calls if c[0] == 'POST' and c[1].endswith('/clients')], [])

    def test_malformed_client_arguments_are_refused(self):
        for bad in ({'client_id': 'ab'}, {'client_id': 'has space'}, {'login_theme': 'bad theme'},
                    {'redirect_uri': 'https://kobil/redirect uri'}):
            with self.assertRaises(ValueError):
                ensure_client(FakeBackend(), **{'client_id': 'KOBILAPPActivation',
                                                'flow_alias': 'KOBILAPP Device Activation',
                                                'login_theme': 'kobil-lite',
                                                'redirect_uri': 'https://kobil/OpenIdRedirectUri', **bad})


if __name__ == '__main__':
    unittest.main()


class JourneyDiscoveryTests(unittest.TestCase):
    def setUp(self):
        import os
        os.environ['KOBIL_TEST_ADMIN_PASSWORD'] = 'not-the-real-one'

    def test_clients_are_classified_by_their_flow_not_their_name(self):
        backend = FakeBackend(clients=[
            {'clientId': 'AnyNameAtAll', 'id': 'c1', 'attributes': {'login_theme': 'kobil-lite'},
             'authenticationFlowBindingOverrides': {'browser': 'flow-uuid'}},
            {'clientId': 'NoOverride', 'id': 'c2', 'attributes': {}, 'authenticationFlowBindingOverrides': {}},
        ])
        ensure_flow(backend, 'Whatever Enrolment')
        result = discover_journeys(backend)
        self.assertEqual([e['client_id'] for e in result['activation']], ['AnyNameAtAll'])
        self.assertEqual(result['activation'][0]['flow_alias'], 'Whatever Enrolment')
        self.assertTrue(result['activation'][0]['links_device_to_user'])
        self.assertEqual(result['login'], [])
        self.assertEqual(result['other_clients_with_own_flow'], 0)
        # Minimal disclosure: four fields plus the link flag, nothing else about the client.
        self.assertEqual(set(result['activation'][0]), {'client_id', 'flow_alias', 'login_theme', 'steps', 'links_device_to_user'})

    def test_a_named_list_reads_only_those_clients(self):
        backend = FakeBackend(clients=[
            {'clientId': 'Mine', 'id': 'c1', 'attributes': {'login_theme': 'kobil-lite'},
             'authenticationFlowBindingOverrides': {'browser': 'flow-uuid'}},
            {'clientId': 'SomeoneElses', 'id': 'c2', 'attributes': {'login_theme': 'kobil-lite'},
             'authenticationFlowBindingOverrides': {'browser': 'flow-uuid'}}])
        ensure_flow(backend, 'Enrolment')
        result = discover_journeys(backend, client_ids=['Mine'])
        self.assertEqual([e['client_id'] for e in result['activation']], ['Mine'])
        listed = [c for c in backend.calls if c[0] == 'GET' and c[1].endswith('/clients')]
        self.assertTrue(all((c[2].get('params') or {}).get('clientId') == 'Mine' for c in listed))
        with self.assertRaises(ValueError):
            discover_journeys(backend, client_ids=[])
        with self.assertRaises(ValueError):
            discover_journeys(backend, client_ids=['bad id'])

    def test_a_single_identity_step_is_a_login_journey(self):
        backend = FakeBackend(clients=[
            {'clientId': 'Login', 'id': 'c1', 'attributes': {'login_theme': 'kobil-headless-v2'},
             'authenticationFlowBindingOverrides': {'browser': 'flow-uuid'}}],
            offered=('kobil-verify-uid-authenticator',))
        ensure_flow(backend, 'Login Flow', steps=['kobil-verify-uid-authenticator'], step_config={})
        result = discover_journeys(backend)
        self.assertEqual([e['client_id'] for e in result['login']], ['Login'])
        self.assertEqual(result['activation'], [])
