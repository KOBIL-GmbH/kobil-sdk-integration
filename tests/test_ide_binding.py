"""The IDE entry point follows the project the host opened, so a new app needs no new plug-in setup."""
import os
import tempfile
import unittest
import unittest.mock
from pathlib import Path

os.environ.setdefault('KOBIL_SDK_SENTRY_ENVIRONMENT', 'tests')
os.environ.setdefault('KOBIL_SDK_USAGE_LOG', '0')

from kobil_sdk_integration import ide_stdio


class ResolveProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def app(self, name, marker='.xcodeproj'):
        folder = self.root / name
        (folder / ('App' + marker)).mkdir(parents=True)
        return folder

    def test_new_app_folder_wins_over_a_stale_binding(self):
        old, new = self.app('old'), self.app('new')
        project, source = ide_stdio.resolve_project({'KOBIL_SDK_PROJECT': str(old)}, new)
        self.assertEqual((project, source), (new, 'cwd'))

    def test_workspace_folder_counts_too(self):
        new = self.app('ws', '.xcworkspace')
        self.assertEqual(ide_stdio.resolve_project({}, new), (new, 'cwd'))

    def test_same_folder_reports_env(self):
        app = self.app('same')
        self.assertEqual(ide_stdio.resolve_project({'KOBIL_SDK_PROJECT': str(app)}, app), (app, 'env'))

    def test_folder_without_a_project_keeps_the_binding(self):
        old = self.app('old')
        plain = self.root / 'plain'
        plain.mkdir()
        self.assertEqual(ide_stdio.resolve_project({'KOBIL_SDK_PROJECT': str(old)}, plain), (old, 'env'))

    def test_nothing_to_bind_is_refused(self):
        plain = self.root / 'plain'
        plain.mkdir()
        with self.assertRaisesRegex(ValueError, 'PROJECT_NOT_SELECTED'):
            ide_stdio.resolve_project({}, plain)

    def test_binding_must_be_an_existing_absolute_folder(self):
        plain = self.root / 'plain'
        plain.mkdir()
        for bad in ('relative/path', str(self.root / 'missing')):
            with self.assertRaisesRegex(ValueError, 'PROJECT_NOT_SELECTED'):
                ide_stdio.resolve_project({'KOBIL_SDK_PROJECT': bad}, plain)

    def test_home_and_root_are_never_taken_from_the_working_directory(self):
        home = Path.home()
        with self.assertRaisesRegex(ValueError, 'PROJECT_NOT_SELECTED'):
            ide_stdio.resolve_project({}, home)
        with self.assertRaisesRegex(ValueError, 'PROJECT_NOT_SELECTED'):
            ide_stdio.resolve_project({}, Path('/'))

    def test_symlinked_working_directory_is_resolved(self):
        real = self.app('real')
        link = self.root / 'link'
        link.symlink_to(real)
        project, source = ide_stdio.resolve_project({}, link)
        self.assertEqual((project, source), (real, 'cwd'))


if __name__ == '__main__':
    unittest.main()


class RuntimeInfoTests(unittest.TestCase):
    def test_runtime_info_names_how_the_project_was_chosen(self):
        from kobil_sdk_integration import server
        with unittest.mock.patch.dict(os.environ, {'KOBIL_SDK_PROJECT_SOURCE': 'cwd'}):
            self.assertEqual(server.sdk_runtime_info()['project_binding'], 'cwd')
        with unittest.mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('KOBIL_SDK_PROJECT_SOURCE', None)
            self.assertEqual(server.sdk_runtime_info()['project_binding'], 'unknown')
