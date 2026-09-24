import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from kobil_sdk_integration import bundled_environment as bundled
from kobil_sdk_integration.age_store import atomic_write, read_document, encrypt_write, recipient
from kobil_sdk_integration.backend import AST, authentication, configuration
from kobil_sdk_integration.credentials import CredentialError, bounded_process, resolve
from kobil_sdk_integration.environment_transfer import encrypt_recipients


@unittest.skipUnless(shutil.which('age') and shutil.which('age-keygen'), 'age tools required')
class DefaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.project = self.root/'project'; self.project.mkdir()
        home = self.root/'home'; home.mkdir()
        p = patch.dict('os.environ', {'HOME': str(home)}); p.start(); self.addCleanup(p.stop)
        self.identity = self.root/'delivery.key'
        code, key = bounded_process(['age-keygen']); self.assertEqual(code, 0)
        atomic_write(self.identity, key)
        ref={'provider':'keyring','service':'transfer/test','account':'credential'}
        self.profile={'schema_version':2,'environment':'akinci','tenant':'test',
            'ast_url':'https://ast.example', 'auth':{'type':'oauth_password',
            'token_url':'https://idp.example/token','client_id':'test-client',
            'username':'fixture-user','credential':ref}}
        self.doc={'version':2,'keychain':{'transfer/test':{'credential':'fixture-password'}},
                  'environments':{'akinci':self.profile}}
        self.make_bundle()

    def make_bundle(self):
        path=self.root/'bundle.age'; path.unlink(missing_ok=True)
        encrypt_recipients(path,[recipient(self.identity)],self.doc)
        if hasattr(self,'resource'):self.resource.stop()
        self.resource=patch.object(bundled,'bundle_bytes',return_value=path.read_bytes())
        self.resource.start(); self.addCleanup(self.resource.stop)

    def test_missing_identity_prepares_project_without_plaintext_or_connection(self):
        result=bundled.initialize(str(self.project))
        self.assertEqual(result['status'],'delivery_identity_required')
        local=self.project/'.kobil-sdk'
        self.assertTrue((local/'recipient.txt').is_file())
        self.assertFalse((local/'connection.json').exists())
        self.assertFalse((local/'environments.age').exists())

    def test_import_reencrypts_credentials_and_rerun_preserves_additional_servers(self):
        result=bundled.initialize(str(self.project),str(self.identity))
        self.assertEqual(result['status'],'initialized')
        cfg=configuration(path=result['connection_path'])
        ref=cfg['auth']['credential']
        self.assertEqual(ref['provider'],'age')
        self.assertNotEqual(ref['identity'],str(self.identity))
        self.assertEqual(resolve(ref),'fixture-password')
        data=read_document(ref['store'],ref['identity'])
        extra=copy.deepcopy(cfg);extra['environment']='other'
        data['environments']['other']=extra
        encrypt_write(Path(ref['store']),ref['identity'],data,True)
        before=Path(ref['store']).read_bytes()
        selected=Path(result['connection_path']);before_selector=selected.read_bytes()
        again=bundled.initialize(str(self.project),str(self.identity))
        self.assertEqual(again['status'],'existing_environment_preserved')
        self.assertEqual(Path(ref['store']).read_bytes(),before)
        self.assertEqual(selected.read_bytes(),before_selector)
        self.assertNotIn(b'fixture-password',before)
        self.assertNotIn('fixture-password',json.dumps(result))

    def test_wrong_key_does_not_create_store(self):
        other=self.root/'wrong.key';code,key=bounded_process(['age-keygen']);atomic_write(other,key)
        with self.assertRaisesRegex(CredentialError,'AGE_DECRYPT_FAILED'):
            bundled.initialize(str(self.project),str(other))
        self.assertFalse((self.project/'.kobil-sdk/environments.age').exists())

    def test_sender_file_reference_is_never_resolved(self):
        self.doc['environments']['akinci']['auth']['credential']={'provider':'file','path':'/private/sender'}
        self.make_bundle()
        with self.assertRaisesRegex(CredentialError,'CONFIG_INVALID'):
            bundled.initialize(str(self.project),str(self.identity))
        self.assertFalse((self.project/'.kobil-sdk/environments.age').exists())

    def test_delivery_identity_cannot_be_inside_project(self):
        inside=self.project/'key';shutil.copyfile(self.identity,inside);inside.chmod(0o600)
        with self.assertRaises(CredentialError):bundled.initialize(str(self.project),str(inside))


class PasswordGrantTests(unittest.TestCase):
    def test_password_grant_gets_fresh_token_without_client_secret(self):
        cfg={'schema_version':2,'environment':'example','tenant':'tenant','ast_url':'https://ast.example',
            'auth':{'type':'oauth_password','token_url':'https://idp.example/token','client_id':'client',
                    'username':'user','credential':{'provider':'env','name':'TEST_PASSWORD'}}}
        self.assertEqual(authentication(cfg)['type'],'oauth_password')
        b=AST(cfg);self.addCleanup(b.close)
        with patch('kobil_sdk_integration.credentials.resolve',return_value='fixture'):
            with patch.object(b,'send',return_value={'access_token':'fresh'}) as send:
                self.assertEqual(b.token(),'fresh')
                self.assertEqual(send.call_args.kwargs['data'],{'grant_type':'password',
                    'client_id':'client','username':'user','password':'fixture'})
        del cfg['auth']['username']
        with self.assertRaises(ValueError):authentication(cfg)
