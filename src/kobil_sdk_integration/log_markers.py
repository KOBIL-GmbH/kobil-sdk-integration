"""Read measured markers out of a decrypted MCSDK log, locally and read-only.

The guidance tells an agent to "read the native log" before attributing a
failure. This module does that reading deterministically so the result does
not depend on how carefully a reader scans a few thousand lines:

* ``signed_jwt_grant``: did the SDK post a jwt-bearer grant and did the token
  endpoint answer 200 under the same request uuid (one qualified source of grant evidence; a fresh ``iat`` or OfflineLogin OK is not).
* ``key_protection``: what the device reported about the signing key
  (``securityLevel``, hardware / strong-hardware keystore flags) - the
  difference between a software key (emulator, virtual fallback) and a
  hardware key (physical device).
* ``start_not_supported``: whether a NOT_SUPPORTED-class failure around Start
  came with a missing-dependency trace (``JcaContentSignerBuilder`` /
  bouncycastle) - in which case it is NOT proof of missing secure hardware.
* ``explicit_tms``: token-exchange refusals that explain a silent FAILED/0
  (wrong token holder) or a missing scope.

Only diagnostic metadata (positions, timestamps, UUIDs, client IDs, booleans and class names) is reported;
no token, claim or payload text is copied out of the log.
"""
from __future__ import annotations

import re
from pathlib import Path

_TS = r'\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\]'
_JWT_EVENT = re.compile(_TS + r'.*Received Event: \[event=GetIamAccessTokenUsingJwtBearer, client_id=(?P<client>[^,\]]+)')
_TOKEN_POST = re.compile(_TS + r'.*Rest Data for Event with UUID \[(?P<uuid>[0-9a-f-]{36})\].*\[Method=POST\]\[Path=(?P<path>/auth/realms/[^/\]]+/protocol/openid-connect/token)\]')
_HTTP = re.compile(_TS + r'.*HTTP Response for Event with UUID \[(?P<uuid>[0-9a-f-]{36})\] (?P<outcome>Success|Failed|Error)\s*(?P<code>\d{3})?')
_SEC_LEVEL = re.compile(r'isKeyInsideSecureHardware securityLevel (?P<level>\d+)')
_KEYSTORE = re.compile(r'GetKeystoreInfo has strong hardware keystore (?P<strong>true|false), has hardware keystore (?P<hw>true|false)')
_MISSING_CLASS = re.compile(r'(NoClassDefFoundError|ClassNotFoundException)[^\n]*?(?P<cls>[A-Za-z0-9_/.$]*(JcaContentSignerBuilder|bouncycastle)[A-Za-z0-9_/.$]*)')
_PKCS10_FAIL = re.compile(r'generatePKCS10SignRequest - exception occurred')
_NOT_SUPPORTED = re.compile(r'(NOT_SUPPORTED|NotSupported|status=46\b|800000278)')
_HOLDER = re.compile(r'client is not the token holder')
_EXCHANGE_DENIAL = re.compile(r'TOKEN_EXCHANGE_ERROR[^\n]*not_allowed')
_SCOPE_403 = re.compile(r'(516004034|explicit authentication scope [\'"]?\w+[\'"]? is missing)')
_FRESHNESS = re.compile(r'(516004035|older than required)')


def _lines(text: str):
    for i, line in enumerate(text.splitlines(), start=1):
        yield i, line


def signed_jwt_grant(text: str) -> dict:
    """Correlate the jwt-bearer event with the token POST and its HTTP result."""
    events, posts, responses = [], {}, {}
    for i, line in _lines(text):
        m = _JWT_EVENT.search(line)
        if m:
            events.append({'line': i, 'ts': m.group('ts'), 'client_id': m.group('client').strip()})
            continue
        m = _TOKEN_POST.search(line)
        if m:
            posts[m.group('uuid')] = {'line': i, 'ts': m.group('ts'), 'path': m.group('path')}
            continue
        m = _HTTP.search(line)
        if m and m.group('uuid') in posts:
            responses[m.group('uuid')] = {'line': i, 'ts': m.group('ts'), 'outcome': m.group('outcome'),
                                          'status': int(m.group('code')) if m.group('code') else None}
    # UUIDs of SDK events and HTTP requests differ in this format. Bound each
    # candidate by the next received operation; never associate a later login's
    # HTTP result with an earlier event. This is a sequential-log heuristic,
    # not a universal causal proof for multiplexed or reordered logs.
    received = [i for i, line in _lines(text) if 'Received Event:' in line]
    attempts = []
    for event in events:
        boundary = next((i for i in received if i > event['line']), float('inf'))
        candidates = sorted(((u, p) for u, p in posts.items()
                             if event['line'] < p['line'] < boundary),
                            key=lambda item: item[1]['line'])
        attempt = {'event_line': event['line'], 'event_ts': event['ts'],
                   'proof': None, 'proven': False}
        if len(candidates) == 1:
            uuid, post = candidates[0]
            resp = responses.get(uuid)
            # Interleaved operations before the response also make attribution
            # uncertain in this log format, even if request/response IDs match.
            if resp and not post['line'] < resp['line'] < boundary:
                resp = None
            proof = {'uuid': uuid, 'event_ts': event['ts'], 'post_ts': post['ts'],
                     'post_line': post['line'], 'response_ts': resp['ts'] if resp else None,
                     'http_status': resp['status'] if resp else None,
                     'response_line': resp['line'] if resp else None}
            attempt['proof'] = proof
            attempt['proven'] = bool(resp and resp['status'] == 200 and resp['outcome'] == 'Success')
        attempts.append(attempt)
    successful = [a for a in attempts if a['proven']]
    # Keep the original fields for callers, but explicitly identify their scope:
    # proof denotes the last successful attempt, not the current session state.
    selected = successful[-1] if successful else (attempts[-1] if attempts else None)
    return {'events': events, 'attempts': attempts,
            'proof': selected['proof'] if selected else None,
            'proven': bool(successful),
            'latest_attempt_proven': bool(attempts and attempts[-1]['proven']),
            'note': ('At least one sequential-log jwt-bearer attempt has a matching token POST/HTTP 200; '
                     'inspect attempts for later failures. This does not establish current session state '
                     'or causal linkage in multiplexed logs.' if successful else
                     'No unambiguous sequential jwt-bearer attempt with HTTP 200; do not claim SignedJWT from this log')}


def key_protection(text: str) -> dict:
    """Report the last observed key-protection statements."""
    levels, keystore = [], None
    for i, line in _lines(text):
        m = _SEC_LEVEL.search(line)
        if m:
            levels.append({'line': i, 'security_level': int(m.group('level'))})
        m = _KEYSTORE.search(line)
        if m:
            keystore = {'line': i, 'strong_hardware_keystore': m.group('strong') == 'true',
                        'hardware_keystore': m.group('hw') == 'true'}
    last_level = levels[-1]['security_level'] if levels else None
    if keystore is None and last_level is None:
        kind = 'unknown'
    elif (keystore and keystore['hardware_keystore']) or (last_level is not None and last_level >= 1):
        kind = 'hardware'
    else:
        kind = 'software'
    return {'security_levels': levels, 'keystore': keystore, 'key_kind': kind,
            'note': {'hardware': 'hardware-backed key reported; proves nothing about the virtual fallback',
                     'software': 'software-backed key (securityLevel 0, no hardware keystore): virtual-smart-card path; '
                                 'proves the protocol, not hardware key protection',
                     'unknown': 'no key-protection statements in this log'}[kind]}


def start_not_supported(text: str) -> dict:
    """Attribute a NOT_SUPPORTED-class Start failure: dependency vs hardware."""
    not_supported, pkcs10_fail, missing = [], [], []
    for i, line in _lines(text):
        if _NOT_SUPPORTED.search(line):
            not_supported.append(i)
        if _PKCS10_FAIL.search(line):
            pkcs10_fail.append(i)
        m = _MISSING_CLASS.search(line)
        if m:
            missing.append({'line': i, 'class': m.group('cls')})
    if missing:
        cause = 'missing_dependency'
        note = ('CSR helper could not load a bouncycastle class (add the delivery-pinned '
                'org.bouncycastle:bcpkix dependency); this is NOT proof that the device lacks secure hardware')
    elif not_supported or pkcs10_fail:
        cause = 'undetermined'
        note = 'NOT_SUPPORTED seen without a dependency trace; read key_protection before attributing it to hardware'
    else:
        cause = 'none'
        note = 'no NOT_SUPPORTED-class failure in this log'
    return {'not_supported_lines': not_supported, 'pkcs10_failure_lines': pkcs10_fail,
            'missing_classes': missing, 'cause': cause, 'note': note}


def explicit_tms(text: str) -> dict:
    """Exchange refusals that explain explicit-TMS failures."""
    holder, scope, fresh, denied = [], [], [], []
    for i, line in _lines(text):
        if _EXCHANGE_DENIAL.search(line):
            denied.append(i)
        if _HOLDER.search(line):
            holder.append(i)
        if _SCOPE_403.search(line):
            scope.append(i)
        if _FRESHNESS.search(line):
            fresh.append(i)
    if holder:
        verdict = 'wrong_token_holder'
        note = 'exchange refused: the SDK token belongs to another client; one interactive login with the token client in this session fixes it'
    elif scope:
        verdict = 'missing_explicit_scope'
        note = 'the token client has no optional explicit-auth scope; realm configuration item for the realm owner'
    elif fresh:
        verdict = 'freshness_too_strict'
        note = 'requireFreshnessOfAuthentication below confirmation latency; product gap, not a configuration error'
    elif denied:
        verdict = 'undetermined_exchange_denial'
        note = 'Token exchange denied; inspect the exact server reason, current token holder and policy. not_allowed alone does not identify the cause.'
    else:
        verdict = 'none'
        note = 'no explicit-TMS refusal markers in this log'
    return {'token_holder_lines': holder, 'missing_scope_lines': scope, 'freshness_lines': fresh,
            'exchange_denial_lines': denied, 'verdict': verdict, 'note': note}


def analyse(text: str) -> dict:
    return {'signed_jwt': signed_jwt_grant(text), 'key_protection': key_protection(text),
            'start_not_supported': start_not_supported(text), 'explicit_tms': explicit_tms(text)}


def register(mcp):
    @mcp.tool()
    def sdk_log_markers(decrypted_log_path: str) -> dict:
        """Read measured markers from one DECRYPTED MCSDK log file, locally and read-only.

        Reports sequential jwt-bearer grant evidence per attempt (correlated issuer
        events are another valid source of grant evidence), the key-protection statements (software vs hardware key), the
        attribution of a NOT_SUPPORTED-class Start failure (missing bouncycastle
        dependency vs undetermined) and explicit-TMS exchange refusals (wrong
        token holder, missing scope, freshness). Returns line numbers,
        timestamps, uuids, client IDs, booleans and class names; never copies token,
        claim or payload text. Decrypt the log first; an encrypted ks*.log
        yields no markers.
        """
        path = Path(decrypted_log_path).expanduser()
        if not path.is_file():
            raise ValueError('decrypted_log_path must point to an existing file')
        text = path.read_text(encoding='utf-8', errors='replace')
        if 'LoggingFramework Version' in text[:200] and '%%%' in text[:2000]:
            raise ValueError('this looks like an encrypted MCSDK log; decrypt it first')
        result = analyse(text)
        result['file'] = path.name
        result['lines'] = text.count('\n') + 1
        return result
