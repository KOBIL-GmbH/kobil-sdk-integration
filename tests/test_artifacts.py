import hashlib
import os
import tempfile
import unittest
import zipfile

from kobil_sdk_integration.artifacts import (ANDROID_LIBS, IOS_FRAMEWORKS, delivery_root, ensure_ios_release,
                                             frameworks_dir, import_delivery,
                                             install_android_zip, install_ios_zip, installed, installed_all,
                                             release_notes, version_from_name)


def make_zip(folder, name='MCSDK_iOS_xcframeworks_15.16.803.3089231.zip', sets=('debug', 'release'),
             frameworks=IOS_FRAMEWORKS, sidecar=True, extra=()):
    path = os.path.join(folder, name)
    with zipfile.ZipFile(path, 'w') as archive:
        for variant in sets:
            for fw in frameworks:
                archive.writestr('MCSDK_iOS_xcframeworks/%s/%s.xcframework/Info.plist' % (variant, fw), 'plist')
        for member in extra:
            archive.writestr(member, 'x')
    if sidecar:
        with open(path, 'rb') as stream:
            digest = hashlib.sha512(stream.read()).hexdigest()
        open(path + '.sha512', 'w').write(digest + '  ' + name + '\n')
    return path


class ArtifactTests(unittest.TestCase):
    def test_version_is_read_from_the_delivered_name(self):
        self.assertEqual(version_from_name('MCSDK_iOS_xcframeworks_15.16.803.3089231.zip'), '15.16.803.3089231')
        self.assertIsNone(version_from_name('sdk.zip'))

    def test_a_verified_zip_is_extracted_into_the_store_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = os.path.join(tmp, 'store')
            record = install_ios_zip(make_zip(tmp), store)
            self.assertEqual(record['version'], '15.16.803.3089231')
            self.assertFalse(record['already_installed'])
            for variant in ('debug', 'release'):
                for fw in IOS_FRAMEWORKS:
                    self.assertTrue(os.path.isdir(os.path.join(record['variants'][variant], fw + '.xcframework')))
            again = install_ios_zip(os.path.join(tmp, 'MCSDK_iOS_xcframeworks_15.16.803.3089231.zip'), store)
            self.assertTrue(again['already_installed'])
            self.assertEqual([r['version'] for r in installed(store)], ['15.16.803.3089231'])
            version, folder = frameworks_dir(store)
            self.assertEqual(version, '15.16.803.3089231')
            self.assertTrue(folder.name == 'debug')

    def test_checksum_mismatch_and_missing_checksum_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_zip(tmp)
            with self.assertRaises(ValueError):
                install_ios_zip(path, os.path.join(tmp, 's'), expected_sha512='0' * 128)
            bare = make_zip(tmp, name='MCSDK_iOS_xcframeworks_15.16.900.1.zip', sidecar=False)
            with self.assertRaises(ValueError):
                install_ios_zip(bare, os.path.join(tmp, 's'))
            self.assertEqual(installed(os.path.join(tmp, 's')), [])

    def test_incomplete_sets_and_unsafe_members_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            partial = make_zip(tmp, name='MCSDK_iOS_xcframeworks_15.16.1.1.zip', frameworks=IOS_FRAMEWORKS[:3])
            with self.assertRaises(ValueError):
                install_ios_zip(partial, os.path.join(tmp, 's'))
            slip = make_zip(tmp, name='MCSDK_iOS_xcframeworks_15.16.2.1.zip', extra=('../evil.txt',))
            with self.assertRaises(ValueError):
                install_ios_zip(slip, os.path.join(tmp, 's'))

    def test_store_selection_needs_a_version_when_several_are_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = os.path.join(tmp, 'store')
            install_ios_zip(make_zip(tmp), store)
            install_ios_zip(make_zip(tmp, name='MCSDK_iOS_xcframeworks_15.17.0.1.zip'), store)
            with self.assertRaises(ValueError):
                frameworks_dir(store)
            self.assertEqual(frameworks_dir(store, '15.17.0.1', 'release')[0], '15.17.0.1')
            with self.assertRaises(ValueError):
                frameworks_dir(store, '15.17.0.1', 'nightly')


def make_android_zip(folder, name='MCSDK_Android_libs_15.16.3088426.zip', libs=ANDROID_LIBS, sidecar=True):
    path = os.path.join(folder, name)
    with zipfile.ZipFile(path, 'w') as archive:
        for lib in libs:
            for variant in ('debug', 'release'):
                archive.writestr('MCSDK_Android_libs_15.16.3088426/%s-%s.aar' % (lib, variant), 'aar')
        archive.writestr('MCSDK_Android_libs_15.16.3088426/mcw_build.gradle', 'gradle')
    if sidecar:
        with open(path, 'rb') as stream:
            open(path + '.sha512', 'w').write(hashlib.sha512(stream.read()).hexdigest() + '\n')
    return path


class DeliveryTests(unittest.TestCase):
    def test_android_zip_is_installed_with_its_aars(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = install_android_zip(make_android_zip(tmp), os.path.join(tmp, 's'))
            self.assertEqual(record['version'], '15.16.3088426')
            self.assertEqual(len(record['libs']), 2 * len(ANDROID_LIBS))
            self.assertTrue(os.path.isfile(os.path.join(record['libs_dir'], 'wrapper-release.aar')))
            self.assertTrue(os.path.isfile(os.path.join(record['path'], 'mcw_build.gradle')))
            partial = make_android_zip(tmp, name='MCSDK_Android_libs_15.17.1.zip', libs=ANDROID_LIBS[:2])
            with self.assertRaises(ValueError):
                install_android_zip(partial, os.path.join(tmp, 's'))

    def test_a_delivery_folder_is_imported_with_its_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            delivery = os.path.join(tmp, 'delivery')
            ios, android = os.path.join(delivery, '15.16', 'ios'), os.path.join(delivery, '15.16', 'android')
            os.makedirs(ios); os.makedirs(android)
            make_zip(ios); make_android_zip(android)
            open(os.path.join(ios, 'CHANGELOG.md'), 'w').write('# Changelog\n## 15.16\n')
            open(os.path.join(ios, 'README.md'), 'w').write('notes')
            open(os.path.join(delivery, 'postman-collections.zip'), 'w').write('not an sdk')
            store = os.path.join(tmp, 'store')
            os.environ['KOBIL_SDK_DELIVERY'] = delivery  # keep the bundled delivery out of this test
            outcome = import_delivery(delivery, store)
            self.assertEqual(sorted((i['platform'], i['already_installed']) for i in outcome['installed']),
                             [('android', False), ('ios', False)])
            self.assertEqual(outcome['skipped'], [])
            self.assertEqual(sorted(r['platform'] for r in installed_all(store)), ['android', 'ios'])
            notes = release_notes('ios', store=store)
            self.assertTrue(notes['text'].startswith('# Changelog'))
            with self.assertRaises(ValueError):
                release_notes('ios', document='risks.json', store=store)
            again = import_delivery(delivery, store)
            self.assertTrue(all(i['already_installed'] for i in again['installed']))
            with self.assertRaises(ValueError):
                import_delivery(os.path.join(tmp, 'nowhere'), store)
            del os.environ['KOBIL_SDK_DELIVERY']

    def test_an_unverifiable_zip_is_skipped_not_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            delivery = os.path.join(tmp, 'd'); os.makedirs(delivery)
            make_zip(delivery, sidecar=False)
            outcome = import_delivery(delivery, os.path.join(tmp, 's'))
            self.assertEqual(outcome['installed'], [])
            self.assertEqual(len(outcome['skipped']), 1)


class BundledDeliveryTests(unittest.TestCase):
    def test_delivery_folder_resolution_order(self):
        import os as _os
        from kobil_sdk_integration import artifacts
        self.assertEqual(str(delivery_root('/explicit')), '/explicit')
        _os.environ['KOBIL_SDK_DELIVERY'] = '/from-env'
        try:
            self.assertEqual(str(delivery_root()), '/from-env')
        finally:
            del _os.environ['KOBIL_SDK_DELIVERY']
        self.assertIn(delivery_root().name, ('sdk-delivery', 'delivery'))

    def test_integration_imports_the_delivery_when_the_store_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            delivery = os.path.join(tmp, 'sdk-delivery', '15.16', 'ios'); os.makedirs(delivery)
            make_zip(delivery)
            store = os.path.join(tmp, 'store')
            release, folder, imported = ensure_ios_release(store, os.path.join(tmp, 'sdk-delivery'))
            self.assertEqual(release, '15.16.803.3089231')
            self.assertTrue(folder.name == 'debug')
            self.assertEqual(imported['installed'][0]['already_installed'], False)
            release2, folder2, imported2 = ensure_ios_release(store, os.path.join(tmp, 'sdk-delivery'))
            self.assertIsNone(imported2)
            self.assertEqual(folder2, folder)
