"""IDP authentication and HTTP transport; no app-flow policy."""
import os
from .backend import BackendError, segment

def admin_settings(cfg):
    """The IDP administrative connection, with its credential resolved server-side."""
    admin = cfg.get('admin')
    if not admin:
        raise BackendError('No IDP administration configured; add an "admin" block to the '
                           'connection file (idp_url, realm, client_id, username, credential or password_env)')
    from .backend import admin_reference
    from .credentials import resolve, CredentialError
    try:secret=resolve(admin_reference(admin))
    except CredentialError as error:raise BackendError(str(error)) from None
    return admin, secret


def admin_token(backend):
    """A Keycloak administration token. The password never leaves this process."""
    admin, secret = admin_settings(backend.cfg)
    url = '%s/auth/realms/%s/protocol/openid-connect/token' % (
        admin['idp_url'].rstrip('/'), segment(admin['realm']))
    result = backend.send('POST', url, data={
        'grant_type': 'password', 'client_id': admin['client_id'],
        'username': admin['username'], 'password': secret})
    token = result.get('access_token') if isinstance(result, dict) else None
    if not isinstance(token, str) or not token:
        raise BackendError('IDP administration did not return an access token')
    return token


def _call(backend, token, method, path, body=None, params=None, allow_not_found=False):
    url = backend.cfg['admin']['idp_url'].rstrip('/') + path
    kwargs = {'headers': {'Authorization': 'Bearer ' + token}, 'allow_not_found': allow_not_found}
    if body is not None:
        kwargs['json'] = body
    if params is not None:
        kwargs['params'] = params
    return backend.send(method, url, **kwargs)
