"""A local store for delivered SDK releases, so nobody unzips by hand.

KOBIL delivers the iOS SDK as a zip with two sets of the same four XCFrameworks, debug
and release, plus a .sha512 sidecar. This verifies the checksum, extracts the zip into a
private store keyed by platform and version, checks that both sets are complete, and
records a manifest. Nothing is downloaded here: the zip is whatever channel KOBIL used,
SFTP or otherwise. The store is what the project integration reads from.
"""
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import zipfile
from pathlib import Path

IOS_FRAMEWORKS = ('KSMasterController', 'hnb', 'kssidp', 'KSTrustedWebView')
ANDROID_LIBS = ('AndroidInterface', 'Configurator', 'androidloader', 'hardening', 'hardeningBridge',
                'kssidp-wrapper', 'proxy_static', 'uihardening', 'wrapper')
VARIANTS = ('debug', 'release')
DELIVERY_NOTES = ('CHANGELOG.md', 'README.md', 'risks.json', 'TestedDevices.xls')
PLATFORMS = ('ios', 'android')
VERSION = re.compile(r'\d+\.\d+\.\d+(?:\.\d+)?')
HEX_SHA512 = re.compile(r'[0-9a-fA-F]{128}')


def store_root(store=None):
    return Path(store or os.environ.get('KOBIL_SDK_ARTIFACTS') or '~/.kobil-sdk/artifacts').expanduser()


BUNDLED_DELIVERY = Path(__file__).resolve().parents[2] / 'sdk-delivery'


def delivery_root(delivery=None):
    """Where the delivered zips are, first match wins.

    1. an explicit folder, 2. KOBIL_SDK_DELIVERY, 3. the delivery bundled with this MCP
    (``sdk-delivery/`` next to the package: what a customer receives together with the
    plug-in), 4. ~/.kobil-sdk/delivery for a manual drop.
    """
    if delivery:
        return Path(delivery).expanduser()
    env = os.environ.get('KOBIL_SDK_DELIVERY')
    if env:
        return Path(env).expanduser()
    if BUNDLED_DELIVERY.is_dir():
        return BUNDLED_DELIVERY
    return Path('~/.kobil-sdk/delivery').expanduser()


def _keep_notes(source, dest):
    """Copy the release notes that travel next to the zip, so the changelog is in the store."""
    kept = []
    for name in DELIVERY_NOTES:
        note = source.parent / name
        if note.is_file():
            shutil.copy2(note, dest / name)
            kept.append(name)
    return kept


def version_from_name(name):
    match = VERSION.search(name)
    return match.group(0) if match else None


def sha512_of(path):
    digest = hashlib.sha512()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def expected_checksum(source, expected_sha512=None):
    """The checksum to verify against: the argument, else the .sha512 sidecar KOBIL ships."""
    if expected_sha512 is not None:
        if not isinstance(expected_sha512, str) or not HEX_SHA512.fullmatch(expected_sha512.strip()):
            raise ValueError('expected_sha512 must be 128 hexadecimal characters')
        return expected_sha512.strip().lower()
    sidecar = Path(str(source) + '.sha512')
    if sidecar.is_file():
        match = HEX_SHA512.search(sidecar.read_text(errors='replace'))
        if match:
            return match.group(0).lower()
    raise ValueError('No checksum to verify against: keep the delivered .sha512 file next to the zip '
                     'or pass expected_sha512. An unverified SDK is not installed.')


def _safe_members(archive):
    for member in archive.infolist():
        name = member.filename
        if name.startswith('/') or '..' in Path(name).parts or '\\' in name:
            raise ValueError('The archive contains an unsafe path: %s' % name)
        yield member


def _variant_dirs(extracted):
    """Locate the debug and release sets, wherever the zip put them."""
    found = {}
    for variant in VARIANTS:
        for candidate in sorted(extracted.rglob(variant)):
            if candidate.is_dir() and all((candidate / (n + '.xcframework')).is_dir() for n in IOS_FRAMEWORKS):
                found[variant] = candidate
                break
    missing = [v for v in VARIANTS if v not in found]
    if missing:
        raise ValueError('The archive lacks a complete %s set of %s' % (' and '.join(missing), ', '.join(IOS_FRAMEWORKS)))
    return found


def install_ios_zip(source, store=None, expected_sha512=None, version=None):
    """Verify and extract a delivered iOS SDK zip into the store. Idempotent per version."""
    source = Path(source).expanduser()
    if not source.is_file() or source.suffix.lower() != '.zip':
        raise ValueError('Provide the path of the delivered SDK zip file')
    if version is not None and not VERSION.fullmatch(str(version)):
        raise ValueError('version must look like 15.16.803.3089231')
    version = version or version_from_name(source.name)
    if not version:
        raise ValueError('The zip name carries no version; pass version explicitly')
    checksum = expected_checksum(source, expected_sha512)
    actual = sha512_of(source)
    if actual != checksum:
        raise ValueError('SHA-512 mismatch for %s; the file is not the delivered release' % source.name)
    root = store_root(store)
    dest = root / 'ios' / version
    manifest = dest / 'manifest.json'
    if manifest.is_file():
        record = json.loads(manifest.read_text())
        if record.get('sha512') == actual and all((dest / v).is_dir() for v in VARIANTS):
            record['already_installed'] = True
            if not record.get('notes'):
                record['notes'] = _keep_notes(source, dest)
                manifest.write_text(json.dumps({k: v for k, v in record.items() if k != 'already_installed'}, indent=2) + '\n')
            return record
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(dest.parent)) as tmp:
        extracted = Path(tmp) / 'x'
        with zipfile.ZipFile(source) as archive:
            for member in _safe_members(archive):
                archive.extract(member, extracted)
        sets = _variant_dirs(extracted)
        dest.mkdir()
        for variant, folder in sets.items():
            shutil.move(str(folder), str(dest / variant))
    record = {'platform': 'ios', 'version': version, 'sha512': actual, 'source': str(source),
              'installed_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'path': str(dest),
              'frameworks': list(IOS_FRAMEWORKS), 'variants': {v: str(dest / v) for v in VARIANTS},
              'notes': _keep_notes(source, dest), 'already_installed': False}
    manifest.write_text(json.dumps(record, indent=2) + '\n')
    return record


def installed(store=None):
    """Every release in the store, newest version string last."""
    root = store_root(store) / 'ios'
    records = []
    if root.is_dir():
        for manifest in sorted(root.glob('*/manifest.json')):
            try:
                records.append(json.loads(manifest.read_text()))
            except ValueError:
                continue
    return records


def frameworks_dir(store=None, version=None, variant='debug'):
    """The folder holding one complete framework set, for the project integration."""
    if variant not in VARIANTS:
        raise ValueError('variant is debug or release')
    records = installed(store)
    if version is None:
        if len(records) != 1:
            raise ValueError('%d SDK releases installed; name the version' % len(records)
                             if records else 'No SDK release installed; run the install first')
        record = records[0]
    else:
        record = next((r for r in records if r.get('version') == version), None)
        if not record:
            raise ValueError('SDK release %s is not installed' % version)
    folder = Path(record['variants'][variant])
    if not all((folder / (n + '.xcframework')).is_dir() for n in IOS_FRAMEWORKS):
        raise ValueError('The installed %s set is incomplete; reinstall the release' % variant)
    return record['version'], folder


def install_android_zip(source, store=None, expected_sha512=None, version=None):
    """Verify and extract a delivered Android SDK zip (flat debug/release AARs) into the store."""
    source = Path(source).expanduser()
    if not source.is_file() or source.suffix.lower() != '.zip':
        raise ValueError('Provide the path of the delivered SDK zip file')
    if version is not None and not VERSION.fullmatch(str(version)):
        raise ValueError('version must look like 15.16.3088426')
    version = version or version_from_name(source.name)
    if not version:
        raise ValueError('The zip name carries no version; pass version explicitly')
    checksum = expected_checksum(source, expected_sha512)
    actual = sha512_of(source)
    if actual != checksum:
        raise ValueError('SHA-512 mismatch for %s; the file is not the delivered release' % source.name)
    root = store_root(store)
    dest = root / 'android' / version
    manifest = dest / 'manifest.json'
    if manifest.is_file():
        record = json.loads(manifest.read_text())
        if record.get('sha512') == actual and (dest / 'libs').is_dir():
            record['already_installed'] = True
            if not record.get('notes'):
                record['notes'] = _keep_notes(source, dest)
                manifest.write_text(json.dumps({k: v for k, v in record.items() if k != 'already_installed'}, indent=2) + '\n')
            return record
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(dest.parent)) as tmp:
        extracted = Path(tmp) / 'x'
        with zipfile.ZipFile(source) as archive:
            for member in _safe_members(archive):
                archive.extract(member, extracted)
        aars = {p.name: p for p in extracted.rglob('*.aar')}
        missing = ['%s-%s.aar' % (lib, variant) for lib in ANDROID_LIBS for variant in VARIANTS
                   if '%s-%s.aar' % (lib, variant) not in aars]
        if missing:
            raise ValueError('The archive lacks: %s' % ', '.join(missing))
        libs = dest / 'libs'
        libs.mkdir(parents=True)
        for name, path in sorted(aars.items()):
            shutil.move(str(path), str(libs / name))
        for extra in extracted.rglob('*.gradle'):
            shutil.move(str(extra), str(dest / extra.name))
    record = {'platform': 'android', 'version': version, 'sha512': actual, 'source': str(source),
              'installed_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'path': str(dest),
              'libs': sorted(aars), 'libs_dir': str(libs), 'notes': _keep_notes(source, dest),
              'already_installed': False}
    manifest.write_text(json.dumps(record, indent=2) + '\n')
    return record


def installed_all(store=None):
    """Every release in the store, both platforms."""
    root = store_root(store)
    records = []
    for platform in PLATFORMS:
        folder = root / platform
        if folder.is_dir():
            for manifest in sorted(folder.glob('*/manifest.json')):
                try:
                    records.append(json.loads(manifest.read_text()))
                except ValueError:
                    continue
    return records


def import_delivery(delivery=None, store=None):
    """Install every delivered zip found under the delivery folder. Idempotent per release."""
    root = delivery_root(delivery)
    if not root.is_dir():
        raise ValueError('Delivery folder %s does not exist; point KOBIL_SDK_DELIVERY at the folder '
                         'holding the zips KOBIL delivered, or pass delivery_dir' % root)
    installers = {'ios': (re.compile(r'MCSDK_iOS_.*\.zip$', re.I), install_ios_zip),
                  'android': (re.compile(r'MCSDK_Android_.*\.zip$', re.I), install_android_zip)}
    outcome = {'delivery': str(root), 'installed': [], 'skipped': []}
    for zip_path in sorted(root.rglob('*.zip')):
        for platform, (pattern, install) in installers.items():
            if pattern.match(zip_path.name):
                try:
                    record = install(zip_path, store)
                    outcome['installed'].append({'platform': platform, 'version': record['version'],
                                                 'already_installed': record['already_installed'],
                                                 'path': record['path']})
                except ValueError as exc:
                    outcome['skipped'].append({'file': str(zip_path), 'reason': str(exc)})
                break
    if not outcome['installed'] and not outcome['skipped']:
        raise ValueError('No MCSDK_iOS_*.zip or MCSDK_Android_*.zip under %s' % root)
    return outcome


def _refresh_notes_from_delivery(record, store=None):
    """Copy the release documents into a store entry that was installed before they were kept.

    The zip is looked up again under the delivery folder by name; whatever documents sit
    next to it are copied, and the manifest updated. Nothing else is touched.
    """
    source = Path(record.get('source') or '')
    candidates = [source] if source.name and source.is_file() else []
    root = delivery_root()
    if root.is_dir() and source.name:
        candidates.extend(p for p in root.rglob(source.name) if p not in candidates)
    for zip_path in candidates:
        dest = Path(record['path'])
        kept = _keep_notes(zip_path, dest)
        if kept:
            record['notes'] = kept
            manifest = dest / 'manifest.json'
            manifest.write_text(json.dumps({k: v for k, v in record.items() if k != 'already_installed'}, indent=2) + '\n')
            return


def release_notes(platform, version=None, document='CHANGELOG.md', store=None, limit=200000):
    """A delivery document kept in the store, so the changelog can be shown without the zip."""
    if platform not in PLATFORMS:
        raise ValueError('platform is ios or android')
    if document not in DELIVERY_NOTES:
        raise ValueError('document is one of %s' % ', '.join(DELIVERY_NOTES))
    records = [r for r in installed_all(store) if r.get('platform') == platform]
    if version is None:
        if len(records) != 1:
            raise ValueError('%d %s releases installed; name the version' % (len(records), platform)
                             if records else 'No %s release installed' % platform)
        record = records[0]
    else:
        record = next((r for r in records if r.get('version') == version), None)
        if not record:
            raise ValueError('%s release %s is not installed' % (platform, version))
    path = Path(record['path']) / document
    if not path.is_file():
        _refresh_notes_from_delivery(record, store)
    if not path.is_file():
        raise ValueError('%s was not delivered next to the %s %s zip' % (document, platform, record['version']))
    if document.endswith('.xls'):
        return {'platform': platform, 'version': record['version'], 'document': document, 'path': str(path),
                'text': None, 'note': 'Binary spreadsheet; open the file directly.'}
    text = path.read_text(errors='replace')
    return {'platform': platform, 'version': record['version'], 'document': document, 'path': str(path),
            'text': text[:limit], 'truncated': len(text) > limit}


def ensure_ios_release(store=None, delivery=None, version=None, variant='debug'):
    """The framework set to integrate, importing the delivery first when the store is empty.

    This is what lets one tool call go from "nothing installed" to "frameworks in the
    project": the delivery bundled with the MCP (or the configured folder) is imported on
    first use, verified against its checksums, and never downloaded.
    """
    imported = None
    if not any(r.get('platform') == 'ios' for r in installed_all(store)):
        imported = import_delivery(delivery, store)
    release, folder = frameworks_dir(store, version, variant)
    return release, folder, imported
