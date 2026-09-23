import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import uuid
from kobil_sdk_integration import environment_transfer as transfer, age_store, credentials
from kobil_sdk_integration.backend import configuration


@unittest.skipUnless(shutil.which('age') and shutil.which('age-keygen'), 'age tools required')
class ServerTransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.identity=self.root/'identity'
        code,raw=credentials.bounded_process(['age-keygen']);self.assertEqual(code,0)
        age_store.atomic_write(self.identity,raw)
        self.public=age_store.recipient(self.identity)
        self.bundle=self.root/'servers.age';self.output=self.root/'imported.age'
        self.refs=[];self.files=[]
        for name in ['server-a','server-b']:
            ref={'provider':'file','path':str(self.root/(name+'-secret'))}
            age_store.atomic_write(Path(ref['path']),('fixture-'+name).encode())
            cfg={'schema_version':2,'environment':name,'tenant':'test','ast_url':'https://ast.example',
                 'auth':{'type':'bearer','credential':ref},
                 'admin':{'idp_url':'https://idp.example','realm':'master','client_id':'admin-cli','username':'test','credential':ref}}
            p=self.root/(name+'.json');age_store.atomic_write(p,json.dumps(cfg).encode());self.files.append(str(p))
        self.db={('local-server','admin'):'preserve-local'}
    @unittest.skipUnless(os.name == 'posix', 'POSIX file permissions')
    def test_access_error_identifies_identity_before_decrypt(self):
        self.identity.chmod(0o644)
        with patch.object(age_store, 'bounded_process') as process:
            with self.assertRaisesRegex(credentials.CredentialError, 'ACCESS_DENIED: private identity'):
                age_store.read_document(self.bundle, self.identity)
            process.assert_not_called()

    @unittest.skipUnless(os.name == 'posix', 'POSIX file permissions')
    def test_access_error_identifies_bundle_before_decrypt(self):
        self.export()
        self.bundle.chmod(0o644)
        with patch.object(age_store, 'recipient', return_value=self.public), patch.object(age_store, 'bounded_process') as process:
            with self.assertRaisesRegex(credentials.CredentialError, 'ACCESS_DENIED: encrypted bundle/store'):
                age_store.read_document(self.bundle, self.identity)
            process.assert_not_called()

    def lookup(self,ref):
        try:return self.db[(ref['service'],ref['account'])]
        except KeyError:raise credentials.CredentialError('CREDENTIAL_NOT_FOUND')
    def store(self,ref,value,replace=False):
        key=(ref['service'],ref['account'])
        if key in self.db and not replace:raise credentials.CredentialError('ALREADY_EXISTS')
        self.db[key]=value
    def delete(self,ref):del self.db[(ref['service'],ref['account'])]
    def export(self):
        return transfer.export_bundle(str(self.bundle),[self.public],self.files)
    def do_import(self,names=None):
        with patch.object(transfer,'resolve',side_effect=self.lookup),patch.object(transfer,'store',side_effect=self.store),patch.object(transfer,'delete',side_effect=self.delete):
            return transfer.import_bundle(str(self.bundle),str(self.identity),names or ['server-a','server-b'],'partner',str(self.output))
    def test_two_servers_roundtrip_and_selector(self):
        exported=self.export();self.assertEqual(exported['credential_count'],4)
        wire=age_store.read_document(self.bundle,self.identity)
        self.assertNotIn(str(self.root),json.dumps(wire))
        self.assertNotIn(b'fixture-',self.bundle.read_bytes())
        result=self.do_import();self.assertEqual(result['status'],'imported')
        self.assertEqual(self.db[('local-server','admin')],'preserve-local')
        imported=age_store.read_document(self.output,self.identity)
        self.assertEqual(imported['keychain'],{})
        self.assertNotIn('fixture-',json.dumps(result))
        for name in ['server-a','server-b']:
            cfg=imported['environments'][name]
            for role,container in transfer.slots(cfg):
                self.assertEqual(container['credential']['service'],f'kobil-sdk/import/partner/{name}/{role}')
                self.assertEqual(self.lookup(container['credential']),'fixture-'+name)
        selector=self.root/'selector.json'
        age_store.atomic_write(selector,json.dumps({'age_environment':{'store':str(self.output),'identity':str(self.identity),'environment':'server-a'}}).encode())
        self.assertEqual(configuration('server-a',selector)['environment'],'server-a')
        self.assertEqual(self.output.stat().st_mode & 0o777,0o600)
    def test_selection_imports_only_selected_server(self):
        self.export();r=self.do_import(['server-b'])
        self.assertEqual(r['environments'],['server-b']);self.assertEqual(len(r['credential_references']),2)
    def test_duplicate_blocks_before_any_write(self):
        self.export();self.db[('kobil-sdk/import/partner/server-b/idp','credential')]='existing'
        before=copy.deepcopy(self.db)
        with self.assertRaises(credentials.CredentialError):self.do_import()
        self.assertEqual(self.db,before);self.assertFalse(self.output.exists())
    def test_output_failure_rolls_back_only_created_entries(self):
        self.export()
        with patch.object(transfer,'encrypt_write',side_effect=credentials.CredentialError('STORE_FAILED')):
            with self.assertRaises(credentials.CredentialError):self.do_import()
        self.assertEqual(self.db,{('local-server','admin'):'preserve-local'})
    def test_import_never_resolves_sender_paths(self):
        self.export();d=age_store.read_document(self.bundle,self.identity)
        d['environments']['server-a']['auth']['credential']={'provider':'file','path':'/should/not/read'}
        age_store.encrypt_write(self.bundle,self.identity,d,True)
        with self.assertRaises(credentials.CredentialError):self.do_import()
        self.assertEqual(len(self.db),1)
    def test_unauthorized_recipient_and_duplicate_environment(self):
        self.export();wrong=self.root/'wrong';code,raw=credentials.bounded_process(['age-keygen']);age_store.atomic_write(wrong,raw)
        with self.assertRaises(credentials.CredentialError):age_store.read_document(self.bundle,wrong)
        with patch.object(transfer,'resolve') as resolve:
            with self.assertRaises(credentials.CredentialError):transfer.export_bundle(str(self.root/'other.age'),[self.public],[self.files[0],self.files[0]])
            resolve.assert_not_called()
    def test_keyring_failure_rolls_back_and_reports_failed_cleanup(self):
        self.export();calls=[]
        def fail_second(ref,value,replace=False):
            calls.append(ref)
            if len(calls)==2:raise credentials.CredentialError('STORE_FAILED')
            self.store(ref,value,replace)
        with patch.object(transfer,'resolve',side_effect=self.lookup),patch.object(transfer,'store',side_effect=fail_second),patch.object(transfer,'delete',side_effect=credentials.CredentialError('ACCESS_DENIED')):
            result=transfer.import_bundle(str(self.bundle),str(self.identity),['server-a'],'partner',str(self.output))
        self.assertEqual(result['status'],'cleanup_required')
        self.assertEqual(len(result['credential_references']),1)
        self.assertNotIn('fixture-',json.dumps(result))
        self.assertFalse(self.output.exists())
    @unittest.skipUnless(os.environ.get('KOBIL_RUN_NATIVE_CREDENTIAL_TESTS')=='1','Native credential opt-in required')
    def test_actual_keychain_two_server_transfer(self):
        source={'provider':'keyring','service':'kobil-sdk-transfer-test-'+uuid.uuid4().hex,'account':'source'}
        namespace='test-'+uuid.uuid4().hex
        targets=[credentials.imported_keyring_reference(f'{namespace}/{name}/{role}','credential')
                 for name in ['server-a','server-b'] for role in ['ast','idp']]
        created=[]
        try:
            credentials.store(source,'disposable-server-transfer');created.append(source)
            for file in self.files:
                p=Path(file);cfg=json.loads(p.read_text())
                for _,container in transfer.slots(cfg):container['credential']=source
                p.write_text(json.dumps(cfg))
            self.export()
            r=transfer.import_bundle(str(self.bundle),str(self.identity),['server-a','server-b'],namespace,str(self.output))
            self.assertEqual(r['status'],'imported');created.extend(targets)
            for ref in targets:self.assertEqual(credentials.resolve(ref),'disposable-server-transfer')
            self.assertEqual(credentials.resolve(source),'disposable-server-transfer')
        finally:
            for ref in reversed(created):credentials.delete(ref)
