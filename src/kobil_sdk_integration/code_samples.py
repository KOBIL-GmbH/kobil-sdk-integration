"""Basic code samples for events, errors and waiting, served from knowledge/code_samples (GettingStarted and app code, trimmed)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent / 'knowledge'
PLATFORMS = {'ios': 'ios', 'swift': 'ios', 'android': 'android', 'kotlin': 'android', 'flutter': 'flutter', 'dart': 'flutter'}


def get(platform, topic=None):
    key = PLATFORMS.get((platform or '').lower())
    if not key:
        raise ValueError('platform must be ios, android or flutter')
    index = json.loads((ROOT / 'code_samples' / 'index.json').read_text())
    entry = index['platforms'][key]
    samples = [s for s in entry['samples'] if topic in (None, '', s['topic'], s['id'])]
    if not samples:
        raise ValueError('topic must be one of: ' + ', '.join(sorted({s['topic'] for s in entry['samples']})))
    return {'platform': key, 'language': entry['language'], 'verified': entry['verified'], 'intro': index['intro'],
            'rules': index['rules'], 'completion_handler': index['completion_handler'],
            'samples': [{**s, 'code': (ROOT / 'code_samples' / s['file']).read_text()} for s in samples]}


def _norm(name):
    n = re.sub(r'^(KSM|Ksm)', '', (name or '').strip())
    n = re.sub(r'Event$', '', n)
    return n.lower()


def event_result(event=None):
    """The result event of an event the app sends, and whether the completion handler may be nil. No name: the whole table."""
    table = json.loads((ROOT / 'code_samples' / 'event_results.json').read_text())
    if not event:
        return table
    wanted = _norm(event)
    for name, row in table['events'].items():
        if _norm(name) == wanted:
            return {'event': name, **row, 'about': table['about'], 'note': table['note']}
    raise ValueError('unknown event "%s": it is not an event the app sends to the SDK; call without a name for the whole table' % event)
