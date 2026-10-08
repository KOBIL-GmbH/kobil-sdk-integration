"""Usage breadcrumbs, a local usage log, optional Sentry error reporting and user problem reports.

Everything that leaves the machine goes through Sentry and only when a DSN is set (KOBIL_SDK_SENTRY_DSN or the
private file <state dir>/sentry-dsn) and the
sentry-sdk package is installed. The local usage log (state dir, default ~/.kobil-sdk/usage.jsonl, mode 600,
rotated at 1 MB) is on by default and can be switched off with KOBIL_SDK_USAGE_LOG=0.

Breadcrumbs and usage records carry claims only: tool name, argument key names, duration, result size,
outcome, error type and error code. Argument values, results, paths, hosts and messages are never recorded.
Error events carry the exception type, a leading error code, the tool name, package-relative frames and the
kobil.* breadcrumbs. A problem report is the only place with free text: the user's own words, redacted for
secret shapes, plus an optional contact address the user chose to give for personal support.
"""
import atexit
import collections
import contextlib
import functools
import json
import os
import platform
import re
import sys
import time
import uuid
from pathlib import Path

CODE = re.compile(r'^[A-Z][A-Z0-9_]{3,}$')
SAFE_VALUE = re.compile(r'^[A-Za-z0-9_.:,+-]{0,80}$')
EMAIL = re.compile(r'^[^@\s]{1,64}@[^@\s]{1,120}\.[A-Za-z]{2,24}$')
DROP = ('user', 'request', 'extra', 'server_name', 'modules', 'contexts', 'message')
FRAME_DROP = ('vars', 'pre_context', 'context_line', 'post_context')
PACKAGE = 'kobil_sdk_integration/'
MAX_LOG_BYTES = 1_000_000
FEEDBACK_AFTER_CALLS = 20
FEEDBACK_EVERY_SECONDS = 24 * 3600
CATEGORIES = ('bug', 'hang', 'idea', 'other')

_sentry = None
_session = uuid.uuid4().hex[:12]
_calls = 0
_started = time.time()
_ring = collections.deque(maxlen=200)


def reset():
    global _sentry, _calls, _started
    _sentry = None
    _calls = 0
    _started = time.time()
    _ring.clear()


def state_dir():
    return Path(os.environ.get('KOBIL_SDK_HOME') or Path.home() / '.kobil-sdk')


def _private_dir(path):
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def _clean(data):
    out = {}
    for key, value in data.items():
        if isinstance(value, bool) or isinstance(value, (int, float)):
            out[key] = value
        elif isinstance(value, str) and SAFE_VALUE.match(value):
            out[key] = value
    return out


def _append(record):
    if os.environ.get('KOBIL_SDK_USAGE_LOG') == '0':
        return
    try:
        directory = state_dir()
        _private_dir(directory)
        path = directory / 'usage.jsonl'
        if path.exists() and path.stat().st_size > MAX_LOG_BYTES:
            os.replace(path, directory / 'usage.jsonl.1')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, 'a') as handle:
            handle.write(json.dumps(record, sort_keys=True) + '\n')
    except OSError:
        pass


def crumb(category, message, **data):
    data = _clean(data)
    record = {'ts': round(time.time(), 3), 'session': _session, 'category': 'kobil.' + category,
              'message': message, 'data': data}
    _ring.append(record)
    _append(record)
    if _sentry is not None:
        try:
            _sentry.add_breadcrumb(category=record['category'], message=message, data=data, level='info')
        except Exception:
            pass


def _keep_crumb(crumb_, hint):
    return crumb_ if str(crumb_.get('category', '')).startswith('kobil.') else None


def _path(value):
    if not isinstance(value, str):
        return value
    index = value.find(PACKAGE)
    return value[index:] if index >= 0 else value.rsplit('/', 1)[-1]


def _message(value):
    head = str(value or '').split(':', 1)[0].strip()
    return head if CODE.match(head) else '[redacted]'


def _is_feedback(event):
    return (event.get('tags') or {}).get('kobil_feedback') == '1'


def invalid_fields(error):
    """Field names (never values) of a pydantic argument validation error, e.g. 'missing:a,unexpected:b'."""
    errors = getattr(error, 'errors', None)
    if not callable(errors):
        return None
    try:
        details = errors()
    except Exception:
        return None
    groups = {}
    for item in details:
        kind = {'missing': 'missing', 'extra_forbidden': 'unexpected'}.get(item.get('type'), 'invalid')
        loc = item.get('loc') or ()
        name = str(loc[0]) if loc else ''
        if name and SAFE_VALUE.match(name):
            groups.setdefault(kind, [])
            if name not in groups[kind]:
                groups[kind].append(name)
    parts = [kind + ':' + ','.join(groups[kind]) for kind in ('missing', 'unexpected', 'invalid') if groups.get(kind)]
    return ','.join(parts) or None


def scrub(event, hint):
    feedback = _is_feedback(event)
    kept = {key: event.get(key) for key in ('contexts', 'extra', 'message') if feedback and key in event}
    if feedback and 'contexts' in kept:
        kept['contexts'] = {'feedback': kept['contexts'].get('feedback', {})}
    for key in DROP:
        event.pop(key, None)
    event.update(kept)
    crumbs = event.get('breadcrumbs')
    if isinstance(crumbs, dict):
        crumbs['values'] = [c for c in crumbs.get('values', []) if str(c.get('category', '')).startswith('kobil.')]
    else:
        event.pop('breadcrumbs', None)
    fields = (event.get('tags') or {}).get('invalid_fields')
    for item in (event.get('exception') or {}).get('values', []):
        item['value'] = ('invalid arguments (%s)' % fields) if fields and item.get('type') == 'ValidationError' else _message(item.get('value'))
        for frame in (item.get('stacktrace') or {}).get('frames', []):
            for key in FRAME_DROP:
                frame.pop(key, None)
            frame['abs_path'] = _path(frame.get('abs_path') or frame.get('filename'))
    return event


SPAN_KEEP = ('http.response.status_code', 'http.request.method')


def _rate(value):
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return 1.0


def scrub_transaction(event, hint):
    """Performance events keep names, durations and status; hosts, URLs, queries and personal data are removed."""
    for key in ('server_name', 'user', 'request', 'extra', 'modules'):
        event.pop(key, None)
    event['contexts'] = {'trace': (event.get('contexts') or {}).get('trace', {})}
    crumbs = event.get('breadcrumbs')
    if isinstance(crumbs, dict):
        crumbs['values'] = [c for c in crumbs.get('values', []) if str(c.get('category', '')).startswith('kobil.')]
    else:
        event.pop('breadcrumbs', None)
    for span in event.get('spans', []):
        own = str(span.get('op', '')).startswith('kobil.')
        span['description'] = span.get('description') if own and SAFE_VALUE.match(str(span.get('description'))) else (span.get('op') or 'span')
        span['data'] = {k: v for k, v in (span.get('data') or {}).items() if k in SPAN_KEEP or (own and isinstance(v, (int, float, bool)))}
        span['tags'] = {k: v for k, v in (span.get('tags') or {}).items() if k in ('http.status_code', 'status')}
    return event


def _transaction(op, name):
    if _sentry is None:
        return contextlib.nullcontext()
    try:
        return _sentry.start_transaction(op=op, name=name)
    except Exception:
        return contextlib.nullcontext()


def _txn(txn, status=None, **data):
    for key, value in data.items():
        try:
            txn.set_data(key, value)
        except Exception:
            pass
    if status:
        try:
            txn.set_status(status)
        except Exception:
            pass


@contextlib.contextmanager
def timed(op, name):
    """Time a block (server start, a phase): one usage record and, with Sentry, one transaction."""
    began = time.perf_counter()
    with _transaction(op, '%s %s' % (op, name)) as txn:
        try:
            yield txn
        finally:
            crumb('timing', '%s %s' % (op, name), ms=int((time.perf_counter() - began) * 1000))


@contextlib.contextmanager
def span(kind, name):
    """A named phase inside a tool call: child span in Sentry and one usage record with its duration.

    kind and name are fixed identifiers chosen in code (never hosts, paths or user input); anything else becomes
    'unnamed'.
    """
    name = name if isinstance(name, str) and SAFE_VALUE.match(name) and name else 'unnamed'
    began = time.perf_counter()
    ok = True
    if _sentry is None:
        scope = contextlib.nullcontext()
    else:
        try:
            scope = _sentry.start_span(op='kobil.' + kind, name=name)
        except Exception:
            scope = contextlib.nullcontext()
    try:
        with scope:
            yield
    except BaseException:
        ok = False
        raise
    finally:
        crumb('span', '%s %s' % (kind, name), ms=int((time.perf_counter() - began) * 1000), ok=ok)


def init(env):
    global _sentry
    if env.get('KOBIL_SDK_SENTRY_DISABLE') == '1':
        return 'disabled'
    dsn = env.get('KOBIL_SDK_SENTRY_DSN')
    if not dsn:
        try:
            dsn = (state_dir() / 'sentry-dsn').read_text().strip()
        except OSError:
            dsn = None
    if not dsn:
        return 'disabled'
    try:
        import sentry_sdk
    except ImportError:
        return 'unavailable'
    try:
        from importlib.metadata import version
        release = version('kobil-sdk-integration')
    except Exception:
        release = None
    sentry_sdk.init(dsn=dsn, release=release, environment=env.get('KOBIL_SDK_SENTRY_ENVIRONMENT', 'local'),
                    send_default_pii=False, include_local_variables=False, traces_sample_rate=_rate(env.get('KOBIL_SDK_SENTRY_TRACES')),
                    server_name='', max_breadcrumbs=200, before_send=scrub, before_send_transaction=scrub_transaction, before_breadcrumb=_keep_crumb)
    sentry_sdk.set_tag('session', _session)
    sha = git_sha()
    if sha:
        sentry_sdk.set_tag('commit', sha)
    _sentry = sentry_sdk
    return 'enabled'


def git_sha():
    """Short commit of the source checkout this package runs from, None for a wheel install."""
    import subprocess
    try:
        out = subprocess.run(['git', '-C', str(Path(__file__).resolve().parent), 'rev-parse', '--short=10', 'HEAD'],
                             capture_output=True, text=True, timeout=2).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return out if re.fullmatch(r'[0-9a-f]{7,12}', out) else None


def count_call():
    global _calls
    _calls += 1
    return _calls


def _size(result):
    try:
        return len(json.dumps(result, default=str))
    except Exception:
        return -1


def install(mcp):
    """Record every tool call (start, end, duration, result size, outcome) and capture failures."""
    manager = mcp._tool_manager
    original = manager.call_tool

    @functools.wraps(original)
    async def call_tool(name, arguments=None, *args, **kwargs):
        keys = ','.join(sorted(str(k) for k in (arguments or {})))
        count_call()
        crumb('tool', 'call_start', tool=name, arg_keys=keys, n=_calls)
        began = time.perf_counter()
        with _transaction('mcp.tool', 'tool %s' % name) as txn:
            _txn(txn, arg_keys=keys, n=_calls)
            try:
                result = await original(name, arguments, *args, **kwargs)
            except Exception as wrapped:
                error = wrapped.__cause__ or wrapped
                code = _message(str(error))
                fields = invalid_fields(error)
                _txn(txn, 'internal_error', error_type=type(error).__name__)
                crumb('tool', 'call_end', tool=name, ok=False, ms=int((time.perf_counter() - began) * 1000),
                      error_type=type(error).__name__, error_code=code if code != '[redacted]' else 'none',
                      invalid_fields=fields or '')
                if _sentry is not None:
                    try:
                        _sentry.set_tag('tool', name)
                        if fields:
                            _sentry.set_tag('invalid_fields', fields)
                        _sentry.capture_exception(error)
                    except Exception:
                        pass
                raise wrapped
            size = _size(result)
            _txn(txn, 'ok', result_bytes=size)
            crumb('tool', 'call_end', tool=name, ok=True, ms=int((time.perf_counter() - began) * 1000),
                  result_bytes=size, arg_keys=keys)
            return result

    manager.call_tool = call_tool


def startup(status, toolset, tool_count):
    from importlib.metadata import version
    try:
        package = version('kobil-sdk-integration')
    except Exception:
        package = 'unknown'
    crumb('lifecycle', 'start', version=package, python=platform.python_version(), os=sys.platform,
          machine=platform.machine(), toolset=toolset, tools=tool_count, sentry=status, pid=os.getpid())
    atexit.register(lambda: crumb('lifecycle', 'exit', calls=_calls, uptime_s=int(time.time() - _started)))


def feedback_hint():
    """Return a one-time hint to ask the user for feedback after enough calls, at most once a day."""
    if _calls < FEEDBACK_AFTER_CALLS:
        return None
    path = state_dir() / 'feedback-state.json'
    try:
        last = json.loads(path.read_text()).get('last_ask', 0)
    except (OSError, ValueError):
        last = 0
    if time.time() - last < FEEDBACK_EVERY_SECONDS:
        return None
    try:
        _private_dir(path.parent)
        path.write_text(json.dumps({'last_ask': time.time()}))
        os.chmod(path, 0o600)
    except OSError:
        pass
    return {'tool': 'sdk_report_problem',
            'ask_user': 'Ask the user once, in one short sentence, whether anything was confusing or broken. '
                        'If yes, show them the text you would send and call sdk_report_problem only after they agree. '
                        'Personal support: they may add an email address, which is optional.'}


SECRET_SHAPES = (
    (re.compile(r'eyJ[\w-]+\.[\w-]+\.[\w-]*'), '[jwt]'),
    (re.compile(r'(?i)\b(bearer|basic)\s+[\w.~+/=-]{8,}'), r'\1 [redacted]'),
    (re.compile(r'(?i)\b(password|passwd|pwd|secret|token|apikey|api_key|code|pin)\s*[=:]\s*\S+'), r'\1=[redacted]'),
    (re.compile(r'\b[A-Za-z0-9+/_-]{24,}={0,2}'), '[redacted]'),
    (re.compile(r'\b\d{6,}\b'), '[number]'),
    (re.compile(r'/(?:Users|home)/[^\s/]+'), '/[home]'),
)


def redact(text):
    text = str(text or '')[:2000]
    for pattern, replacement in SECRET_SHAPES:
        text = pattern.sub(replacement, text)
    return text


def _sentry_tag_session():
    return _session


def _send_feedback(feedback, associated_event_id):
    """Send Sentry's own feedback envelope item so the report shows up in the User Feedback view."""
    from sentry_sdk.envelope import Envelope, Item, PayloadRef
    client = _sentry.get_client()
    if client is None or client.transport is None:
        return False
    event_id = uuid.uuid4().hex
    payload = {'event_id': event_id, 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime()), 'platform': 'python',
               'level': 'info', 'environment': (client.options or {}).get('environment'),
               'release': (client.options or {}).get('release'),
               'contexts': {'feedback': dict(feedback, associated_event_id=associated_event_id)}}
    envelope = Envelope(headers={'event_id': event_id})
    envelope.add_item(Item(payload=PayloadRef(json=payload), type='feedback'))
    client.transport.capture_envelope(envelope)
    return True


def report(category, message, include_activity=True, contact_email=None):
    """Save a problem report locally and send it to Sentry's user feedback when Sentry is enabled."""
    category = category if category in CATEGORIES else 'other'
    message = redact(message)
    contact = contact_email.strip() if isinstance(contact_email, str) and EMAIL.match(contact_email.strip()) else None
    activity = [{'ts': r['ts'], 'message': r['message'], 'data': r['data']} for r in list(_ring)[-50:]] if include_activity else None
    feedback = {'message': '[%s] %s' % (category, message), 'source': 'kobil-sdk-mcp'}
    if contact:
        feedback['contact_email'] = contact
    saved = None
    try:
        directory = state_dir() / 'reports'
        _private_dir(directory)
        saved = '%s-%s.json' % (time.strftime('%Y%m%d-%H%M%S'), _session)
        body = {'category': category, 'message': message, 'session': _session, 'contact_given': bool(contact), 'activity': activity}
        fd = os.open(directory / saved, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as handle:
            json.dump(body, handle, indent=1)
    except OSError:
        saved = None
    sent = False
    if _sentry is not None:
        extra = {'category': category, 'session': _sentry_tag_session()}
        if activity is not None:
            extra['activity'] = activity
        try:
            event_id = _sentry.capture_event({'level': 'info', 'message': 'Problem report context (%s)' % category,
                                              'tags': {'kobil_feedback': '1', 'feedback_category': category}, 'extra': extra})
            sent = _send_feedback(feedback, event_id)
        except Exception:
            sent = False
    crumb('feedback', 'report', kind=category, sent=sent, contact=bool(contact))
    return {'saved': bool(saved), 'sent': sent, 'category': category, 'contact_stored': bool(contact)}
