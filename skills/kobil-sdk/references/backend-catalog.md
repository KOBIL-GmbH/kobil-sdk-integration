# Backend catalog — 0.6.0

The MCP registers 177 tools: the original 36, 139 domain administration tools,
and two connection/capability tools. Tools use the selected customer connection;
no internal service dependency or hardcoded environment is installed.

## Start here

- `sdk_connections_list`: selected profile metadata only. Currently one selected
  connection per MCP process; does not scan for profiles or change a global environment.
- `sdk_backend_capabilities(expected_environment)`: installed tools and explicit
  coverage gaps. Optional `probe_idp_server=true` queries IDP version metadata.
  Permissions for all other operations remain unverified.
- `sdk_app_list`: enumerate AST registrations before selecting or creating an app.
  Follow `next_cursor`. Backend traversal explicitly uses page/pageSize; AST's
  default response is only the first 20 apps.
- `sdk_idp_user_list`, `sdk_idp_client_list`: use administrative enumeration and
  follow `next_offset`. Internal UUIDs differ from public names/client IDs.
- `sdk_backend_verify`: separate configuration from authenticated backend access.

## Function descriptions

- [AST apps, versions, devices and push](backend-ast-admin.md)
- [IDP users](backend-idp-users.md)
- [IDP clients, scopes, mappers, roles and groups](backend-idp-access.md)
- [Flows, sessions, realms, federation and authorization](backend-idp-extended.md)
- [Private credential and token operations](backend-idp-secrets.md)

Each operation describes its identifiers, effects and requirements. Read-only
collections return explicit continuation/completion metadata. Pages are not
atomic snapshots of a changing backend. Mutations preserve unspecified fields;
explicit list values replace those lists. Nested provider config merges with
existing config. Concurrent administrative writes are not an atomic transaction.
No implicit retries after unknown mutation outcomes.

## Contract and verification matrix

The source distribution contains `docs/backend-tool-matrix.json`, mapping every
new domain tool to its implementation and endpoint expression. Contracts were
reviewed against the Keycloak Admin REST reference and authorization resource
implementation, plus AST v1 service contracts. This is a feature matrix, not a
claim that every endpoint of every backend release is implemented.

Read-only app/user/client discovery and IDP server metadata passed against one
configured nonproduction deployment on 2026-09-21. The broader catalog has
fixture/schema/protocol coverage. New delete, rotation, realm and other
administrative writes were not exercised on live customer resources. Deployed
IDP/AST API differences or missing roles can still reject an operation.

## Known boundaries

- AST cross-user client/activity resolution needs an optional observability adapter;
  it is not implemented. Device detail returns only information the AST API supplies.
- AST version updates cover integrity, lock and registration user; app updates
  cover categories. Policy creation and arbitrary app metadata are not exposed.
- IDP client writes cover core OpenID Connect fields. Mapper writes cover typed
  user-attribute mappings; other mapper types remain inspectable/deletable.
- Identity-provider configuration targets OIDC; storage configuration targets LDAP.
  Other provider metadata can be inspected. Supported policy types are user,
  client, role and aggregate; resource/scope permissions are typed. Arbitrary
  scripts and unrestricted provider JSON are not accepted.
- Realm/token endpoints may require distinct permissions and enabled features.
  A 404 may mean a missing resource or an unavailable API; do not infer permission
  or support from the installed tool list alone.
- Private files are bounded, owner-only on Unix, and never overwritten. Native
  Windows ACL enforcement/testing remains outside this verification checkpoint.
- App build, activation/login and TMS SDK events are independent acceptance steps.

Credential storage references are `env`, `keyring` or private `file`. Existing
admin configuration remains the v0.4.0-compatible environment-reference schema;
this update does not silently restore the separate shared-credentials branch.

## Sources

[Keycloak Admin REST API](https://www.keycloak.org/docs-api/latest/rest-api/index.html)
and [Keycloak authorization admin implementation](https://github.com/keycloak/keycloak/tree/main/services/src/main/java/org/keycloak/authorization/admin).
