# Extended IDP administration — 0.6.0

Existing SDK helpers remain available. Environment/realm permissions and deployed API support are required.

### `sdk_idp_flow_list`

Read a bounded page of authentication flow metadata. Requires realm admin read permission; follow next_offset until complete. Does not change configuration.

Parameters: `expected_environment, first, max_results, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_flow_get`

Inspect authentication flow selected by flow_id. Requires corresponding realm admin permission. Backend constraints and built-in protection are preserved.

Parameters: `expected_environment, flow_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_flow_delete`

Permanently delete authentication flow selected by flow_id. Requires corresponding realm admin permission. Backend constraints and built-in protection are preserved.

Parameters: `expected_environment, flow_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_required_actions_list`

Read a bounded page of realm required action metadata. Requires realm admin read permission; follow next_offset until complete. Does not change configuration.

Parameters: `expected_environment, first, max_results, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_required_action_get`

Inspect realm required action selected by alias. Requires corresponding realm admin permission. Backend constraints and built-in protection are preserved.

Parameters: `expected_environment, alias, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_required_action_delete`

Permanently delete realm required action selected by alias. Requires corresponding realm admin permission. Backend constraints and built-in protection are preserved.

Parameters: `expected_environment, alias, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_identity_provider_list`

Read a bounded page of identity provider metadata. Requires realm admin read permission; follow next_offset until complete. Does not change configuration.

Parameters: `expected_environment, first, max_results, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_identity_provider_get`

Inspect identity provider selected by alias. Requires corresponding realm admin permission. Backend constraints and built-in protection are preserved.

Parameters: `expected_environment, alias, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_identity_provider_delete`

Permanently delete identity provider selected by alias. Requires corresponding realm admin permission. Backend constraints and built-in protection are preserved.

Parameters: `expected_environment, alias, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_component_list`

Read a bounded page of storage/provider component metadata. Requires realm admin read permission; follow next_offset until complete. Does not change configuration.

Parameters: `expected_environment, first, max_results, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_component_get`

Inspect storage/provider component selected by component_id. Requires corresponding realm admin permission. Backend constraints and built-in protection are preserved.

Parameters: `expected_environment, component_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_component_delete`

Permanently delete storage/provider component selected by component_id. Requires corresponding realm admin permission. Backend constraints and built-in protection are preserved.

Parameters: `expected_environment, component_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_flow_create`

Create a custom authentication flow. Existing aliases report conflict; built-in flows are never replaced. Requires manage-realm. Add executions separately using supported activation recipe tools.

Parameters: `expected_environment, alias, description, provider_id, top_level, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_flow_executions_list`

List execution IDs and requirements of a flow by alias, not flow UUID. Read-only, locally paginated; use the IDs with execution_update.

Parameters: `expected_environment, flow_alias, first, max_results, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_flow_execution_update`

Change only the selected execution requirement in the named flow. Requires manage-realm. Does not reorder, recreate or configure authenticator secrets.

Parameters: `expected_environment, flow_alias, execution_id, requirement, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_required_action_update`

Update selected non-secret required action fields, retaining unspecified configuration. Requires realm management permission. Optional provider_config_file supplies allowlisted OIDC settings privately.

Parameters: `expected_environment, alias, changes, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_identity_provider_update`

Update selected non-secret identity provider fields, retaining unspecified configuration. Requires realm management permission. Optional provider_config_file supplies allowlisted OIDC settings privately.

Parameters: `expected_environment, alias, changes, provider_config_file, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_sessions_list`

Read online/offline sessions by user UUID or internal client UUID. Offline user sessions require offline_client_id. Returns pagination metadata; does not authenticate or end sessions.

Parameters: `expected_environment, owner_type, owner_id, offline, offline_client_id, first, max_results, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_session_logout`

End exactly one realm session by session ID. Set offline only for an offline session. Requires manage-users; destructive session termination, not account deletion.

Parameters: `expected_environment, session_id, offline, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_user_logout`

End all sessions for the explicitly selected user UUID. Requires manage-users. Does not delete the user or credentials.

Parameters: `expected_environment, user_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_user_consents_revoke`

Revoke a user consent for a public client ID (not its internal UUID). May terminate associated sessions. Requires manage-users; no implicit bulk revocation.

Parameters: `expected_environment, user_id, client_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_events_list`

Read a bounded page of authentication or admin audit events. Date filters use backend-supported date format. Requires view-events; logging must be enabled separately. Sensitive representations are redacted.

Parameters: `expected_environment, event_kind, user_id, client_id, date_from, date_to, first, max_results, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_bruteforce_get`

Inspect brute-force lockout state for one user UUID. Requires realm/user administration permission. Does not change the realm security policy.

Parameters: `expected_environment, user_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_bruteforce_clear`

Clear brute-force lockout state for one user UUID. Requires realm/user administration permission. Does not change the realm security policy.

Parameters: `expected_environment, user_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_realms_list`

Read a locally paginated page of realms visible to the configured administrator. Follow next_offset; excludes secrets. Cross-realm visibility is permission-dependent.

Parameters: `expected_environment, first, max_results`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_realm_get`

Inspect the explicit or configured realm with secret fields redacted. Requires view-realm. Does not test SDK runtime compatibility.

Parameters: `expected_environment, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_realm_create`

Create a generic Keycloak realm (disabled by default). Requires server-level create-realm permission. This does not provision KOBIL AST services or tenants.

Parameters: `expected_environment, new_realm, display_name, enabled`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_realm_update`

Update selected realm settings, preserving unspecified properties. Requires manage-realm. Security policy changes are explicit fields; no implicit password or session reset.

Parameters: `expected_environment, changes, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_realm_delete`

Permanently delete the explicitly named realm and its users/clients. Requires server administrator permission. Never inferred from the configured default realm.

Parameters: `expected_environment, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_server_info`

Read server version and provider metadata using the configured admin connection. Requires server-info permission; does not infer AST version or operation permissions.

Parameters: `expected_environment`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_cache_clear`

Invalidate exactly one selected realm, user or key cache. Requires manage-realm and may affect authentication performance. Does not delete persisted data.

Parameters: `expected_environment, cache, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_user_federation_list`

Read linked external identities for a user UUID; locally bounded pagination. Does not retrieve provider access tokens.

Parameters: `expected_environment, user_id, first, max_results, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_user_federation_link`

Link a verified external identity to a user UUID. Requires manage-users. Caller must establish external account ownership; this does not perform an external login.

Parameters: `expected_environment, user_id, provider_alias, external_user_id, external_username, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_user_federation_unlink`

Remove one external identity link from a user. Requires manage-users. Does not delete the local or external account.

Parameters: `expected_environment, user_id, provider_alias, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_authorization_resource_list`

Read paginated authorization resources for an internal client UUID. Requires authorization-enabled client and view-clients. Distinct from OAuth client scopes.

Parameters: `expected_environment, client_id, name, first, max_results, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_authorization_resource_get`

Inspect one authorization resource by stable ID under an internal client UUID. Requires corresponding authorization administration rights.

Parameters: `expected_environment, client_id, resource_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_authorization_resource_delete`

Delete one authorization resource by stable ID under an internal client UUID. Requires corresponding authorization administration rights.

Parameters: `expected_environment, client_id, resource_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_authorization_resource_create`

Create an authorization resource under an internal client UUID. Existing-name conflicts are reported. Requires manage-authorization; no implicit permission grants.

Parameters: `expected_environment, client_id, name, fields, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_authorization_resource_update`

Update selected authorization resource metadata by stable ID, preserving scopes and other unspecified fields. Requires manage-authorization.

Parameters: `expected_environment, client_id, resource_id, changes, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_authorization_scope_list`

Read paginated authorization scopes for an internal client UUID. Requires authorization-enabled client and view-clients. Distinct from OAuth client scopes.

Parameters: `expected_environment, client_id, name, first, max_results, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_authorization_scope_get`

Inspect one authorization scope by stable ID under an internal client UUID. Requires corresponding authorization administration rights.

Parameters: `expected_environment, client_id, scope_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_authorization_scope_delete`

Delete one authorization scope by stable ID under an internal client UUID. Requires corresponding authorization administration rights.

Parameters: `expected_environment, client_id, scope_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_authorization_scope_create`

Create an authorization scope under an internal client UUID. Existing-name conflicts are reported. Requires manage-authorization; no implicit permission grants.

Parameters: `expected_environment, client_id, name, fields, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_authorization_scope_update`

Update selected authorization scope metadata by stable ID, preserving scopes and other unspecified fields. Requires manage-authorization.

Parameters: `expected_environment, client_id, scope_id, changes, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_resource_server_get`

Inspect authorization resource-server settings for an internal client UUID. Requires an authorization-enabled client and view-clients permission.

Parameters: `expected_environment, client_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_authorization_enable`

Enable authorization services on an existing confidential client by internal UUID, preserving other client settings. Requires manage-clients; backend rejects incompatible client types.

Parameters: `expected_environment, client_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_identity_provider_create`

Create an OIDC identity provider from a private mode-0600 JSON configuration reference. Disabled by default. Allowlisted OIDC configuration only; credentials never returned. Requires manage-identity-providers.

Parameters: `expected_environment, alias, provider_config_file, display_name, enabled, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_component_create`

Create an LDAP user-storage component under an explicit parent realm ID using allowlisted configuration in a private JSON file. Requires manage-realm. Other provider types are not implemented.

Parameters: `expected_environment, name, parent_id, provider_config_file, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_component_update`

Rename a component or update allowlisted LDAP configuration from a private JSON file. Requires manage-realm. Unspecified settings and credentials are preserved; other component configuration types are unsupported.

Parameters: `expected_environment, component_id, name, provider_config_file, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_identity_provider_mapper_list`

Read locally paginated identity-provider mapper metadata for an alias. Requires view-identity-providers. Does not change user attributes.

Parameters: `expected_environment, provider_alias, first, max_results, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_identity_provider_mapper_create`

Create an OIDC user-attribute importer mapper with explicit claim, attribute and sync mode. Requires manage-identity-providers. Other mapper types are not supported.

Parameters: `expected_environment, provider_alias, name, claim, user_attribute, sync_mode, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_identity_provider_mapper_update`

Rename one identity-provider mapper, preserving provider type, configuration and mapping semantics. Requires manage-identity-providers.

Parameters: `expected_environment, provider_alias, mapper_id, name, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_identity_provider_mapper_delete`

Delete one identity-provider mapper by ID. Requires manage-identity-providers. Does not delete existing imported user attributes.

Parameters: `expected_environment, provider_alias, mapper_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_policy_list`

List authorization policy metadata with server pagination. Uses internal client UUID and requires authorization read permission. Use stable IDs for changes.

Parameters: `expected_environment, client_id, name, first, max_results, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_policy_get`

Inspect authorization policy by stable ID. Requires authorization administration permission; deleting may affect access decisions.

Parameters: `expected_environment, client_id, policy_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_policy_delete`

Delete authorization policy by stable ID. Requires authorization administration permission; deleting may affect access decisions.

Parameters: `expected_environment, client_id, policy_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_policy_create`

Create typed authorization policy. Explicit membership IDs only; no scripts or arbitrary policy configuration accepted. Requires manage-authorization. Existing objects report backend conflicts.

Parameters: `expected_environment, client_id, policy_type, name, fields, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_policy_update`

Update a typed authorization policy by stable ID, preserving unspecified fields. Type must match the existing backend object; no arbitrary configuration or scripts accepted.

Parameters: `expected_environment, client_id, policy_id, policy_type, changes, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_permission_list`

List authorization permission metadata with server pagination. Uses internal client UUID and requires authorization read permission. Use stable IDs for changes.

Parameters: `expected_environment, client_id, name, first, max_results, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_permission_get`

Inspect authorization permission by stable ID. Requires authorization administration permission; deleting may affect access decisions.

Parameters: `expected_environment, client_id, permission_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_permission_delete`

Delete authorization permission by stable ID. Requires authorization administration permission; deleting may affect access decisions.

Parameters: `expected_environment, client_id, permission_id, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_permission_create`

Create typed authorization permission. Explicit membership IDs only; no scripts or arbitrary policy configuration accepted. Requires manage-authorization. Existing objects report backend conflicts.

Parameters: `expected_environment, client_id, permission_type, name, fields, realm`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_idp_permission_update`

Update a typed authorization permission by stable ID, preserving unspecified fields. Type must match the existing backend object; no arbitrary configuration or scripts accepted.

Parameters: `expected_environment, client_id, permission_id, permission_type, changes, realm`.

Live verification: not performed; no live-write coverage claimed.
