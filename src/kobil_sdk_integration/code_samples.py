"""Basic code samples for events, errors and waiting, served from knowledge/code_samples (GettingStarted and app code, trimmed)."""
import json
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
            'rules': index['rules'],
            'samples': [{**s, 'code': (ROOT / 'code_samples' / s['file']).read_text()} for s in samples]}
