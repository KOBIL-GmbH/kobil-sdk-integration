"""Diagnose TMS authorization from metadata without reading or modifying tokens."""
import re


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


def register(mcp):
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
