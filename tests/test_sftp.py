import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, MagicMock

from kobil_sdk_integration import sftp


class Remote:
    def __init__(self, files):
        self.files = files
    def normalize(self, path):
        return '/outside' if 'escape' in path else path.replace('/./', '/')
    def stat(self, path):
        return SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_size=len(self.files[path]), st_mtime=1)
    def open(self, path, mode):
        return io.BytesIO(self.files[path])


class SftpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cfg = {'host': 'sdk.example', 'username': 'customer', 'remote_root': '/releases',
                    'known_hosts': str(self.root / 'known_hosts'), 'password_env': 'TEST_SFTP_PASSWORD',
                    'max_bytes': 1024}
        p = self.root / 'connection.json'
        p.write_text(json.dumps(self.cfg))
        self.env = patch.dict(os.environ, {'KOBIL_SDK_SFTP_CONNECTION': str(p),
            'KOBIL_SDK_DELIVERY': str(self.root / 'downloads'), 'TEST_SFTP_PASSWORD': 'fixture-secret'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def remote(self, files):
        context = MagicMock()
        context.__enter__.return_value = Remote(files)
        return patch.object(sftp, 'connection', return_value=context)

    def test_download_checksum_notes_and_private_files(self):
        data = b'sdk archive'
        digest = hashlib.sha512(data).hexdigest()
        files = {'/releases/SDK.zip': data, '/releases/SDK.zip.sha512': (digest+'  SDK.zip').encode(),
                 '/releases/CHANGELOG.md': b'release notes'}
        with self.remote(files):
            result = sftp.download('SDK.zip', companion_paths=['SDK.zip.sha512', 'CHANGELOG.md'])
        self.assertTrue(result['checksum_verified'])
        self.assertEqual(Path(result['path']).read_bytes(), data)
        self.assertEqual(Path(result['path']).stat().st_mode & 0o777, 0o600)
        self.assertEqual(Path(result['delivery_dir']).stat().st_mode & 0o777, 0o700)
        self.assertTrue(Path(result['path']+'.sha512').exists())
        self.assertNotIn('fixture-secret', str(result))

    def test_unverified_download_is_explicit_and_does_not_overwrite(self):
        with self.remote({'/releases/a.zip': b'a'}):
            a = sftp.download('a.zip'); b = sftp.download('a.zip')
        self.assertFalse(a['checksum_verified'])
        self.assertNotEqual(a['path'], b['path'])
        self.assertTrue(Path(a['path']).exists())

    def test_checksum_failure_cleans_partial_delivery(self):
        with self.remote({'/releases/a.zip': b'a'}):
            with self.assertRaisesRegex(sftp.DeliveryError, 'mismatch'):
                sftp.download('a.zip', '0'*128)
        self.assertEqual(list((self.root/'downloads').iterdir()), [])

    def test_size_limit(self):
        with self.remote({'/releases/a.zip': b'a'*1025}):
            with self.assertRaisesRegex(sftp.DeliveryError, 'size limit'):
                sftp.download('a.zip')

    def test_traversal_and_symlink_escape(self):
        for path in ('../a', '/etc/passwd', 'escape', 'a\\b', 'a\n'):
            with self.subTest(path=path), self.remote({}):
                with self.assertRaises(sftp.DeliveryError):
                    sftp.download(path)

    def test_no_inline_password_and_missing_config(self):
        p=Path(os.environ['KOBIL_SDK_SFTP_CONNECTION'])
        p.write_text(json.dumps({**self.cfg, 'password': 'fixture-secret'}))
        with self.assertRaises(sftp.DeliveryError) as error:
            sftp.configuration()
        self.assertNotIn('fixture-secret',str(error.exception))
        p.unlink()
        with self.assertRaises(sftp.DeliveryError):
            sftp.configuration()

    def test_password_file_permissions(self):
        p=self.root/'secret';p.write_text('fixture-secret');p.chmod(0o600)
        self.assertEqual(sftp._password({'password_file':str(p)}),'fixture-secret')
        p.chmod(0o644)
        with self.assertRaises(sftp.DeliveryError):
            sftp._password({'password_file':str(p)})

    def test_keyring_reference(self):
        with patch('keyring.get_password',return_value='fixture-secret') as get:
            self.assertEqual(sftp._password({'password_keyring':{'service':'sdk','account':'customer'}}),'fixture-secret')
            get.assert_called_once_with('sdk','customer')

    def test_verified_host_keys_no_automatic_trust_and_no_discovery(self):
        with patch.object(sftp.paramiko,'SSHClient') as cls:
            with sftp.connection(self.cfg):pass
            client=cls.return_value
            self.assertIsInstance(client.set_missing_host_key_policy.call_args.args[0],sftp.paramiko.RejectPolicy)
            client.load_host_keys.assert_called_once_with(self.cfg['known_hosts'])
            self.assertFalse(client.connect.call_args.kwargs['allow_agent'])
            self.assertFalse(client.connect.call_args.kwargs['look_for_keys'])
            client.close.assert_called_once()

    def test_auth_failure_is_redacted(self):
        with patch.object(sftp.paramiko,'SSHClient') as cls:
            cls.return_value.connect.side_effect=sftp.paramiko.AuthenticationException('fixture-secret')
            with self.assertRaisesRegex(sftp.DeliveryError,'authentication failed') as error:
                with sftp.connection(self.cfg):pass
            self.assertNotIn('fixture-secret',str(error.exception))
            cls.return_value.close.assert_called_once()

    def test_changed_file_cleanup(self):
        fake=Remote({'/releases/a.zip':b'a'})
        initial=fake.stat('/releases/a.zip')
        with patch.object(sftp,'connection') as ctx:
            ctx.return_value.__enter__.return_value=fake
            with patch.object(fake,'stat',side_effect=[initial,SimpleNamespace(st_size=2,st_mtime=2)]):
                with self.assertRaisesRegex(sftp.DeliveryError,'changed'):
                    sftp.download('a.zip')
        self.assertFalse(list((self.root/'downloads').iterdir()))

class LocalSftpIntegrationTests(unittest.TestCase):
    def test_real_ssh_listing_download_and_host_mismatch(self):
        import socket
        import threading
        import posixpath
        import paramiko
        data = b'local SDK fixture'
        digest = hashlib.sha512(data).hexdigest()
        files = {'/releases/SDK.zip':data, '/releases/SDK.zip.sha512':digest.encode()}
        class Auth(paramiko.ServerInterface):
            def check_auth_password(self, user, password):
                return paramiko.AUTH_SUCCESSFUL if (user,password)==('customer','fixture-secret') else paramiko.AUTH_FAILED
            def check_channel_request(self, kind, chanid):
                return paramiko.OPEN_SUCCEEDED if kind=='session' else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
        class FS(paramiko.SFTPServerInterface):
            def canonicalize(self,path): return posixpath.normpath(path)
            def stat(self,path):
                if path not in files:return paramiko.SFTP_NO_SUCH_FILE
                a=paramiko.SFTPAttributes();a.st_mode=stat.S_IFREG|0o600;a.st_size=len(files[path]);a.st_mtime=1;return a
            def list_folder(self,path):
                if path!='/releases':return paramiko.SFTP_NO_SUCH_FILE
                out=[]
                for name in files:
                    a=self.stat(name);a.filename=posixpath.basename(name);out.append(a)
                return out
            def open(self,path,flags,attr):
                if path not in files or flags & (os.O_WRONLY|os.O_RDWR):return paramiko.SFTP_PERMISSION_DENIED
                h=paramiko.SFTPHandle(flags);h.readfile=io.BytesIO(files[path]);return h
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);key=paramiko.RSAKey.generate(2048)
            listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(4);listener.settimeout(.2)
            port=listener.getsockname()[1];stop=threading.Event();transports=[]
            def serve():
                while not stop.is_set():
                    try:conn,_=listener.accept()
                    except socket.timeout:continue
                    except OSError:break
                    t=paramiko.Transport(conn);transports.append(t);t.add_server_key(key)
                    t.set_subsystem_handler('sftp',paramiko.SFTPServer,FS)
                    try:t.start_server(server=Auth())
                    except (EOFError,paramiko.SSHException):pass
            thread=threading.Thread(target=serve,daemon=True);thread.start()
            known=root/'known_hosts';known.write_text(f'[127.0.0.1]:{port} {key.get_name()} {key.get_base64()}\n')
            cfg=root/'sftp.json';cfg.write_text(json.dumps({'host':'127.0.0.1','port':port,'username':'customer',
                'remote_root':'/releases','known_hosts':str(known),'password_env':'TEST_SFTP_PASSWORD'}))
            try:
                with patch.dict(os.environ,{'KOBIL_SDK_SFTP_CONNECTION':str(cfg),'TEST_SFTP_PASSWORD':'fixture-secret','KOBIL_SDK_DELIVERY':str(root/'delivery')}):
                    listing=sftp.list_delivery();self.assertEqual(len(listing['entries']),2)
                    result=sftp.download('SDK.zip',companion_paths=['SDK.zip.sha512'])
                    self.assertTrue(result['checksum_verified']);self.assertEqual(Path(result['path']).read_bytes(),data)
                    wrong=paramiko.RSAKey.generate(2048)
                    known.write_text(f'[127.0.0.1]:{port} {wrong.get_name()} {wrong.get_base64()}\n')
                    with self.assertRaisesRegex(sftp.DeliveryError,'host key mismatch'):sftp.list_delivery()
            finally:
                stop.set();listener.close()
                for t in transports:t.close()
                thread.join(timeout=3)
