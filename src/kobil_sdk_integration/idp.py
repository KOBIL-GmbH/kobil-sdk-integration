"""Optional IDP test-user provisioning; secrets stay in the local runtime."""
import json
import os
from pathlib import Path
import re
import secrets
import stat

from .backend import AST, BackendError, authentication, https_url, segment


def configuration(expected_environment=None):
    selected = os.environ.get('KOBIL_SDK_IDP_CONNECTION')
    if not selected:
        raise BackendError('IDP_CONNECTION_NOT_SELECTED: configure KOBIL_SDK_IDP_CONNECTION with an IDP credential reference')
    try:
        cfg = json.loads(Path(selected).expanduser().read_text(encoding='utf-8'))
        if set(cfg) != {'schema_version', 'environment', 'realm', 'admin_url', 'auth', 'allow_test_provisioning'}:
            raise ValueError()
        if cfg['schema_version'] != 2 or type(cfg['allow_test_provisioning']) is not bool:
            raise ValueError()
        segment(cfg['environment']); segment(cfg['realm']); https_url(cfg['admin_url'])
        authentication(cfg)
    except Exception:
        raise BackendError('IDP_CONNECTION_INVALID: check the IDP profile; credentials must be references') from None
    if expected_environment is not None and expected_environment != cfg['environment']:
        raise BackendError('IDP_ENVIRONMENT_MISMATCH')
    return cfg


class IDP(AST):
    def __init__(self, cfg):
        super().__init__(dict(cfg, tenant=cfg['realm']))
        self.root = cfg['admin_url'].rstrip('/') + '/realms/' + segment(cfg['realm'])

    def request(self, method, path, body=None, **kwargs):
        return self.send(method, self.root + path,
                         headers={'Authorization': 'Bearer ' + self.token()}, json=body, **kwargs)

    def writable(self):
        if self.cfg['allow_test_provisioning'] is not True:
            raise BackendError('IDP_TEST_PROVISIONING_DISABLED')

    def user_get(self, username):
        segment(username)
        rows = self.request('GET', '/users', params={'username': username, 'exact': 'true', 'max': 2})
        if not isinstance(rows, list) or len(rows) > 1:
            raise BackendError('IDP_USER_RESPONSE_INVALID')
        if not rows:
            return {'username': username, 'exists': False}
        row = rows[0]
        if not isinstance(row, dict) or row.get('username') != username or type(row.get('enabled')) is not bool:
            raise BackendError('IDP_USER_RESPONSE_INVALID')
        uid = row.get('id'); segment(uid)
        return {'username': username, 'exists': True, 'user_id': uid, 'enabled': row['enabled']}

    def user_create(self, username):
        self.writable()
        existing = self.user_get(username)
        if existing['exists']:
            raise BackendError('IDP_USER_EXISTS: select the existing user; it was not changed')
        # One POST only; transport failure may mean it committed. Never replay.
        self.request('POST', '/users', {'username': username, 'enabled': True})
        result = self.user_get(username)
        if not result['exists']:
            raise BackendError('IDP_USER_READBACK_FAILED: inspect backend state before retrying creation')
        return dict(result, created=True)

    def activation_write(self, username, user_id, output_path, period='1d', replace_existing=False):
        self.writable()
        if not isinstance(period, str) or not re.fullmatch(r'(?:[1-9]|1[0-9]|2[0-4])h|1d', period):
            raise ValueError('Activation lifetime must be 1–24h or 1d.')
        if type(replace_existing) is not bool:
            raise ValueError('replace_existing must be boolean')
        user = self.user_get(username)
        if not user['exists'] or user['user_id'] != user_id or not user['enabled']:
            raise BackendError('IDP_ACTIVATION_USER_MISMATCH_OR_DISABLED')
        path = '/users/' + segment(user_id)
        credentials = self.request('GET', path + '/credentials')
        if not isinstance(credentials, list) or any(not isinstance(c, dict) or not isinstance(c.get('type'), str) for c in credentials):
            raise BackendError('IDP_CREDENTIAL_METADATA_INVALID')
        if any(c['type'] != 'ACTIVATION_CODE' for c in credentials):
            raise BackendError('IDP_USER_ALREADY_ENROLLED: this tool only provisions unactivated test users')
        if credentials and not replace_existing:
            raise BackendError('IDP_ACTIVATION_EXISTS: inspect previous attempts before explicitly replacing')
        # Reserve/write/fsync delivery BEFORE changing the backend. Even uncertain
        # responses leave a recoverable private copy; never expose it in errors.
        payload = {'username': username, 'user_uuid': user_id,
                   'activation_code': str(secrets.randbelow(90000000) + 10000000),
                   'environment': self.cfg['environment'], 'realm': self.cfg['realm'],
                   'period': period, 'status': 'pending'}
        target, fd = reserve_private_output(output_path)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            def save():
                stream.seek(0); json.dump(payload, stream); stream.truncate(); stream.flush(); os.fsync(stream.fileno())
            save()
            try:
                self.request('PUT', path, {'credentials': [{'type': 'ACTIVATION_CODE',
                    'credentialData': json.dumps({'period': period}),
                    'secretData': json.dumps({'code': payload['activation_code']})}]})
            except BackendError:
                # Treat every failed write conservatively; no automatic second PUT.
                return {'path': str(target), 'status': 'unknown', 'retry_safe': False,
                        'message': 'Private credential retained. Inspect backend state before retrying or using it.'}
            payload['status'] = 'issued'
            save()
        return {'path': str(target), 'status': 'issued', 'username': username,
                'user_id': user_id, 'period': period, 'activation_verified': False}


def reserve_private_output(value):
    if os.name != 'posix':
        raise BackendError('PRIVATE_DELIVERY_UNAVAILABLE: secure file delivery requires POSIX permissions in this preview')
    target = Path(value).expanduser().absolute()
    # Pin the private parent directory descriptor to avoid symlink substitution.
    parent = target.parent
    if parent.resolve() != parent or target.name in {'.', '..'}:
        raise ValueError('Use a private directory without symlinks.')
    directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(directory)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError('Output directory must be owned by you and have mode 0700.')
        fd = os.open(target.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        return target, fd
    finally:
        os.close(directory)
