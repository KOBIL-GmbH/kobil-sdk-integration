import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("xcode_install", Path(__file__).parents[1] / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class PackagingTests(unittest.TestCase):
    def test_paths_with_spaces_and_combined_manifest(self):
        root = Path('/Applications/Test User/KOBIL/release')
        files = installer.plugin_files(root)
        manifest = json.loads(files['plugin.json'])
        server = manifest['mcpServers']['KOBILSDK']
        self.assertEqual(server['type'], 'stdio')
        self.assertEqual(server['command'], str(root / '.venv/bin/kobil-sdk-mcp'))
        self.assertNotIn('env', server)
        self.assertIn(str(root / 'skills/kobil-sdk/SKILL.md'), files['skills/kobil-sdk/SKILL.md'])
        self.assertEqual(json.loads(files['.mcp.json'])['mcpServers']['KOBILSDK'], server)

    def test_pinned_dirty_checkout_rejected_before_install(self):
        with patch.object(installer, 'run', side_effect=[installer.COMMIT, ' M pyproject.toml']):
            with self.assertRaisesRegex(RuntimeError, 'local modifications'):
                installer.verify_release(Path('/test/release'), 'git')
        with patch.object(installer, 'run', return_value='wrong commit'):
            with self.assertRaisesRegex(RuntimeError, 'pin'):
                installer.verify_release(Path('/test/release'), 'git')

    def test_idempotence_and_preserving_customizations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'plugin'
            files = installer.plugin_files(Path(tmp) / 'release')
            installer.write_plugin(root, files)
            installer.write_plugin(root, files)
            (root / 'plugin.json').write_text('custom')
            with self.assertRaisesRegex(RuntimeError, 'preserve'):
                installer.write_plugin(root, files)
            self.assertEqual((root / 'plugin.json').read_text(), 'custom')

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'plugin'
            root.symlink_to(Path(tmp), target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, 'symlink'):
                installer.write_plugin(root, {'plugin.json': '{}'})

    def test_keychain_secret_goes_only_to_child_environment(self):
        files = installer.plugin_files(Path('/test/release'), Path('/private/config.json'),
                                       ('service', 'account', 'KOBIL_CLIENT_SECRET'), Path('/test/plugin'))
        namespace = {'__name__': 'test_launcher'}
        exec(files['launch.py'], namespace)
        result = types.SimpleNamespace(stdout='test-only-secret\n')
        with patch.object(namespace['subprocess'], 'run', return_value=result) as read, \
             patch.object(namespace['os'], 'execve') as launch:
            namespace['main']()
        self.assertNotIn('test-only-secret', str(read.call_args))
        self.assertEqual(launch.call_args.args[2]['KOBIL_CLIENT_SECRET'], 'test-only-secret')
        self.assertNotIn('test-only-secret', str(launch.call_args.args[:2]))
        self.assertNotIn('test-only-secret', ''.join(files.values()))

    def test_keychain_failure_redacted(self):
        namespace = {'__name__': 'test_launcher'}
        exec(installer.launcher_text(Path('/test'), ('service', 'account', 'KOBIL_SECRET')), namespace)
        with patch.object(namespace['subprocess'], 'run', side_effect=OSError('private diagnostic')), \
             patch('builtins.print') as output, self.assertRaises(SystemExit):
            namespace['main']()
        self.assertNotIn('private diagnostic', str(output.call_args))
        with self.assertRaises(ValueError):
            installer.launcher_text(Path('/test'), ('service', 'account', 'PATH'))


if __name__ == '__main__':
    unittest.main()
