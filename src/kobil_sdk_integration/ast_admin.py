"""Typed AST administration using verified routes; no arbitrary HTTP interface."""
import base64
import json
import os
from pathlib import Path
import stat
from uuid import UUID

from .backend import AST, BackendError, configuration, segment


UNSUPPORTED = {
    'sdk_ast_client_resolve': 'Cross-user client search requires an optional observability adapter.',
}


def _run(environment, operation):
    backend = AST(configuration(environment))
    try:
        return operation(backend)
    finally:
        backend.close()


def _uuid(value):
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Expected an IDP user UUID') from None


def _collection(value):
    """Accept complete collection responses only, never silently truncate a page."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ('apps', 'content', 'data'):
            if isinstance(value.get(key), list):
                rows = value[key]
                total = value.get('totalCount', value.get('totalElements'))
                if value.get('last') is False or value.get('next') or value.get('nextCursor'):
                    raise BackendError('Incomplete AST collection: backend pagination contract is not verified')
                if total is not None and (type(total) is not int or total != len(rows)):
                    raise BackendError('Incomplete AST collection: backend pagination contract is not verified')
                if total is None and key != 'apps':
                    raise BackendError('AST collection has no completeness metadata')
                return rows
    raise BackendError('Unrecognized AST collection response')


def _apps(backend):
    # AST app pages are plain arrays (no count); explicitly request the documented
    # maximum page size. Duplicate IDs/names detect ignored paging or shifting data.
    rows, seen = [], set()
    for page in range(1, 101):
        batch = _collection(backend.request('GET', f'/apps?page={page}&pageSize=100'))
        if len(batch) > 100:
            raise BackendError('AST app response exceeds requested page size')
        for item in batch:
            key = item if isinstance(item, str) else item.get('appName') if isinstance(item, dict) else None
            if not isinstance(key, str) or not key or key in seen:
                raise BackendError('App listing changed or repeated during pagination')
            seen.add(key)
        rows.extend(batch)
        if len(batch) < 100:
            return rows
    raise BackendError('App collection exceeds automatic pagination limit')


def _page(rows, cursor, page_size):
    if type(page_size) is not int or not 1 <= page_size <= 200:
        raise ValueError('page_size must be between 1 and 200')
    if not isinstance(cursor, str) or not cursor.isascii() or not cursor.isdigit():
        raise ValueError('cursor must be a nonnegative decimal offset')
    offset = int(cursor)
    end = offset + page_size
    return {'items': rows[offset:end], 'total': len(rows),
            'next_cursor': str(end) if end < len(rows) else None,
            'complete': end >= len(rows), 'pagination': 'local_offset_over_complete_backend_collection'}


APP_FIELDS = ('id', 'appName', 'tenantId')
VERSION_FIELDS = ('id', 'appName', 'platform', 'versionStr', 'registerUserId', 'isCheckIntegrity', 'versionLock', 'policyId')
DEVICE_FIELDS = ('id', 'astClientId', 'userId', 'appName', 'platform', 'versionStr', 'state', 'status', 'riskBits', 'riskbits', 'createdAt', 'lastLogin')
PUSH_PUBLIC = ('categories', 'iosBundleId', 'iosIsDevelopment', 'iosApnsTeamId', 'iosApnsKeyId', 'bundleId', 'teamId', 'keyId')
PUSH_PRIVATE = ('iosApnsCertificate', 'iosApnsPrivateKey', 'apnsCert', 'apnsKey', 'apnsCertPassword', 'fcmServiceAccountJSON', 'androidApiKey', 'hpkClientSecret')


def _select(row, fields):
    if not isinstance(row, dict):
        raise BackendError('Unrecognized AST object response')
    return {key: row[key] for key in fields if key in row and isinstance(row[key], (str, int, bool, type(None)))}


def _app(backend, name):
    row = backend.request('GET', '/apps/' + segment(name))
    if not isinstance(row, dict) or row.get('appName') != name:
        raise BackendError('AST app identity does not match request')
    pnc = row.get('pushNotificationConfig') or {}
    if not isinstance(pnc, dict):
        raise BackendError('Unrecognized push configuration')
    return row, dict(pnc)


def _private_file(path):
    source = Path(path).expanduser()
    if not source.is_absolute():
        raise ValueError('Provide an absolute private file path')
    try:
        fd = os.open(source, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077 or info.st_size > 1024 * 1024:
                raise ValueError('Expected a private regular file, at most 1 MiB, with mode 0600')
            return stream.read(1024 * 1024 + 1)
    except OSError:
        raise ValueError('Cannot read private input file') from None


def register(mcp):
    @mcp.tool()
    def sdk_app_list(expected_environment: str, name: str = '', category: str = '', cursor: str = '0', page_size: int = 100) -> dict:
        """List AST app registrations when the app name is unknown. Read-only; requires AST tenant access.

        Optional name substring/category filters; cursor is a decimal offset into a fresh complete
        collection fetched with backend pagination (not a stable snapshot). Follow next_cursor until null. Returns safe IDs/names/
        categories, never push credentials. Refuses unknown/incomplete backend paging envelopes.
        Next call sdk_app_versions for the selected exact app name.
        """
        _page([], cursor, page_size)
        def operation(b):
            rows = []
            for item in _apps(b):
                item = {'appName': item} if isinstance(item, str) else item
                safe = _select(item, APP_FIELDS)
                if not isinstance(safe.get('appName'), str):
                    raise BackendError('AST app entry has no name')
                categories = item.get('categories', (item.get('pushNotificationConfig') or {}).get('categories', []))
                if not isinstance(categories, list) or any(not isinstance(x, str) for x in categories):
                    raise BackendError('Invalid app categories')
                safe['categories'] = categories
                if name.casefold() in safe['appName'].casefold() and (not category or category in categories):
                    rows.append(safe)
            rows.sort(key=lambda r: (r['appName'], str(r.get('id', ''))))
            return _page(rows, cursor, page_size)
        return _run(expected_environment, operation)

    @mcp.tool()
    def sdk_app_version_get(expected_environment: str, app_name: str, version_id: str) -> dict:
        """Find one version ID within the complete version listing for an exact app. Read-only;
        returns registration user, platform and integrity policy. Missing/ambiguous IDs fail.
        """
        segment(version_id)
        def operation(b):
            matches = [r for r in b._version_rows(app_name) if str(r.get('id')) == version_id and r.get('appName') == app_name]
            if len(matches) != 1:
                raise BackendError('Version not found uniquely in the selected app')
            return _select(matches[0], VERSION_FIELDS)
        return _run(expected_environment, operation)

    @mcp.tool()
    def sdk_app_version_delete(expected_environment: str, app_name: str, version_id: str) -> dict:
        """Delete an exact version ID after verifying it belongs to app_name. Destructive;
        requires AST management permission. Returns affected registration metadata; backend
        dependency/conflict errors are propagated. Does not delete the app or user.
        """
        segment(version_id)
        def operation(b):
            matches = [r for r in b._version_rows(app_name) if str(r.get('id')) == version_id and r.get('appName') == app_name]
            if len(matches) != 1:
                raise BackendError('Version not found uniquely in the selected app; no deletion performed')
            b.request('DELETE', '/versions/' + segment(version_id))
            return {'deleted': True, 'version': _select(matches[0], VERSION_FIELDS)}
        return _run(expected_environment, operation)

    @mcp.tool()
    def sdk_app_update(expected_environment: str, app_name: str, categories: list[str]) -> dict:
        """Update app categories while preserving all existing push settings. Requires AST
        app-update permission. App name is the immutable selector; arbitrary metadata/rename
        is not supported by this API. Returns changed/reused. No credential values returned.
        """
        return sdk_ast_push_update(expected_environment, app_name, categories=categories)

    @mcp.tool()
    def sdk_app_delete(expected_environment: str, app_name: str) -> dict:
        """Delete an exact app AND its related versions (backend cascade). Destructive;
        requires app-delete permission. Reads the app/version inventory first, returns the
        affected versions. Device effects are backend-defined and not claimed as verified.
        """
        def operation(b):
            _app(b, app_name)
            versions = b._version_rows(app_name)
            if any(v.get('appName') != app_name for v in versions):
                raise BackendError('App version inventory does not match; no deletion performed')
            b.request('DELETE', '/apps/' + segment(app_name))
            return {'app_name': app_name, 'deleted': True, 'cascade_versions': True,
                    'versions': [_select(v, VERSION_FIELDS) for v in versions],
                    'device_effects_verified': False}
        return _run(expected_environment, operation)

    @mcp.tool()
    def sdk_app_version_update(expected_environment: str, app_name: str, version_id: str, check_integrity: bool | None = None, locked: bool | None = None, register_user_id: str | None = None) -> dict:
        """Update selected version integrity/lock/registration-user fields by exact ID.
        Preserves app/platform/version and unspecified policy fields via read-modify-write.
        Requires version-update permission. Refuses registration-user replacement on a
        policy-based version. Returns changed/reused; does not move or rename a version.
        """
        path = '/versions/' + segment(version_id)
        changes = {}
        for field, value in [('isCheckIntegrity', check_integrity), ('versionLock', locked)]:
            if value is not None:
                if type(value) is not bool:
                    raise ValueError('Version flags must be booleans')
                changes[field] = value
        if register_user_id is not None:
            segment(register_user_id)
            if len(register_user_id) > 255:
                raise ValueError('Registration user ID exceeds 255 characters')
            changes['registerUserId'] = register_user_id
        if not changes:
            raise ValueError('Select a version field to update')
        def operation(b):
            row = b.request('GET', path)
            if not isinstance(row, dict) or row.get('appName') != app_name or row.get('id') != version_id:
                raise BackendError('Version identity does not match; no update performed')
            required = ('appName', 'platform', 'versionStr', 'versionLock', 'isCheckIntegrity')
            if any(k not in row for k in required) or not (row.get('registerUserId') or row.get('policyId')):
                raise BackendError('Incomplete version policy; refusing lossy update')
            if register_user_id is not None and row.get('policyId'):
                raise ValueError('Registration user cannot replace a policy-based registration')
            fields = sorted(k for k, value in changes.items() if row.get(k) != value)
            if fields:
                body = {k: row[k] for k in (*required, 'registerUserId', 'policyId') if k in row}
                body.update(changes)
                b.request('PUT', path, body)
            return {'app_name': app_name, 'version_id': version_id, 'changed': bool(fields), 'reused': not fields, 'fields': fields}
        return _run(expected_environment, operation)

    @mcp.tool()
    def sdk_ast_device_list(expected_environment: str, user_uuid: str, cursor: str = '0', page_size: int = 100) -> dict:
        """List a user's AST clients using their IDP UUID, not username. Read-only. Returns
        safe device identifiers/state and local offset pagination. Unknown partial server
        pages fail explicitly. Next use sdk_ast_device_get with the chosen client ID.
        """
        user_uuid = _uuid(user_uuid)
        _page([], cursor, page_size)
        def operation(b):
            response = b.request('GET', '/astclients?userId=' + segment(user_uuid))
            if not isinstance(response, dict) or not any(k in response for k in ('totalCount', 'totalElements')):
                raise BackendError('Device collection completeness cannot be verified: missing total count')
            rows = [_select(r, DEVICE_FIELDS) for r in _collection(response)]
            rows.sort(key=lambda r: str(r.get('id', r.get('astClientId', ''))))
            return _page(rows, cursor, page_size)
        return _run(expected_environment, operation)

    @mcp.tool()
    def sdk_ast_device_get(expected_environment: str, client_id: str) -> dict:
        """Read one AST client by exact client ID, with safe state/risk fields if supplied.
        Does not resolve a username or query an observability service. Requires tenant read access.
        """
        path = '/astclients/' + segment(client_id)
        return _run(expected_environment, lambda b: _select(b.request('GET', path), DEVICE_FIELDS))

    @mcp.tool()
    def sdk_ast_device_unlink(expected_environment: str, user_uuid: str, client_id: str) -> dict:
        """Remove the exact user UUID/device association via AST unlink. Destructive association
        change; does not imply deletion of the client record. Requires AST management permission.
        """
        user_uuid = _uuid(user_uuid)
        segment(client_id)
        def operation(b):
            b.request('POST', '/unlink', {'userId': user_uuid, 'astClientId': client_id})
            return {'unlinked': True, 'user_id': user_uuid, 'client_id': client_id}
        return _run(expected_environment, operation)

    @mcp.tool()
    def sdk_ast_device_delete(expected_environment: str, client_id: str) -> dict:
        """Delete the exact AST client/device record. Destructive, requires AST management
        rights. Backend constraints/errors are propagated; no user account is deleted.
        """
        path = '/astclients/' + segment(client_id)
        def operation(b):
            b.request('DELETE', path)
            return {'deleted': True, 'client_id': client_id}
        return _run(expected_environment, operation)

    @mcp.tool()
    def sdk_ast_push_get(expected_environment: str, app_name: str) -> dict:
        """Inspect APNs/FCM setup for an exact app. Read-only, returns public identifiers and
        presence flags only; no certificate, private key, password or service-account payload.
        Certificate expiry requires sdk_ast_push_validate with local files.
        """
        def operation(b):
            _, pnc = _app(b, app_name)
            public = _select(pnc, PUSH_PUBLIC)
            public['configured_material'] = {key: bool(pnc.get(key)) for key in PUSH_PRIVATE}
            return {'app_name': app_name, 'push': public}
        return _run(expected_environment, operation)

    @mcp.tool()
    def sdk_ast_push_fcm_set(expected_environment: str, app_name: str, service_account_file: str) -> dict:
        """Replace only an app's FCM service account using an absolute private JSON file
        (mode 0600). Reads then preserves APNs/other push fields, writes a flat config.
        Requires AST management rights; returns changed/reused without any credentials.
        """
        configuration(expected_environment)
        raw = _private_file(service_account_file)
        try:
            value = json.loads(raw)
            if value.get('type') != 'service_account' or not all(isinstance(value.get(k), str) and value[k] for k in ('project_id', 'client_email', 'private_key')):
                raise ValueError()
        except (ValueError, AttributeError):
            raise ValueError('Expected a valid FCM service-account JSON file') from None
        encoded = base64.b64encode(raw).decode()
        def operation(b):
            _, pnc = _app(b, app_name)
            changed = pnc.get('fcmServiceAccountJSON') != encoded
            if changed:
                pnc['fcmServiceAccountJSON'] = encoded
                b.request('PUT', '/apps/' + segment(app_name), pnc)
            return {'app_name': app_name, 'changed': changed, 'reused': not changed, 'fields': ['fcmServiceAccountJSON']}
        return _run(expected_environment, operation)

    @mcp.tool()
    def sdk_ast_push_update(expected_environment: str, app_name: str, ios_bundle_id: str | None = None, ios_is_development: bool | None = None, ios_team_id: str | None = None, ios_key_id: str | None = None, apns_certificate_file: str | None = None, apns_private_key_file: str | None = None, categories: list[str] | None = None) -> dict:
        """Update selected modern APNs fields/categories, preserving unspecified push fields.
        Credential material must be absolute private files (0600); no inline secrets accepted.
        Uses verified flat PUT config. Requires AST management rights. Older field aliases
        are not auto-converted; backend schema errors are propagated. No implicit clear/remove.
        """
        configuration(expected_environment)
        changes = {}
        for key, value in [('iosBundleId', ios_bundle_id), ('iosApnsTeamId', ios_team_id), ('iosApnsKeyId', ios_key_id)]:
            if value is not None:
                segment(value)
                changes[key] = value
        if ios_is_development is not None:
            if type(ios_is_development) is not bool:
                raise ValueError('ios_is_development must be boolean')
            changes['iosIsDevelopment'] = ios_is_development
        if categories is not None:
            if not categories or any(not isinstance(c, str) or not c.strip() for c in categories):
                raise ValueError('Provide at least one non-empty category')
            changes['categories'] = categories
        for key, path in [('iosApnsCertificate', apns_certificate_file), ('iosApnsPrivateKey', apns_private_key_file)]:
            if path is not None:
                raw = _private_file(path)
                if not raw.lstrip().startswith(b'-----BEGIN'):
                    raise ValueError('APNs input must be PEM material')
                changes[key] = 'data:application/x-pem-file;base64,' + base64.b64encode(raw).decode()
        if apns_certificate_file is not None and apns_private_key_file is not None:
            check = sdk_ast_push_validate(expected_environment, apns_certificate_file, apns_private_key_file)
            if not check['key_matches'] or not check['currently_valid']:
                raise ValueError('APNs certificate/key mismatch or certificate outside validity dates')
        if not changes:
            raise ValueError('Select at least one push setting to update')
        def operation(b):
            _, pnc = _app(b, app_name)
            fields = sorted(k for k, v in changes.items() if pnc.get(k) != v)
            if fields:
                pnc.update(changes)
                b.request('PUT', '/apps/' + segment(app_name), pnc)
            return {'app_name': app_name, 'changed': bool(fields), 'reused': not fields, 'fields': fields}
        return _run(expected_environment, operation)

    @mcp.tool()
    def sdk_tms_display_message(expected_environment: str, user_uuid: str, text: str) -> dict:
        """Send a real display-only message to an IDP user UUID through AST. This contacts
        the user's devices; use only for requested messaging. Requires management permission.
        Acceptance by the API does not prove delivery/read/acknowledgement. No TMS approval inferred.
        """
        user_uuid = _uuid(user_uuid)
        if not isinstance(text, str) or not text.strip() or len(text) > 10000:
            raise ValueError('Message text must contain 1–10000 characters')
        def operation(b):
            result = b.request('POST', '/display-message', {'userId': user_uuid, 'text': text})
            return {'accepted': True, 'user_id': user_uuid, 'delivery_verified': False,
                    'acknowledgement_supported': None,
                    'result': _select(result, ('id', 'messageId', 'status')) if isinstance(result, dict) else {}}
        return _run(expected_environment, operation)

    @mcp.tool()
    def sdk_ast_push_validate(expected_environment: str, certificate_file: str, private_key_file: str) -> dict:
        """Validate a local PEM certificate/private-key pair from private files (0600).
        Local-only: checks parseability, key match and validity dates; returns SHA-256
        fingerprint and expiry. Does not prove APNs entitlement, topic or server acceptance.
        Encrypted keys without an external decryption provider are unsupported.
        """
        configuration(expected_environment)
        from datetime import datetime, timezone
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        cert_raw, key_raw = _private_file(certificate_file), _private_file(private_key_file)
        try:
            cert = x509.load_pem_x509_certificate(cert_raw)
            key = serialization.load_pem_private_key(key_raw, password=None)
            encoding, fmt = serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
            matching = cert.public_key().public_bytes(encoding, fmt) == key.public_key().public_bytes(encoding, fmt)
        except (ValueError, TypeError):
            raise ValueError('Cannot parse unencrypted PEM certificate/key material') from None
        now = datetime.now(timezone.utc)
        start, end = cert.not_valid_before_utc, cert.not_valid_after_utc
        return {'local_only': True, 'key_matches': matching, 'currently_valid': start <= now <= end,
                'valid_from': start.isoformat(), 'valid_until': end.isoformat(),
                'sha256': cert.fingerprint(hashes.SHA256()).hex(), 'apns_acceptance_verified': False}
