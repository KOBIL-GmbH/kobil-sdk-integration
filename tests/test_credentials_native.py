"""Opt-in native-store checks use only disposable entries, never real accounts."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import uuid
from kobil_sdk_integration.credentials import store, resolve, delete, CredentialError


class NativeCredentialTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('KOBIL_RUN_NATIVE_CREDENTIAL_TESTS') == '1', 'Native store tests require explicit opt-in')
    def test_disposable_native_entry(self):
        ref={'provider':'keyring','service':'kobil-sdk-test-'+uuid.uuid4().hex,'account':'disposable'}
        created=False
        try:
            store(ref,'disposable-test-value');created=True
            self.assertEqual(resolve(ref),'disposable-test-value')
            with self.assertRaises(CredentialError) as error:resolve(ref | {'account':'absent'})
            self.assertEqual(error.exception.code,'CREDENTIAL_NOT_FOUND')
            store(ref,'rotated-test-value',replace=True)
            self.assertEqual(resolve(ref),'rotated-test-value')
        finally:
            if created:delete(ref)

    @unittest.skipUnless(shutil.which('age') and shutil.which('age-keygen'), 'age tools not installed')
    def test_disposable_age_envelope(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);identity=p/'identity';encrypted=p/'encrypted.age'
            subprocess.run(['age-keygen','-o',str(identity)],check=True,capture_output=True)
            identity.chmod(0o600)
            recipient=subprocess.run(['age-keygen','-y',str(identity)],check=True,capture_output=True,text=True).stdout.strip()
            plain=json.dumps({'version':2,'keychain':{'test':{'user':'disposable-value'}}}).encode()
            result=subprocess.run(['age','-r',recipient],input=plain,check=True,capture_output=True)
            encrypted.write_bytes(result.stdout);encrypted.chmod(0o600)
            ref={'provider':'age','store':str(encrypted),'identity':str(identity),'service':'test','account':'user'}
            self.assertEqual(resolve(ref),'disposable-value')
            with self.assertRaises(CredentialError) as error:resolve(ref | {'account':'absent'})
            self.assertEqual(error.exception.code,'CREDENTIAL_NOT_FOUND')
            encrypted.write_bytes(b'corrupt')
            with self.assertRaises(CredentialError) as error:resolve(ref)
            self.assertEqual(error.exception.code,'AGE_DECRYPT_FAILED')

    @unittest.skipUnless(os.environ.get('KOBIL_RUN_NATIVE_CREDENTIAL_TESTS') == '1' and shutil.which('age') and shutil.which('age-keygen'), 'Native store and age opt-in required')
    def test_native_keychain_to_age_to_native_keychain(self):
        from kobil_sdk_integration import age_store
        from test_age_store import Registry
        registry=Registry();age_store.register(registry);tools=registry.tools
        prefix='kobil-sdk-transfer-test-'+uuid.uuid4().hex
        source={'provider':'keyring','service':prefix,'account':'source'}
        target={'provider':'keyring','service':prefix,'account':'destination'}
        source_created=False;target_created=False
        try:
            store(source,'disposable-transfer-value');source_created=True
            with tempfile.TemporaryDirectory() as tmp:
                identity=str(Path(tmp)/'identity');output=str(Path(tmp)/'transfer.age')
                public=tools['sdk_age_identity_create'](identity)['recipient']
                tools['sdk_age_transfer_export'](output,[public],[{'service':'portable','account':'user','source':source}])
                tools['sdk_age_credential_import_keyring'](output,identity,'portable','user',prefix,'destination');target_created=True
                self.assertEqual(resolve(target),'disposable-transfer-value')
                with self.assertRaises(CredentialError):
                    tools['sdk_age_credential_import_keyring'](output,identity,'portable','user',prefix,'destination')
        finally:
            if target_created:delete(target)
            if source_created:delete(source)
