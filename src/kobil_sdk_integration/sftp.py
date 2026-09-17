"""Configured, read-only SFTP delivery. Secrets never enter tool arguments/results."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile

import paramiko


class DeliveryError(ValueError):
    pass


def configuration():
    try:
        path = Path(os.environ.get('KOBIL_SDK_SFTP_CONNECTION', '~/.config/kobil-sdk/sftp.json')).expanduser()
        cfg = json.loads(path.read_text())
        for key in ('host', 'username', 'remote_root', 'known_hosts'):
            if not isinstance(cfg.get(key), str) or not cfg[key].strip():
                raise ValueError()
        if not cfg['remote_root'].startswith('/'):
            raise ValueError()
        if not isinstance(cfg.get('port', 22), int) or not 1 <= cfg.get('port', 22) <= 65535:
            raise ValueError()
        methods = [k for k in ('password_env', 'password_file', 'password_keyring', 'private_key') if cfg.get(k)]
        if len(methods) != 1 or 'password' in cfg:
            raise ValueError()
        cfg['max_bytes'] = int(cfg.get('max_bytes', 4 * 1024**3))
        if not 0 < cfg['max_bytes'] <= 32 * 1024**3:
            raise ValueError()
        return cfg
    except (OSError, ValueError, TypeError, KeyError):
        raise DeliveryError('Invalid SFTP configuration; see sdk-delivery documentation') from None


def _password(cfg):
    try:
        if cfg.get('password_env'):
            value = os.environ.get(cfg['password_env'])
        elif cfg.get('password_file'):
            path = Path(cfg['password_file']).expanduser()
            with path.open('rb') as f:
                mode = os.fstat(f.fileno())
                if not stat.S_ISREG(mode.st_mode) or (os.name != 'nt' and mode.st_mode & 0o077):
                    raise ValueError()
                data = f.read(16385)
                if len(data) > 16384:
                    raise ValueError()
            value = data.decode().rstrip('\r\n')
        elif cfg.get('password_keyring'):
            import keyring
            ref = cfg['password_keyring']
            value = keyring.get_password(ref['service'], ref['account'])
        else:
            return None
        if not isinstance(value, str) or not value:
            raise ValueError()
        return value
    except Exception:
        raise DeliveryError('SFTP credential unavailable; unlock/configure the selected credential provider') from None


@contextmanager
def connection(cfg):
    client = paramiko.SSHClient()
    try:
        client.load_host_keys(str(Path(cfg['known_hosts']).expanduser()))
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        client.connect(hostname=cfg['host'], port=cfg.get('port', 22), username=cfg['username'],
                       password=_password(cfg),
                       key_filename=str(Path(cfg['private_key']).expanduser()) if cfg.get('private_key') else None,
                       allow_agent=False, look_for_keys=False, timeout=20, auth_timeout=20,
                       banner_timeout=20, channel_timeout=30)
        with client.open_sftp() as sftp:
            sftp.get_channel().settimeout(30)
            yield sftp
    except DeliveryError:
        raise
    except paramiko.BadHostKeyException:
        raise DeliveryError('SFTP host key mismatch; verify the host with the delivery provider') from None
    except paramiko.AuthenticationException:
        raise DeliveryError('SFTP authentication failed; check the selected credential provider') from None
    except paramiko.SSHException:
        raise DeliveryError('SFTP SSH connection failed; verify trusted known_hosts and server availability') from None
    except (OSError, EOFError):
        raise DeliveryError('SFTP transfer failed; check access, connectivity and local storage') from None
    finally:
        client.close()


def remote_path(sftp, cfg, relative):
    if not isinstance(relative, str) or '\\' in relative or any(ord(c) < 32 for c in relative):
        raise DeliveryError('Expected a relative SFTP path')
    p = PurePosixPath(relative)
    if p.is_absolute() or '..' in p.parts:
        raise DeliveryError('SFTP path must stay within the configured release root')
    root = sftp.normalize(cfg['remote_root']).rstrip('/') or '/'
    result = sftp.normalize(root.rstrip('/') + '/' + str(p))
    if result != root and not result.startswith(root.rstrip('/') + '/'):
        raise DeliveryError('Remote symlink escapes the configured release root')
    return result


def list_delivery(relative_path='.'):
    cfg = configuration()
    with connection(cfg) as sftp:
        path = remote_path(sftp, cfg, relative_path)
        entries = []
        for entry in sftp.listdir_iter(path, read_aheads=1):
            if len(entries) >= 1000:
                raise DeliveryError('Directory exceeds 1000 entries; select a narrower release directory')
            entries.append({'name': entry.filename, 'bytes': entry.st_size,
                            'kind': 'directory' if stat.S_ISDIR(entry.st_mode) else
                                    'file' if stat.S_ISREG(entry.st_mode) else 'other'})
        return {'path': relative_path, 'entries': sorted(entries, key=lambda x: x['name']),
                'next_step': 'Select an explicit release and download its archives, SHA-512 sidecars and release notes with sdk_sftp_download.'}


def _fetch(sftp, cfg, relative, folder):
    remote = remote_path(sftp, cfg, relative)
    before = sftp.stat(remote)
    if not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= cfg['max_bytes']:
        raise DeliveryError('Expected a regular file within the configured download size limit')
    name = PurePosixPath(remote).name
    if not name or name in ('.', '..', '.partial') or '\\' in name or any(ord(c) < 32 for c in name) or (folder / name).exists():
        raise DeliveryError('Invalid or duplicate delivery filename')
    temporary = folder / '.partial'
    digest = hashlib.sha512()
    count = 0
    with sftp.open(remote, 'rb') as source, temporary.open('xb') as target:
        os.chmod(temporary, 0o600)
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            count += len(chunk)
            if count > cfg['max_bytes'] or count > before.st_size:
                raise DeliveryError('Remote file grew or exceeded the download size limit')
            target.write(chunk)
            digest.update(chunk)
    after = sftp.stat(remote)
    if count != before.st_size or (before.st_size, before.st_mtime) != (after.st_size, after.st_mtime):
        raise DeliveryError('Remote file changed during download; retry the selected release')
    destination = folder / name
    temporary.rename(destination)
    return {'path': str(destination), 'bytes': count, 'sha512': digest.hexdigest()}


def download(relative_path, expected_sha512=None, companion_paths=None):
    if expected_sha512 is not None and not re.fullmatch(r'[a-fA-F0-9]{128}', expected_sha512):
        raise DeliveryError('expected_sha512 must contain 128 hexadecimal characters')
    companions = companion_paths or []
    if not isinstance(companions, list) or len(companions) > 10 or not all(isinstance(x, str) for x in companions):
        raise DeliveryError('Provide at most 10 companion paths for checksums and release notes')
    cfg = configuration()
    root = Path(os.environ.get('KOBIL_SDK_DELIVERY', '~/.kobil-sdk/delivery')).expanduser()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='sftp-', dir=root))
    os.chmod(folder, 0o700)
    try:
        with connection(cfg) as sftp:
            primary = _fetch(sftp, cfg, relative_path, folder)
            records = [_fetch(sftp, cfg, item, folder) for item in companions]
        sidecar = Path(primary['path'] + '.sha512')
        supplier = expected_sha512
        if sidecar.exists():
            if sidecar.stat().st_size > 16384:
                raise DeliveryError('Checksum sidecar is too large')
            matches = re.findall(r'(?<![0-9a-fA-F])[0-9a-fA-F]{128}(?![0-9a-fA-F])', sidecar.read_text())
            if len(matches) != 1:
                raise DeliveryError('Expected exactly one SHA-512 in the supplier sidecar')
            if supplier and supplier.lower() != matches[0].lower():
                raise DeliveryError('Supplier sidecar conflicts with expected_sha512')
            supplier = matches[0]
        if supplier and primary['sha512'].lower() != supplier.lower():
            raise DeliveryError('Downloaded file SHA-512 mismatch; delivery discarded')
        return {**primary, 'delivery_dir': str(folder), 'companions': records,
                'checksum_verified': supplier is not None, 'host_key_verified': True,
                'next_step': 'Call sdk_artifacts_import with delivery_dir (or sdk_artifacts_install with path and supplier checksum). A computed hash alone is not supplier verification. Ask which changelog to show (iOS/Android/Flutter), then print it via sdk_artifacts_notes after import.'}
    except BaseException:
        # Only this call owns this random private directory; preserve other deliveries.
        import shutil
        shutil.rmtree(folder)
        raise
