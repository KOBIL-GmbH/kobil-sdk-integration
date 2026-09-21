import unittest
from unittest.mock import MagicMock, patch
from kobil_sdk_integration import idp_access


class Registry:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(function):
            self.tools[function.__name__] = function
            return function
        return register


class AccessTests(unittest.TestCase):
    def setUp(self):
        registry = Registry()
        idp_access.register(registry)
        self.tools = registry.tools
        self.patch = patch.object(idp_access, 'Admin')
        self.admin = self.patch.start()
        self.addCleanup(self.patch.stop)
        self.api = self.admin.return_value.__enter__.return_value

    def run_tool(self, tool_name, **kwargs):
        return self.tools['sdk_idp_' + tool_name](expected_environment='test', **kwargs)

    def test_discovery_uses_public_filter_not_uuid_path(self):
        self.run_tool('client_list', client_id='mobile', first=10, max_results=20, realm='selected')
        self.admin.assert_called_once_with('test', 'selected')
        self.api.page.assert_called_once_with('/clients', 10, 20, params={'clientId': 'mobile'})

    def test_internal_client_id_and_encoded_role(self):
        self.run_tool('role_get', role_name='a/b', client_uuid='internal-uuid')
        self.api.call.assert_called_once_with('GET', '/clients/internal-uuid/roles/a%2Fb')

    def test_update_preserves_omitted_fields_and_explicit_false(self):
        self.run_tool('client_update', client_uuid='id', enabled=False, redirect_uris=[])
        args = self.api.update.call_args.args
        self.assertEqual(args[1], {'enabled': False, 'redirectUris': []})

    def test_scope_update_only_requested_fields(self):
        self.run_tool('scope_update', scope_id='scope', description='new')
        self.assertEqual(self.api.update.call_args.args[1], {'description': 'new'})

    def test_role_missing_description_rejected(self):
        with self.assertRaises(ValueError):
            self.run_tool('role_update', role_name='x')
        self.api.update.assert_not_called()

    def test_assignment_resolves_every_role_before_write(self):
        self.api.call.side_effect = [{'id': 'r1', 'name': 'reader'}, ValueError('missing')]
        with self.assertRaises(ValueError):
            self.run_tool('role_assign', subject_type='group', subject_id='g', role_names=['reader', 'missing'])
        self.assertTrue(all(call.args[0] == 'GET' for call in self.api.call.call_args_list))

    def test_assignment_is_scoped_and_uses_resolved_ids(self):
        self.api.call.side_effect = [{'id': 'role-uuid', 'name': 'reader'}, None]
        self.run_tool('role_assign', subject_type='user', subject_id='u', role_names=['reader'], client_uuid='c')
        self.assertEqual(self.api.call.call_args.args, ('POST', '/users/u/role-mappings/clients/c'))
        self.assertEqual(self.api.call.call_args.kwargs['body'], [{'id': 'role-uuid', 'name': 'reader'}])

    def test_scope_collections_use_local_pagination(self):
        self.run_tool('scope_list', first=10, max_results=5)
        self.api.page.assert_called_once_with('/client-scopes', 10, 5, paginated=False)

    def test_invalid_owner_is_not_a_path_passthrough(self):
        with self.assertRaises(ValueError):
            self.run_tool('mapper_list', owner_type='../users', owner_id='x')
        self.api.page.assert_not_called()

    def test_other_mapper_provider_cannot_be_overwritten(self):
        self.api.raw.return_value = {'protocolMapper': 'oidc-hardcoded-claim-mapper'}
        with self.assertRaises(ValueError):
            self.run_tool('mapper_update', owner_type='scope', owner_id='s', mapper_id='m', name='n', user_attribute='attr', claim_name='claim')
        self.api.update.assert_not_called()

    def test_mapper_preserves_unrelated_config(self):
        self.api.raw.return_value = {'protocolMapper': 'oidc-usermodel-attribute-mapper', 'config': {'custom.setting': 'keep'}}
        self.run_tool('mapper_update', owner_type='scope', owner_id='s', mapper_id='m', name='n', user_attribute='attr', claim_name='claim')
        body = self.api.update.call_args.args[1]
        self.assertEqual(body['config']['custom.setting'], 'keep')
        self.assertEqual(body['config']['user.attribute'], 'attr')

    def test_group_membership_does_not_delete_user(self):
        self.run_tool('group_member_remove', group_id='g', user_id='u')
        self.api.call.assert_called_once_with('DELETE', '/users/u/groups/g', body=None)

    def test_composite_can_mix_parent_and_member_scopes(self):
        self.api.call.side_effect = [{'id': 'r', 'name': 'reader'}, None]
        self.run_tool('role_composite_add', role_name='parent', member_role_names=['reader'], member_client_uuid='c')
        self.assertEqual(self.api.call.call_args_list[0].args, ('GET', '/clients/c/roles/reader'))
        self.assertEqual(self.api.call.call_args_list[1].args, ('POST', '/roles/parent/composites'))


if __name__ == '__main__':
    unittest.main()
