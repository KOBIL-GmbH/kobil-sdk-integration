# AST administration — 0.6.0

Existing SDK helpers remain available. Environment/realm permissions and deployed API support are required.

### `sdk_app_list`

List AST app registrations when the app name is unknown. Read-only; requires AST tenant access.

        Optional name substring/category filters; cursor is a decimal offset into a fresh complete
        collection fetched with backend pagination (not a stable snapshot). Follow next_cursor until null. Returns safe IDs/names/
        categories, never push credentials. Refuses unknown/incomplete backend paging envelopes.
        Next call sdk_app_versions for the selected exact app name.
        

Parameters: `expected_environment, name, category, cursor, page_size`.

Live verification: read-only check passed 2026-09-21.

### `sdk_app_version_get`

Find one version ID within the complete version listing for an exact app. Read-only;
        returns registration user, platform and integrity policy. Missing/ambiguous IDs fail.
        

Parameters: `expected_environment, app_name, version_id`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_app_version_delete`

Delete an exact version ID after verifying it belongs to app_name. Destructive;
        requires AST management permission. Returns affected registration metadata; backend
        dependency/conflict errors are propagated. Does not delete the app or user.
        

Parameters: `expected_environment, app_name, version_id`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_app_update`

Update app categories while preserving all existing push settings. Requires AST
        app-update permission. App name is the immutable selector; arbitrary metadata/rename
        is not supported by this API. Returns changed/reused. No credential values returned.
        

Parameters: `expected_environment, app_name, categories`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_app_delete`

Delete an exact app AND its related versions (backend cascade). Destructive;
        requires app-delete permission. Reads the app/version inventory first, returns the
        affected versions. Device effects are backend-defined and not claimed as verified.
        

Parameters: `expected_environment, app_name`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_app_version_update`

Update selected version integrity/lock/registration-user fields by exact ID.
        Preserves app/platform/version and unspecified policy fields via read-modify-write.
        Requires version-update permission. Refuses registration-user replacement on a
        policy-based version. Returns changed/reused; does not move or rename a version.
        

Parameters: `expected_environment, app_name, version_id, check_integrity, locked, register_user_id`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_ast_device_list`

List a user's AST clients using their IDP UUID, not username. Read-only. Returns
        safe device identifiers/state and local offset pagination. Unknown partial server
        pages fail explicitly. Next use sdk_ast_device_get with the chosen client ID.
        

Parameters: `expected_environment, user_uuid, cursor, page_size`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_ast_device_get`

Read one AST client by exact client ID, with safe state/risk fields if supplied.
        Does not resolve a username or query an observability service. Requires tenant read access.
        

Parameters: `expected_environment, client_id`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_ast_device_unlink`

Remove the exact user UUID/device association via AST unlink. Destructive association
        change; does not imply deletion of the client record. Requires AST management permission.
        

Parameters: `expected_environment, user_uuid, client_id`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_ast_device_delete`

Delete the exact AST client/device record. Destructive, requires AST management
        rights. Backend constraints/errors are propagated; no user account is deleted.
        

Parameters: `expected_environment, client_id`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_ast_push_get`

Inspect APNs/FCM setup for an exact app. Read-only, returns public identifiers and
        presence flags only; no certificate, private key, password or service-account payload.
        Certificate expiry requires sdk_ast_push_validate with local files.
        

Parameters: `expected_environment, app_name`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_ast_push_fcm_set`

Replace only an app's FCM service account using an absolute private JSON file
        (mode 0600). Reads then preserves APNs/other push fields, writes a flat config.
        Requires AST management rights; returns changed/reused without any credentials.
        

Parameters: `expected_environment, app_name, service_account_file`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_ast_push_update`

Update selected modern APNs fields/categories, preserving unspecified push fields.
        Credential material must be absolute private files (0600); no inline secrets accepted.
        Uses verified flat PUT config. Requires AST management rights. Older field aliases
        are not auto-converted; backend schema errors are propagated. No implicit clear/remove.
        

Parameters: `expected_environment, app_name, ios_bundle_id, ios_is_development, ios_team_id, ios_key_id, apns_certificate_file, apns_private_key_file, categories`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_tms_display_message`

Send a real display-only message to an IDP user UUID through AST. This contacts
        the user's devices; use only for requested messaging. Requires management permission.
        Acceptance by the API does not prove delivery/read/acknowledgement. No TMS approval inferred.
        

Parameters: `expected_environment, user_uuid, text`.

Live verification: not performed; no live-write coverage claimed.

### `sdk_ast_push_validate`

Validate a local PEM certificate/private-key pair from private files (0600).
        Local-only: checks parseability, key match and validity dates; returns SHA-256
        fingerprint and expiry. Does not prove APNs entitlement, topic or server acceptance.
        Encrypted keys without an external decryption provider are unsupported.
        

Parameters: `expected_environment, certificate_file, private_key_file`.

Live verification: not performed; no live-write coverage claimed.
