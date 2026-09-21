"""Check that the page an IDP client serves to the SDK is one the SDK can read.

KSSIDP parses every login page as strict XML. A theme with unbalanced tags, an unclosed
void element or a raw ampersand is discarded silently: no delegate call, no result, no
error, and the app waits forever. On the verification realm the working markup lives in a
patch applied inside the idp-core pod, which reverts when the pod restarts, so the only
way to know whether login still works is to look at the page. This does that.
"""
import re
from urllib.parse import urlencode
from xml.etree import ElementTree

from .backend import BackendError, https_url, segment

CLIENT_ID = re.compile(r'[A-Za-z0-9_.\-]{1,120}')
JSON_INPUT = re.compile(r'<input\b[^>]*\bid="jsonInput"[^>]*>', re.I)


def idp_base_url(cfg):
    """The IDP host, from the admin block or from the OAuth token URL."""
    admin = cfg.get('admin')
    if admin and admin.get('idp_url'):
        return admin['idp_url'].rstrip('/')
    token_url = (cfg.get('oauth') or {}).get('token_url') or ''
    marker = '/auth/realms/'
    if marker not in token_url:
        raise BackendError('Cannot derive the IDP host: no admin.idp_url and no oauth.token_url '
                           'under /auth/realms/ in the connection file')
    return token_url.split(marker, 1)[0]


def check_login_page(backend, client_id, redirect_uri='https://kobil/OpenIdRedirectUri'):
    """Fetch a client's first login page as a browser would and parse it as strict XML.

    Reads only. An activation client answers HTTP 406 to a request without the SDK's AST
    headers; that is expected and reported as not checkable, not as a failure.
    """
    if not isinstance(client_id, str) or not CLIENT_ID.fullmatch(client_id):
        raise ValueError('Provide the IDP client id')
    https_url(redirect_uri)
    cfg = backend.cfg
    url = '%s/auth/realms/%s/protocol/openid-connect/auth?%s' % (
        idp_base_url(cfg), segment(cfg['tenant']), urlencode({
            'client_id': client_id, 'redirect_uri': redirect_uri, 'response_type': 'code',
            'scope': 'openid', 'response_mode': 'form_post', 'nonce': 'theme-check'}))
    status, body = backend.fetch_text(url)
    result = {'client_id': client_id, 'http_status': status, 'bytes': len(body)}
    if status == 406:
        result.update({'checked': False, 'well_formed': None, 'json_input_has_type': None,
                       'note': 'This client\'s flow starts with an AST step driven by SDK headers '
                               'and refuses a browser request. Expected for an activation client; '
                               'only a device can validate it.'})
        return result
    if status != 200:
        raise BackendError('The authorisation endpoint answered HTTP %d for client %s' % (status, client_id))
    error = None
    try:
        ElementTree.fromstring(body)
        well_formed = True
    except ElementTree.ParseError as exc:
        well_formed = False
        error = str(exc)
    json_input = JSON_INPUT.search(body)
    json_input_has_type = (' type=' in json_input.group(0)) if json_input else None
    result.update({'checked': True, 'well_formed': well_formed, 'error': error,
                   'json_input_has_type': json_input_has_type})
    if well_formed and json_input_has_type is not False:
        result['note'] = 'KSSIDP can read this page. A failure on the device is not the theme.'
    else:
        reasons = []
        if not well_formed:
            reasons.append('the page is not well-formed XML (%s)' % error)
        if json_input_has_type is False:
            reasons.append('the jsonInput field has no type attribute, which KSSIDP reads unconditionally')
        result['note'] = ('KSSIDP will drop this page silently because %s. On the verification realm this '
                          'means the theme patch in the idp-core pod has reverted; reapply '
                          'kobil-ast-template-xhtml-fix.patch (login/template.ftl and headlessv2-json.ftl).'
                          % '; '.join(reasons))
    return result
