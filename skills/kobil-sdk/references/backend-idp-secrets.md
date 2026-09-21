> Clean service-interface branch: contract tests only; prior implementation live evidence does not qualify this branch.

# IDP private credential operations — 0.6.0

Existing SDK helpers remain available. Environment/realm permissions and deployed API support are required.

### `sdk_idp_user_password_set`

Explicitly reset a user's password from an env/keyring/private-file reference. Requires manage-users; temporary defaults true. No password appears in arguments/results; account reuse never invokes this implicitly.

Parameters: `expected_environment, user_uuid, credential, temporary, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_client_secret_write`

Read a confidential client's existing secret into a NEW private JSON file. Requires client administration; does not rotate it. Use internal client UUID, not public clientId. Returns file metadata only.

Parameters: `expected_environment, client_uuid, output_path, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_client_secret_rotate`

Rotate one confidential client's secret and save the new value to a NEW private JSON file. Changes authentication for consumers. Never automatically retry an uncertain rotation; inspect server state first.

Parameters: `expected_environment, client_uuid, output_path, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_source_token_write`

Request a user token using an explicitly configured direct-grant client and credential references; save response privately. Requires that realm/client to allow direct grant. No browser/SSO bypass or automatic retry.

Parameters: `expected_environment, client_id, username, password, output_path, client_secret, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_token_exchange`

Exchange an authorized subject access token for the requested audience and save the response privately. Realm/client must permit token exchange. Subject reference must resolve to raw token text, not a JSON response file.

Parameters: `expected_environment, client_id, audience, subject_token, output_path, client_secret, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_tenant_create`

Create a KOBIL tenant via v4_realm. Requires tenant-provisioning rights and explicitly chosen provisioning realm/themes. This is not generic Keycloak realm creation; unsupported deployments report an API error.

Parameters: `expected_environment, tenant, login_theme, account_theme, provisioning_realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_tms_trigger`

Trigger a KOBIL v3_user TMS transaction through the IDP route. Separate from AST sdk_tms_trigger; requires IDP TMS rights. Returns transaction metadata, not proof of device confirmation.

Parameters: `expected_environment, user_uuid, text, realm`.

Live verification: not performed for this clean service-interface branch.
