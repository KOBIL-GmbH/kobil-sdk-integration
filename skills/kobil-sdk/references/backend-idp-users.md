> Clean service-interface branch: contract tests only; prior implementation live evidence does not qualify this branch.

# IDP users — 0.6.0

Existing SDK helpers remain available. Environment/realm permissions and deployed API support are required.

### `sdk_idp_user_list`

List users in an explicit realm. Read-only; needs query/view-users. Follow next_offset until complete; returns no passwords. Use the returned UUID for device/activation tools.

Parameters: `expected_environment, realm, search, first, max_results`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_user_search`

Search users by username/email/enabled state. Exact matching defaults to true. Read-only, paginated; does not create identities or reset passwords.

Parameters: `expected_environment, realm, username, email, enabled, exact, first, max_results`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_user_count`

Count users matching an optional search. Read-only realm admin query; count is not a stable pagination snapshot.

Parameters: `expected_environment, realm, search`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_user_get`

Read a user by UUID or exact username (exactly one). Requires view-users. Returns profile metadata; inspect credential metadata and device state separately.

Parameters: `expected_environment, user_uuid, username, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_user_create`

Create an IDP profile without a password. Requires manage-users. Existing-name conflicts are reported, not overwritten. Follow with explicit group/credential setup if needed.

Parameters: `expected_environment, profile, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_user_update`

Update only selected profile fields, preserving other fields. Requires manage-users. Never resets a password; attributes supplied replace that attribute map explicitly.

Parameters: `expected_environment, user_uuid, changes, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_user_enable`

Enable an existing user. Changes availability only; no password/group changes. Requires manage-users.

Parameters: `expected_environment, user_uuid, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_user_disable`

Disable an existing user without deleting the profile. Requires manage-users; active-session revocation is a separate operation.

Parameters: `expected_environment, user_uuid, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_user_delete`

Permanently delete the exact user UUID from the selected realm. Requires manage-users; do not substitute a username or use for routine reuse.

Parameters: `expected_environment, user_uuid, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_user_credentials_list`

List credential IDs/types/labels for a user, never credential contents. Read-only; existing passwords cannot be recovered.

Parameters: `expected_environment, user_uuid, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_user_credential_delete`

Remove one credential by its ID from the selected user. Requires manage-users; may prevent login. Does not delete the profile.

Parameters: `expected_environment, user_uuid, credential_id, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_user_required_actions_update`

Replace this user's required-action list (empty clears it). Requires manage-users; does not alter realm-wide defaults or send email.

Parameters: `expected_environment, user_uuid, actions, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_user_verify_email_send`

Send a verification email to the selected user. Communication/write operation requiring explicit user intent and configured realm email; does not mark email verified.

Parameters: `expected_environment, user_uuid, realm`.

Live verification: not performed for this clean service-interface branch.

### `sdk_idp_user_actions_email_send`

Send an action email for specified required actions. Communication/write; explicit recipient UUID. Lifespan in seconds (60..86400); SMTP delivery is not proven by backend acceptance.

Parameters: `expected_environment, user_uuid, actions, lifespan, realm`.

Live verification: not performed for this clean service-interface branch.
