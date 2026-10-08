"""sdk_artifact_info also describes a delivered .xcframework folder (hash, size, slices), read-only."""
import os
import plistlib
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('KOBIL_SDK_SENTRY_ENVIRONMENT', 'tests')
os.environ.setdefault('KOBIL_SDK_USAGE_LOG', '0')

from kobil_sdk_integration import server


def make(root, name='hnb', identifiers=('ios-arm64', 'ios-arm64-simulator')):
    folder = Path(root) / (name + '.xcframework')
    folder.mkdir()
    libs = [{'LibraryIdentifier': i, 'LibraryPath': name + '.framework', 'SupportedPlatform': 'ios',
             'SupportedArchitectures': ['arm64']} for i in identifiers]
    (folder / 'Info.plist').write_bytes(plistlib.dumps({'AvailableLibraries': libs, 'CFBundlePackageType': 'XFWK'}))
    for i in identifiers:
        (folder / i / (name + '.framework')).mkdir(parents=True)
        (folder / i / (name + '.framework') / name).write_bytes(b'binary-' + i.encode())
    return folder


class XCFrameworkInfoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_folder_is_described_with_slices_and_tree_hash(self):
        folder = make(self.tmp.name)
        info = server.sdk_artifact_info(str(folder))
        self.assertEqual(info['kind'], 'xcframework')
        self.assertEqual(info['slices'], ['ios-arm64', 'ios-arm64-simulator'])
        self.assertEqual(info['files'], 3)
        self.assertGreater(info['bytes'], 0)
        self.assertEqual(len(info['sha256']), 64)
        self.assertFalse(info['compatibility_verified'])

    def test_hash_changes_with_content_and_is_stable(self):
        folder = make(self.tmp.name)
        first = server.sdk_artifact_info(str(folder))['sha256']
        self.assertEqual(first, server.sdk_artifact_info(str(folder))['sha256'])
        (folder / 'ios-arm64' / 'hnb.framework' / 'hnb').write_bytes(b'changed')
        self.assertNotEqual(first, server.sdk_artifact_info(str(folder))['sha256'])

    def test_other_folders_are_still_refused(self):
        other = Path(self.tmp.name) / 'plain'
        other.mkdir()
        with self.assertRaises(ValueError):
            server.sdk_artifact_info(str(other))

    def test_folder_without_plist_is_refused(self):
        folder = Path(self.tmp.name) / 'x.xcframework'
        folder.mkdir()
        with self.assertRaisesRegex(ValueError, 'Info.plist'):
            server.sdk_artifact_info(str(folder))

    def test_symlinks_are_not_followed(self):
        folder = make(self.tmp.name)
        outside = Path(self.tmp.name) / 'secret.txt'
        outside.write_text('s' * 5000)
        (folder / 'link').symlink_to(outside)
        info = server.sdk_artifact_info(str(folder))
        self.assertLess(info['bytes'], 5000)

    def test_no_contents_or_absolute_inner_paths_are_returned(self):
        info = server.sdk_artifact_info(str(make(self.tmp.name)))
        self.assertNotIn('binary-', repr(info))


if __name__ == '__main__':
    unittest.main()
