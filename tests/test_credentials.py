import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch, Mock
import httpx
from kobil_sdk_integration import credentials as c
from kobil_sdk_integration import credential_worker as worker
from kobil_sdk_integration.credential_cli import main
from kobil_sdk_integration.backend import AST, configuration, BackendError

REF = {'provider':'keyring','service':'test-service','account':'test-account'}
CFG = {'schema_version':2,'environment':'test','tenant':'example','ast_url':'https://ast.example',
       'services':[{'name':'astLogin','url':'https://ast.example'}],
       'auth':{'type':'bearer','credential':REF}}


class CredentialTests(unittest.TestCase):
    def test_reference_validation_and_no_arbitrary_providers(self):
        for ref in [{}, {'provider':'plaintext'}, REF | {'password':'canary'},
                    REF | {'account':''}, {'provider':'env','name':'bad name'},
                    REF | {'fallback':{'provider':'env','name':'TOKEN'}},
                    {'provider':'age','store':'relative','identity':'/a', 'service':'s','account':'a'}]:
            with self.assertRaises(c.CredentialError): c.validate_reference(ref)
        self.assertEqual(c.validate_reference(REF), REF)

    def test_only_explicit_not_found_fallback(self):
        age={'provider':'age','store':'/store','identity':'/identity','service':'s','account':'a'}
        with patch.object(c,'native_call',return_value=None), patch.object(c,'age_read',return_value='fixture') as read:
            self.assertEqual(c.resolve(REF | {'fallback':age}),'fixture'); read.assert_called_once()
        for code in ['STORE_LOCKED','ACCESS_DENIED','PROVIDER_UNAVAILABLE']:
            with patch.object(c,'native_call',side_effect=c.CredentialError(code)), patch.object(c,'age_read') as read:
                with self.assertRaises(c.CredentialError): c.resolve(REF | {'fallback':age})
                read.assert_not_called()

    def test_worker_checks_returned_account(self):
        backend=Mock();backend.get_credential.return_value=types.SimpleNamespace(username='someone-else',password='canary')
        with patch.object(worker,'native_backend',return_value=backend):
            for op in ['get','set','delete']:
                with self.assertRaises(c.CredentialError) as e: worker.operate({'operation':op,'service':'s','account':'a','value':'new'})
                self.assertNotIn('canary',str(e.exception))
        backend.set_password.assert_not_called();backend.delete_password.assert_not_called()

    def test_store_requires_explicit_replace(self):
        backend=Mock();backend.get_credential.return_value=types.SimpleNamespace(username='a',password='old')
        payload={'operation':'set','service':'s','account':'a','value':'new'}
        with patch.object(worker,'native_backend',return_value=backend):
            with self.assertRaises(c.CredentialError):worker.operate(payload)
            worker.operate(payload | {'replace':True})
        backend.set_password.assert_called_once_with('s','a','new')

    def test_native_error_is_sanitized(self):
        backend=Mock();backend.get_credential.side_effect=RuntimeError('canary-secret')
        with patch.object(worker,'native_backend',return_value=backend):
            with self.assertRaises(c.CredentialError) as e:worker.operate({'operation':'get','service':'s','account':'a'})
        self.assertNotIn('canary',str(e.exception))

    def test_worker_pipe_has_no_secret_in_arguments(self):
        with patch.object(c,'bounded_process',return_value=(0,b'{"ok":true}')) as run:
            c.store(REF,'canary')
        argv,data=run.call_args.args
        self.assertNotIn('canary',str(argv));self.assertIn(b'canary',data)

    def test_subprocess_timeout_and_output_limit(self):
        with self.assertRaises(c.CredentialError):
            c.bounded_process([sys.executable,'-c','import time;time.sleep(10)'],timeout=.05)
        with self.assertRaises(c.CredentialError):
            c.bounded_process([sys.executable,'-c','import sys;sys.stdout.write("x"*1100000)'])

    def test_age_exact_lookup_and_bad_schema(self):
        ref={'provider':'age','store':'/store','identity':'/id','service':'s','account':'b'}
        envelope={'version':2,'keychain':{'s':{'a':'wrong-account-canary'}}}
        with patch.object(c,'private_read',side_effect=[b'AGE-SECRET-KEY-1ABC',b'encrypted']), patch.object(c,'bounded_process',return_value=(0,json.dumps(envelope).encode())):
            with self.assertRaises(c.CredentialError) as e:c.resolve(ref)
        self.assertEqual(e.exception.code,'CREDENTIAL_NOT_FOUND')
        self.assertNotIn('canary',str(e.exception))

    def test_age_permissions_and_symlink(self):
        if os.name != 'posix':self.skipTest('POSIX permissions')
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'identity';f.write_text('private');f.chmod(0o644)
            with self.assertRaises(c.CredentialError):c.private_read(f)
            f.chmod(0o600);self.assertEqual(c.private_read(f),b'private')
            link=Path(tmp)/'link';link.symlink_to(f)
            with self.assertRaises(c.CredentialError):c.private_read(link)

    def test_configuration_is_lazy_and_rejects_mixed_auth(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(c,'resolve') as read:
            f=Path(tmp)/'config.json';f.write_text(json.dumps(CFG))
            self.assertEqual(configuration(path=f),CFG);read.assert_not_called()
            f.write_text(json.dumps(CFG | {'token_env':'TOKEN'}))
            with self.assertRaises(BackendError):configuration(path=f)

    def test_oauth_secret_only_to_token_endpoint_no_write_retry(self):
        auth={'type':'oauth_client_credentials','credential':REF,'token_url':'https://idp.example/token','client_id':'client'}
        b=AST(CFG | {'auth':auth});self.addCleanup(b.close);b.client.close();calls=[]
        def handler(req):
            calls.append(req)
            if req.url.host=='idp.example':
                self.assertIn(b'canary-secret',req.content)
                return httpx.Response(200,json={'access_token':'canary-token'})
            self.assertNotIn(b'canary-secret',req.content)
            self.assertEqual(req.headers['authorization'],'Bearer canary-token')
            return httpx.Response(401,json={'secret':'canary-secret'})
        b.client=httpx.Client(transport=httpx.MockTransport(handler))
        with patch.object(c,'resolve',return_value='canary-secret'):
            with self.assertRaises(BackendError) as e:b.request('POST','/apps',{})
        self.assertEqual(len(calls),2);self.assertNotIn('canary',str(e.exception))

    def test_cli_status_no_lookup_and_migration_no_secret_copy(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(c,'native_call') as native:
            f=Path(tmp)/'config.json';f.write_text(json.dumps(CFG));original=f.read_bytes();out=io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(['--config',str(f),'status']),0)
                dest=Path(tmp)/'new.json'
                self.assertEqual(main(['--config',str(f),'prepare-keyring','--service','new','--account','new','--output',str(dest)]),0)
            native.assert_not_called();self.assertEqual(f.read_bytes(),original)
            self.assertEqual(json.loads(dest.read_text())['auth']['credential']['account'],'new')
            self.assertFalse(json.loads(out.getvalue().splitlines()[0])['credential_checked'])
