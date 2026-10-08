"""Look and feel ships as words: a plain description, a measured guide for every platform, no code templates."""
import os
import re
import unittest
from pathlib import Path

os.environ.setdefault('KOBIL_SDK_SENTRY_ENVIRONMENT', 'tests')
os.environ.setdefault('KOBIL_SDK_USAGE_LOG', '0')

ROOT = Path(__file__).resolve().parent.parent
REFERENCES = ROOT / 'skills' / 'kobil-sdk' / 'references'
WORDS = REFERENCES / 'look-and-feel.md'
GUIDE = REFERENCES / 'design-system.md'
DOCS = [GUIDE, REFERENCES / 'reference-app-design.md', WORDS]
FORBIDDEN = re.compile(r'shift-core|theme_config|ios-visual-check|ssms|mini-?app|lib/feature', re.I)


class LookAndFeelTests(unittest.TestCase):
    def test_no_internal_source_or_foreign_tool_references(self):
        for path in DOCS:
            self.assertIsNone(FORBIDDEN.search(path.read_text()), path.name)

    def test_every_relative_link_exists(self):
        for path in DOCS:
            for link in re.findall(r'\]\(([^)#]+)\)', path.read_text()):
                if '://' not in link:
                    self.assertTrue((path.parent / link).exists(), '%s -> %s' % (path.name, link))

    def test_the_description_in_words_has_no_code(self):
        text = WORDS.read_text()
        self.assertNotIn('```', text)
        self.assertNotRegex(text, r'`[^`]*\(')
        for heading in ('The impression', 'Colour', 'Shape and space', 'The screens, in words', 'What to avoid'):
            self.assertIn(heading, text)

    def test_guide_covers_all_three_platforms(self):
        guide = GUIDE.read_text()
        for needle in ('SwiftUI', 'Jetpack Compose', 'Flutter'):
            self.assertIn(needle, guide)

    def test_words_and_guide_agree_on_the_main_colours(self):
        words, guide = WORDS.read_text().upper(), GUIDE.read_text().upper()
        for value in ('1D19FF', '04004C', 'F2F4F9'):
            self.assertIn(value, guide)

    def test_no_code_templates_ship(self):
        self.assertFalse((REFERENCES / 'theme').exists())
        self.assertEqual(list(REFERENCES.rglob('KobilTheme*')) + list(REFERENCES.rglob('kobil_theme*')), [])

    def test_skill_points_to_the_words_and_the_guide(self):
        skill = (ROOT / 'skills' / 'kobil-sdk' / 'SKILL.md').read_text()
        for needle in ('look-and-feel.md', 'design-system.md', "owner's own design", 'no code template'):
            self.assertIn(needle, skill)


if __name__ == '__main__':
    unittest.main()
