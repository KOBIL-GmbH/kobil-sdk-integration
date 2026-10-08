"""One short request ('build me an app with the KOBIL SDK') expands into the full, verified task."""
import asyncio
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('KOBIL_SDK_SENTRY_ENVIRONMENT', 'tests')
os.environ.setdefault('KOBIL_SDK_USAGE_LOG', '0')

from kobil_sdk_integration import app_brief, server

NAMES = ('KSMasterController', 'hnb', 'kssidp', 'KSTrustedWebView')
STATUS = {'environment': 'demo', 'tenant': 'tenant1', 'configured': True,
          'tls_check_hosts': ['idp.example.test', 'ast.example.test']}


def tool_schemas():
    return {t.name: t.inputSchema for t in asyncio.run(server.mcp.list_tools())}


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name).resolve()
        self.project = root / 'MyShop'
        (self.project / 'MyShop.xcodeproj').mkdir(parents=True)
        (self.project / 'MyShop.xcodeproj' / 'project.pbxproj').write_text('DEVELOPMENT_TEAM = TEAM123456;\n')
        self.delivery = root / 'SDK' / 'debug'
        for name in NAMES:
            (self.delivery / (name + '.xcframework')).mkdir(parents=True)
        self.env = {'KOBIL_SDK_PROJECT': str(self.project), 'KOBIL_SDK_HOME': str(root / 'state')}

    def brief(self, **kwargs):
        with mock.patch.dict(os.environ, self.env, clear=False):
            return app_brief.build('ios', status=kwargs.pop('status', STATUS), **kwargs)


class BriefContentTests(Fixture):
    def test_every_step_uses_a_real_tool_with_real_parameter_names(self):
        schemas = tool_schemas()
        brief = self.brief(delivery_folder=str(self.delivery.parent))
        self.assertGreaterEqual(len(brief['steps']), 8)
        for step in brief['steps']:
            self.assertIn(step['tool'], schemas, step)
            required = set(schemas[step['tool']].get('required', []))
            allowed = set(schemas[step['tool']]['properties'])
            args = set(step['args'])
            self.assertTrue(required <= args, '%s misses %s' % (step['tool'], required - args))
            self.assertTrue(args <= allowed, '%s has unknown %s' % (step['tool'], args - allowed))

    def test_facts_from_the_backend_and_the_project_are_filled_in(self):
        brief = self.brief(delivery_folder=str(self.delivery.parent))
        text = brief['prompt']
        self.assertEqual(brief['needs_input'], [])
        self.assertEqual(brief['decisions']['team_id'], 'TEAM123456')
        self.assertEqual(brief['decisions']['target_name'], 'MyShop')
        self.assertIn('demo', text)
        self.assertIn('idp.example.test', text)
        self.assertEqual(brief['decisions']['frameworks_dir'], str(self.delivery))
        self.assertIn('myshop', brief['decisions']['test_user_prefix'])

    def test_decisions_follow_the_verified_defaults(self):
        d = self.brief(delivery_folder=str(self.delivery)).get('decisions')
        self.assertEqual((d['activation_client'], d['login_client']), ('KobilMobileEnrollment', 'KobilMobileLogin'))
        self.assertFalse(d['mtls'])
        self.assertEqual(d['jwt_sign_key_policy_simulator'], 'ALLOW_VIRTUAL_SMART_CARD')

    def test_rules_and_gates_are_complete(self):
        brief = self.brief(delivery_folder=str(self.delivery))
        self.assertEqual([g['id'] for g in brief['gates']], [1, 2, 3, 4, 5, 6])
        joined = ' '.join(brief['rules']).lower()
        for needle in ('never print', 'project.pbxproj', 'sdk_onboarding_prepare', 'existing users'):
            self.assertIn(needle, joined)
        self.assertIn('ACTIVITY.md', brief['prompt'])
        self.assertIn('TEST_REPORT.md', brief['prompt'])

    def test_prompt_is_usable_as_one_message(self):
        prompt = self.brief(delivery_folder=str(self.delivery))['prompt']
        self.assertLess(len(prompt), 6500)
        self.assertTrue(prompt.startswith('autopilot.'))

    def test_no_secret_shaped_text_and_no_foreign_paths(self):
        prompt = self.brief(delivery_folder=str(self.delivery))['prompt']
        self.assertNotRegex(prompt, r'eyJ[\w-]{10,}\.')
        self.assertNotIn('/Users/', prompt.replace(str(self.project), '').replace(self.tmp.name, ''))


class NeedsInputTests(Fixture):
    def test_missing_delivery_is_one_question_not_a_guess(self):
        import shutil
        shutil.move(str(self.delivery.parent), str(Path(self.tmp.name) / 'elsewhere'))
        brief = self.brief()
        self.assertEqual([n['key'] for n in brief['needs_input']], ['sdk_delivery_folder'])
        self.assertIn('ask', brief['needs_input'][0]['ask'].lower())

    def test_unconfigured_connection_leads_to_onboarding_not_credentials(self):
        brief = self.brief(status=None, delivery_folder=str(self.delivery))
        keys = [n['key'] for n in brief['needs_input']]
        self.assertIn('connection', keys)

    def test_delivery_is_found_from_the_environment_variable(self):
        import shutil
        moved = Path(self.tmp.name) / 'elsewhere'
        shutil.move(str(self.delivery.parent), str(moved))
        self.env['KOBIL_SDK_DELIVERY'] = str(moved / 'debug')
        self.assertEqual(self.brief()['needs_input'], [])

    def test_a_sibling_sdk_folder_is_found_without_asking(self):
        self.assertEqual(self.brief()['needs_input'], [])

    def test_every_tool_named_in_the_prompt_exists(self):
        names = {t.name for t in asyncio.run(server.mcp.list_tools())}
        mentioned = set(re.findall(r'\bsdk_[a-z_]+', self.brief(delivery_folder=str(self.delivery))['prompt']))
        self.assertEqual(sorted(mentioned - names), [])

    def test_no_xcode_project_in_the_folder_is_reported(self):
        for item in (self.project / 'MyShop.xcodeproj').iterdir():
            item.unlink()
        (self.project / 'MyShop.xcodeproj').rmdir()
        brief = self.brief(delivery_folder=str(self.delivery))
        self.assertIn('xcode_project', [n['key'] for n in brief['needs_input']])


class RememberTests(Fixture):
    def setUp(self):
        super().setUp()
        import shutil
        self.moved = Path(self.tmp.name) / 'elsewhere'
        shutil.move(str(self.delivery.parent), str(self.moved))
        self.env['KOBIL_SDK_HOME'] = str(Path(self.tmp.name) / 'home')

    def test_a_given_folder_is_remembered_privately_and_not_asked_again(self):
        first = self.brief(delivery_folder=str(self.moved))
        self.assertEqual(first['needs_input'], [])
        remembered = Path(self.tmp.name) / 'home' / 'sdk-delivery'
        self.assertEqual(remembered.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.brief()['needs_input'], [])

    def test_a_wrong_folder_is_not_remembered(self):
        self.brief(delivery_folder=str(Path(self.tmp.name) / 'nothing'))
        self.assertFalse((Path(self.tmp.name) / 'home' / 'sdk-delivery').exists())

    def test_a_remembered_folder_that_disappeared_is_asked_again(self):
        self.brief(delivery_folder=str(self.moved))
        import shutil
        shutil.rmtree(self.moved)
        self.assertEqual([n['key'] for n in self.brief()['needs_input']], ['sdk_delivery_folder'])


class FindFrameworkSetTests(Fixture):
    def test_set_is_found_directly_or_in_debug(self):
        self.assertEqual(app_brief.find_framework_set(self.delivery), self.delivery)
        self.assertEqual(app_brief.find_framework_set(self.delivery.parent), self.delivery)

    def test_incomplete_or_missing_sets_are_rejected(self):
        self.assertIsNone(app_brief.find_framework_set(Path(self.tmp.name) / 'nothing'))
        import shutil
        shutil.rmtree(self.delivery / 'hnb.xcframework')
        self.assertIsNone(app_brief.find_framework_set(self.delivery))


class ToolAndPromptTests(Fixture):
    def test_tool_and_mcp_prompt_are_registered(self):
        self.assertIn('sdk_build_app_brief', tool_schemas())
        prompts = {p.name for p in asyncio.run(server.mcp.list_prompts())}
        self.assertIn('build_app', prompts)

    def test_prompt_returns_the_generated_text(self):
        with mock.patch.dict(os.environ, self.env, clear=False), \
                mock.patch.object(server, 'sdk_backend_status', return_value=STATUS):
            result = asyncio.run(server.mcp.get_prompt('build_app', {'sdk_delivery_folder': str(self.delivery)}))
        text = result.messages[0].content.text
        self.assertTrue(text.startswith('autopilot.'))
        self.assertIn('MyShop', text)

    def test_skill_triggers_on_the_short_request_and_names_the_tool(self):
        skill = (Path(__file__).resolve().parent.parent / 'skills' / 'kobil-sdk' / 'SKILL.md').read_text()
        head = skill.split('---', 2)[1].lower()
        for needle in ('build', 'app', 'kobil sdk'):
            self.assertIn(needle, head)
        self.assertIn('sdk_build_app_brief', skill)


if __name__ == '__main__':
    unittest.main()
