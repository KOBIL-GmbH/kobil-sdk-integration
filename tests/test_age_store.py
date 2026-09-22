import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from kobil_sdk_integration import age_store, credentials
from kobil_sdk_integration.backend import configuration, BackendError

class Registry:
    def __init__(self):self.tools={}
    def tool(self):
        def add(f):self.tools[f.__name__]=f;return f
        return add

@unittest.skipUnless(shutil.which('age') and shutil.which('age-keygen'),'age tools required')
class AgeStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.identity=str(self.root/'identity');self.store=str(self.root/'store.age')
        r=Registry();age_store.register(r);self.tools=r.tools
        self.tools['sdk_age_identity_create'](self.identity)
        self.tools['sdk_age_store_create'](self.store,self.identity)

    def test_password_roundtrip_compatible_with_runtime_and_replace(self):
        source=self.root/'password';source.write_text('fixture-password');source.chmod(0o600)
        args=(self.store,self.identity,'sftp-test','account',{'provider':'file','path':str(source)})
        result=self.tools['sdk_age_credential_put'](*args)
        self.assertNotIn('fixture-password',str(result))
        self.assertNotIn(b'fixture-password',Path(self.store).read_bytes())
        ref={'provider':'age','store':self.store,'identity':self.identity,'service':'sftp-test','account':'account'}
        self.assertEqual(credentials.resolve(ref),'fixture-password')
        original=Path(self.store).read_bytes()
        with self.assertRaises(credentials.CredentialError):self.tools['sdk_age_credential_put'](*args)
        self.assertEqual(original,Path(self.store).read_bytes())
        source.write_text('replacement');self.tools['sdk_age_credential_put'](*args,replace=True)
        self.assertEqual(credentials.resolve(ref),'replacement')
        self.assertEqual(Path(self.store).stat().st_mode&0o777,0o600)

    def test_environment_roundtrip_and_no_inline_secret_export(self):
        profile={'schema_version':2,'environment':'test','tenant':'customer','ast_url':'https://ast.example',
                 'auth':{'type':'bearer','credential':{'provider':'age','store':self.store,'identity':self.identity,'service':'ast','account':'token'}}}
        p=self.root/'profile';p.write_text(json.dumps(profile));p.chmod(0o600)
        self.tools['sdk_age_environment_put'](self.store,self.identity,'test',str(p))
        result=self.tools['sdk_age_store_list'](self.store,self.identity)
        self.assertEqual(result['environments'],['test']);self.assertNotIn('https://',str(result))
        out=self.root/'export.json'
        self.tools['sdk_age_environment_export'](self.store,self.identity,'test',str(out))
        self.assertEqual(configuration('test',out),profile)
        selector=self.root/'selector.json'
        self.tools['sdk_age_environment_selector_write'](self.store,self.identity,'test',str(selector))
        self.assertNotIn('https://',selector.read_text())
        self.assertEqual(configuration('test',selector),profile)
        with self.assertRaises(BackendError):configuration('other',selector)

        with self.assertRaises(credentials.CredentialError):self.tools['sdk_age_environment_export'](self.store,self.identity,'test',str(out))
        profile['auth']['password']='not-allowed';p.write_text(json.dumps(profile))
        with self.assertRaises(BackendError):self.tools['sdk_age_environment_put'](self.store,self.identity,'test',str(p),True)

    def test_failed_encrypt_and_lock_do_not_change_existing_store(self):
        before=Path(self.store).read_bytes()
        with age_store.writer_lock(Path(self.store)):
            with self.assertRaises(credentials.CredentialError):self.tools['sdk_age_store_create'](self.store,self.identity)
        with patch.object(age_store,'bounded_process',return_value=(1,b'failure-secret')),patch.object(age_store,'recipient',return_value='age1fixture'):
            with self.assertRaises(credentials.CredentialError) as caught:
                age_store.encrypt_write(Path(self.store),self.identity,{'version':2},True)
        self.assertNotIn('failure-secret',str(caught.exception));self.assertEqual(before,Path(self.store).read_bytes())
        self.assertEqual(sorted(p.name for p in self.root.iterdir()),['identity','store.age'])

    def test_create_never_overwrites_and_rejects_symlink_store(self):
        for tool,path in [('sdk_age_identity_create',self.identity),('sdk_age_store_create',self.store)]:
            before=Path(path).read_bytes()
            with self.assertRaises(credentials.CredentialError):
                if tool.endswith('identity_create'):self.tools[tool](path)
                else:self.tools[tool](path,self.identity)
            self.assertEqual(before,Path(path).read_bytes())
        link=self.root/'link.age';link.symlink_to(self.store)
        with self.assertRaises(credentials.CredentialError):self.tools['sdk_age_store_list'](str(link),self.identity)
