"""Shared administrative transport with explicit realm selection and bounded discovery."""
import os
import re
from .backend import AST, BackendError, configuration, segment
from .idp_transport import admin_token, _call

SENSITIVE = re.compile(r'password|secret|credentialdata|credentials|private.?key|bindcredential|access.?token|refresh.?token|id.?token|client.?assertion|representation', re.I)


SAFE_METADATA = {'passwordPolicy', 'accessTokenLifespan', 'accessTokenLifespanForImplicitFlow',
                 'access.token.claim', 'id.token.claim', 'userinfo.token.claim',
                 'clientAuthenticatorType', 'clientAuthMethod', 'credentialTypes',
                 'passwordCredentialGrantAllowed', 'refreshTokenMaxReuse', 'revokeRefreshToken'}


def redact(value):
    if isinstance(value, dict):
        return {k: ('[redacted]' if SENSITIVE.search(k) and k not in SAFE_METADATA else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


class Admin:
    def __init__(self, expected_environment, realm=None):
        self.cfg = configuration(expected_environment)
        if not self.cfg.get('admin'):
            raise BackendError('IDP administration is not configured for this connection')
        self.realm = realm if realm is not None else self.cfg['tenant']
        self.prefix = '/auth/admin/realms/' + segment(self.realm)
        self.backend = AST(self.cfg)
        self.token = None

    def __enter__(self):
        try:
            self.token = admin_token(self.backend)
            return self
        except BaseException:
            self.backend.close()
            raise

    def __exit__(self, *args):
        self.token = None
        self.backend.close()

    def raw(self, method, path, body=None, params=None):
        """Internal only: obtain a representation for read/merge/write, never expose as a tool."""
        if (path and not path.startswith('/')) or '?' in path or '#' in path:
            raise ValueError('Expected an internal path without query or fragment')
        return _call(self.backend, self.token, method, self.prefix + path, body, params)

    def _safe(self, result):
        cleaned = redact(result)
        # Also remove configured credential values if a service echoes them in an unrelated field.
        refs = [self.cfg['admin'].get('password_env'), self.cfg.get('token_env'),
                self.cfg.get('oauth', {}).get('client_secret_env')]
        secrets = [self.token] + [os.environ.get(ref) for ref in refs if ref]
        def visit(x):
            if isinstance(x, str):
                for secret in secrets:
                    if secret: x=x.replace(secret, '[redacted]')
            elif isinstance(x, dict): x={k:visit(v) for k,v in x.items()}
            elif isinstance(x, list): x=[visit(v) for v in x]
            return x
        return visit(cleaned)

    def call(self, method, path, body=None, params=None):
        result = self.raw(method, path, body, params)
        return self._safe(result)

    def call_global(self, method, path, body=None, params=None):
        if not (path == '/admin/serverinfo' or path == '/admin/realms' or path.startswith('/admin/realms/')):
            raise ValueError('Unsupported global IDP administration path')
        if '?' in path or '#' in path:
            raise ValueError('Use query parameters separately')
        return self._safe(_call(self.backend, self.token, method, '/auth' + path, body, params))

    def page(self, path, first=0, max_results=50, params=None, paginated=True):
        if type(first) is not int or first < 0 or type(max_results) is not int or not 1 <= max_results <= 200:
            raise ValueError('first must be nonnegative; max_results must be 1..200')
        query = dict(params or {})
        if paginated:
            query.update(first=first, max=max_results + 1)
        result = self.call('GET', path, params=query)
        if not isinstance(result, list):
            raise BackendError('Expected an IDP collection response')
        if paginated and len(result) > max_results + 1:
            raise BackendError('IDP ignored pagination; refusing to report an incomplete collection as complete')
        window = result if paginated else result[first:]
        more = len(window) > max_results
        return {'items': window[:max_results], 'first': first,
                'next_offset': first + max_results if more else None,
                'complete': not more, 'environment': self.cfg['environment'], 'realm': self.realm}

    def update(self, path, changes, allowed_fields):
        if not isinstance(changes, dict) or not changes or set(changes) - set(allowed_fields):
            raise ValueError('Provide supported fields to update')
        current = self.raw('GET', path)
        if not isinstance(current, dict):
            raise BackendError('Expected an IDP object before updating')
        if all(current.get(k) == v for k, v in changes.items()):
            return {'changed': False, 'realm': self.realm}
        updated = {**current, **changes}
        if isinstance(current.get('config'), dict) and isinstance(changes.get('config'), dict):
            updated['config'] = {**current['config'], **changes['config']}
        self.raw('PUT', path, updated)
        return {'changed': True, 'updated_fields': sorted(changes), 'realm': self.realm,
                'readback_verified': False}


def load_private_json(path):
    """Read one explicitly selected private configuration file inside the server."""
    import json
    import stat
    from pathlib import Path
    try:
        with Path(path).expanduser().open('rb') as stream:
            meta = os.fstat(stream.fileno())
            if not stat.S_ISREG(meta.st_mode) or (os.name != 'nt' and meta.st_mode & 0o077):
                raise ValueError()
            data = stream.read(65537)
        if len(data) > 65536:raise ValueError()
        result=json.loads(data)
        if not isinstance(result,dict):raise ValueError()
        return result
    except Exception:
        raise ValueError('Expected a private JSON object file (Unix mode 0600, at most 64 KiB)') from None
