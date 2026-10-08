"""Embed the four SDK XCFrameworks into an Xcode project: project file edits, idempotence and the MCP tool."""
import hashlib
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('KOBIL_SDK_SENTRY_ENVIRONMENT', 'tests')
os.environ.setdefault('KOBIL_SDK_USAGE_LOG', '0')

from kobil_sdk_integration import server, xcodeproj

FIXTURE = Path(__file__).parent / 'fixtures' / 'app.pbxproj'
NAMES = xcodeproj.IOS_FRAMEWORKS


class ProjectCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.project = root / 'app' / 'KobilChatApp.xcodeproj'
        self.project.mkdir(parents=True)
        shutil.copy(FIXTURE, self.project / 'project.pbxproj')
        (root / 'app' / 'KobilChatApp').mkdir()
        self.frameworks = root / 'delivery'
        for name in NAMES:
            (self.frameworks / (name + '.xcframework')).mkdir(parents=True)
            (self.frameworks / (name + '.xcframework') / 'Info.plist').write_text('x')

    def text(self):
        return (self.project / 'project.pbxproj').read_text()

    def integrate(self, **kwargs):
        return xcodeproj.integrate(self.project, 'KobilChatApp', self.frameworks, **kwargs)


class IntegrateTests(ProjectCase):
    def test_frameworks_are_linked_embedded_and_signed(self):
        result = self.integrate()
        text = self.text()
        self.assertTrue(result['changed'])
        for name in NAMES:
            self.assertEqual(text.count('%s.xcframework in Embed Frameworks' % name), 2)  # build file and phase entry
            self.assertIn('%s.xcframework in Frameworks' % name, text)
            self.assertTrue((self.project.parent / 'Frameworks' / (name + '.xcframework')).is_dir())
        self.assertIn('isa = PBXCopyFilesBuildPhase;', text)
        self.assertIn('CodeSignOnCopy', text)
        self.assertIn('name = "Embed Frameworks";', text)
        self.assertIn('/* KOBIL SDK */', text)

    def test_bridging_header_and_settings(self):
        self.integrate(marketing_version='2.3.4')
        header = self.project.parent / 'KobilChatApp' / 'KobilChatApp-Bridging-Header.h'
        self.assertIn('KSMasterController/KSMasterController.h', header.read_text())
        text = self.text()
        self.assertIn('SWIFT_OBJC_BRIDGING_HEADER = "KobilChatApp/KobilChatApp-Bridging-Header.h";', text)
        self.assertIn('MARKETING_VERSION = 2.3.4;', text)

    def test_app_target_is_limited_to_iphone_and_ipad(self):
        self.integrate()
        text = self.text()
        self.assertIn('SUPPORTED_PLATFORMS = "iphoneos iphonesimulator";', text)
        self.assertIn('SUPPORTS_MACCATALYST = NO;', text)
        self.assertIn('TARGETED_DEVICE_FAMILY = "1,2";', text)

    def test_second_run_changes_nothing(self):
        self.integrate()
        before = hashlib.sha256(self.text().encode()).hexdigest()
        result = self.integrate()
        self.assertFalse(result['changed'])
        self.assertEqual(hashlib.sha256(self.text().encode()).hexdigest(), before)

    def test_object_ids_are_stable_and_unique(self):
        self.integrate()
        defined = re.findall(r'^\t\t([0-9A-F]{24}) /\*.*?\*/ = ', self.text(), re.M)
        self.assertEqual(len(defined), len(set(defined)))
        self.assertEqual(xcodeproj.object_id('a'), xcodeproj.object_id('a'))

    def test_deployment_target_reaches_every_native_target(self):
        self.integrate(deployment_target='26.0')
        self.assertGreaterEqual(len(re.findall(r'IPHONEOS_DEPLOYMENT_TARGET = 26\.0;', self.text())), 6)

    def test_usage_descriptions_are_added_once_and_never_overwritten(self):
        self.integrate(usage_descriptions={'NSFaceIDUsageDescription': 'Face ID unlocks the key.'})
        self.assertIn('INFOPLIST_KEY_NSFaceIDUsageDescription = "Face ID unlocks the key.";', self.text())
        self.integrate(usage_descriptions={'NSFaceIDUsageDescription': 'Another sentence.'})
        self.assertNotIn('Another sentence.', self.text())

    def test_unknown_usage_key_is_rejected(self):
        with self.assertRaises(ValueError):
            self.integrate(usage_descriptions={'NSLocationUsageDescription': 'x'})

    def test_incomplete_framework_set_names_the_missing_one(self):
        shutil.rmtree(self.frameworks / 'hnb.xcframework')
        with self.assertRaisesRegex(ValueError, 'hnb'):
            self.integrate()
        self.assertNotIn('Embed Frameworks', self.text())

    def test_input_validation(self):
        with self.assertRaises(ValueError):
            xcodeproj.integrate(self.project.parent, 'KobilChatApp', self.frameworks)
        with self.assertRaises(ValueError):
            xcodeproj.integrate(self.project, 'No Such/Target', self.frameworks)
        with self.assertRaises(ValueError):
            xcodeproj.integrate(self.project, 'Missing', self.frameworks)
        with self.assertRaises(ValueError):
            self.integrate(marketing_version='one')

    def test_project_with_foreign_xcframework_references_is_refused(self):
        path = self.project / 'project.pbxproj'
        path.write_text(path.read_text() + '\n/* lastKnownFileType = wrapper.xcframework */\n')
        with self.assertRaises(ValueError):
            self.integrate()


class ToolTests(ProjectCase):
    def test_tool_is_registered_with_explicit_frameworks_folder(self):
        import asyncio
        tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
        schema = tools['sdk_ios_project_integrate'].inputSchema
        self.assertEqual(set(schema['required']), {'project_path', 'target_name', 'frameworks_dir'})

    def test_tool_runs_and_reports_the_next_step(self):
        result = server.sdk_ios_project_integrate(str(self.project), 'KobilChatApp', str(self.frameworks))
        self.assertTrue(result['changed'])
        self.assertIn('build', result['next_step'].lower())


if __name__ == '__main__':
    unittest.main()


class GuidanceTests(unittest.TestCase):
    """The skill and the knowledge must tell an agent how to embed, and that Xcode's own tools cannot."""

    ROOT = Path(__file__).resolve().parent.parent

    def test_skill_names_the_tool_the_crash_and_the_manual_fallback(self):
        skill = (self.ROOT / 'skills' / 'kobil-sdk' / 'SKILL.md').read_text()
        for needle in ('sdk_ios_project_integrate', 'Library not loaded', 'Embed & Sign', 'VersionInfo'):
            self.assertIn(needle, skill)

    def test_knowledge_sequence_and_ios_note_name_the_tool(self):
        import json
        setup = json.loads((self.ROOT / 'src' / 'kobil_sdk_integration' / 'knowledge' / 'setup.json').read_text())
        self.assertIn('sdk_ios_project_integrate', setup['sequence'][4])
        self.assertIn('sdk_ios_project_integrate', setup['platform_notes']['ios'])

    def test_native_handoff_has_the_step(self):
        text = (self.ROOT / 'skills' / 'kobil-sdk' / 'references' / 'native-integration.md').read_text()
        self.assertIn('sdk_ios_project_integrate', text)


class ParameterTableTests(unittest.TestCase):
    """The skill lists the required parameters of the tools an agent calls first; the list must match the schemas."""

    def test_listed_required_parameters_match_the_real_schemas(self):
        import asyncio
        text = (Path(__file__).resolve().parent.parent / 'skills' / 'kobil-sdk' / 'SKILL.md').read_text()
        section = text.split('## Exact parameters of the first calls', 1)[1].split('\n## ', 1)[0]
        listed = dict(re.findall(r'^- `(\w+)\(([^)]*)\)`', section, re.M))
        self.assertGreaterEqual(len(listed), 8)
        tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
        for name, params in listed.items():
            self.assertIn(name, tools)
            self.assertEqual(set(p.strip() for p in params.split(',')), set(tools[name].inputSchema.get('required', [])), name)
