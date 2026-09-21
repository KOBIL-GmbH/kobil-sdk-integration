"""Typed Keycloak admin clients, scopes, mappers, roles and groups.

Endpoint contract: https://www.keycloak.org/docs-api/latest/rest-api/index.html
All client_uuid arguments are internal IDs, never public clientId names.
"""
from typing import Literal
from .backend import segment
from .idp_admin import Admin


def _role_path(client_uuid=None):
    return f"/clients/{segment(client_uuid)}/roles" if client_uuid else "/roles"


def _mapper_path(owner_type, owner_id):
    if owner_type not in ("client", "scope"):
        raise ValueError("owner_type must be client or scope")
    collection = "clients" if owner_type == "client" else "client-scopes"
    return f"/{collection}/{segment(owner_id)}/protocol-mappers/models"


def _assignment_path(subject_type, subject_id, client_uuid=None):
    if subject_type not in ("user", "group"):
        raise ValueError("subject_type must be user or group")
    base = f"/{subject_type}s/{segment(subject_id)}/role-mappings"
    return base + (f"/clients/{segment(client_uuid)}" if client_uuid else "/realm")


def _roles(api, role_names, client_uuid=None):
    if not role_names or len(role_names) > 100:
        raise ValueError("Provide between 1 and 100 role names")
    return [api.call("GET", _role_path(client_uuid) + "/" + segment(name)) for name in dict.fromkeys(role_names)]


def _change(api, method, path, body=None):
    result = api.call(method, path, body=body)
    return {"changed": True, "resource": path, "result": result}


def register(mcp):

    @mcp.tool()
    def sdk_idp_client_list(expected_environment: str, client_id: str | None = None, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read a page of IDP clients. client_id filters the public clientId; returned id is the internal UUID used by client tools. Follow next_offset to continue. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return api.page("/clients", first, max_results, params={"clientId": client_id} if client_id else None)

    @mcp.tool()
    def sdk_idp_client_get(expected_environment: str, client_uuid: str, realm: str | None = None) -> dict:
        """Read one client by internal UUID; credential fields are redacted. Use client_list to resolve a public clientId. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return api.call("GET", f"/clients/{segment(client_uuid)}")

    @mcp.tool()
    def sdk_idp_client_create(expected_environment: str, client_id: str, name: str | None = None, description: str | None = None, enabled: bool | None = None, public_client: bool | None = None, standard_flow_enabled: bool | None = None, direct_access_grants_enabled: bool | None = None, service_accounts_enabled: bool | None = None, redirect_uris: list[str] | None = None, web_origins: list[str] | None = None, realm: str | None = None) -> dict:
        """Create an OpenID Connect client with an explicit public clientId. Conflicts are not silently reused. Does not export its secret. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            body = {k: v for k, v in {"name": name, "description": description, "enabled": enabled, "publicClient": public_client, "standardFlowEnabled": standard_flow_enabled, "directAccessGrantsEnabled": direct_access_grants_enabled, "serviceAccountsEnabled": service_accounts_enabled, "redirectUris": redirect_uris, "webOrigins": web_origins}.items() if v is not None}
            body.update({"clientId": client_id, "protocol": "openid-connect"})
            return _change(api, "POST", "/clients", body)

    @mcp.tool()
    def sdk_idp_client_update(expected_environment: str, client_uuid: str, name: str | None = None, description: str | None = None, enabled: bool | None = None, public_client: bool | None = None, standard_flow_enabled: bool | None = None, direct_access_grants_enabled: bool | None = None, service_accounts_enabled: bool | None = None, redirect_uris: list[str] | None = None, web_origins: list[str] | None = None, realm: str | None = None) -> dict:
        """Update selected client fields by internal UUID, preserving omitted configuration. Empty URI/origin lists explicitly clear those lists. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            changes = {"name": name, "description": description, "enabled": enabled, "publicClient": public_client, "standardFlowEnabled": standard_flow_enabled, "directAccessGrantsEnabled": direct_access_grants_enabled, "serviceAccountsEnabled": service_accounts_enabled, "redirectUris": redirect_uris, "webOrigins": web_origins}
            return api.update(f"/clients/{segment(client_uuid)}", {k: v for k, v in changes.items() if v is not None}, set(changes))

    @mcp.tool()
    def sdk_idp_client_delete(expected_environment: str, client_uuid: str, realm: str | None = None) -> dict:
        """Delete one client by internal UUID, including its configuration. This is destructive. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return _change(api, "DELETE", f"/clients/{segment(client_uuid)}")

    @mcp.tool()
    def sdk_idp_client_service_account_get(expected_environment: str, client_uuid: str, realm: str | None = None) -> dict:
        """Read the service-account user for an internal client UUID. Service accounts must be enabled on that client. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return api.call("GET", f"/clients/{segment(client_uuid)}/service-account-user")

    @mcp.tool()
    def sdk_idp_scope_list(expected_environment: str, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read a locally paginated page of realm client scopes; these are OAuth client scopes, not authorization resource scopes. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return api.page("/client-scopes", first, max_results, paginated=False)

    @mcp.tool()
    def sdk_idp_scope_get(expected_environment: str, scope_id: str, realm: str | None = None) -> dict:
        """Read a realm client scope by ID. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return api.call("GET", f"/client-scopes/{segment(scope_id)}")

    @mcp.tool()
    def sdk_idp_scope_create(expected_environment: str, name: str, description: str = "", realm: str | None = None) -> dict:
        """Create an OpenID Connect realm client scope. Assign it to a client separately with client_scope_assign. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return _change(api, "POST", "/client-scopes", {"name": name, "description": description, "protocol": "openid-connect"})

    @mcp.tool()
    def sdk_idp_scope_update(expected_environment: str, scope_id: str, name: str | None = None, description: str | None = None, realm: str | None = None) -> dict:
        """Update selected client-scope metadata, preserving mappers and unrelated attributes. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return api.update(f"/client-scopes/{segment(scope_id)}", {k: v for k, v in {"name": name, "description": description}.items() if v is not None}, {"name", "description"})

    @mcp.tool()
    def sdk_idp_scope_delete(expected_environment: str, scope_id: str, realm: str | None = None) -> dict:
        """Delete a realm client scope by ID; assignments are affected. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return _change(api, "DELETE", f"/client-scopes/{segment(scope_id)}")

    @mcp.tool()
    def sdk_idp_client_scopes_get(expected_environment: str, client_uuid: str, scope_type: Literal["default", "optional"] = "default", first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read default or optional scope bindings for an internal client UUID. Pagination is local. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            if scope_type not in ("default", "optional"):
                raise ValueError("scope_type must be default or optional")
            return api.page(f"/clients/{segment(client_uuid)}/{scope_type}-client-scopes", first, max_results, paginated=False)

    @mcp.tool()
    def sdk_idp_client_scope_assign(expected_environment: str, client_uuid: str, scope_id: str, scope_type: Literal["default", "optional"] = "default", realm: str | None = None) -> dict:
        """Bind an existing scope as default or optional to a client; idempotent PUT does not create a scope. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            if scope_type not in ("default", "optional"):
                raise ValueError("scope_type must be default or optional")
            return _change(api, "PUT", f"/clients/{segment(client_uuid)}/{scope_type}-client-scopes/{segment(scope_id)}")

    @mcp.tool()
    def sdk_idp_client_scope_remove(expected_environment: str, client_uuid: str, scope_id: str, scope_type: Literal["default", "optional"] = "default", realm: str | None = None) -> dict:
        """Remove only the selected scope binding, retaining the scope itself. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            if scope_type not in ("default", "optional"):
                raise ValueError("scope_type must be default or optional")
            return _change(api, "DELETE", f"/clients/{segment(client_uuid)}/{scope_type}-client-scopes/{segment(scope_id)}")

    @mcp.tool()
    def sdk_idp_mapper_list(expected_environment: str, owner_type: Literal["client", "scope"], owner_id: str, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read protocol mappers on an internal client UUID or client-scope ID. Pagination is local. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return api.page(_mapper_path(owner_type, owner_id), first, max_results, paginated=False)

    @mcp.tool()
    def sdk_idp_mapper_create(expected_environment: str, owner_type: Literal["client", "scope"], owner_id: str, name: str, user_attribute: str, claim_name: str, json_type: Literal["String", "boolean", "long", "int", "JSON"] = "String", in_access_token: bool = True, in_id_token: bool = True, in_userinfo: bool = True, multivalued: bool = False, realm: str | None = None) -> dict:
        """Create a typed OIDC user-attribute-to-claim mapper. Other mapper provider types are not supported by this operation. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return _change(api, "POST", _mapper_path(owner_type, owner_id), {"name": name, "protocol": "openid-connect", "protocolMapper": "oidc-usermodel-attribute-mapper", "config": {"user.attribute": user_attribute, "claim.name": claim_name, "jsonType.label": json_type, "access.token.claim": str(in_access_token).lower(), "id.token.claim": str(in_id_token).lower(), "userinfo.token.claim": str(in_userinfo).lower(), "multivalued": str(multivalued).lower()}})

    @mcp.tool()
    def sdk_idp_mapper_update(expected_environment: str, owner_type: Literal["client", "scope"], owner_id: str, mapper_id: str, name: str, user_attribute: str, claim_name: str, json_type: Literal["String", "boolean", "long", "int", "JSON"] = "String", in_access_token: bool = True, in_id_token: bool = True, in_userinfo: bool = True, multivalued: bool = False, realm: str | None = None) -> dict:
        """Update an existing OIDC user-attribute mapper. Rejects other provider types and preserves unrelated mapper configuration. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            path = _mapper_path(owner_type, owner_id) + "/" + segment(mapper_id)
            current = api.raw("GET", path)
            if current.get("protocolMapper") != "oidc-usermodel-attribute-mapper":
                raise ValueError("Only OIDC user-attribute mappers can be updated by this tool")
            body = {"name": name, "protocol": "openid-connect", "protocolMapper": "oidc-usermodel-attribute-mapper", "config": {"user.attribute": user_attribute, "claim.name": claim_name, "jsonType.label": json_type, "access.token.claim": str(in_access_token).lower(), "id.token.claim": str(in_id_token).lower(), "userinfo.token.claim": str(in_userinfo).lower(), "multivalued": str(multivalued).lower()}}
            body["config"] = {**current.get("config", {}), **body["config"]}
            return api.update(path, body, set(body))

    @mcp.tool()
    def sdk_idp_mapper_delete(expected_environment: str, owner_type: Literal["client", "scope"], owner_id: str, mapper_id: str, realm: str | None = None) -> dict:
        """Delete one protocol mapper from its explicitly selected owner. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return _change(api, "DELETE", _mapper_path(owner_type, owner_id) + "/" + segment(mapper_id))

    @mcp.tool()
    def sdk_idp_role_list(expected_environment: str, client_uuid: str | None = None, search: str | None = None, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read paginated realm roles, or client roles when internal client UUID is supplied. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return api.page(_role_path(client_uuid), first, max_results, params={"search": search} if search else None)

    @mcp.tool()
    def sdk_idp_role_get(expected_environment: str, role_name: str, client_uuid: str | None = None, realm: str | None = None) -> dict:
        """Get a realm role, or a role belonging to the explicitly selected internal client UUID. role_name is the exact role name. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return api.call("GET", _role_path(client_uuid) + "/" + segment(role_name))

    @mcp.tool()
    def sdk_idp_role_create(expected_environment: str, role_name: str, client_uuid: str | None = None, description: str | None = None, realm: str | None = None) -> dict:
        """Create a realm role, or a role belonging to the explicitly selected internal client UUID. role_name is the exact role name. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return _change(api, "POST", _role_path(client_uuid), {"name": role_name, "description": description or ""})

    @mcp.tool()
    def sdk_idp_role_update(expected_environment: str, role_name: str, client_uuid: str | None = None, description: str | None = None, realm: str | None = None) -> dict:
        """Update a realm role, or a role belonging to the explicitly selected internal client UUID. role_name is the exact role name. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            if description is None:
                raise ValueError("Provide a role description to update")
            return api.update(_role_path(client_uuid) + "/" + segment(role_name), {"description": description}, {"description"})

    @mcp.tool()
    def sdk_idp_role_delete(expected_environment: str, role_name: str, client_uuid: str | None = None, realm: str | None = None) -> dict:
        """Delete a realm role, or a role belonging to the explicitly selected internal client UUID. role_name is the exact role name. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return _change(api, "DELETE", _role_path(client_uuid) + "/" + segment(role_name))

    @mcp.tool()
    def sdk_idp_role_composites_get(expected_environment: str, role_name: str, client_uuid: str | None = None, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read composite members of a realm/client role. Pagination is local. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return api.page(_role_path(client_uuid) + "/" + segment(role_name) + "/composites", first, max_results, paginated=False)

    @mcp.tool()
    def sdk_idp_role_composite_add(expected_environment: str, role_name: str, member_role_names: list[str], client_uuid: str | None = None, member_client_uuid: str | None = None, realm: str | None = None) -> dict:
        """Add composite role membership. Parent and member role scopes are explicit; omit each client UUID for realm scope. Members are resolved before any mutation. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            members = _roles(api, member_role_names, member_client_uuid)
            return _change(api, "POST", _role_path(client_uuid) + "/" + segment(role_name) + "/composites", members)

    @mcp.tool()
    def sdk_idp_role_composite_remove(expected_environment: str, role_name: str, member_role_names: list[str], client_uuid: str | None = None, member_client_uuid: str | None = None, realm: str | None = None) -> dict:
        """Remove composite role membership. Parent and member role scopes are explicit; omit each client UUID for realm scope. Members are resolved before any mutation. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            members = _roles(api, member_role_names, member_client_uuid)
            return _change(api, "DELETE", _role_path(client_uuid) + "/" + segment(role_name) + "/composites", members)

    @mcp.tool()
    def sdk_idp_role_members_list(expected_environment: str, role_name: str, member_type: Literal["users", "groups"] = "users", client_uuid: str | None = None, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read a page of users/groups assigned a realm/client role. Unsupported backend routes return a structured backend error. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            if member_type not in ("users", "groups"):
                raise ValueError("member_type must be users or groups")
            return api.page(_role_path(client_uuid) + "/" + segment(role_name) + "/" + member_type, first, max_results)

    @mcp.tool()
    def sdk_idp_group_list(expected_environment: str, search: str | None = None, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read a page of top-level groups. Nested subGroups returned by the backend are not a flattened full-realm enumeration. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return api.page("/groups", first, max_results, params={"search": search} if search else None)

    @mcp.tool()
    def sdk_idp_group_get(expected_environment: str, group_id: str, realm: str | None = None) -> dict:
        """Read one group by UUID, including backend-returned hierarchy metadata. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return api.call("GET", f"/groups/{segment(group_id)}")

    @mcp.tool()
    def sdk_idp_group_count(expected_environment: str, search: str | None = None, top_level: bool = False, realm: str | None = None) -> dict:
        """Count realm groups, optionally filtered by name and top-level status. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return api.call("GET", "/groups/count", params={"search": search, "top": top_level})

    @mcp.tool()
    def sdk_idp_group_create(expected_environment: str, name: str, parent_group_id: str | None = None, realm: str | None = None) -> dict:
        """Create a top-level group or a child of the specified parent UUID. Existing name conflicts are reported by the backend. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            path = f"/groups/{segment(parent_group_id)}/children" if parent_group_id else "/groups"
            return _change(api, "POST", path, {"name": name})

    @mcp.tool()
    def sdk_idp_group_update(expected_environment: str, group_id: str, name: str, realm: str | None = None) -> dict:
        """Rename a group while preserving attributes and unrelated metadata. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return api.update(f"/groups/{segment(group_id)}", {"name": name}, {"name"})

    @mcp.tool()
    def sdk_idp_group_delete(expected_environment: str, group_id: str, realm: str | None = None) -> dict:
        """Delete one group and its backend-managed hierarchy/memberships. Does not delete member users. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return _change(api, "DELETE", f"/groups/{segment(group_id)}")

    @mcp.tool()
    def sdk_idp_group_members_list(expected_environment: str, group_id: str, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read a page of users in a group using its UUID. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return api.page(f"/groups/{segment(group_id)}/members", first, max_results)

    @mcp.tool()
    def sdk_idp_user_groups_list(expected_environment: str, user_id: str, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read a page of group memberships for an exact user UUID. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return api.page(f"/users/{segment(user_id)}/groups", first, max_results)

    @mcp.tool()
    def sdk_idp_group_member_add(expected_environment: str, group_id: str, user_id: str, realm: str | None = None) -> dict:
        """Add an existing user UUID in a group UUID. Does not create/delete the user or group. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return _change(api, "PUT", f"/users/{segment(user_id)}/groups/{segment(group_id)}")

    @mcp.tool()
    def sdk_idp_group_member_remove(expected_environment: str, group_id: str, user_id: str, realm: str | None = None) -> dict:
        """Remove an existing user UUID in a group UUID. Does not create/delete the user or group. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            return _change(api, "DELETE", f"/users/{segment(user_id)}/groups/{segment(group_id)}")

    @mcp.tool()
    def sdk_idp_role_assignments_get(expected_environment: str, subject_type: Literal["user", "group"], subject_id: str, client_uuid: str | None = None, effective: bool = False, first: int = 0, max_results: int = 50, realm: str | None = None) -> dict:
        """Read direct or effective roles assigned to a user/group UUID. Omit client_uuid for realm roles. Pagination is local. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            path = _assignment_path(subject_type, subject_id, client_uuid) + ("/composite" if effective else "")
            return api.page(path, first, max_results, paginated=False)

    @mcp.tool()
    def sdk_idp_role_assign(expected_environment: str, subject_type: Literal["user", "group"], subject_id: str, role_names: list[str], client_uuid: str | None = None, realm: str | None = None) -> dict:
        """Assign direct roles for a user/group UUID. Omit client_uuid for realm roles. Resolves all exact role names before writing; inherited roles are not directly removed. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            path = _assignment_path(subject_type, subject_id, client_uuid)
            roles = _roles(api, role_names, client_uuid)
            return _change(api, "POST", path, roles)

    @mcp.tool()
    def sdk_idp_role_remove(expected_environment: str, subject_type: Literal["user", "group"], subject_id: str, role_names: list[str], client_uuid: str | None = None, realm: str | None = None) -> dict:
        """Remove direct roles for a user/group UUID. Omit client_uuid for realm roles. Resolves all exact role names before writing; inherited roles are not directly removed. Requires realm admin permissions; backend permission/conflict errors are propagated. Realm defaults to the configured tenant."""
        with Admin(expected_environment, realm) as api:
            path = _assignment_path(subject_type, subject_id, client_uuid)
            roles = _roles(api, role_names, client_uuid)
            return _change(api, "DELETE", path, roles)
