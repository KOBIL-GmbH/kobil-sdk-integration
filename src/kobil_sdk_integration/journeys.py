"""Which journeys an IDP realm offers to a native app, and the endpoints that belong to them. Read-only.

Realms name their clients and flows as they like (KobilMobileEnrollment is a copy of the BDDK flows, KSSIDPWebBasedEnrollment
uses the KSSIDP flows), so the flow of each client is read and recognised by its official name or by its steps. The
endpoints come from the realm's own OpenID configuration document, so they are right whatever path layout the IDP uses.
"""
from urllib.parse import urlencode

from .backend import segment, WEBVIEW_REQUEST_HEADERS

KSSIDP_FLOWS = {'KSSIDP Enrollment - Multi form flow': 'activation', 'KSSIDP Mobile App Multi Flow Login': 'login'}
BDDK_FLOWS = {'BDDK Enrollment': 'activation', 'BDDK Login': 'login'}
BDDK_ACTIVATION_STEP = 'bddk-user-password-reg'
KSSIDP_ACTIVATION_STEP = 'kssidp-activation-code-verifier'
LOGIN_FORM_STEPS = ('kobil-username-password-form', 'kssidp-configure-or-verify-password', 'kssidp-verify-uid-authenticator',
                    'kobil-verify-uid-authenticator')
ENDPOINT_KEYS = {'issuer': 'issuer', 'authorization': 'authorization_endpoint', 'token': 'token_endpoint',
                 'userinfo': 'userinfo_endpoint', 'jwks': 'jwks_uri', 'end_session': 'end_session_endpoint'}


def classify(alias, steps):
    """Recognise a browser flow: the standard it follows, its role and whether it carries the official name."""
    steps = list(steps or [])
    official = None
    if alias in KSSIDP_FLOWS:
        based_on, role, official = 'kssidp', KSSIDP_FLOWS[alias], True
    elif alias in BDDK_FLOWS:
        based_on, role, official = 'bddk', BDDK_FLOWS[alias], True
    else:
        official = False
        if any(s.startswith('kssidp-') for s in steps):
            based_on = 'kssidp'
        elif BDDK_ACTIVATION_STEP in steps or ('kobil-username-password-form' in steps and 'kobil-risk-and-policy-evaluator' in steps):
            based_on = 'bddk'
        else:
            based_on = 'other'
        if KSSIDP_ACTIVATION_STEP in steps or BDDK_ACTIVATION_STEP in steps:
            role = 'activation'
        elif based_on != 'other' and any(s in steps for s in LOGIN_FORM_STEPS):
            role = 'login'
        else:
            role = None
    return {'based_on': based_on, 'role': role, 'official_flow': official, 'deprecated': based_on == 'bddk'}


def _endpoints(realm_base, well_known):
    if not realm_base:
        return None
    base = realm_base.rstrip('/')
    try:
        doc = well_known(base + '/.well-known/openid-configuration')
        if not isinstance(doc, dict) or 'authorization_endpoint' not in doc:
            raise ValueError('not an OpenID configuration document')
        out = {name: doc.get(key) for name, key in ENDPOINT_KEYS.items() if doc.get(key)}
        out['source'] = 'well-known'
        return out
    except Exception:
        return {'authorization': base + '/protocol/openid-connect/auth', 'token': base + '/protocol/openid-connect/token',
                'source': 'derived',
                'note': 'The realm OpenID configuration could not be read, so these endpoints are derived from the realm base and not confirmed.'}


def _redirect(uris):
    return next((u for u in (uris or []) if isinstance(u, str) and u and '*' not in u), None)


def discover(api, realm_base=None, well_known=None):
    """Clients with their own browser flow, classified, plus the realm endpoints. Reads only; no secrets, no attributes but the theme."""
    flows = api.call('GET', '/authentication/flows')
    aliases = {f.get('id'): f.get('alias') for f in flows if isinstance(f, dict)} if isinstance(flows, list) else {}
    clients = api.call('GET', '/clients', params={'max': 500})
    endpoints = _endpoints(realm_base, well_known) if well_known else (
        {'authorization': realm_base.rstrip('/') + '/protocol/openid-connect/auth', 'source': 'derived',
         'note': 'derived from the realm base and not confirmed'} if realm_base else None)
    steps_of = {}
    found, without = [], 0
    for client in clients if isinstance(clients, list) else []:
        if not isinstance(client, dict):
            continue
        alias = aliases.get((client.get('authenticationFlowBindingOverrides') or {}).get('browser'))
        if not alias:
            without += 1
            continue
        if alias not in steps_of:
            executions = api.call('GET', '/authentication/flows/%s/executions' % segment(alias))
            steps_of[alias] = [e.get('providerId') for e in executions if isinstance(e, dict) and e.get('providerId')]
        entry = {'client_id': client.get('clientId'), 'flow_alias': alias,
                 'login_theme': (client.get('attributes') or {}).get('login_theme'),
                 **classify(alias, steps_of[alias]), 'steps': steps_of[alias]}
        redirect = _redirect(client.get('redirectUris'))
        entry['redirect_uri'] = redirect
        if endpoints and endpoints.get('authorization') and redirect:
            query = urlencode({'client_id': entry['client_id'], 'redirect_uri': redirect, 'response_type': 'code', 'scope': 'openid'})
            entry['required_request_headers'] = WEBVIEW_REQUEST_HEADERS
            entry['authorization_url_template'] = endpoints['authorization'] + '?' + query + '&nonce=<random>&code_challenge=<code_challenge from GetAstClientData>&code_challenge_method=<code_challenge_method from GetAstClientData>&state=<random state>'
        found.append(entry)
    kssidp = any(c['based_on'] == 'kssidp' and c['official_flow'] for c in found)
    kinds = sorted({c['based_on'] for c in found if c['role']})
    summary = ('%d clients with an activation or login flow (%s). %s' % (
        sum(1 for c in found if c['role']), ', '.join(kinds) or 'none',
        'An official KSSIDP flow exists.' if kssidp else
        ('KSSIDP-based flows exist but none carries the official name; check its steps before use. ' if 'kssidp' in kinds else
         'No KSSIDP flow in this realm. ') + 'BDDK-based clients are the deprecated standard; KobilMobile* style clients are copies of it.'))
    return {'clients': found, 'clients_without_own_flow': without, 'has_kssidp_standard': kssidp, 'summary': summary,
            'endpoints': endpoints}


def register(mcp):
    @mcp.tool()
    def sdk_idp_flow_overview(expected_environment: str, realm: str | None = None) -> dict:
        """Which activation and login journeys the IDP realm offers to a native app, with the endpoints that belong to them. Read-only.

        Reads every client with its own browser flow and recognises the flow by its official name or by its steps: based_on
        kssidp (current standard), bddk (deprecated; KobilMobile* clients are copies of it) or other, role activation or login,
        login_theme, and whether the flow carries the official name. Also returns the realm endpoints (from the realm's own
        OpenID configuration, so they are right whatever the path layout; source "derived" means not confirmed) and, per client,
        the registered redirect_uri, a ready authorization_url_template (fill nonce, state and the PKCE challenge from GetAstClientData) and the required_request_headers the WebView request must carry. Use these addresses;
        never assemble them yourself. No secrets, no attributes other than the theme.
        """
        import httpx
        from .backend import realm_base_url
        from .idp_admin import Admin

        def fetch(url):
            response = httpx.get(url, timeout=10, follow_redirects=False)
            response.raise_for_status()
            return response.json()
        with Admin(expected_environment, realm) as api:
            admin = api.cfg.get('admin') or {}
            base = realm_base_url(admin['idp_url'], api.realm) if admin.get('idp_url') else None
            return discover(api, realm_base=base, well_known=fetch)
