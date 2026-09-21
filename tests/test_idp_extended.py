"""Contract tests for explicit routes, typed writes and private provider configuration."""
import asyncio
import unittest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError
from mcp.server.fastmcp import FastMCP
from kobil_sdk_integration import idp_extended as mod


class Registry:
    def __init__(self): self.tools = {}
    def tool(self):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class ExtendedTests(unittest.TestCase):
    def setUp(self):
        registry = Registry()
        mod.register(registry)
        self.tools = registry.tools
        self.patcher = patch.object(mod, 'Admin')
        self.admin = self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.api = self.admin.return_value.__enter__.return_value

    def call(self, tool_name, **kw):
        return self.tools['sdk_idp_' + tool_name](expected_environment='test', **kw)

    def test_user_session_offline_requires_client(self):
        with self.assertRaises(ValueError):
            self.call('sessions_list', owner_type='user', owner_id='u', offline=True)
        self.admin.assert_not_called()
        self.call('sessions_list', owner_type='user', owner_id='u', offline=True, offline_client_id='c', realm='other')
        self.admin.assert_called_with('test', realm='other')
        self.api.page.assert_called_once_with('/users/u/offline-sessions/c', first=0, max_results=50, paginated=False)

    def test_client_sessions_have_server_pagination(self):
        self.call('sessions_list', owner_type='client', owner_id='c', first=20, max_results=10)
        self.api.page.assert_called_once_with('/clients/c/user-sessions', first=20, max_results=10, paginated=True)

    def test_alias_is_encoded_and_flow_requirement_only(self):
        self.call('flow_execution_update', flow_alias='flow name', execution_id='e', requirement='REQUIRED')
        self.api.call.assert_called_once_with('PUT', '/authentication/flows/flow%20name/executions', body={'id':'e', 'requirement':'REQUIRED'})

    def test_realm_models_reject_unknown_and_invalid_fields(self):
        with self.assertRaises(ValidationError): mod.RealmChanges(smtpServer={'password':'no'})
        with self.assertRaises(ValidationError): mod.RealmChanges(accessTokenLifespan=-1)
        with self.assertRaises(ValueError): self.call('realm_update', changes=mod.RealmChanges())

    def test_admin_events_use_distinct_filter_names(self):
        self.call('events_list', event_kind='admin', user_id='u', client_id='c', first=2)
        self.api.page.assert_called_once_with('/admin-events', first=2, max_results=50, params={'authUser':'u', 'authClient':'c'})

    def test_secret_provider_configuration_is_reference_only(self):
        with patch.object(mod, 'load_private_json', return_value={'clientId':'id','clientSecret':'secret'}) as read:
            self.call('identity_provider_create', alias='external', provider_config_file='/private/idp.json')
        read.assert_called_once_with('/private/idp.json')
        args = self.api.call.call_args.kwargs['body']
        self.assertEqual(args['config']['clientSecret'], 'secret')
        self.assertFalse(args['enabled'])
        self.assertEqual(args['providerId'], 'oidc')

    def test_provider_config_rejects_unrecognized_fields(self):
        with patch.object(mod, 'load_private_json', return_value={'unreviewed':'value'}):
            with self.assertRaises(ValueError):
                self.call('identity_provider_create', alias='external', provider_config_file='/private/idp.json')
        self.api.call.assert_not_called()

    def test_update_provider_uses_preserving_helper(self):
        with patch.object(mod, 'load_private_json', return_value={'clientSecret':'new'}):
            self.call('identity_provider_update', alias='external', changes=mod.ProviderChanges(enabled=True), provider_config_file='/private/idp.json')
        args = self.api.update.call_args.args
        self.assertEqual(args[0], '/identity-provider/instances/external')
        self.assertEqual(args[1], {'enabled':True, 'config':{'clientSecret':'new'}})

    def test_resource_update_does_not_replace_unselected_settings(self):
        self.call('authorization_resource_update', client_id='c', resource_id='r', changes=mod.ResourceChanges(name='new'))
        self.assertEqual(self.api.update.call_args.args[:2], ('/clients/c/authz/resource-server/resource/r', {'name':'new'}))

    def test_policy_membership_must_match_type(self):
        with self.assertRaises(ValueError):
            self.call('policy_create', client_id='c', policy_type='user', name='p', fields=mod.PolicyChanges(clients=['x']))
        self.api.call.assert_not_called()
        self.call('policy_create', client_id='c', policy_type='user', name='p', fields=mod.PolicyChanges(users=['u']))
        self.api.call.assert_called_once_with('POST', '/clients/c/authz/resource-server/policy/user', body={'users':['u'], 'name':'p', 'type':'user'})

    def test_permission_route_uses_specific_type(self):
        self.api.call.return_value = {'type': 'scope'}
        self.call('permission_update', client_id='c', permission_type='scope', permission_id='p', changes=mod.PermissionChanges(policies=['x']))
        self.assertEqual(self.api.update.call_args.args[:2], ('/clients/c/authz/resource-server/permission/scope/p', {'policies':['x']}))

    def test_policy_type_mismatch_stops_write(self):
        self.api.call.return_value = {'type': 'client'}
        with self.assertRaises(ValueError):
            self.call('policy_update', client_id='c', policy_id='p', policy_type='user', changes=mod.PolicyChanges(users=['u']))
        self.api.update.assert_not_called()

    def test_realms_page_is_not_silently_truncated(self):
        self.api.call_global.return_value = [{'realm': str(i)} for i in range(4)]
        result = self.call('realms_list', first=1, max_results=2)
        self.assertEqual(result['next_offset'], 3)
        self.assertFalse(result['complete'])
        self.assertEqual(len(result['items']), 2)

    def test_tools_have_valid_mcp_schemas(self):
        mcp = FastMCP('extended-contract')
        mod.register(mcp)
        tools = asyncio.run(mcp.list_tools())
        self.assertGreater(len(tools), 50)
        for tool in tools:
            self.assertIn('expected_environment', tool.inputSchema['required'])
            self.assertGreater(len(tool.description), 60)
            self.assertNotIn('body', tool.inputSchema['properties'])

if __name__ == '__main__': unittest.main()
