"""AST transaction operations with explicit policy and redacted results."""
import re
from uuid import UUID
from .backend import BackendError


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("Invalid transaction ID")
    return value


def summary(value, transaction_id=None):
    if not isinstance(value, dict):
        raise BackendError('Unrecognized transaction response')
    info = value.get('info', value)
    if not isinstance(info, dict):
        raise BackendError('Unrecognized transaction metadata')
    txn_id = info.get('id', transaction_id)
    status = info.get('status')
    if not isinstance(txn_id, str) or not txn_id:
        raise BackendError('Transaction response has no ID; do not retry creation blindly')
    identifier(txn_id)
    if status is not None and (not isinstance(status, str) or not re.fullmatch(r'[A-Z_]{1,64}', status)):
        raise BackendError('Unrecognized transaction status')
    return {'transaction_id': txn_id, 'status': status}


def trigger(backend, user_uuid, text, retrieval_timeout_seconds, confirmation_timeout_seconds,
            require_explicit_authentication, freshness_seconds):
    try:
        user_uuid = str(UUID(user_uuid))
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Provide the recipient Keycloak UUID') from None
    if not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > 4096:
        raise ValueError('Provide 1–4096 bytes of transaction text')
    for value in (retrieval_timeout_seconds, confirmation_timeout_seconds):
        if type(value) is not int or not 1 <= value <= 86400:
            raise ValueError('Timeout must be 1–86400 seconds')
    if type(require_explicit_authentication) is not bool or type(freshness_seconds) is not int or not -1 <= freshness_seconds <= 86400:
        raise ValueError('Choose explicit authentication and freshness (-1 disables freshness)')
    result = backend.request('POST', '/tms', {
        'userId': user_uuid, 'tmsData': {'text': text, 'external': False, 'data': {}},
        'retrievalTimeout': retrieval_timeout_seconds, 'tmsTimeout': confirmation_timeout_seconds,
        'requireExplicitAuthentication': require_explicit_authentication,
        'requireFreshnessOfAuthentication': freshness_seconds,
        'push': {'skip': True}, 'auditMessage': 'SDK integration transaction test'})
    return summary(result)


def read(backend, transaction_id, result=False):
    identifier(transaction_id)
    value = backend.request('GET', '/tms/' + transaction_id + ('/result' if result else '/status'), allow_not_found=result)
    if value is None:
        return {'transaction_id': transaction_id, 'result_available': False,
                'note': 'No result returned (not ready, expired or unknown ID); inspect status'}
    response = summary(value, transaction_id)
    if result:
        response['result_available'] = True
    return response


def cancel(backend, transaction_id):
    identifier(transaction_id)
    backend.request('DELETE', '/tms/' + transaction_id)
    return {'transaction_id': transaction_id, 'cancel_requested': True,
            'final_result_verified': False}
