"""Read environment facts an integrator would otherwise have to guess.

Without these an agent needs Keycloak admin access to learn which login client to
name, and has to guess the platform string AST accepts. Both are read-only lookups
against the configured environment; neither needs admin rights.
"""
import base64
import json

import httpx

from .backend import BackendError, segment

# Standard KOBIL Shift flow clients. Presence is probed, never assumed.
CANDIDATE_CLIENTS = (
    'IDPLoginHeadlessV2', 'IDPRegistrationHeadlessV2', 'IDPSubsequentLoginHeadlessV2',
    'IDPChangePasswordHeadlessV2', 'IDPForgotPasswordHeadlessV2', 'IDPBiometricAppLockHeadlessV2',
    'KssIdpEnrollment', 'KssIdpLogin', 'KssIdpChangePassword', 'KssIdpForgotPassword',
)


def platforms(backend):
    """Platform values this AST tenant accepts for a version registration."""
    value = backend.request('GET', '/platforms')
    names = value if isinstance(value, list) else (value or {}).get('data')
    if not isinstance(names, list) or any(not isinstance(n, str) or not n for n in names):
        raise BackendError('Unrecognized platform listing')
    return {'platforms': names,
            'note': 'Use one of these verbatim in sdk_app_version_ensure; casing matters.'}


def token_roles(backend):
    """Which roles actually reach the issued token.

    A role granted to the service account still has to travel on a scope the token
    request asks for. When it does not, the token carries no roles and AST answers
    403 while authentication itself looks healthy.
    """
    token = backend.token()
    try:
        part = token.split('.')[1]
        claims = json.loads(base64.urlsafe_b64decode(part + '=' * (-len(part) % 4)))
    except Exception:
        raise BackendError('Issued token is not a readable JWT') from None
    roles = sorted({role
                    for entry in (claims.get('resource_access') or {}).values()
                    if isinstance(entry, dict)
                    for role in entry.get('roles', []) if isinstance(role, str)})
    realm_roles = [r for r in (claims.get('realm_access') or {}).get('roles', []) if isinstance(r, str)]
    return {'client_roles_in_token': roles, 'realm_roles_in_token': sorted(realm_roles),
            'scope_requested': (backend.cfg.get('oauth') or {}).get('scope'),
            'note': 'AST management writes need one of the roles Admin, AstServicesAdmin or a '
                    'ks-management role in the token; app, version and configuration writes '
                    'succeeded with Admin alone on the verification realm (2026-09-16). If none is '
                    'present, request the optional scope that carries one via oauth.scope.'}


def idp_clients(cfg, client_ids=None):
    """Probe which flow clients exist, without Keycloak admin rights.

    The IDP answers a token request for an unknown client with invalid_client and for
    a known one with invalid_grant. No real account is used and nothing is written.
    """
    oauth = cfg.get('oauth')
    if not oauth:
        raise BackendError('Client discovery needs an oauth token endpoint in the connection file')
    names = tuple(client_ids) if client_ids else CANDIDATE_CLIENTS
    if not 1 <= len(names) <= 40 or any(not isinstance(n, str) for n in names):
        raise ValueError('Provide 1 to 40 client ids')
    for name in names:
        segment(name)
    present, absent = [], []
    with httpx.Client(timeout=20, follow_redirects=False, trust_env=False) as client:
        for name in names:
            try:
                response = client.post(oauth['token_url'], data={
                    'grant_type': 'password', 'client_id': name,
                    'username': 'kobil-sdk-probe-nonexistent', 'password': 'kobil-sdk-probe'})
                error = (response.json() or {}).get('error') if response.content else None
            except Exception:
                raise BackendError('IDP probe failed; check the token endpoint and connectivity') from None
            if error == 'invalid_client' or response.status_code == 401 and error == 'invalid_client':
                absent.append(name)
            elif isinstance(error, str):
                present.append(name)
            else:
                absent.append(name)
    return {'clients_present': present, 'clients_absent': absent,
            'note': 'mc_config.json iam.clientId must name the ACTIVATION client (the one bound to the '
                    'flow that consumes an activation code); the login client is passed by the app '
                    'as an override for login only. Presence does not '
                    'prove the flow is configured for your tenant.'}
