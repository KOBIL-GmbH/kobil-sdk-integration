> Clean service-interface branch: contract tests only; prior implementation live evidence does not qualify this branch.

# IDP clients and access — 0.6.0

Existing SDK helpers remain available. Environment/realm permissions and deployed API support are required.

### `sdk_idp_client_list`

Read a page of IDP clients. client_id filters the public clientId; returned id is the internal UUID used by client tools. Follow next_offset to continue. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, client_id, first, max_results, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_client_get`

Read one client by internal UUID; credential fields are redacted. Use client_list to resolve a public clientId. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, client_uuid, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_client_create`

Create an OpenID Connect client with an explicit public clientId. Conflicts are not silently reused. Does not export its secret. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, client_id, name, description, enabled, public_client, standard_flow_enabled, direct_access_grants_enabled, service_accounts_enabled, redirect_uris, web_origins, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_client_update`

Update selected client fields by internal UUID, preserving omitted configuration. Empty URI/origin lists explicitly clear those lists. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, client_uuid, name, description, enabled, public_client, standard_flow_enabled, direct_access_grants_enabled, service_accounts_enabled, redirect_uris, web_origins, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_client_delete`

Delete one client by internal UUID, including its configuration. This is destructive. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, client_uuid, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_client_service_account_get`

Read the service-account user for an internal client UUID. Service accounts must be enabled on that client. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, client_uuid, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_scope_list`

Read a locally paginated page of realm client scopes; these are OAuth client scopes, not authorization resource scopes. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, first, max_results, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_scope_get`

Read a realm client scope by ID. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, scope_id, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_scope_create`

Create an OpenID Connect realm client scope. Assign it to a client separately with client_scope_assign. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, name, description, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_scope_update`

Update selected client-scope metadata, preserving mappers and unrelated attributes. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, scope_id, name, description, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_scope_delete`

Delete a realm client scope by ID; assignments are affected. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, scope_id, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_client_scopes_get`

Read default or optional scope bindings for an internal client UUID. Pagination is local. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, client_uuid, scope_type, first, max_results, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_client_scope_assign`

Bind an existing scope as default or optional to a client; idempotent PUT does not create a scope. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, client_uuid, scope_id, scope_type, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_client_scope_remove`

Remove only the selected scope binding, retaining the scope itself. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, client_uuid, scope_id, scope_type, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_mapper_list`

Read protocol mappers on an internal client UUID or client-scope ID. Pagination is local. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, owner_type, owner_id, first, max_results, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_mapper_create`

Create a typed OIDC user-attribute-to-claim mapper. Other mapper provider types are not supported by this operation. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, owner_type, owner_id, name, user_attribute, claim_name, json_type, in_access_token, in_id_token, in_userinfo, multivalued, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_mapper_update`

Update an existing OIDC user-attribute mapper. Rejects other provider types and preserves unrelated mapper configuration. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, owner_type, owner_id, mapper_id, name, user_attribute, claim_name, json_type, in_access_token, in_id_token, in_userinfo, multivalued, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_mapper_delete`

Delete one protocol mapper from its explicitly selected owner. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, owner_type, owner_id, mapper_id, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_role_list`

Read paginated realm roles, or client roles when internal client UUID is supplied. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, client_uuid, search, first, max_results, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_role_get`

Get a realm role, or a role belonging to the explicitly selected internal client UUID. role_name is the exact role name. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, role_name, client_uuid, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_role_create`

Create a realm role, or a role belonging to the explicitly selected internal client UUID. role_name is the exact role name. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, role_name, client_uuid, description, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_role_update`

Update a realm role, or a role belonging to the explicitly selected internal client UUID. role_name is the exact role name. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, role_name, client_uuid, description, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_role_delete`

Delete a realm role, or a role belonging to the explicitly selected internal client UUID. role_name is the exact role name. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, role_name, client_uuid, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_role_composites_get`

Read composite members of a realm/client role. Pagination is local. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, role_name, client_uuid, first, max_results, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_role_composite_add`

Add composite role membership. Parent and member role scopes are explicit; omit each client UUID for realm scope. Members are resolved before any mutation. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, role_name, member_role_names, client_uuid, member_client_uuid, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_role_composite_remove`

Remove composite role membership. Parent and member role scopes are explicit; omit each client UUID for realm scope. Members are resolved before any mutation. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, role_name, member_role_names, client_uuid, member_client_uuid, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_role_members_list`

Read a page of users/groups assigned a realm/client role. Unsupported backend routes return a structured backend error. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, role_name, member_type, client_uuid, first, max_results, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_group_list`

Read a page of top-level groups. Nested subGroups returned by the backend are not a flattened full-realm enumeration. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, search, first, max_results, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_group_get`

Read one group by UUID, including backend-returned hierarchy metadata. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, group_id, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_group_count`

Count realm groups, optionally filtered by name and top-level status. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, search, top_level, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_group_create`

Create a top-level group or a child of the specified parent UUID. Existing name conflicts are reported by the backend. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, name, parent_group_id, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_group_update`

Rename a group while preserving attributes and unrelated metadata. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, group_id, name, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_group_delete`

Delete one group and its backend-managed hierarchy/memberships. Does not delete member users. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, group_id, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_group_members_list`

Read a page of users in a group using its UUID. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, group_id, first, max_results, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_user_groups_list`

Read a page of group memberships for an exact user UUID. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, user_id, first, max_results, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_group_member_add`

Add an existing user UUID in a group UUID. Does not create/delete the user or group. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, group_id, user_id, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_group_member_remove`

Remove an existing user UUID in a group UUID. Does not create/delete the user or group. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, group_id, user_id, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_role_assignments_get`

Read direct or effective roles assigned to a user/group UUID. Omit client_uuid for realm roles. Pagination is local. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, subject_type, subject_id, client_uuid, effective, first, max_results, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_role_assign`

Assign direct roles for a user/group UUID. Omit client_uuid for realm roles. Resolves all exact role names before writing; inherited roles are not directly removed. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, subject_type, subject_id, role_names, client_uuid, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_role_remove`

Remove direct roles for a user/group UUID. Omit client_uuid for realm roles. Resolves all exact role names before writing; inherited roles are not directly removed. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant.

Parameters: `expected_environment, subject_type, subject_id, role_names, client_uuid, realm`.

Live verification: not performed for this clean service-interface branch.
