"""Guard the shipped guidance: required facts present, no internal identifiers.

Two deterministic checks that run with the normal unit suite:

1. ``tests/guidance_assertions.json`` lists phrases the served knowledge
   (``sdk_knowledge_get``), the skill references and SKILL.md must contain -
   measured facts an agent has to be able to read - and phrases that must not
   return.
2. A leak scan over every shipped text file for identifiers that must never
   appear in this public repository: internal page ids, test-fixture user
   names, transaction ids, device serials, personal paths, e-mail addresses,
   internal hostnames and customer names. Functional realm/environment
   identifiers that are part of the bundled configuration are allow-listed
   explicitly below with their reason.
"""
import json
import re
import unittest
from pathlib import Path

from kobil_sdk_integration.knowledge_api import get_topic

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'kobil-sdk'
def _norm(text):
    # collapse whitespace and drop markdown code ticks so formatting cannot hide a fact
    return re.sub(r'\s+', ' ', text.replace('`', ''))


ASSERTIONS = json.loads((Path(__file__).parent / 'guidance_assertions.json').read_text(encoding='utf-8'))

# Identifiers that must never ship. Each pattern is case-insensitive.
FORBIDDEN = {
    'confluence page id': r'\b6219901\d\b',
    'transaction ulid': r'\b01M[0-9A-Z]{23}\b',
    'fixture user name': r'\b(ak539-[a-z0-9-]+|round[0-9]-[a-z0-9-]+-(app|probe|jwt|android)[a-z0-9-]*)\b',
    'device serial': r'\b(3C071FDJH000NY|00008150-[0-9A-F]{16})\b',
    'personal path': r'/Users/[a-z]+\.[a-z]+/',
    'e-mail address': r'\b[a-z0-9._-]+@[a-z0-9.-]+\.(com|de|et|test)\b',
    'internal hostname': r'\b(sicher\.men|k2ndlevel01|[a-z0-9.-]+\.kobil\.com)\b',
    'native or server source reference': r'\b[A-Za-z0-9_./-]+\.(cc|cpp|cxx|java)(:\d+(-\d+)?)?\b',
    'internal ticket key': r'\b(AK|DS|CBE|IDP|SDSH|KHC|WLA)-\d{2,5}\b',
    'source-review claim': r'\b(source reviewed in|on the inspected [A-Za-z]+ source|inspected [A-Za-z]+ source)\b',
    'customer or env name': r'\b(fis_bmw|fis bmw|bddklogin|arabox|migros|nouvobanq|gondor|asgard|bekb|3beg|keb)\b',
}
# Functional identifiers shipped on purpose (bundled default environment and
# realm policy map). Keep this list short and justified.
ALLOWED_TERMS = {'akinci', 'superapp', 'bddk', 'bddklogin'}  # bundled realm/client policy map, pre-1.0 public
# Public contact/documentation hosts that are not internal infrastructure.
ALLOWED_HOSTS = {'developer.kobil.com', 'www.kobil.com', 'github.com'}

TEXT_SUFFIXES = {'.md', '.json', '.py', '.toml', '.txt', '.yaml', '.yml'}
SCAN_DIRS = ['skills', 'src', 'docs', 'README.md', 'CHANGELOG.md', 'pyproject.toml', '.codex-plugin']


def _shipped_files():
    for entry in SCAN_DIRS:
        p = ROOT / entry
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in p.rglob('*'):
                if f.is_file() and f.suffix in TEXT_SUFFIXES and '__pycache__' not in f.parts:
                    yield f


class GuidanceAssertionTests(unittest.TestCase):
    def test_served_knowledge_contains_measured_facts(self):
        for topic, rules in ASSERTIONS['topics'].items():
            for platform in ('android', 'ios'):
                text = _norm(json.dumps(get_topic(topic, platform, sdk_version='unverified-release'), ensure_ascii=False))
                for phrase in rules.get('must_contain', []):
                    self.assertIn(phrase, text, (topic, platform, phrase))
                for phrase in rules.get('must_not_contain', []):
                    self.assertNotIn(phrase, text, (topic, platform, phrase))

    def test_references_contain_measured_facts(self):
        for name, rules in ASSERTIONS['references'].items():
            text = _norm((SKILL / 'references' / name).read_text(encoding='utf-8'))
            for phrase in rules.get('must_contain', []):
                self.assertIn(phrase, text, (name, phrase))

    def test_skill_md_links_the_gates(self):
        text = _norm((SKILL / 'SKILL.md').read_text(encoding='utf-8'))
        for phrase in ASSERTIONS['skill_md_must_contain']:
            self.assertIn(phrase, text, phrase)

    def test_cross_file_consistency(self):
        """The same measured fact must be stated wherever the agent may read it."""
        def location_text(loc):
            kind, _, name = loc.partition(':')
            if kind == 'topic':
                return _norm(json.dumps(get_topic(name, 'android', sdk_version='unverified-release'), ensure_ascii=False))
            if kind == 'ref':
                return _norm((SKILL / 'references' / name).read_text(encoding='utf-8'))
            if kind == 'skill':
                return _norm((SKILL / 'SKILL.md').read_text(encoding='utf-8'))
            raise ValueError(loc)
        for rule in ASSERTIONS['cross_file']['rules']:
            for loc in rule['in']:
                self.assertTrue(rule['phrase'] in location_text(loc), f"'{rule['phrase']}' missing in {loc}")


class LeakScanTests(unittest.TestCase):
    def test_no_internal_identifiers_in_shipped_text(self):
        hits = []
        for f in _shipped_files():
            if f.name == 'test_guidance_guard.py':
                continue
            text = f.read_text(encoding='utf-8', errors='replace')
            for label, pattern in FORBIDDEN.items():
                for m in re.finditer(pattern, text, re.IGNORECASE):
                    token = m.group(0).lower()
                    if label == 'internal hostname' and token in ALLOWED_HOSTS:
                        continue
                    if token in ALLOWED_TERMS:
                        continue
                    line = text.count('\n', 0, m.start()) + 1
                    hits.append(f'{f.relative_to(ROOT)}:{line}: {label}: {m.group(0)}')
        self.assertEqual(hits, [], 'internal identifiers in shipped text:\n' + '\n'.join(hits))


if __name__ == '__main__':
    unittest.main()
