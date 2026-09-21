"""Typed extended Keycloak administration tools.

Routes follow the Keycloak Admin REST API. Backend version/permissions can still
reject operations; no tool silently falls back to another environment.
"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .idp_admin import Admin, load_private_json
from .backend import segment


class Fields(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RealmChanges(Fields):
    displayName: str | None = None
    enabled: bool | None = None
    registrationAllowed: bool | None = None
    resetPasswordAllowed: bool | None = None
    verifyEmail: bool | None = None
    loginWithEmailAllowed: bool | None = None
    duplicateEmailsAllowed: bool | None = None
    bruteForceProtected: bool | None = None
    accessTokenLifespan: int | None = Field(default=None, ge=1)
    ssoSessionIdleTimeout: int | None = Field(default=None, ge=1)


class RequiredActionChanges(Fields):
    name: str | None = None
    enabled: bool | None = None
    defaultAction: bool | None = None
    priority: int | None = Field(default=None, ge=0)


class ProviderChanges(Fields):
    displayName: str | None = None
    enabled: bool | None = None
    trustEmail: bool | None = None
    storeToken: bool | None = None
    linkOnly: bool | None = None
    firstBrokerLoginFlowAlias: str | None = None


class ResourceScope(Fields):
    id: str


class ResourceChanges(Fields):
    name: str | None = None
    displayName: str | None = None
    type: str | None = None
    uris: list[str] | None = None
    ownerManagedAccess: bool | None = None
    scopes: list[ResourceScope] | None = None


class ScopeChanges(Fields):
    name: str | None = None
    displayName: str | None = None
    iconUri: str | None = None


def _data(changes):
    result = changes.model_dump(exclude_none=True)
    if not result:
        raise ValueError("At least one changed field is required")
    return result


def _auth(client_id):
    return f"/clients/{segment(client_id)}/authz/resource-server"



class PolicyRole(Fields):
    id: str
    required: bool = False


class PolicyChanges(Fields):
    name: str | None = None
    description: str | None = None
    logic: Literal["POSITIVE", "NEGATIVE"] | None = None
    decisionStrategy: Literal["UNANIMOUS", "AFFIRMATIVE", "CONSENSUS"] | None = None
    roles: list[PolicyRole] | None = None
    users: list[str] | None = None
    clients: list[str] | None = None
    policies: list[str] | None = None


class PermissionChanges(Fields):
    name: str | None = None
    description: str | None = None
    decisionStrategy: Literal["UNANIMOUS", "AFFIRMATIVE", "CONSENSUS"] | None = None
    resources: list[str] | None = None
    scopes: list[str] | None = None
    policies: list[str] | None = None


PROVIDER_CONFIG_FIELDS = {
    "authorizationUrl", "tokenUrl", "userInfoUrl", "logoutUrl", "issuer",
    "clientId", "clientSecret", "defaultScope", "validateSignature", "useJwksUrl",
    "jwksUrl", "syncMode", "pkceEnabled", "pkceMethod", "clientAuthMethod",
}
LDAP_CONFIG_FIELDS = {
    "connectionUrl", "usersDn", "bindDn", "bindCredential", "vendor", "enabled",
    "usernameLDAPAttribute", "rdnLDAPAttribute", "uuidLDAPAttribute", "userObjectClasses",
    "editMode", "importEnabled", "syncRegistrations", "authType", "searchScope",
    "useTruststoreSpi", "connectionPooling", "pagination", "batchSizeForSync",
    "fullSyncPeriod", "changedSyncPeriod", "startTls",
}


def _private_config(path, allowed, lists=False):
    config = load_private_json(path)
    if not isinstance(config, dict) or set(config) - allowed:
        raise ValueError("Unsupported provider configuration fields")
    for value in config.values():
        if lists:
            if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
                raise ValueError("Component configuration requires arrays of strings")
        elif not isinstance(value, str):
            raise ValueError("Identity provider configuration requires string values")
    return config


def _policy_data(policy_type, changes):
    data = _data(changes)
    membership = {"user": "users", "client": "clients", "aggregate": "policies", "role": "roles"}[policy_type]
    if any(key in data for key in {"users", "clients", "policies", "roles"} - {membership}):
        raise ValueError("Membership fields must match the policy type")
    return data


def register(mcp):
    """Register independently discoverable, operation-specific MCP tools."""

    @mcp.tool()
    def sdk_idp_flow_list(expected_environment: str, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read a bounded page of authentication flow metadata. Requires realm admin read permission; follow next_offset until complete. Does not change configuration."""
        with Admin(expected_environment, realm=realm) as api:
            return api.page("/authentication/flows", first=first, max_results=max_results, paginated=False)

    @mcp.tool()
    def sdk_idp_flow_get(expected_environment: str, flow_id: str, realm: str | None = None) -> dict:
        """Inspect authentication flow selected by flow_id. Requires corresponding realm admin permission. Backend constraints and built-in protection are preserved."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("GET", f"/authentication/flows/{segment(flow_id)}")

    @mcp.tool()
    def sdk_idp_flow_delete(expected_environment: str, flow_id: str, realm: str | None = None) -> dict:
        """Permanently delete authentication flow selected by flow_id. Requires corresponding realm admin permission. Backend constraints and built-in protection are preserved."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("DELETE", f"/authentication/flows/{segment(flow_id)}")

    @mcp.tool()
    def sdk_idp_required_actions_list(expected_environment: str, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read a bounded page of realm required action metadata. Requires realm admin read permission; follow next_offset until complete. Does not change configuration."""
        with Admin(expected_environment, realm=realm) as api:
            return api.page("/authentication/required-actions", first=first, max_results=max_results, paginated=False)

    @mcp.tool()
    def sdk_idp_required_action_get(expected_environment: str, alias: str, realm: str | None = None) -> dict:
        """Inspect realm required action selected by alias. Requires corresponding realm admin permission. Backend constraints and built-in protection are preserved."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("GET", f"/authentication/required-actions/{segment(alias)}")

    @mcp.tool()
    def sdk_idp_required_action_delete(expected_environment: str, alias: str, realm: str | None = None) -> dict:
        """Permanently delete realm required action selected by alias. Requires corresponding realm admin permission. Backend constraints and built-in protection are preserved."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("DELETE", f"/authentication/required-actions/{segment(alias)}")

    @mcp.tool()
    def sdk_idp_identity_provider_list(expected_environment: str, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read a bounded page of identity provider metadata. Requires realm admin read permission; follow next_offset until complete. Does not change configuration."""
        with Admin(expected_environment, realm=realm) as api:
            return api.page("/identity-provider/instances", first=first, max_results=max_results, paginated=False)

    @mcp.tool()
    def sdk_idp_identity_provider_get(expected_environment: str, alias: str, realm: str | None = None) -> dict:
        """Inspect identity provider selected by alias. Requires corresponding realm admin permission. Backend constraints and built-in protection are preserved."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("GET", f"/identity-provider/instances/{segment(alias)}")

    @mcp.tool()
    def sdk_idp_identity_provider_delete(expected_environment: str, alias: str, realm: str | None = None) -> dict:
        """Permanently delete identity provider selected by alias. Requires corresponding realm admin permission. Backend constraints and built-in protection are preserved."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("DELETE", f"/identity-provider/instances/{segment(alias)}")

    @mcp.tool()
    def sdk_idp_component_list(expected_environment: str, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read a bounded page of storage/provider component metadata. Requires realm admin read permission; follow next_offset until complete. Does not change configuration."""
        with Admin(expected_environment, realm=realm) as api:
            return api.page("/components", first=first, max_results=max_results, paginated=False)

    @mcp.tool()
    def sdk_idp_component_get(expected_environment: str, component_id: str, realm: str | None = None) -> dict:
        """Inspect storage/provider component selected by component_id. Requires corresponding realm admin permission. Backend constraints and built-in protection are preserved."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("GET", f"/components/{segment(component_id)}")

    @mcp.tool()
    def sdk_idp_component_delete(expected_environment: str, component_id: str, realm: str | None = None) -> dict:
        """Permanently delete storage/provider component selected by component_id. Requires corresponding realm admin permission. Backend constraints and built-in protection are preserved."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("DELETE", f"/components/{segment(component_id)}")

    @mcp.tool()
    def sdk_idp_flow_create(expected_environment: str, alias: str, description: str = "", provider_id: Literal["basic-flow", "client-flow"] = "basic-flow", top_level: bool = True, realm: str | None = None) -> dict:
        """Create a custom authentication flow. Existing aliases report conflict; built-in flows are never replaced. Requires manage-realm. Add executions separately using supported activation recipe tools."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("POST", "/authentication/flows", body={"alias": alias, "description": description, "providerId": provider_id, "topLevel": top_level, "builtIn": False})

    @mcp.tool()
    def sdk_idp_flow_executions_list(expected_environment: str, flow_alias: str, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """List execution IDs and requirements of a flow by alias, not flow UUID. Read-only, locally paginated; use the IDs with execution_update."""
        with Admin(expected_environment, realm=realm) as api:
            return api.page(f"/authentication/flows/{segment(flow_alias)}/executions", first=first, max_results=max_results, paginated=False)

    @mcp.tool()
    def sdk_idp_flow_execution_update(expected_environment: str, flow_alias: str, execution_id: str, requirement: Literal["REQUIRED", "ALTERNATIVE", "DISABLED", "CONDITIONAL"], realm: str | None = None) -> dict:
        """Change only the selected execution requirement in the named flow. Requires manage-realm. Does not reorder, recreate or configure authenticator secrets."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("PUT", f"/authentication/flows/{segment(flow_alias)}/executions", body={"id": execution_id, "requirement": requirement})

    @mcp.tool()
    def sdk_idp_required_action_update(expected_environment: str, alias: str, changes: RequiredActionChanges, realm: str | None = None) -> dict:
        """Update selected non-secret required action fields, retaining unspecified configuration. Requires realm management permission. Optional provider_config_file supplies allowlisted OIDC settings privately."""
        with Admin(expected_environment, realm=realm) as api:
            return api.update(f"/authentication/required-actions/{segment(alias)}", _data(changes), set(RequiredActionChanges.model_fields))

    @mcp.tool()
    def sdk_idp_identity_provider_update(expected_environment: str, alias: str, changes: ProviderChanges, provider_config_file: str | None = None, realm: str | None = None) -> dict:
        """Update selected non-secret identity provider fields, retaining unspecified configuration. Requires realm management permission. Optional provider_config_file supplies allowlisted OIDC settings privately."""
        with Admin(expected_environment, realm=realm) as api:
            data = changes.model_dump(exclude_none=True)
            if provider_config_file:
                data["config"] = _private_config(provider_config_file, PROVIDER_CONFIG_FIELDS)
            if not data:
                raise ValueError("At least one changed field is required")
            return api.update(f"/identity-provider/instances/{segment(alias)}", data, set(ProviderChanges.model_fields) | {"config"})

    @mcp.tool()
    def sdk_idp_sessions_list(expected_environment: str, owner_type: Literal["user", "client"], owner_id: str, offline: bool = False, offline_client_id: str | None = None, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read online/offline sessions by user UUID or internal client UUID. Offline user sessions require offline_client_id. Returns pagination metadata; does not authenticate or end sessions."""
        if owner_type == "user":
            if offline and not offline_client_id:
                raise ValueError("offline_client_id is required for offline user sessions")
            suffix = f"offline-sessions/{segment(offline_client_id)}" if offline else "sessions"
            path = f"/users/{segment(owner_id)}/{suffix}"
            paginated = False
        elif owner_type == "client":
            path = f"/clients/{segment(owner_id)}/" + ("offline-sessions" if offline else "user-sessions")
            paginated = True
        else:
            raise ValueError("owner_type must be user or client")
        with Admin(expected_environment, realm=realm) as api:
            return api.page(path, first=first, max_results=max_results, paginated=paginated)

    @mcp.tool()
    def sdk_idp_session_logout(expected_environment: str, session_id: str, offline: bool = False, realm: str | None = None) -> dict:
        """End exactly one realm session by session ID. Set offline only for an offline session. Requires manage-users; destructive session termination, not account deletion."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("DELETE", f"/sessions/{segment(session_id)}", params={"isOffline": str(offline).lower()})

    @mcp.tool()
    def sdk_idp_user_logout(expected_environment: str, user_id: str, realm: str | None = None) -> dict:
        """End all sessions for the explicitly selected user UUID. Requires manage-users. Does not delete the user or credentials."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("POST", f"/users/{segment(user_id)}/logout")

    @mcp.tool()
    def sdk_idp_user_consents_revoke(expected_environment: str, user_id: str, client_id: str, realm: str | None = None) -> dict:
        """Revoke a user consent for a public client ID (not its internal UUID). May terminate associated sessions. Requires manage-users; no implicit bulk revocation."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("DELETE", f"/users/{segment(user_id)}/consents/{segment(client_id)}")

    @mcp.tool()
    def sdk_idp_events_list(expected_environment: str, event_kind: Literal["authentication", "admin"] = "authentication", user_id: str | None = None, client_id: str | None = None, date_from: str | None = None, date_to: str | None = None, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read a bounded page of authentication or admin audit events. Date filters use backend-supported date format. Requires view-events; logging must be enabled separately. Sensitive representations are redacted."""
        params = {"dateFrom": date_from, "dateTo": date_to}
        if event_kind == "admin":
            params.update({"authUser": user_id, "authClient": client_id})
            path = "/admin-events"
        else:
            params.update({"user": user_id, "client": client_id})
            path = "/events"
        with Admin(expected_environment, realm=realm) as api:
            return api.page(path, first=first, max_results=max_results, params={k:v for k,v in params.items() if v is not None})

    @mcp.tool()
    def sdk_idp_bruteforce_get(expected_environment: str, user_id: str, realm: str | None = None) -> dict:
        """Inspect brute-force lockout state for one user UUID. Requires realm/user administration permission. Does not change the realm security policy."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("GET", f"/attack-detection/brute-force/users/{segment(user_id)}")

    @mcp.tool()
    def sdk_idp_bruteforce_clear(expected_environment: str, user_id: str, realm: str | None = None) -> dict:
        """Clear brute-force lockout state for one user UUID. Requires realm/user administration permission. Does not change the realm security policy."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("DELETE", f"/attack-detection/brute-force/users/{segment(user_id)}")

    @mcp.tool()
    def sdk_idp_realms_list(expected_environment: str, first: int = 0, max_results: int = 50) -> dict:
        """Read a locally paginated page of realms visible to the configured administrator. Follow next_offset; excludes secrets. Cross-realm visibility is permission-dependent."""
        if type(first) is not int or first < 0 or type(max_results) is not int or not 1 <= max_results <= 200:
            raise ValueError("first must be nonnegative; max_results must be 1..200")
        with Admin(expected_environment) as api:
            realms = api.call_global("GET", "/admin/realms")
            if not isinstance(realms, list):
                raise ValueError("Expected a realm collection")
            more = len(realms) > first + max_results
            return {"items": realms[first:first + max_results], "first": first,
                    "next_offset": first + max_results if more else None,
                    "complete": not more, "environment": expected_environment}

    @mcp.tool()
    def sdk_idp_realm_get(expected_environment: str, realm: str | None = None) -> dict:
        """Inspect the explicit or configured realm with secret fields redacted. Requires view-realm. Does not test SDK runtime compatibility."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("GET", "")

    @mcp.tool()
    def sdk_idp_realm_create(expected_environment: str, new_realm: str, display_name: str | None = None, enabled: bool = False) -> dict:
        """Create a generic Keycloak realm (disabled by default). Requires server-level create-realm permission. This does not provision KOBIL AST services or tenants."""
        with Admin(expected_environment) as api:
            return api.call_global("POST", "/admin/realms", body={"realm": new_realm, "displayName": display_name or new_realm, "enabled": enabled})

    @mcp.tool()
    def sdk_idp_realm_update(expected_environment: str, changes: RealmChanges, realm: str | None = None) -> dict:
        """Update selected realm settings, preserving unspecified properties. Requires manage-realm. Security policy changes are explicit fields; no implicit password or session reset."""
        with Admin(expected_environment, realm=realm) as api:
            return api.update("", _data(changes), set(RealmChanges.model_fields))

    @mcp.tool()
    def sdk_idp_realm_delete(expected_environment: str, realm: str) -> dict:
        """Permanently delete the explicitly named realm and its users/clients. Requires server administrator permission. Never inferred from the configured default realm."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("DELETE", "")

    @mcp.tool()
    def sdk_idp_server_info(expected_environment: str) -> dict:
        """Read server version and provider metadata using the configured admin connection. Requires server-info permission; does not infer AST version or operation permissions."""
        with Admin(expected_environment) as api:
            return api.call_global("GET", "/admin/serverinfo")

    @mcp.tool()
    def sdk_idp_cache_clear(expected_environment: str, cache: Literal["realm", "user", "keys"], realm: str | None = None) -> dict:
        """Invalidate exactly one selected realm, user or key cache. Requires manage-realm and may affect authentication performance. Does not delete persisted data."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("POST", {"realm": "/clear-realm-cache", "user": "/clear-user-cache", "keys": "/clear-keys-cache"}[cache])

    @mcp.tool()
    def sdk_idp_user_federation_list(expected_environment: str, user_id: str, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read linked external identities for a user UUID; locally bounded pagination. Does not retrieve provider access tokens."""
        with Admin(expected_environment, realm=realm) as api:
            return api.page(f"/users/{segment(user_id)}/federated-identity", first=first, max_results=max_results, paginated=False)

    @mcp.tool()
    def sdk_idp_user_federation_link(expected_environment: str, user_id: str, provider_alias: str, external_user_id: str, external_username: str, realm: str | None = None) -> dict:
        """Link a verified external identity to a user UUID. Requires manage-users. Caller must establish external account ownership; this does not perform an external login."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("POST", f"/users/{segment(user_id)}/federated-identity/{segment(provider_alias)}", body={"identityProvider": provider_alias, "userId": external_user_id, "userName": external_username})

    @mcp.tool()
    def sdk_idp_user_federation_unlink(expected_environment: str, user_id: str, provider_alias: str, realm: str | None = None) -> dict:
        """Remove one external identity link from a user. Requires manage-users. Does not delete the local or external account."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("DELETE", f"/users/{segment(user_id)}/federated-identity/{segment(provider_alias)}")

    @mcp.tool()
    def sdk_idp_authorization_resource_list(expected_environment: str, client_id: str, name: str | None = None, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read paginated authorization resources for an internal client UUID. Requires authorization-enabled client and view-clients. Distinct from OAuth client scopes."""
        with Admin(expected_environment, realm=realm) as api:
            return api.page(_auth(client_id) + "/resource", first=first, max_results=max_results, params={"name": name} if name else None)

    @mcp.tool()
    def sdk_idp_authorization_resource_get(expected_environment: str, client_id: str, resource_id: str, realm: str | None = None) -> dict:
        """Inspect one authorization resource by stable ID under an internal client UUID. Requires corresponding authorization administration rights."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("GET", _auth(client_id) + f"/resource/{segment(resource_id)}")

    @mcp.tool()
    def sdk_idp_authorization_resource_delete(expected_environment: str, client_id: str, resource_id: str, realm: str | None = None) -> dict:
        """Delete one authorization resource by stable ID under an internal client UUID. Requires corresponding authorization administration rights."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("DELETE", _auth(client_id) + f"/resource/{segment(resource_id)}")

    @mcp.tool()
    def sdk_idp_authorization_resource_create(expected_environment: str, client_id: str, name: str, fields: ResourceChanges | None = None, realm: str | None = None) -> dict:
        """Create an authorization resource under an internal client UUID. Existing-name conflicts are reported. Requires manage-authorization; no implicit permission grants."""
        with Admin(expected_environment, realm=realm) as api:
            body = fields.model_dump(exclude_none=True) if fields else {}
            body["name"] = name
            return api.call("POST", _auth(client_id) + "/resource", body=body)

    @mcp.tool()
    def sdk_idp_authorization_resource_update(expected_environment: str, client_id: str, resource_id: str, changes: ResourceChanges, realm: str | None = None) -> dict:
        """Update selected authorization resource metadata by stable ID, preserving scopes and other unspecified fields. Requires manage-authorization."""
        with Admin(expected_environment, realm=realm) as api:
            return api.update(_auth(client_id) + f"/resource/{segment(resource_id)}", _data(changes), set(ResourceChanges.model_fields))

    @mcp.tool()
    def sdk_idp_authorization_scope_list(expected_environment: str, client_id: str, name: str | None = None, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read paginated authorization scopes for an internal client UUID. Requires authorization-enabled client and view-clients. Distinct from OAuth client scopes."""
        with Admin(expected_environment, realm=realm) as api:
            return api.page(_auth(client_id) + "/scope", first=first, max_results=max_results, params={"name": name} if name else None)

    @mcp.tool()
    def sdk_idp_authorization_scope_get(expected_environment: str, client_id: str, scope_id: str, realm: str | None = None) -> dict:
        """Inspect one authorization scope by stable ID under an internal client UUID. Requires corresponding authorization administration rights."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("GET", _auth(client_id) + f"/scope/{segment(scope_id)}")

    @mcp.tool()
    def sdk_idp_authorization_scope_delete(expected_environment: str, client_id: str, scope_id: str, realm: str | None = None) -> dict:
        """Delete one authorization scope by stable ID under an internal client UUID. Requires corresponding authorization administration rights."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("DELETE", _auth(client_id) + f"/scope/{segment(scope_id)}")

    @mcp.tool()
    def sdk_idp_authorization_scope_create(expected_environment: str, client_id: str, name: str, fields: ScopeChanges | None = None, realm: str | None = None) -> dict:
        """Create an authorization scope under an internal client UUID. Existing-name conflicts are reported. Requires manage-authorization; no implicit permission grants."""
        with Admin(expected_environment, realm=realm) as api:
            body = fields.model_dump(exclude_none=True) if fields else {}
            body["name"] = name
            return api.call("POST", _auth(client_id) + "/scope", body=body)

    @mcp.tool()
    def sdk_idp_authorization_scope_update(expected_environment: str, client_id: str, scope_id: str, changes: ScopeChanges, realm: str | None = None) -> dict:
        """Update selected authorization scope metadata by stable ID, preserving scopes and other unspecified fields. Requires manage-authorization."""
        with Admin(expected_environment, realm=realm) as api:
            return api.update(_auth(client_id) + f"/scope/{segment(scope_id)}", _data(changes), set(ScopeChanges.model_fields))

    @mcp.tool()
    def sdk_idp_resource_server_get(expected_environment: str, client_id: str, realm: str | None = None) -> dict:
        """Inspect authorization resource-server settings for an internal client UUID. Requires an authorization-enabled client and view-clients permission."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("GET", _auth(client_id))

    @mcp.tool()
    def sdk_idp_authorization_enable(expected_environment: str, client_id: str, realm: str | None = None) -> dict:
        """Enable authorization services on an existing confidential client by internal UUID, preserving other client settings. Requires manage-clients; backend rejects incompatible client types."""
        with Admin(expected_environment, realm=realm) as api:
            return api.update(f"/clients/{segment(client_id)}", {"authorizationServicesEnabled": True}, {"authorizationServicesEnabled"})

    @mcp.tool()
    def sdk_idp_identity_provider_create(expected_environment: str, alias: str, provider_config_file: str, display_name: str | None = None, enabled: bool = False, realm: str | None = None) -> dict:
        """Create an OIDC identity provider from a private mode-0600 JSON configuration reference. Disabled by default. Allowlisted OIDC configuration only; credentials never returned. Requires manage-identity-providers."""
        config = _private_config(provider_config_file, PROVIDER_CONFIG_FIELDS)
        with Admin(expected_environment, realm=realm) as api:
            return api.call("POST", "/identity-provider/instances", body={"alias": alias, "providerId": "oidc", "displayName": display_name or alias, "enabled": enabled, "config": config})

    @mcp.tool()
    def sdk_idp_component_create(expected_environment: str, name: str, parent_id: str, provider_config_file: str, realm: str | None = None) -> dict:
        """Create an LDAP user-storage component under an explicit parent realm ID using allowlisted configuration in a private JSON file. Requires manage-realm. Other provider types are not implemented."""
        config = _private_config(provider_config_file, LDAP_CONFIG_FIELDS, lists=True)
        with Admin(expected_environment, realm=realm) as api:
            return api.call("POST", "/components", body={"name": name, "parentId": parent_id, "providerId": "ldap", "providerType": "org.keycloak.storage.UserStorageProvider", "config": config})

    @mcp.tool()
    def sdk_idp_component_update(expected_environment: str, component_id: str, name: str | None = None, provider_config_file: str | None = None, realm: str | None = None) -> dict:
        """Rename a component or update allowlisted LDAP configuration from a private JSON file. Requires manage-realm. Unspecified settings and credentials are preserved; other component configuration types are unsupported."""
        data = {"name": name} if name is not None else {}
        if provider_config_file:
            data["config"] = _private_config(provider_config_file, LDAP_CONFIG_FIELDS, lists=True)
        if not data:
            raise ValueError("At least one changed field is required")
        with Admin(expected_environment, realm=realm) as api:
            path = f"/components/{segment(component_id)}"
            if provider_config_file:
                current = api.call("GET", path)
                if not isinstance(current, dict) or current.get("providerId") != "ldap" or current.get("providerType") != "org.keycloak.storage.UserStorageProvider":
                    raise ValueError("Private configuration update requires an LDAP user storage component")
            return api.update(path, data, {"name", "config"})

    @mcp.tool()
    def sdk_idp_identity_provider_mapper_list(expected_environment: str, provider_alias: str, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read locally paginated identity-provider mapper metadata for an alias. Requires view-identity-providers. Does not change user attributes."""
        with Admin(expected_environment, realm=realm) as api:
            return api.page(f"/identity-provider/instances/{segment(provider_alias)}/mappers", first=first, max_results=max_results, paginated=False)

    @mcp.tool()
    def sdk_idp_identity_provider_mapper_create(expected_environment: str, provider_alias: str, name: str, claim: str, user_attribute: str, sync_mode: Literal["IMPORT", "FORCE", "INHERIT"] = "INHERIT", realm: str | None = None) -> dict:
        """Create an OIDC user-attribute importer mapper with explicit claim, attribute and sync mode. Requires manage-identity-providers. Other mapper types are not supported."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("POST", f"/identity-provider/instances/{segment(provider_alias)}/mappers", body={"name": name, "identityProviderAlias": provider_alias, "identityProviderMapper": "oidc-user-attribute-idp-mapper", "config": {"claim": claim, "user.attribute": user_attribute, "syncMode": sync_mode}})

    @mcp.tool()
    def sdk_idp_identity_provider_mapper_update(expected_environment: str, provider_alias: str, mapper_id: str, name: str, realm: str | None = None) -> dict:
        """Rename one identity-provider mapper, preserving provider type, configuration and mapping semantics. Requires manage-identity-providers."""
        with Admin(expected_environment, realm=realm) as api:
            return api.update(f"/identity-provider/instances/{segment(provider_alias)}/mappers/{segment(mapper_id)}", {"name": name}, {"name"})

    @mcp.tool()
    def sdk_idp_identity_provider_mapper_delete(expected_environment: str, provider_alias: str, mapper_id: str, realm: str | None = None) -> dict:
        """Delete one identity-provider mapper by ID. Requires manage-identity-providers. Does not delete existing imported user attributes."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("DELETE", f"/identity-provider/instances/{segment(provider_alias)}/mappers/{segment(mapper_id)}")

    @mcp.tool()
    def sdk_idp_policy_list(expected_environment: str, client_id: str, name: str | None = None, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """List authorization policy metadata with server pagination. Uses internal client UUID and requires authorization read permission. Use stable IDs for changes."""
        with Admin(expected_environment, realm=realm) as api:
            return api.page(_auth(client_id) + "/policy", first=first, max_results=max_results, params={"name": name} if name else None)

    @mcp.tool()
    def sdk_idp_policy_get(expected_environment: str, client_id: str, policy_id: str, realm: str | None = None) -> dict:
        """Inspect authorization policy by stable ID. Requires authorization administration permission; deleting may affect access decisions."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("GET", _auth(client_id) + f"/policy/{segment(policy_id)}")

    @mcp.tool()
    def sdk_idp_policy_delete(expected_environment: str, client_id: str, policy_id: str, realm: str | None = None) -> dict:
        """Delete authorization policy by stable ID. Requires authorization administration permission; deleting may affect access decisions."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("DELETE", _auth(client_id) + f"/policy/{segment(policy_id)}")

    @mcp.tool()
    def sdk_idp_policy_create(expected_environment: str, client_id: str, policy_type: Literal["user", "client", "aggregate", "role"], name: str, fields: PolicyChanges, realm: str | None = None) -> dict:
        """Create typed authorization policy. Explicit membership IDs only; no scripts or arbitrary policy configuration accepted. Requires manage-authorization. Existing objects report backend conflicts."""
        data = _policy_data(policy_type, fields)
        data.update({"name": name, "type": policy_type})
        with Admin(expected_environment, realm=realm) as api:
            return api.call("POST", _auth(client_id) + f"/policy/{segment(policy_type)}", body=data)

    @mcp.tool()
    def sdk_idp_policy_update(expected_environment: str, client_id: str, policy_id: str, policy_type: Literal["user", "client", "aggregate", "role"], changes: PolicyChanges, realm: str | None = None) -> dict:
        """Update a typed authorization policy by stable ID, preserving unspecified fields. Type must match the existing backend object; no arbitrary configuration or scripts accepted."""
        data = _policy_data(policy_type, changes)
        with Admin(expected_environment, realm=realm) as api:
            path = _auth(client_id) + f"/policy/{segment(policy_type)}/{segment(policy_id)}"
            current = api.call("GET", path)
            if not isinstance(current, dict) or current.get("type") != policy_type:
                raise ValueError("Existing policy type does not match requested type")
            return api.update(path, data, set(PolicyChanges.model_fields))

    @mcp.tool()
    def sdk_idp_permission_list(expected_environment: str, client_id: str, name: str | None = None, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """List authorization permission metadata with server pagination. Uses internal client UUID and requires authorization read permission. Use stable IDs for changes."""
        with Admin(expected_environment, realm=realm) as api:
            return api.page(_auth(client_id) + "/permission", first=first, max_results=max_results, params={"name": name} if name else None)

    @mcp.tool()
    def sdk_idp_permission_get(expected_environment: str, client_id: str, permission_id: str, realm: str | None = None) -> dict:
        """Inspect authorization permission by stable ID. Requires authorization administration permission; deleting may affect access decisions."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("GET", _auth(client_id) + f"/permission/{segment(permission_id)}")

    @mcp.tool()
    def sdk_idp_permission_delete(expected_environment: str, client_id: str, permission_id: str, realm: str | None = None) -> dict:
        """Delete authorization permission by stable ID. Requires authorization administration permission; deleting may affect access decisions."""
        with Admin(expected_environment, realm=realm) as api:
            return api.call("DELETE", _auth(client_id) + f"/permission/{segment(permission_id)}")

    @mcp.tool()
    def sdk_idp_permission_create(expected_environment: str, client_id: str, permission_type: Literal["resource", "scope"], name: str, fields: PermissionChanges, realm: str | None = None) -> dict:
        """Create typed authorization permission. Explicit membership IDs only; no scripts or arbitrary policy configuration accepted. Requires manage-authorization. Existing objects report backend conflicts."""
        data = _data(fields)
        data.update({"name": name, "type": permission_type})
        with Admin(expected_environment, realm=realm) as api:
            return api.call("POST", _auth(client_id) + f"/permission/{segment(permission_type)}", body=data)

    @mcp.tool()
    def sdk_idp_permission_update(expected_environment: str, client_id: str, permission_id: str, permission_type: Literal["resource", "scope"], changes: PermissionChanges, realm: str | None = None) -> dict:
        """Update a typed authorization permission by stable ID, preserving unspecified fields. Type must match the existing backend object; no arbitrary configuration or scripts accepted."""
        data = _data(changes)
        with Admin(expected_environment, realm=realm) as api:
            path = _auth(client_id) + f"/permission/{segment(permission_type)}/{segment(permission_id)}"
            current = api.call("GET", path)
            if not isinstance(current, dict) or current.get("type") != permission_type:
                raise ValueError("Existing permission type does not match requested type")
            return api.update(path, data, set(PermissionChanges.model_fields))
