import os
import tempfile
import unittest

from kobil_sdk_integration.backend import BackendError
from kobil_sdk_integration.certificate import backend_hosts, select_root, write_root_certificate

LEAF = {'pem': 'LEAF', 'subject': 'idp.example', 'issuer': 'Mid', 'not_after': 'x', 'sha256': '1'}
MID = {'pem': 'MID', 'subject': 'Mid', 'issuer': 'Root', 'not_after': 'y', 'sha256': '2'}
ROOT = {'pem': '-----BEGIN CERTIFICATE-----\nROOT\n-----END CERTIFICATE-----\n',
        'subject': 'Root', 'issuer': 'Root', 'not_after': 'z', 'sha256': '3'}
CFG = {'environment': 'test', 'tenant': 'sample', 'ast_url': 'https://ast.example',
       'services': [{'name': 'astLogin', 'url': 'https://ast.example/x'}, {'name': 'push', 'url': 'https://scp.example/n'}],
       'oauth': {'token_url': 'https://idp.example/auth/realms/sample/protocol/openid-connect/token'}}


class CertificateTests(unittest.TestCase):
    def test_the_self_signed_root_is_selected(self):
        self.assertEqual(select_root([LEAF, MID, ROOT])['subject'], 'Root')
        self.assertEqual(select_root([LEAF, MID])['subject'], 'Mid')
        with self.assertRaises(BackendError):
            select_root([])

    def test_hosts_come_from_ast_services_and_idp_in_order(self):
        self.assertEqual(backend_hosts(CFG), ['ast.example', 'scp.example', 'idp.example'])
        with_admin = dict(CFG, admin={'idp_url': 'https://admin-idp.example'})
        self.assertEqual(backend_hosts(with_admin)[-1], 'admin-idp.example')

    def test_root_is_written_once_and_every_host_is_checked_against_it(self):
        checked = []
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'root.pem')
            result = write_root_certificate(CFG, out, fetch=lambda h: [LEAF, MID, ROOT],
                                            verify=lambda h, p: checked.append(h) or h != 'scp.example')
            self.assertEqual(open(out).read(), ROOT['pem'])
            self.assertEqual(oct(os.stat(out).st_mode & 0o777), '0o600')
            self.assertEqual(result['read_from'], 'idp.example')
            self.assertEqual(result['file_name'], 'root.pem')
            self.assertEqual(checked, ['ast.example', 'scp.example', 'idp.example'])
            self.assertEqual(result['hosts_trusting_this_root'], ['ast.example', 'idp.example'])
            self.assertEqual(result['hosts_not_trusting_this_root'], ['scp.example'])
            with self.assertRaises(ValueError):
                write_root_certificate(CFG, out, fetch=lambda h: [ROOT], verify=lambda h, p: True)

    def test_missing_directory_and_bad_host_are_refused_before_any_network(self):
        with self.assertRaises(ValueError):
            write_root_certificate(CFG, '/no/such/dir/root.pem', fetch=lambda h: 1/0, verify=lambda h, p: True)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                write_root_certificate(CFG, os.path.join(tmp, 'r.pem'), host='bad host',
                                       fetch=lambda h: 1/0, verify=lambda h, p: True)
