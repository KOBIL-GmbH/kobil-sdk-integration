"""Diagnose TMS authorization from metadata without reading or modifying tokens."""
import re
from .backend import segment
from .idp_admin import Admin


def _scopes(value):
    if value is None:
        return None
    if not isinstance(value, list) or len(value) > 128 or any(
        not isinstance(item, str) or not re.fullmatch(r'[A-Za-z0-9_:/.-]{1,128}', item)
        or item.count('.') >= 2 for item in value
    ):
        raise ValueError('Provide scope names only, never tokens; maximum 128 names.')
    return set(value)


def diagnose(current_scopes=None, exchange_requested_scopes=None,
             exchange_http_status=None, exchanged_scopes=None,
             ast_error_code=None):
    current = _scopes(current_scopes)
    requested = _scopes(exchange_requested_scopes)
    issued = _scopes(exchanged_scopes)
    if exchange_http_status is not None and (
        type(exchange_http_status) is not int or not 100 <= exchange_http_status <= 599
    ):
        raise ValueError('Exchange HTTP status must be an integer from 100 to 599.')
    if ast_error_code is not None and (
        type(ast_error_code) is not int or not 0 <= ast_error_code <= 4294967295
    ):
        raise ValueError('AST error code must be an unsigned 32-bit integer.')
    evidence = []
    next_checks = []
    status = 'needs_evidence'
    if current is not None and 'tms' not in current:
        evidence.append('Ordinary login token lacks tms; this alone is not a user-creation or transaction-authentication failure.')
    if ast_error_code == 516004034:
        status = 'blocked'
        evidence.append('AST rejected the decision because its authorization token lacks explicit scope tms.')
    if requested is not None and 'tms' in requested:
        evidence.append('Caller reports a transaction token-exchange request for tms.')
        if exchange_http_status == 200:
            evidence.append('Exchange HTTP 200 is not proof that tms was granted.')
            if issued is not None and 'tms' not in issued:
                status = 'blocked'
                evidence.append('The reported exchange result did not grant the requested tms scope.')
                next_checks.append('Compare effective scopes and mappings of the actual exchange client, plus issuer token-exchange behavior; compare users under the same client and transaction policy.')
            elif issued is not None:
                status = 'blocked' if ast_error_code == 516004034 else 'scope_metadata_checked'
                next_checks.append('Correlate the exchanged token with the token used for the AST decision; scope metadata alone does not prove fresh authentication or backend acceptance.')
            else:
                next_checks.append('Inspect scope names on the actual exchange result; do not substitute a later GetIamAccessTokenClaims result or ordinary login token.')
        elif exchange_http_status is not None and exchange_http_status >= 400:
            status = 'blocked'
            next_checks.append('Inspect the token-exchange error and token-holder/client binding before changing scope configuration.')
        else:
            next_checks.append('Capture the matching token-exchange HTTP result and issued scope names.')
    else:
        next_checks.append('Check the downloaded transaction requirement and matching SDK token-exchange trace before concluding that a scope or user attribute is missing.')
    return {'status': status, 'evidence': evidence, 'next_checks': next_checks,
            'runtime_verified': False, 'backend_modified': False,
            'limits': 'Caller-supplied metadata only. Do not recreate users, grant default tms scope or disable explicit authentication to force a pass. Capture hasErrorOccurred, errorCode, errorDescription and reportId where exposed on confirmation/result/end events, not only Warning/RuntimeError/FatalError.'}


REQUIRED_SCOPE = 'tms'
MOBILE_LOGIN_FLOW = 'KOBIL Mobile Login'
_CLIENT_ID = re.compile(r'[A-Za-z0-9_.:-]{1,256}')


def _names(scopes):
    return {s.get('name') for s in scopes if isinstance(s, dict)}


def explicit_preflight(token_client, default_scopes, optional_scopes, flows,
                       enrollment_client_id=None, required_scope=REQUIRED_SCOPE,
                       expected_flow_alias=MOBILE_LOGIN_FLOW):
    """Judge, from client representations only, whether a token client can answer an
    explicit-authentication TMS. Pure function: no network, no tokens, no mutation.

    Measured contract (Akinci, 2026-10-01): the token client must (1) carry the required
    scope as an OPTIONAL client scope, (2) be the holder of the SDK's current token, (3) run
    the KOBIL mobile browser flow via a client-level override."""
    errors, warnings = [], []
    client_id = token_client.get('clientId')
    optional = _names(optional_scopes)
    default = _names(default_scopes)
    if required_scope in default:
        warnings.append(f"{required_scope} is a DEFAULT scope on {client_id}; every ordinary token now carries it. The measured contract only needs it as optional scope - keep it optional.")
    elif required_scope not in optional:
        errors.append(f"{client_id} has no optional client scope {required_scope}; the SDK's exchange returns HTTP 200 without it and AST rejects the decision with 403 / 516004034. Assign {required_scope} as optional scope to this client only.")
    override = (token_client.get('authenticationFlowBindingOverrides') or {}).get('browser')
    alias = {f.get('id'): f.get('alias') for f in flows if isinstance(f, dict)}.get(override)
    if not override:
        errors.append(f"{client_id} has no browser flow override; interactive login then fails with CANNOT_ACQUIRE_TOKEN_DATA (IDP: X-KOBIL-ASTCLIENTDATA is missing). Set authenticationFlowBindingOverrides.browser to '{expected_flow_alias}'.")
    elif alias != expected_flow_alias:
        warnings.append(f"{client_id} browser flow override is '{alias}', not '{expected_flow_alias}'. Verify it is a KOBIL mobile flow variant.")
    if enrollment_client_id and enrollment_client_id != client_id:
        warnings.append(f"Enrollment client {enrollment_client_id} differs from token client {client_id}. After activation the SDK still holds the enrollment client's token; run one interactive login with {client_id} before the first explicit TMS, otherwise the exchange is refused not_allowed 'client is not the token holder' and the SDK ends FAILED/0 before the dialog.")
    if not token_client.get('enabled', True):
        errors.append(f"{client_id} is disabled.")
    return {'status': 'blocked' if errors else 'client_checked', 'token_client': client_id,
            'optional_scopes': sorted(optional), 'browser_flow_override': alias or override,
            'errors': errors, 'warnings': warnings, 'runtime_verified': False, 'backend_modified': False,
            'limits': 'Read-only client configuration check. Satisfying it does not prove fresh user authentication; it removes the three measured blockers (missing optional scope, wrong token holder, missing mobile flow override).'}


def register(mcp):
    @mcp.tool()
    def sdk_tms_explicit_preflight(expected_environment: str, token_client_id: str,
                                   enrollment_client_id: str | None = None,
                                   realm: str | None = None) -> dict:
        """Read-only check whether the SDK token client (mc_config iam.clientId) can answer
        an explicit-authentication TMS: optional client scope tms, KOBIL mobile browser-flow
        override, and a token-holder warning when enrollment and token client differ.
        Reads client, scopes and flows via the IDP admin API; changes nothing."""
        for value in (token_client_id, enrollment_client_id or token_client_id):
            if not _CLIENT_ID.fullmatch(value):
                raise ValueError('Provide public clientId names, never tokens or UUIDs with spaces.')
        with Admin(expected_environment, realm) as api:
            clients = api.page('/clients', 0, 2, params={'clientId': token_client_id})
            matches = [c for c in (clients if isinstance(clients, list) else []) if c.get('clientId') == token_client_id]
            if not matches:
                return {'status': 'blocked', 'errors': [f'Client {token_client_id} not found in realm.'], 'warnings': [],
                        'runtime_verified': False, 'backend_modified': False}
            client = matches[0]
            uuid = segment(client['id'])
            default_scopes = api.call('GET', f'/clients/{uuid}/default-client-scopes')
            optional_scopes = api.call('GET', f'/clients/{uuid}/optional-client-scopes')
            flows = api.call('GET', '/authentication/flows')
        return explicit_preflight(client, default_scopes or [], optional_scopes or [], flows or [],
                                  enrollment_client_id)

    @mcp.tool()
    def sdk_tms_auth_diagnose(current_scopes: list[str] | None = None,
                             exchange_requested_scopes: list[str] | None = None,
                             exchange_http_status: int | None = None,
                             exchanged_scopes: list[str] | None = None,
                             ast_error_code: int | None = None) -> dict:
        """Diagnose explicit TMS authorization using scope NAMES and numeric results only.

        Distinguish ordinary login scopes from the actual transaction exchange
        result. HTTP200 does not establish tms issuance. Error516004034 confirms
        AST's rejection, not a user-creation defect. Read-only, no backend calls
        or token values. Timeout/server cancellation are separate test gates.
        """
        return diagnose(current_scopes, exchange_requested_scopes,
                        exchange_http_status, exchanged_scopes, ast_error_code)
