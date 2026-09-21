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
observability-based client resolution, and unverified API routes remain gaps.
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
the inspected dashboard revision to MCP operations. 41 underlying HTTP contracts
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
