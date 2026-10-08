"""2026-10-08 Xcode run: the agent could not learn the AST host or the realm base path from the MCP."""
import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from kobil_sdk_integration import backend
from kobil_sdk_integration.server import sdk_backend_status


class BackendStatusHostsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        state = patch.object(backend, '_connection_override', None); state.start(); self.addCleanup(state.stop)

    def use(self, cfg):
        path = self.root / 'c.json'; path.write_text(json.dumps(cfg))
        env = patch.dict(os.environ, KOBIL_SDK_CONNECTION=str(path)); env.start(); self.addCleanup(env.stop)

    def test_hosts_and_realm_base_from_admin_profile(self):
        self.use({'environment': 'akinci', 'tenant': 'superapp', 'ast_url': 'https://ast.example.test/ast/',
                  'token_env': 'FIXTURE_TOKEN',
                  'services': [{'name': 'tms', 'url': 'https://tms.example.test/x'}],
                  'admin': {'idp_url': 'https://idp.example.test/auth', 'realm': 'superapp',
                            'client_id': 'admin-cli', 'username': 'admin', 'password_env': 'FIXTURE_ADMIN'}})
        r = sdk_backend_status()
        self.assertEqual(r['hosts']['ast'], 'ast.example.test')
        self.assertEqual(r['hosts']['idp'], 'idp.example.test')
        self.assertEqual(r['hosts']['services'], {'tms': 'tms.example.test'})
        self.assertEqual(r['idp_realm_base'], 'https://idp.example.test/auth/realms/superapp')
        self.assertEqual(r['tls_check_hosts'], ['ast.example.test', 'idp.example.test', 'tms.example.test'])
        self.assertNotIn('FIXTURE', json.dumps(r))

    def test_no_admin_profile_reports_idp_unknown(self):
        self.use({'environment': 'e', 'tenant': 't', 'ast_url': 'https://ast.example.test', 'token_env': 'FIXTURE_TOKEN'})
        r = sdk_backend_status()
        self.assertEqual(r['hosts'], {'ast': 'ast.example.test', 'idp': None, 'services': {}})
        self.assertIsNone(r['idp_realm_base'])
        self.assertEqual(r['tls_check_hosts'], ['ast.example.test'])

    def test_realm_base_not_doubled_when_idp_url_already_names_the_realm(self):
        self.use({'environment': 'e', 'tenant': 't', 'ast_url': 'https://ast.example.test', 'token_env': 'FIXTURE_TOKEN',
                  'admin': {'idp_url': 'https://idp.example.test/auth/realms/t', 'realm': 't',
                            'client_id': 'c', 'username': 'u', 'password_env': 'FIXTURE_ADMIN'}})
        self.assertEqual(sdk_backend_status()['idp_realm_base'], 'https://idp.example.test/auth/realms/t')

    def test_realm_base_has_auth_prefix_when_idp_url_is_a_bare_host(self):
        # Measured 2026-10-08: an agent built https://host/realms/<realm> (404); the Keycloak path is /auth/realms/<realm>,
        # the same prefix the admin client and the token call use.
        for idp_url in ('https://idp.example.test', 'https://idp.example.test/', 'https://idp.example.test/auth/',
                        'https://idp.example.test/auth/realms/superapp/'):
            self.use({'environment': 'e', 'tenant': 't', 'ast_url': 'https://ast.example.test', 'token_env': 'FIXTURE_TOKEN',
                      'admin': {'idp_url': idp_url, 'realm': 'superapp', 'client_id': 'c', 'username': 'u',
                                'password_env': 'FIXTURE_ADMIN'}})
            self.assertEqual(sdk_backend_status()['idp_realm_base'], 'https://idp.example.test/auth/realms/superapp', idp_url)
