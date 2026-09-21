"""Explicit dashboard service contracts, without dashboard UI or app-flow policy."""
import json
from pathlib import Path
from urllib.parse import urlencode
from typing import Literal
from .backend import AST, configuration, segment
from .idp_admin import Admin, load_private_json, redact
from .idp_transport import _call
from .idp_secrets import CredentialRef, resolve, output_file, write_result

ROUTES = json.loads(Path(__file__).with_name('service_routes.json').read_text())


def prepare(domain, operation, identifiers, query, payload_file, realm=None):
    spec = ROUTES.get(domain + '.' + operation)
    if not spec:
        raise ValueError('Unknown service operation; inspect sdk_service_operations')
    ids = dict(identifiers or {})
    query = dict(query or {})
    if set(ids) != set(spec['identifiers']):
        raise ValueError('Provide exactly the operation identifiers from sdk_service_operations')
    if set(query) - set(spec['query']) or not set(spec.get('required_query', [])) <= set(query):
        raise ValueError('Unsupported or missing query parameters')
    for key, value in query.items():
        if not isinstance(value, (str, int, bool)) or len(str(value)) > 256:
            raise ValueError('Query values must be bounded scalar values')
        if key in ('first', 'page', 'pageSize', 'max'):
            if type(value) is not int or value < (0 if key == 'first' else 1):
                raise ValueError('Invalid pagination value')
            if key in ('pageSize', 'max') and value > 200:
                raise ValueError('Page size must not exceed 200')
    if bool(payload_file) != spec['body_required']:
        raise ValueError('This operation requires a private payload file' if spec['body_required'] else 'This operation does not accept a body')
    values = {k: segment(v) for k, v in ids.items()}
    if domain == 'idp': values['realm'] = segment(realm)
    path = spec['path'].format(**values)
    body = load_private_json(payload_file) if payload_file else None
    return spec['method'], path, query, body


def ast_request(environment, operation, identifiers=None, query=None, payload_file=None):
    method, path, query, body = prepare('ast', operation, identifiers, query, payload_file)
    cfg = configuration(environment)
    backend = AST(cfg)
    try:
        if query: path += '?' + urlencode(query)
        result = backend.request(method, path, body)
        return {'operation': operation, 'result': redact(result),
                'collection_scope': 'one server response; use explicit pagination where supported',
                'runtime_verified': False}
    finally:
        backend.close()


def idp_request(environment, operation, identifiers=None, query=None, payload_file=None, realm=None):
    cfg = configuration(environment)
    selected = realm if realm is not None else cfg['tenant']
    method, path, query, body = prepare('idp', operation, identifiers, query, payload_file, selected)
    with Admin(environment, selected) as api:
        result = _call(api.backend, api.token, method, path, body, query)
        return {'operation': operation, 'result': api._safe(result),
                'collection_scope': 'one server response; follow explicit first/max pagination',
                'runtime_verified': False}


def register(mcp):
    @mcp.tool()
    def sdk_service_operations(domain: Literal['idp', 'ast'] | None = None) -> dict:
        """Inspect every low-level operation's HTTP method/path, identifiers, query parameters and body requirement. Operations mirror service contracts; no environment defaults or app-flow choices."""
        return {k:v for k,v in ROUTES.items() if domain is None or k.startswith(domain + '.')}

    @mcp.tool()
    def sdk_ast_service_request(expected_environment: str, operation: str,
                                identifiers: dict[str,str] | None = None,
                                query: dict[str,str | int | bool] | None = None,
                                payload_file: str | None = None) -> dict:
        """Execute one explicitly selected AST operation from sdk_service_operations. No arbitrary URLs. Mutation bodies come from a private mode0600 JSON file and are sent as supplied: use the documented full representation where required. Deletes and registration removal are real mutations. One request, no automatic retry or app orchestration. Collections are one response, not an assertion of completeness."""
        return ast_request(expected_environment, operation, identifiers, query, payload_file)

    @mcp.tool()
    def sdk_idp_service_request(expected_environment: str, operation: str,
                                identifiers: dict[str,str] | None = None,
                                query: dict[str,str | int | bool] | None = None,
                                payload_file: str | None = None, realm: str | None = None) -> dict:
        """Execute one IDP operation from sdk_service_operations, including KOBIL v3_user, activation-code credential updates, SMTP realm configuration and client-management permissions. Bodies are explicit private mode0600 JSON files. No arbitrary URLs, predefined flow, SMTP preset or automatic retry. Realm update requires the intended representation. User path identifiers are UUIDs except v3_user operations, which use their documented username or UUID contract."""
        return idp_request(expected_environment, operation, identifiers, query, payload_file, realm)

    @mcp.tool()
    def sdk_idp_refresh_token_write(expected_environment: str, client_id: str,
                                     refresh_token: CredentialRef, output_path: str,
                                     client_secret: CredentialRef | None = None,
                                     realm: str | None = None) -> dict:
        """Refresh an authorized IDP token using server-side credential references and save token response privately. A refresh may rotate the token; never retry blindly after an uncertain response. No login flow is chosen."""
        with Admin(expected_environment,realm) as api, output_file(output_path) as (stream,path):
            form={'grant_type':'refresh_token','client_id':client_id,'refresh_token':resolve(refresh_token)}
            if client_secret: form['client_secret']=resolve(client_secret)
            url=api.cfg['admin']['idp_url'].rstrip('/')+'/auth/realms/'+segment(api.realm)+'/protocol/openid-connect/token'
            result=api.backend.send('POST',url,data=form)
            if not isinstance(result,dict) or not result.get('access_token'):
                from .backend import BackendError
                raise BackendError('Token refresh returned no access token; do not retry without checking token state')
            return write_result(stream,path,result)

    @mcp.tool()
    def sdk_ast_device_inventory(expected_environment: str, first_user: int = 0, max_users: int = 20) -> dict:
        """Read a bounded page of IDP users and each user's AST devices. Continue next_user_offset. Per-user failures are returned, never silently omitted. This is dashboard-style inventory, not a new AST endpoint. Device collection completeness is not inferred from a response shape."""
        if type(max_users) is not int or not 1 <= max_users <= 50:
            raise ValueError('max_users must be 1..50')
        with Admin(expected_environment) as admin:
            page=admin.page('/users',first_user,max_users)
            backend=AST(admin.cfg)
            responses=[]; errors=[]
            try:
                for user in page['items']:
                    uid=user.get('id') if isinstance(user,dict) else None
                    if not uid:
                        errors.append({'user_id':None,'error':'missing_user_identifier'})
                        continue
                    try:
                        result=backend.request('GET','/astclients?'+urlencode({'userId':uid}))
                        responses.append({'user_id':uid,'result':redact(result)})
                    except Exception:
                        errors.append({'user_id':uid,'error':'device_request_failed'})
            finally:
                backend.close()
            return {'responses':responses,'errors':errors,'next_user_offset':page['next_offset'],
                    'user_page_complete':page['complete'],'device_completeness_verified':False}
