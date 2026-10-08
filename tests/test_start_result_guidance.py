"""The Start result comes back through the completion handler of the request; guidance must say so (an agent hung on it)."""
import json
import os
import unittest
from pathlib import Path

os.environ.setdefault('KOBIL_SDK_SENTRY_ENVIRONMENT', 'tests')
os.environ.setdefault('KOBIL_SDK_USAGE_LOG', '0')

ROOT = Path(__file__).resolve().parent.parent


class StartResultGuidanceTests(unittest.TestCase):
    def test_skill_names_the_completion_handler_the_nil_trap_and_the_timeout(self):
        skill = (ROOT / 'skills' / 'kobil-sdk' / 'SKILL.md').read_text()
        for needle in ('withCompletionHandler', 'never pass nil', 'timeout'):
            self.assertIn(needle, skill)

    def test_ios_knowledge_says_where_results_arrive(self):
        setup = json.loads((ROOT / 'src' / 'kobil_sdk_integration' / 'knowledge' / 'setup.json').read_text())
        note = setup['platform_notes']['ios']
        for needle in ('withCompletionHandler', 'StartResult', 'never nil', 'timeout'):
            self.assertIn(needle, note)

    def test_the_symptom_is_described_so_an_agent_can_recognise_it(self):
        text = (ROOT / 'skills' / 'kobil-sdk' / 'references' / 'native-integration.md').read_text()
        self.assertIn('StartResult', text)
        self.assertIn('no further log line', text)


if __name__ == '__main__':
    unittest.main()
