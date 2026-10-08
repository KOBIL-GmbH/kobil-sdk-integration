"""A scripted device test: a display message, a signature request and a payment, spaced out.

Testers asked for the same sequence after every build: "send a chat message, a signature
request and a payment, 30 seconds apart", so each can be looked at on the phone. Sending
them by hand takes three calls and a stopwatch; this sends them from a background thread
and keeps the IDs, so the caller returns at once and reads progress later.

Every step writes backend state. A step that fails is recorded and not retried.
"""
import hashlib
import threading
import time
import uuid
from datetime import datetime, timezone

STEPS = ('message', 'signature', 'payment')
SAMPLE_DOCUMENT = 'Sample-Agreement.pdf'


def step_request(step, confirmation_timeout_seconds):
    """What each step sends: generic sample content, using the documented data keys."""
    if step == 'message':
        return {'kind': 'display_message',
                'text': 'Welcome! This is a test message from your provider.',
                'data': {'title': 'Support'}, 'timeout_seconds': 3600}
    if step == 'signature':
        digest = hashlib.sha256(('sample document ' + SAMPLE_DOCUMENT).encode()).hexdigest()
        return {'kind': 'transaction', 'text': 'Sign {{documentName}} (SHA-256 {{documentSha256}})',
                'data': {'requestType': 'signature', 'documentName': SAMPLE_DOCUMENT, 'documentSha256': digest},
                'confirmation_timeout_seconds': confirmation_timeout_seconds}
    if step == 'payment':
        return {'kind': 'transaction', 'text': 'Approve payment of {{amount}} {{currency}} to {{merchant}}',
                'data': {'requestType': 'payment', 'amount': '24.50', 'currency': 'EUR', 'merchant': 'Test Shop'},
                'confirmation_timeout_seconds': confirmation_timeout_seconds}
    raise ValueError('steps are %s' % ', '.join(STEPS))


def validate(steps, delay_seconds, confirmation_timeout_seconds):
    steps = list(STEPS) if steps is None else list(steps)
    if not steps or len(steps) > len(STEPS) or len(set(steps)) != len(steps) or any(s not in STEPS for s in steps):
        raise ValueError('steps: each of %s at most once' % ', '.join(STEPS))
    if type(delay_seconds) is not int or not 5 <= delay_seconds <= 300:
        raise ValueError('delay_seconds must be 5–300')
    if type(confirmation_timeout_seconds) is not int or not 30 <= confirmation_timeout_seconds <= 3600:
        raise ValueError('confirmation_timeout_seconds must be 30–3600')
    return steps


class Runs:
    """Sequences started by this server process. Nothing is written to disk."""

    def __init__(self, sleep=time.sleep):
        self._runs = {}
        self._lock = threading.Lock()
        self._sleep = sleep

    def start(self, send_message, send_transaction, steps, delay_seconds, confirmation_timeout_seconds):
        steps = validate(steps, delay_seconds, confirmation_timeout_seconds)
        run_id = uuid.uuid4().hex[:12]
        record = {'run_id': run_id, 'delay_seconds': delay_seconds, 'finished': False,
                  'steps': [{'step': s, 'sent': False, 'planned_after_seconds': i * delay_seconds}
                            for i, s in enumerate(steps)]}
        with self._lock:
            self._runs[run_id] = record

        def work():
            for index, step in enumerate(steps):
                if index:
                    self._sleep(delay_seconds)
                request = step_request(step, confirmation_timeout_seconds)
                entry = record['steps'][index]
                try:
                    if request['kind'] == 'display_message':
                        result = send_message(request['text'], request['data'], request['timeout_seconds'])
                    else:
                        result = send_transaction(request['text'], request['data'], request['confirmation_timeout_seconds'])
                    update = {'sent': True, **result}
                except Exception as error:  # recorded, never retried: the write may have happened
                    update = {'sent': False, 'error': str(error) or type(error).__name__,
                              'note': 'Not retried; check the backend before sending again.'}
                update['at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
                with self._lock:
                    entry.update(update)
            with self._lock:
                record['finished'] = True

        threading.Thread(target=work, name='tms-sequence-' + run_id, daemon=True).start()
        return self.status(run_id)

    def status(self, run_id):
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                raise ValueError('Unknown run_id (runs are kept only while this server runs)')
            return {**record, 'steps': [dict(s) for s in record['steps']]}


RUNS = Runs()
