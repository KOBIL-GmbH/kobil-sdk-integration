"""AST transaction operations with explicit policy and redacted results."""
import base64
import binascii
import hashlib
import re
from uuid import UUID
from .backend import BackendError

MAX_DATA_KEYS = 20


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
    if transaction_id is not None and txn_id != transaction_id:
        raise BackendError("Transaction response ID does not match requested ID")
    if status is not None and (not isinstance(status, str) or not re.fullmatch(r'[A-Z_]{1,64}', status)):
        raise BackendError('Unrecognized transaction status')
    return {'transaction_id': txn_id, 'status': status}


def recipient(user_uuid):
    try:
        return str(UUID(user_uuid))
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Provide the recipient Keycloak UUID') from None


def message_data(text, data):
    """The AST MessageData object: text (plain or Mustache template) plus substitution data."""
    if not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > 4096:
        raise ValueError('Provide 1–4096 bytes of text')
    data = {} if data is None else data
    if not isinstance(data, dict) or len(data) > MAX_DATA_KEYS:
        raise ValueError('data must be an object of at most %d string pairs' % MAX_DATA_KEYS)
    size = len(text.encode('utf-8'))
    for key, value in data.items():
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', key):
            raise ValueError('data keys must be identifiers of at most 64 characters')
        if not isinstance(value, str) or len(value.encode('utf-8')) > 1024:
            raise ValueError('data values must be strings of at most 1024 bytes')
        size += len(key) + len(value.encode('utf-8'))
    if size > 8192:
        raise ValueError('text and data together must stay under 8192 bytes')
    return {'text': text, 'external': False, 'data': dict(data)}


def trigger(backend, user_uuid, text, retrieval_timeout_seconds, confirmation_timeout_seconds,
            require_explicit_authentication, freshness_seconds, data=None):
    user_uuid = recipient(user_uuid)
    tms_data = message_data(text, data)
    for value in (retrieval_timeout_seconds, confirmation_timeout_seconds):
        if type(value) is not int or not 1 <= value <= 86400:
            raise ValueError('Timeout must be 1–86400 seconds')
    if type(require_explicit_authentication) is not bool or type(freshness_seconds) is not int or not -1 <= freshness_seconds <= 86400:
        raise ValueError('Choose explicit authentication and freshness (-1 disables freshness)')
    result = backend.request('POST', '/tms', {
        'userId': user_uuid, 'tmsData': tms_data,
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
    if response['status'] is None:
        raise BackendError('Transaction response has no status')
    if result:
        response['result_available'] = True
        response.update(signature_evidence(value.get('signedData')))
    return response


def signature_evidence(signed_data):
    """Proof that the device signed, without echoing the CMS: presence, size and digest.

    AST returns signedData (a PKCS#7 CMS over the transaction data with the device's
    certificate chain) only for an accepted transaction.
    """
    if not isinstance(signed_data, str) or not signed_data:
        return {'signed_data_present': False}
    text = signed_data.strip()
    try:
        raw = base64.b64decode(text + '=' * (-len(text) % 4), altchars=b'-_' if ('-' in text or '_' in text) else None, validate=True)
    except (binascii.Error, ValueError):
        return {'signed_data_present': True, 'signed_data_decodable': False}
    return {'signed_data_present': True, 'signed_data_bytes': len(raw),
            'signed_data_sha256': hashlib.sha256(raw).hexdigest(),
            'signed_data_is_der_sequence': raw[:1] == b'\x30'}


def display_message(backend, user_uuid, text, timeout_seconds, data=None):
    """Send a one-way display message; the phone shows it, nothing is confirmed or signed."""
    user_uuid = recipient(user_uuid)
    body = message_data(text, data)
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 86400:
        raise ValueError('Timeout must be 1–86400 seconds')
    result = backend.request('POST', '/display-message', {
        'userId': user_uuid, 'displayMessageData': body,
        'displayMessageTimeout': timeout_seconds,
        'push': {'skip': True}, 'auditMessage': 'SDK integration display message test'})
    message_id = result.get('id') if isinstance(result, dict) else None
    if not isinstance(message_id, str) or not message_id:
        raise BackendError('Display message response has no ID; do not resend blindly')
    return {'display_message_id': identifier(message_id), 'accepted_for_delivery': True,
            'delivery_verified': False}


def cancel(backend, transaction_id):
    identifier(transaction_id)
    backend.request('DELETE', '/tms/' + transaction_id)
    return {'transaction_id': transaction_id, 'cancel_requested': True,
            'final_result_verified': False}
