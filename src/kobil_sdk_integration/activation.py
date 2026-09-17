"""Provision the user and the one-time code a device needs for its first activation.

Registering the app and its version in AST does not make the app usable: the first
launch reports ACTIVATION_REQUIRED and asks for a user id and an activation code.
Issuing that code is an IDP operation, not an AST one, and it needs administrative
rights the AST service account does not carry. Without these tools the step has to
be done by hand in the portal, which is where integrations stall.

The activation user is deliberately not the registration user recorded on the
version: those two roles are kept separate.
"""
import json
import os
import re
import secrets

from .backend import BackendError, segment

USERNAME = re.compile(r'[A-Za-z0-9._@+-]{3,120}')
PERIOD = re.compile(r'[1-9][0-9]{0,3}[mhd]')
UUID4 = re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')


def admin_settings(cfg):
    """The IDP administrative connection, with its credential read from the environment."""
    admin = cfg.get('admin')
    if not admin:
        raise BackendError('No IDP administration configured; add an "admin" block to the '
                           'connection file (idp_url, realm, client_id, username, password_env)')
    secret = os.environ.get(admin['password_env'])
    if not secret:
        raise BackendError('IDP administrator credential is not configured in the runtime environment')
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


def find_user(backend, username, token=None):
    """Return the tenant user with this exact username, or None."""
    if not isinstance(username, str) or not USERNAME.fullmatch(username):
        raise ValueError('Provide a username of 3 to 120 characters')
    token = token or admin_token(backend)
    found = _call(backend, token, 'GET',
                  '/auth/admin/realms/%s/users' % segment(backend.cfg['tenant']),
                  params={'username': username, 'exact': 'true', 'max': 2})
    if not isinstance(found, list):
        raise BackendError('Unrecognized user listing from the IDP')
    for entry in found:
        if isinstance(entry, dict) and entry.get('username', '').lower() == username.lower():
            if not isinstance(entry.get('id'), str) or not UUID4.fullmatch(entry['id']):
                raise BackendError('User record carries no usable identifier')
            return entry
    return None


def _group_id(backend, token, name):
    groups = _call(backend, token, 'GET',
                   '/auth/admin/realms/%s/groups' % segment(backend.cfg['tenant']),
                   params={'search': name, 'max': 50})
    if not isinstance(groups, list):
        raise BackendError('Unrecognized group listing from the IDP')
    for entry in groups:
        if isinstance(entry, dict) and entry.get('name') == name and isinstance(entry.get('id'), str):
            return entry['id']
    raise BackendError('Group "%s" does not exist in this tenant; name the group ordinary '
                       'users belong to' % name)


def ensure_user(backend, username, email=None, first_name='KOBIL', last_name='Test User',
                group='ks-users'):
    """Create a passwordless tenant user for device activation, or report the existing one.

    No password is set: the person activating the device chooses one, and the realm
    password policy is applied then. The user joins the group ordinary tenant users
    belong to, because group membership, not the bare account, is what the Shift flows
    read. An existing user is never modified.
    """
    if email is not None and (not isinstance(email, str) or not re.fullmatch(r'[^@\s]{1,64}@[^@\s]{3,190}', email)):
        raise ValueError('Provide a valid email address or none')
    for value in (first_name, last_name):
        if not isinstance(value, str) or not re.fullmatch(r"[\w .'-]{1,60}", value):
            raise ValueError('Provide a plain first and last name')
    if not isinstance(group, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,120}', group):
        raise ValueError('Provide the group name ordinary tenant users belong to')
    token = admin_token(backend)
    realm = segment(backend.cfg['tenant'])
    existing = find_user(backend, username, token)
    if existing:
        return {'username': existing['username'], 'user_uuid': existing['id'], 'created': False,
                'enabled': bool(existing.get('enabled')),
                'note': 'Existing user reused; nothing was modified.'}
    group_uuid = _group_id(backend, token, group)
    # The KOBIL v3_user endpoint refuses an administration token issued by the master
    # realm, so the user is created through the standard administration API and shaped
    # like the tenant's existing users.
    _call(backend, token, 'POST', '/auth/admin/realms/%s/users' % realm, {
        'username': username, 'email': email or '%s@example.com' % username,
        'emailVerified': True, 'enabled': True,
        'firstName': first_name, 'lastName': last_name,
        'attributes': {'status': ['REGISTERED']}})
    created = find_user(backend, username, token)
    if not created:
        raise BackendError('The IDP accepted the user but it cannot be read back; inspect the tenant')
    _call(backend, token, 'PUT', '/auth/admin/realms/%s/users/%s/groups/%s' % (
        realm, segment(created['id']), segment(group_uuid)))
    joined = _call(backend, token, 'GET', '/auth/admin/realms/%s/users/%s/groups' % (
        realm, segment(created['id'])))
    names = [g.get('name') for g in joined if isinstance(g, dict)] if isinstance(joined, list) else []
    if group not in names:
        raise BackendError('The user was created but did not join group "%s"; complete or remove '
                           'it before activating' % group)
    return {'username': created['username'], 'user_uuid': created['id'], 'created': True,
            'enabled': bool(created.get('enabled')), 'groups': sorted(n for n in names if n),
            'note': 'The user has no credential yet. The activation journey sets no password, so '
                    'issue one with set_login_password before the first login; the password '
                    'field of an activation screen is not sent to the IDP.'}


def set_activation_code(backend, user_uuid, valid_for='60d', digits=8):
    """Issue a fresh one-time activation code for this user and confirm it was stored.

    The code is generated here, never accepted as an argument, so it cannot arrive
    through a chat transcript or a shell history. It is returned once.
    """
    if not isinstance(user_uuid, str) or not UUID4.fullmatch(user_uuid):
        raise ValueError('Provide the tenant user UUID')
    if not isinstance(valid_for, str) or not PERIOD.fullmatch(valid_for):
        raise ValueError('Provide a validity such as 30m, 12h or 60d')
    if type(digits) is not int or not 6 <= digits <= 12:
        raise ValueError('Choose a code length of 6 to 12 digits')
    token = admin_token(backend)
    realm = segment(backend.cfg['tenant'])
    user = _call(backend, token, 'GET', '/auth/admin/realms/%s/users/%s' % (realm, segment(user_uuid)))
    if not isinstance(user, dict) or user.get('id') != user_uuid:
        raise BackendError('That user does not exist in this tenant')
    code = ''.join(secrets.choice('0123456789') for _ in range(digits))
    # The representation is sent back unchanged apart from the added credential, so an
    # update cannot quietly drop profile fields.
    body = {key: user[key] for key in ('username', 'email', 'firstName', 'lastName', 'enabled',
                                       'emailVerified') if key in user}
    body['credentials'] = [{'type': 'ACTIVATION_CODE',
                            'credentialData': json.dumps({'period': valid_for}),
                            'secretData': json.dumps({'code': code})}]
    _call(backend, token, 'PUT', '/auth/admin/realms/%s/users/%s' % (realm, segment(user_uuid)), body)
    stored = _call(backend, token, 'GET',
                   '/auth/admin/realms/%s/users/%s/credentials' % (realm, segment(user_uuid)))
    types = [c.get('type') for c in stored if isinstance(c, dict)] if isinstance(stored, list) else []
    if 'ACTIVATION_CODE' not in types:
        raise BackendError('The activation code was not stored; do not hand out the code')
    return {'user_uuid': user_uuid, 'username': user.get('username'),
            'activation_code': code, 'valid_for': valid_for,
            'credential_types': sorted(t for t in types if isinstance(t, str)),
            'note': 'One-time secret, shown once. Type it into the app together with the '
                    'username to activate this device. Never commit or log it. A failed '
                    'attempt may already have consumed it; inspect state before reissuing.'}


PASSWORD_LOWER = 'abcdefghjkmnpqrstuvwxyz'
PASSWORD_UPPER = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
PASSWORD_DIGITS = '23456789'


def generate_password(length):
    """A password that satisfies the realm policy: upper, lower and digit, no ambiguous glyphs."""
    alphabet = PASSWORD_LOWER + PASSWORD_UPPER + PASSWORD_DIGITS
    while True:
        candidate = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c in PASSWORD_LOWER for c in candidate) and any(c in PASSWORD_UPPER for c in candidate)
                and any(c in PASSWORD_DIGITS for c in candidate)):
            return candidate


def set_login_password(backend, user_uuid, length=14):
    """Set the permanent IDP password the login journey checks, and confirm it was stored.

    The activation journey (activation code + AST activate/link) sets no password, and a
    user created by ensure_user has no credential at all, so the first login would fail
    with a wrong-password answer. The password is generated here, never accepted as an
    argument, and returned once.
    """
    if not isinstance(user_uuid, str) or not UUID4.fullmatch(user_uuid):
        raise ValueError('Provide the tenant user UUID')
    if type(length) is not int or not 10 <= length <= 64:
        raise ValueError('Choose a password length of 10 to 64 characters')
    token = admin_token(backend)
    realm = segment(backend.cfg['tenant'])
    user = _call(backend, token, 'GET', '/auth/admin/realms/%s/users/%s' % (realm, segment(user_uuid)))
    if not isinstance(user, dict) or user.get('id') != user_uuid:
        raise BackendError('That user does not exist in this tenant')
    password = generate_password(length)
    _call(backend, token, 'PUT', '/auth/admin/realms/%s/users/%s/reset-password' % (realm, segment(user_uuid)),
          {'type': 'password', 'value': password, 'temporary': False})
    stored = _call(backend, token, 'GET',
                   '/auth/admin/realms/%s/users/%s/credentials' % (realm, segment(user_uuid)))
    types = [c.get('type') for c in stored if isinstance(c, dict)] if isinstance(stored, list) else []
    if 'password' not in types:
        raise BackendError('The password was not stored; do not hand it out')
    return {'user_uuid': user_uuid, 'username': user.get('username'), 'password': password,
            'credential_types': sorted(t for t in types if isinstance(t, str)),
            'note': 'Permanent IDP password, shown once. It is what the email-and-password login '
                    'journey checks; the activation journey never sets one. Hand it to the tester '
                    'as the login password. Never commit or log it.'}


def user_status(backend, user_uuid):
    """What the IDP records for a test user: credentials, sessions, failed logins.

    This is the reliable record of a device flow when the app's console goes quiet: a
    login creates a session for the login client, a wrong password counts a failure, and
    an activation consumes the ACTIVATION_CODE credential. Reads only.
    """
    if not isinstance(user_uuid, str) or not UUID4.fullmatch(user_uuid):
        raise ValueError('Provide the tenant user UUID')
    token = admin_token(backend)
    realm = segment(backend.cfg['tenant'])
    base = '/auth/admin/realms/%s/users/%s' % (realm, segment(user_uuid))
    user = _call(backend, token, 'GET', base)
    if not isinstance(user, dict) or user.get('id') != user_uuid:
        raise BackendError('That user does not exist in this tenant')
    creds = _call(backend, token, 'GET', base + '/credentials')
    sessions = _call(backend, token, 'GET', base + '/sessions')
    force = _call(backend, token, 'GET',
                  '/auth/admin/realms/%s/attack-detection/brute-force/users/%s' % (realm, segment(user_uuid)))
    force = force if isinstance(force, dict) else {}
    return {
        'user_uuid': user_uuid, 'username': user.get('username'), 'enabled': bool(user.get('enabled')),
        'credential_types': sorted(c.get('type') for c in creds if isinstance(c, dict) and isinstance(c.get('type'), str))
                            if isinstance(creds, list) else [],
        'sessions': [{'start_ms': s.get('start'), 'last_access_ms': s.get('lastAccess'),
                      'clients': sorted((s.get('clients') or {}).values())}
                     for s in sessions if isinstance(s, dict)] if isinstance(sessions, list) else [],
        'failed_logins': int(force.get('numFailures') or 0),
        'last_failure_ms': force.get('lastFailure') or None,
        'locked': bool(force.get('disabled')),
        'note': 'A session for the login client proves a login reached the IDP; a failure count '
                'proves a rejected credential; a missing ACTIVATION_CODE credential means the '
                'code was consumed. Timestamps are epoch milliseconds.'}
