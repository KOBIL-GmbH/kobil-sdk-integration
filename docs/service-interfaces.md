# IDP and AST interfaces

This feature starts from the pre-merge baseline. It ports typed API wrappers,
not the reverted app-flow recipes, journey classifier, provisioning helpers,
Swift sample or Xcode project generator. Authentication is in idp_transport.py;
it has no activation module dependency. Existing 13 baseline tools remain.

Domain references:
- [IDP users](../skills/kobil-sdk/references/backend-idp-users.md)
- [IDP clients, roles and groups](../skills/kobil-sdk/references/backend-idp-access.md)
- [IDP flows, realms and authorization](../skills/kobil-sdk/references/backend-idp-extended.md)
- [Credential/token operations](../skills/kobil-sdk/references/backend-idp-secrets.md)
- [AST administration](../skills/kobil-sdk/references/backend-ast-admin.md)
- [App-flow source policy](../skills/kobil-sdk/references/app-flow-sources.md)

The operations are explicit: creating a flow, assigning an execution or updating
a client requires the caller to choose those resources and settings. There is no
native/Headless journey selector and no inferred provisioning sequence.

Coverage is not every endpoint of every backend version. Custom provider families,
and unverified API routes remain gaps.
Tests validate transport contracts and safeguards, not deployed permissions or
end-to-end mobile behavior. Prior branch live checks are not acceptance evidence
for this clean branch.

Connections retain KOBIL_SDK_CONNECTION. Optional oauth.scope is supported.
The optional admin object has idp_url, realm, client_id, username and password_env;
the server reads the password from the named environment variable. Private
credential operations also accept environment, private-file or OS-keyring
references. Never put credential values in tool arguments or public config.

## Dashboard coverage

[Route matrix](dashboard-interface-coverage.json) maps all 45 IDP/AST routes in
the inspected dashboard revision to MCP operations. 49 explicit HTTP contracts (including eight additional audited operations)
are available through `sdk_service_operations`, `sdk_idp_service_request` and
`sdk_ast_service_request`, alongside typed tools. Token refresh and bounded
cross-user device inventory have dedicated tools. This covers that dashboard
revision, not an assertion about every endpoint in every vendor release.

Use `sdk_service_operations(domain="ast")` to inspect exact identifiers/query keys.
For example, operation `version_unregister` takes identifiers `{ "version": "…" }`
and query `{ "architectureName": "…" }`. It performs a real DELETE.
Bodies for POST/PUT come from an explicit mode0600 JSON file; the schema is the
backend operation's representation, without dashboard-specific defaults.
KOBIL activation codes use `idp.v3_user_update` with the API credential payload;
this does not choose a flow, reset a password or create a user implicitly.

Reads return one server response and do not claim all pages were retrieved.
Use the typed paginated tools where available; otherwise inspect server metadata
and provide documented page parameters. Mutations have no automatic retry.
Dashboard SMTP mode presets, app-flow recipes and infrastructure addresses are
not included. Realm SMTP changes use explicitly supplied smtpServer settings.


## Additional audited operations

The IDP dispatcher now includes `v3_user_get`, `v3_user_search`, `v3_user_delete`,
`authenticator_providers`, `flow_execution_create`, `execution_config_create`,
`authenticator_config_get`, and `authenticator_config_update`. Inspect
`sdk_service_operations(domain="idp")` for exact method, identifiers and body requirements.
Config bodies are explicit private JSON files; provider settings are sent unchanged.
These operations never recommend an authenticator, flow or client.

`sdk_idp_login_page_fetch` implements the ninth audited REST operation: the OIDC
GET authorization endpoint. Supply the existing client, registered redirect URI,
and new output file. Optional state, nonce and S256 code challenge are supported.
Redirects are reported as failures rather than followed; cookies are not exported
for subsequent login. The saved page is untrusted content, not an SDK compatibility test.

`sdk_idp_activation_code_generate` generates a fresh code. To set a selected code,
use `sdk_idp_activation_code_set` with a credential reference. It returns metadata
only. Both operate on an existing user without choosing a flow.

`sdk_ast_token_write` saves the configured AST token privately.
`sdk_backend_auth_test` tests IDP or AST token acquisition without returning a secret.
Connection selection stays explicit through KOBIL_SDK_CONNECTION and the
expected_environment guard. To switch profiles or reload tool definitions, use the
host client's MCP configuration/restart controls; the server does not mutate
process-wide connection state for concurrent callers.

## Optional Grafana client correlation

`sdk_ast_find_client` uses a separate mode0600 provider JSON file. Example shape:

```json
{
  "environment": "customer-test",
  "url": "https://grafana.example.org",
  "datasource_uid": "customer-loki",
  "labels": {"namespace": "customer-app"},
  "credential": {"provider": "keyring", "service": "customer-grafana", "account": "service-token"}
}
```

The credential is a Grafana bearer token authorized to query that datasource.
Env and private-file references are also supported. No provider is needed for
normal IDP/AST tools. The search uses literal client-ID filtering, up to 30 days
and 1000 entries. It returns timestamps and candidate user UUIDs without raw logs.
Results do not establish authoritative ownership or complete history. Existing
username/password Grafana sessions are not imported; configure a bearer token.
