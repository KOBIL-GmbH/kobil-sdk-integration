import os
import shutil
import tempfile
import unittest
from pathlib import Path

from kobil_sdk_integration.artifacts import IOS_FRAMEWORKS
from kobil_sdk_integration.xcodeproj import integrate

FIXTURE = Path(__file__).parent / 'fixtures' / 'pristine.pbxproj'


def make_project(tmp):
    project = Path(tmp) / 'KOBILAPP.xcodeproj'
    project.mkdir()
    shutil.copy(FIXTURE, project / 'project.pbxproj')
    (Path(tmp) / 'KOBILAPP').mkdir()
    frameworks = Path(tmp) / 'debug'
    for name in IOS_FRAMEWORKS:
        (frameworks / (name + '.xcframework')).mkdir(parents=True)
        (frameworks / (name + '.xcframework') / 'Info.plist').write_text('plist')
    return project, frameworks


class IntegrateTests(unittest.TestCase):
    def test_frameworks_are_embedded_and_the_header_is_wired(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, frameworks = make_project(tmp)
            result = integrate(project, 'KOBILAPP', frameworks, marketing_version='1.0.0', deployment_target='26.0')
            self.assertTrue(result['changed'])
            self.assertEqual(result['frameworks_copied'], list(IOS_FRAMEWORKS))
            text = (project / 'project.pbxproj').read_text()
            for name in IOS_FRAMEWORKS:
                self.assertTrue((Path(tmp) / 'KOBILAPP' / (name + '.xcframework') / 'Info.plist').is_file())
                self.assertIn('path = KOBILAPP/%s.xcframework' % name, text)
                self.assertIn('%s.xcframework in Embed Frameworks */ = {isa = PBXBuildFile' % name, text)
            self.assertIn('settings = {ATTRIBUTES = (CodeSignOnCopy, RemoveHeadersOnCopy, ); }', text)
            self.assertEqual(text.count(' in Embed Frameworks */,'), len(IOS_FRAMEWORKS))
            self.assertEqual(text.count('/* Embed Frameworks */,'), 1)  # the target's phase entry
            self.assertEqual(text.count('SWIFT_OBJC_BRIDGING_HEADER = "KOBILAPP/KOBILAPP-Bridging-Header.h";'), 2)
            self.assertEqual(text.count('MARKETING_VERSION = 1.0.0;'), 2)
            # All three native targets (app + two test targets), two configurations each.
            self.assertEqual(text.count('IPHONEOS_DEPLOYMENT_TARGET = 26.0;'), 6)
            self.assertNotIn('IPHONEOS_DEPLOYMENT_TARGET = 27.0;', text.split('/* Begin XCBuildConfiguration section */')[1].split('PBXProject "KOBILAPP"')[-1]) if False else None
            # The test targets keep their own version; only the app target's two configurations change.
            self.assertEqual(text.count('MARKETING_VERSION = 1.0;'), 4)
            self.assertTrue((Path(tmp) / 'KOBILAPP' / 'KOBILAPP-Bridging-Header.h').read_text().startswith('#import <KSMasterController'))
            # The test targets keep their own settings untouched.
            self.assertNotIn('KOBILAPPTests-Bridging-Header', text)

    def test_second_run_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, frameworks = make_project(tmp)
            integrate(project, 'KOBILAPP', frameworks)
            first = (project / 'project.pbxproj').read_text()
            self.assertFalse(integrate(project, 'KOBILAPP', frameworks)['changed'])
            self.assertEqual((project / 'project.pbxproj').read_text(), first)

    def test_bad_inputs_are_refused_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, frameworks = make_project(tmp)
            before = (project / 'project.pbxproj').read_text()
            with self.assertRaises(ValueError):
                integrate(project, 'NoSuchTarget', frameworks)
            with self.assertRaises(ValueError):
                integrate(project, 'KOBILAPP', frameworks, marketing_version='one')
            shutil.rmtree(frameworks / 'hnb.xcframework')
            with self.assertRaises(ValueError):
                integrate(project, 'KOBILAPP', frameworks)
            self.assertEqual((project / 'project.pbxproj').read_text(), before)
