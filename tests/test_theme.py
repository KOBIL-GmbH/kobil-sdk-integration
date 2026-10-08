"""The theme is words, served by the MCP; an owner's own theme replaces the default at project or user level."""
import asyncio
import os
import re
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('KOBIL_SDK_SENTRY_ENVIRONMENT', 'tests')
os.environ.setdefault('KOBIL_SDK_USAGE_LOG', '0')

from kobil_sdk_integration import server, theme

SECTIONS = ('The impression', 'Colour', 'Shape and space', 'Type', 'Movement', 'Components in words',
            'The screens in words', 'What to avoid')


class DefaultThemeTests(unittest.TestCase):
    def setUp(self):
        self.text = theme.default_text()

    def test_has_all_sections_tables_and_no_code(self):
        for heading in SECTIONS:
            self.assertIn('## ' + heading, self.text)
        self.assertNotIn('```', self.text)
        self.assertGreaterEqual(self.text.count('\n| '), 25)

    def test_colours_are_usable_roles_with_light_and_dark_values(self):
        rows = re.findall(r'^\| ([A-Za-z ]+) \| `(#[0-9A-F]{6})` \| `(#[0-9A-F]{6})` \|', self.text, re.M)
        roles = {r[0] for r in rows}
        for role in ('Brand', 'Brand dark', 'Screen', 'Surface', 'Text primary', 'Text secondary', 'Hairline', 'Error', 'Success'):
            self.assertIn(role, roles)

    def test_measures_and_type_scale_are_given_as_numbers(self):
        for needle in ('| Height of buttons and text fields | 48 |', 'Screen title | 24 | semibold', 'Body | 16 | regular'):
            self.assertIn(needle, self.text)

    def test_says_how_to_replace_it_and_has_no_internal_references(self):
        self.assertIn('sdk_theme_set', self.text)
        self.assertIsNone(re.search(r'shift-core|theme_config|ios-visual-check|ssms|mini-?app|lib/feature|flutter token', self.text, re.I))


class ResolutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name).resolve()
        self.project = root / 'App'
        self.project.mkdir()
        self.home = root / 'home'
        self.env = {'KOBIL_SDK_PROJECT': str(self.project), 'KOBIL_SDK_HOME': str(self.home)}

    def test_default_when_nothing_is_set(self):
        got = theme.load(self.env)
        self.assertEqual(got['source'], 'default')
        self.assertEqual(got['text'], theme.default_text())

    def test_project_beats_user_beats_default_and_env_beats_all(self):
        theme.save('# User theme\nuser', 'user', self.env)
        self.assertEqual(theme.load(self.env)['source'], 'user')
        theme.save('# Project theme\nproject', 'project', self.env)
        self.assertEqual(theme.load(self.env)['source'], 'project')
        custom = Path(self.tmp.name) / 'mine.md'
        custom.write_text('# From file\nfile')
        self.assertEqual(theme.load({**self.env, 'KOBIL_SDK_THEME': str(custom)})['text'], '# From file\nfile')

    def test_project_file_is_private_and_inside_the_state_folder_of_the_project(self):
        theme.save('# T\nx', 'project', self.env)
        path = self.project / '.kobil-sdk' / 'theme.md'
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_user_theme_lives_in_the_state_directory(self):
        theme.save('# T\nx', 'user', self.env)
        self.assertTrue((self.home / 'theme.md').is_file())

    def test_reset_returns_to_the_next_level(self):
        theme.save('# U\nu', 'user', self.env)
        theme.save('# P\np', 'project', self.env)
        self.assertTrue(theme.reset('project', self.env)['removed'])
        self.assertEqual(theme.load(self.env)['source'], 'user')
        self.assertTrue(theme.reset('user', self.env)['removed'])
        self.assertEqual(theme.load(self.env)['source'], 'default')
        self.assertFalse(theme.reset('user', self.env)['removed'])

    def test_unreadable_override_falls_back_to_the_default(self):
        (self.project / '.kobil-sdk').mkdir()
        (self.project / '.kobil-sdk' / 'theme.md').write_bytes(b'\xff\xfe\x00')
        self.assertEqual(theme.load(self.env)['source'], 'default')

    def test_project_scope_needs_a_project(self):
        with self.assertRaisesRegex(ValueError, 'PROJECT_NOT_SELECTED'):
            theme.save('# T\nx', 'project', {'KOBIL_SDK_HOME': str(self.home)})


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.env = {'KOBIL_SDK_PROJECT': tempfile.mkdtemp(), 'KOBIL_SDK_HOME': tempfile.mkdtemp()}

    def test_refused_inputs(self):
        for bad, why in (('', 'empty'), ('   \n', 'empty'), ('x' * 24001, 'too long'), ('a\x00b', 'binary'),
                         ('# T\ntoken eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc', 'secret'),
                         ('# T\npassword=hunter2', 'secret'), (None, 'text'), (123, 'text')):
            with self.assertRaises(ValueError, msg=why):
                theme.save(bad, 'project', self.env)

    def test_unknown_scope_is_refused(self):
        with self.assertRaises(ValueError):
            theme.save('# T\nx', 'global', self.env)
        with self.assertRaises(ValueError):
            theme.reset('global', self.env)

    def test_colour_codes_are_not_mistaken_for_secrets(self):
        theme.save('# T\nbrand #1D19FF, screen #F2F4F9, radius 16', 'project', self.env)


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = {'KOBIL_SDK_PROJECT': str(Path(self.tmp.name) / 'App'), 'KOBIL_SDK_HOME': str(Path(self.tmp.name) / 'home')}
        (Path(self.tmp.name) / 'App').mkdir()

    def test_tools_are_registered_with_clear_parameters(self):
        tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
        self.assertEqual(tools['sdk_theme_get'].inputSchema.get('required', []), [])
        self.assertEqual(set(tools['sdk_theme_set'].inputSchema['required']), {'theme_markdown'})
        self.assertIn('scope', tools['sdk_theme_set'].inputSchema['properties'])
        self.assertIn('scope', tools['sdk_theme_reset'].inputSchema['properties'])

    def test_round_trip_through_the_tools(self):
        with mock.patch.dict(os.environ, self.env):
            first = server.sdk_theme_get()
            self.assertEqual(first['source'], 'default')
            self.assertIn('Colour', ' '.join(first['sections']))
            self.assertIn('sdk_theme_set', first['how_to_replace'])
            saved = server.sdk_theme_set('# Mine\nOnly red.', 'project')
            self.assertTrue(saved['saved'])
            self.assertEqual(server.sdk_theme_get()['text'].strip(), '# Mine\nOnly red.')
            self.assertEqual(server.sdk_theme_get()['source'], 'project')
            server.sdk_theme_reset('project')
            self.assertEqual(server.sdk_theme_get()['source'], 'default')

    def test_result_never_contains_absolute_paths(self):
        with mock.patch.dict(os.environ, self.env):
            server.sdk_theme_set('# Mine\nx', 'project')
            self.assertNotIn(self.tmp.name, repr(server.sdk_theme_get()) + repr(server.sdk_theme_set('# M\nx', 'user')))


class WiringTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parent.parent

    def test_skill_and_package_data(self):
        skill = (self.ROOT / 'skills' / 'kobil-sdk' / 'SKILL.md').read_text()
        for needle in ('sdk_theme_get', 'sdk_theme_set', "owner's own theme"):
            self.assertIn(needle, skill)
        self.assertIn('knowledge/*.md', (self.ROOT / 'pyproject.toml').read_text())

    def test_the_app_brief_loads_the_theme_through_the_tool(self):
        from kobil_sdk_integration import app_brief
        with mock.patch.dict(os.environ, {'KOBIL_SDK_PROJECT': '/nonexistent'}):
            brief = app_brief.build('ios', status={'configured': True, 'environment': 'e', 'tls_check_hosts': []})
        self.assertIn('sdk_theme_get', [s['tool'] for s in brief['steps']])
        self.assertIn('sdk_theme_get', brief['prompt'])


if __name__ == '__main__':
    unittest.main()
