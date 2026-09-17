"""Provision the IDP browser flow and client that a first device activation needs.

Registering an app, a version and an activation code is not enough: the SDK opens an
OAuth authorisation request against a client, and that client's browser flow decides
which journey the user gets. A realm whose clients only carry login and registration
journeys cannot consume an activation code at all, whatever the app sends.

These helpers create a dedicated flow and a dedicated client for activation. They are
additive: nothing existing is modified, so a wrong guess is removed by deleting the two
resources this module created.
"""
import json
import re

from .activation import _call, admin_token
from .backend import BackendError, segment

ALIAS = re.compile(r'[A-Za-z0-9][A-Za-z0-9 ._-]{2,80}')
CLIENT_ID = re.compile(r'[A-Za-z0-9_.-]{3,120}')
THEME = re.compile(r'[A-Za-z0-9_-]{1,60}')
REQUIREMENTS = ('REQUIRED', 'ALTERNATIVE', 'DISABLED', 'CONDITIONAL')

# The order an activation walks, verified on a device 2026-09-16: mint the AST client
# (activate), verify the one-time code, bind that client to the user (link), then spend
# the code so it cannot be replayed. Two AST steps, not one: activate alone leaves the
# device unlinked and AST later answers 513_4036 ast_login_with_unactivated_client.
DEFAULT_STEPS = (
    'ast-login-authenticator',
    # KSSIDP has its own authenticators, and only these have templates in a KSSIDP theme.
    # kssidp-activation-code-verifier renders username + activation-code. The kobil-*
    # equivalents render templates a KSSIDP theme does not ship, so the IDP answers HTTP 500
    # with FreeMarker TemplateNotFoundException, and kssidp-verify-act-code renders nothing
    # at all and rejects the request with "Missing parameter: username".
    'kssidp-activation-code-verifier',
    'ast-login-authenticator',
    'kssidp-delete-activation-code',
)

# The variant with a password page. Unreachable on the current IDP build: Keycloak injects a
# history.replaceState script into every page rendered *after* a form POST, with raw &
# characters in its URL, which is fatal in XHTML. KSSIDP parses strictly and discards that
# page silently: no delegate call, no post, the app waits forever with no error. So an
# activation can afford ONE rendered page, the code page. The login password is set with
# set_login_password instead. Check any suspect page with `xmllint --noout` before blaming
# the app.
PASSWORD_STEP_VARIANT = (
    'ast-login-authenticator',
    'kssidp-activation-code-verifier',
    'kssidp-configure-or-verify-password',
    'ast-login-authenticator',
    'kssidp-delete-activation-code',
)

# The login theme must ship the templates the chosen authenticators render. On this
# deployment kobil-lite carries the kssidp-* templates and is well-formed XHTML, which the
# SDK's strict parser requires.
DEFAULT_LOGIN_THEME = 'kobil-lite'

# An authenticator with no configuration falls back to its own defaults, which are not the
# ones an activation needs. The AST step in particular then demands an X-KOBIL-ASTCLIENTID
# header that a device cannot have before its first activation, and answers HTTP 406 with
# IDP subsystem 580. Keys name a step as "provider" (its first occurrence in the flow) or
# "provider#N" (its Nth occurrence), so the two AST steps get their own settings. The option
# name ast_clientid_required is inverted in the product: "true" makes the header optional.
DEFAULT_STEP_CONFIG = {
    'ast-login-authenticator#1': {'Action': 'activate', 'ast_clientid_required': 'true',
                                  'MLoA': 'none'},
    'ast-login-authenticator#2': {'Action': 'link', 'ast_clientid_required': 'false',
                                  'read_ast_data_from_session': 'true', 'MLoA': 'none'},
}
CONFIG_KEY = re.compile(r'[A-Za-z_][A-Za-z0-9_.-]{0,60}')
STEP_KEY = re.compile(r'(?P<provider>[A-Za-z0-9_.-]+)(?:#(?P<occurrence>[1-9][0-9]?))?')


def split_step_key(key):
    """'provider' -> (provider, 1); 'provider#2' -> (provider, 2)."""
    if not isinstance(key, str) or not STEP_KEY.fullmatch(key):
        raise ValueError('Name a step as "provider" or "provider#N"')
    match = STEP_KEY.fullmatch(key)
    return match.group('provider'), int(match.group('occurrence') or 1)


def nth_execution(executions, provider, occurrence):
    """The Nth execution of a provider in flow order, or None."""
    matches = [e for e in executions if isinstance(e, dict) and e.get('providerId') == provider]
    return matches[occurrence - 1] if len(matches) >= occurrence else None


def available_authenticators(backend, token):
    """Provider ids this IDP build actually offers, so a typo fails before any write."""
    found = _call(backend, token, 'GET',
                  '/auth/admin/realms/%s/authentication/authenticator-providers'
                  % segment(backend.cfg['tenant']))
    if not isinstance(found, list):
        raise BackendError('Unrecognized authenticator listing from the IDP')
    return {entry['id'] for entry in found if isinstance(entry, dict) and isinstance(entry.get('id'), str)}


def _flow(backend, token, alias):
    realm = segment(backend.cfg['tenant'])
    flows = _call(backend, token, 'GET', '/auth/admin/realms/%s/authentication/flows' % realm)
    if not isinstance(flows, list):
        raise BackendError('Unrecognized flow listing from the IDP')
    for entry in flows:
        if isinstance(entry, dict) and entry.get('alias') == alias:
            return entry
    return None


def describe_flow(backend, alias, token=None):
    """The executions of one flow, in order, as the IDP reports them."""
    if not isinstance(alias, str) or not ALIAS.fullmatch(alias):
        raise ValueError('Provide the flow alias')
    token = token or admin_token(backend)
    flow = _flow(backend, token, alias)
    if not flow:
        return {'alias': alias, 'exists': False, 'steps': []}
    executions = _call(backend, token, 'GET',
                       '/auth/admin/realms/%s/authentication/flows/%s/executions'
                       % (segment(backend.cfg['tenant']), segment(alias)))
    steps = [{'provider': e.get('providerId'), 'requirement': e.get('requirement'),
              'display_name': e.get('displayName'), 'index': e.get('index')}
             for e in executions if isinstance(e, dict)]
    return {'alias': alias, 'exists': True, 'flow_id': flow.get('id'), 'steps': steps}


def ensure_flow(backend, alias, steps=None, requirement='REQUIRED', description=None, step_config=None):
    """Create a top-level browser flow with these authenticators, or report the existing one.

    An existing flow is never rewritten: its steps are returned as they are, so a flow
    someone else tuned by hand is not silently reset.
    """
    if not isinstance(alias, str) or not ALIAS.fullmatch(alias):
        raise ValueError('Provide a flow alias of 3 to 81 characters')
    if requirement not in REQUIREMENTS:
        raise ValueError('Choose a documented requirement')
    # An explicitly empty list is a mistake, not a request for the defaults.
    steps = DEFAULT_STEPS if steps is None else tuple(steps)
    if not 1 <= len(steps) <= 12 or any(not isinstance(s, str) for s in steps):
        raise ValueError('Provide 1 to 12 authenticator provider ids')
    if description is not None and (not isinstance(description, str) or len(description) > 255):
        raise ValueError('Keep the description under 256 characters')
    token = admin_token(backend)
    realm = segment(backend.cfg['tenant'])
    existing = _flow(backend, token, alias)
    if existing:
        result = describe_flow(backend, alias, token)
        result['created'] = False
        result['note'] = 'Existing flow reused; its steps were not modified.'
        return result
    offered = available_authenticators(backend, token)
    unknown = [s for s in steps if s not in offered]
    if unknown:
        raise BackendError('This IDP build does not offer: %s' % ', '.join(sorted(unknown)))
    _call(backend, token, 'POST', '/auth/admin/realms/%s/authentication/flows' % realm, {
        'alias': alias, 'description': description or 'Device activation with an activation code',
        'providerId': 'basic-flow', 'topLevel': True, 'builtIn': False})
    created = _flow(backend, token, alias)
    if not created:
        raise BackendError('The IDP accepted the flow but it cannot be read back')
    for provider in steps:
        _call(backend, token, 'POST',
              '/auth/admin/realms/%s/authentication/flows/%s/executions/execution' % (realm, segment(alias)),
              {'provider': provider})
    executions = _call(backend, token, 'GET',
                       '/auth/admin/realms/%s/authentication/flows/%s/executions' % (realm, segment(alias)))
    for execution in executions if isinstance(executions, list) else []:
        if execution.get('requirement') == requirement:
            continue
        payload = dict(execution)
        payload['requirement'] = requirement
        _call(backend, token, 'PUT',
              '/auth/admin/realms/%s/authentication/flows/%s/executions' % (realm, segment(alias)), payload)
    applied = DEFAULT_STEP_CONFIG if step_config is None else step_config
    if not isinstance(applied, dict):
        raise ValueError('Provide step configuration as a mapping of step key to settings')
    configured = []
    for key, config in applied.items():
        provider, occurrence = split_step_key(key)
        if list(steps).count(provider) >= occurrence:
            configure_step(backend, alias, provider, config, token, occurrence)
            configured.append(key)
    result = describe_flow(backend, alias, token)
    result['created'] = True
    placed = [s['provider'] for s in result['steps']]
    if placed != list(steps):
        raise BackendError('The flow was created but its steps read back as %s' % placed)
    result['step_config_applied'] = sorted(configured)
    result['note'] = ('Bind this flow to a client with sdk_activation_client_ensure. '
                      'Delete the flow to undo; nothing existing was modified.')
    return result


def configure_step(backend, alias, provider, config, token=None, occurrence=1):
    """Attach authenticator configuration to one step of a flow. Verified by readback.

    occurrence picks the Nth step that runs this provider, counted in flow order, so a
    flow with two AST steps can give activate and link their own settings.
    """
    if not isinstance(alias, str) or not ALIAS.fullmatch(alias):
        raise ValueError('Provide the flow alias')
    if not isinstance(provider, str) or not provider:
        raise ValueError('Provide the authenticator provider id')
    if type(occurrence) is not int or not 1 <= occurrence <= 12:
        raise ValueError('occurrence counts a provider\'s steps from 1')
    if not isinstance(config, dict) or not config or len(config) > 30:
        raise ValueError('Provide 1 to 30 configuration entries')
    for key, value in config.items():
        if not isinstance(key, str) or not CONFIG_KEY.fullmatch(key):
            raise ValueError('Configuration keys must be plain identifiers')
        if not isinstance(value, str) or len(value) > 4000:
            raise ValueError('Configuration values must be strings')
    token = token or admin_token(backend)
    realm = segment(backend.cfg['tenant'])
    executions = _call(backend, token, 'GET',
                       '/auth/admin/realms/%s/authentication/flows/%s/executions' % (realm, segment(alias)))
    if not isinstance(executions, list):
        raise BackendError('Unrecognized execution listing from the IDP')
    step = nth_execution(executions, provider, occurrence)
    label = provider if occurrence == 1 else '%s#%d' % (provider, occurrence)
    if not step:
        raise BackendError('Flow "%s" has no step %s' % (alias, label))
    if not step.get('configurable'):
        raise BackendError('Step %s does not accept configuration' % label)
    config_alias = 'kobil-sdk-%s' % label.replace('#', '-')
    existing = step.get('authenticationConfig')
    if existing:
        _call(backend, token, 'PUT', '/auth/admin/realms/%s/authentication/config/%s' % (realm, segment(existing)),
              {'id': existing, 'alias': config_alias, 'config': config})
    else:
        _call(backend, token, 'POST',
              '/auth/admin/realms/%s/authentication/executions/%s/config' % (realm, segment(step['id'])),
              {'alias': config_alias, 'config': config})
    refreshed = _call(backend, token, 'GET',
                      '/auth/admin/realms/%s/authentication/flows/%s/executions' % (realm, segment(alias)))
    step = nth_execution(refreshed if isinstance(refreshed, list) else [], provider, occurrence)
    stored_id = (step or {}).get('authenticationConfig')
    if not stored_id:
        raise BackendError('The configuration was not stored on step %s' % label)
    stored = _call(backend, token, 'GET',
                   '/auth/admin/realms/%s/authentication/config/%s' % (realm, segment(stored_id)))
    values = (stored or {}).get('config') or {}
    missing = {k: v for k, v in config.items() if values.get(k) != v}
    if missing:
        raise BackendError('Stored configuration does not match for: %s' % ', '.join(sorted(missing)))
    return {'alias': alias, 'provider': provider, 'occurrence': occurrence, 'config': values,
            'note': 'Authenticator defaults are not activation defaults; this is what the '
                    'step actually runs with.'}


def attach_client_scope(backend, client_uuid, scope_name, token=None):
    """Give the client the scope that carries the AST client id into the access token.

    Without it the token has no AST client id, and the SDK refuses the very last step of an
    activation with "AST client id is not set in IAM access token", status
    CannotAcquireTokenData, after the IDP has already issued a perfectly good token set.
    """
    if not isinstance(scope_name, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,60}', scope_name):
        raise ValueError('Provide the client scope name')
    token = token or admin_token(backend)
    realm = segment(backend.cfg['tenant'])
    scopes = _call(backend, token, 'GET', '/auth/admin/realms/%s/client-scopes' % realm)
    if not isinstance(scopes, list):
        raise BackendError('Unrecognized client scope listing from the IDP')
    scope = next((s for s in scopes if isinstance(s, dict) and s.get('name') == scope_name), None)
    if not scope:
        raise BackendError('This realm has no client scope "%s"; name the scope that carries '
                           'the AST client id' % scope_name)
    _call(backend, token, 'PUT', '/auth/admin/realms/%s/clients/%s/default-client-scopes/%s'
          % (realm, segment(client_uuid), segment(scope['id'])))
    attached = _call(backend, token, 'GET',
                     '/auth/admin/realms/%s/clients/%s/default-client-scopes' % (realm, segment(client_uuid)))
    names = sorted(s.get('name') for s in attached if isinstance(s, dict)) if isinstance(attached, list) else []
    if scope_name not in names:
        raise BackendError('The client scope "%s" did not attach' % scope_name)
    return names


def ensure_client(backend, client_id, flow_alias, login_theme, redirect_uri,
                  ast_client_scope='ast'):
    """Create the public client the app names in mc_config.json, bound to that flow."""
    if not isinstance(client_id, str) or not CLIENT_ID.fullmatch(client_id):
        raise ValueError('Provide a client id of 3 to 120 characters')
    if not isinstance(flow_alias, str) or not ALIAS.fullmatch(flow_alias):
        raise ValueError('Provide the flow alias to bind')
    if not isinstance(login_theme, str) or not THEME.fullmatch(login_theme):
        raise ValueError('Provide the login theme name')
    if not isinstance(redirect_uri, str) or not re.fullmatch(r'[A-Za-z0-9_.:/\-*]{1,200}', redirect_uri):
        raise ValueError('Provide the redirect URI the SDK is configured with')
    token = admin_token(backend)
    realm = segment(backend.cfg['tenant'])
    found = _call(backend, token, 'GET', '/auth/admin/realms/%s/clients' % realm,
                  params={'clientId': client_id, 'max': 2})
    if not isinstance(found, list):
        raise BackendError('Unrecognized client listing from the IDP')
    existing = next((c for c in found if isinstance(c, dict) and c.get('clientId') == client_id), None)
    if existing:
        return {'client_id': client_id, 'created': False,
                'login_theme': (existing.get('attributes') or {}).get('login_theme'),
                'flow_overrides': existing.get('authenticationFlowBindingOverrides'),
                'note': 'Existing client reused; nothing was modified.'}
    flow = _flow(backend, token, flow_alias)
    if not flow:
        raise BackendError('Flow "%s" does not exist; create it first' % flow_alias)
    _call(backend, token, 'POST', '/auth/admin/realms/%s/clients' % realm, {
        'clientId': client_id, 'protocol': 'openid-connect', 'enabled': True,
        'publicClient': True, 'standardFlowEnabled': True, 'directAccessGrantsEnabled': False,
        'serviceAccountsEnabled': False, 'redirectUris': [redirect_uri],
        # No pkce.code.challenge.method here on purpose. KSSIDP obtains its own AST client
        # data, and therefore its own PKCE pair, after the app has already built the
        # authorisation URL. Forcing PKCE on the client makes the token exchange fail with
        # invalid_grant, "PKCE verification failed: Code mismatch", at the very last step of
        # an otherwise successful activation.
        'attributes': {'login_theme': login_theme},
        'authenticationFlowBindingOverrides': {'browser': flow['id']},
        'description': 'First device activation for MC SDK apps'})
    found = _call(backend, token, 'GET', '/auth/admin/realms/%s/clients' % realm,
                  params={'clientId': client_id, 'max': 2})
    created = next((c for c in found if isinstance(c, dict) and c.get('clientId') == client_id), None)
    if not created:
        raise BackendError('The IDP accepted the client but it cannot be read back')
    bound = (created.get('authenticationFlowBindingOverrides') or {}).get('browser')
    if bound != flow['id']:
        raise BackendError('The client was created but its browser flow is not the requested one')
    attached = attach_client_scope(backend, created['id'], ast_client_scope, token)
    return {'client_id': client_id, 'created': True, 'client_uuid': created.get('id'),
            'login_theme': (created.get('attributes') or {}).get('login_theme'),
            'bound_flow': flow_alias, 'redirect_uris': created.get('redirectUris'),
            'default_client_scopes': attached,
            'note': 'Name this client in mc_config.json iam.clientId, then rebuild the app.'}


ACTIVATION_STEPS = ('kssidp-activation-code-verifier', 'kssidp-verify-act-code')
LOGIN_STEPS = ('kobil-verify-uid-authenticator', 'kssidp-verify-uid-authenticator')


def discover_journeys(backend, client_ids=None):
    """Which clients of this realm carry an activation-code journey, and which a login journey.

    Realms name these clients however they like, so an agent must not look for a name it
    saw elsewhere. This reads the clients with a browser-flow override, reads that flow's
    steps, and classifies: a flow with an activation-code step is an activation journey; a
    flow whose only step asks for the user identity and password is a one-page login
    journey. Everything else is counted, not named.

    Disclosure is kept to the minimum the decision needs: four fields per classified client
    (id, flow alias, theme, step providers), nothing about unrelated clients, never
    secrets, redirect URIs or attributes. With client_ids only those clients are read.
    Reads only; needs the admin block, whose holder can already see the whole realm.
    """
    if client_ids is not None:
        if not isinstance(client_ids, list) or not client_ids or len(client_ids) > 50 or \
                any(not isinstance(c, str) or not CLIENT_ID.fullmatch(c) for c in client_ids):
            raise ValueError('client_ids must be 1 to 50 client ids')
    token = admin_token(backend)
    realm = segment(backend.cfg['tenant'])
    flows = _call(backend, token, 'GET', '/auth/admin/realms/%s/authentication/flows' % realm)
    aliases = {f.get('id'): f.get('alias') for f in flows if isinstance(f, dict)} if isinstance(flows, list) else {}
    if client_ids is None:
        clients = _call(backend, token, 'GET', '/auth/admin/realms/%s/clients' % realm, params={'max': 500})
    else:
        clients = []
        for wanted in client_ids:
            found = _call(backend, token, 'GET', '/auth/admin/realms/%s/clients' % realm,
                          params={'clientId': wanted, 'max': 2})
            clients.extend(c for c in (found if isinstance(found, list) else []) if isinstance(c, dict))
    if not isinstance(clients, list):
        raise BackendError('Unrecognized client listing from the IDP')
    result = {'activation': [], 'login': [], 'other_clients_with_own_flow': 0}
    for client in clients:
        if not isinstance(client, dict):
            continue
        override = (client.get('authenticationFlowBindingOverrides') or {}).get('browser')
        alias = aliases.get(override)
        if not alias:
            continue
        executions = _call(backend, token, 'GET',
                           '/auth/admin/realms/%s/authentication/flows/%s/executions' % (realm, segment(alias)))
        providers = [e.get('providerId') for e in executions if isinstance(e, dict) and e.get('providerId')] \
            if isinstance(executions, list) else []
        entry = {'client_id': client.get('clientId'), 'flow_alias': alias,
                 'login_theme': (client.get('attributes') or {}).get('login_theme'), 'steps': providers}
        if any(p in ACTIVATION_STEPS for p in providers):
            entry['links_device_to_user'] = providers.count('ast-login-authenticator') >= 2
            result['activation'].append(entry)
        elif providers and all(p in LOGIN_STEPS for p in providers):
            result['login'].append(entry)
        else:
            result['other_clients_with_own_flow'] += 1
    result['note'] = ('Use an activation client in mc_config.json; use a login client as the app\'s login '
                      'override. No activation client means the realm needs one: sdk_activation_flow_ensure '
                      'then sdk_activation_client_ensure, under names of your choosing.')
    return result
