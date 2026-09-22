import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from kobil_sdk_integration import credentials, credential_tools, idp_transport
from kobil_sdk_integration.backend import AST, configuration, BackendError
from kobil_sdk_integration.idp_secrets import CredentialRef

REF={'provider':'keyring','service':'kobil-sdk/import/example','account':'ast'}
CFG={'schema_version':2,'environment':'test','tenant':'tenant','ast_url':'https://ast.example',
     'auth':{'type':'oauth_client_credentials','token_url':'https://idp.example/token','client_id':'ast','scope':'scope-a','credential':REF},
     'admin':{'idp_url':'https://idp.example','realm':'admin','client_id':'admin-cli','username':'admin','credential':REF|{'account':'idp'}}}

class Registry:
    def __init__(self):self.tools={}
    def tool(self):
        def add(f):self.tools[f.__name__]=f;return f
        return add

class CredentialIntegrationTests(unittest.TestCase):
    def setUp(self):
        r=Registry();credential_tools.register(r);self.tools=r.tools

    def test_profile_validation_does_not_unlock_and_checks_environment(self):
        with tempfile.TemporaryDirectory() as d,patch.object(credentials,'resolve') as resolve:
            p=Path(d)/'profile';p.write_text(json.dumps(CFG))
            self.assertEqual(configuration('test',p)['admin']['credential']['account'],'idp')
            with self.assertRaises(ValueError):configuration('other',p)
            bad={**CFG,'admin':{**CFG['admin'],'password_env':'PASSWORD'}};p.write_text(json.dumps(bad))
            with self.assertRaises(BackendError):configuration('test',p)
            resolve.assert_not_called()

    def test_ast_scope_and_idp_use_separate_refs(self):
        backend=AST(CFG)
        try:
            with patch.object(credentials,'resolve',return_value='fixture') as resolve,patch.object(backend,'send',return_value={'access_token':'token'}) as send:
                self.assertEqual(backend.token(),'token')
                resolve.assert_called_with(REF)
                self.assertEqual(send.call_args.kwargs['data']['scope'],'scope-a')
                self.assertEqual(idp_transport.admin_token(backend),'token')
                resolve.assert_called_with(REF|{'account':'idp'})
                self.assertEqual(send.call_args.kwargs['data']['grant_type'],'password')
        finally:backend.close()

    def test_status_never_reads_without_probe_and_never_returns_secret(self):
        with patch.object(credential_tools,'configuration',return_value=CFG),patch.object(credential_tools,'resolve',return_value='secret') as resolve:
            self.tools['sdk_credential_status']('test');resolve.assert_not_called()
            result=self.tools['sdk_credential_status']('test','idp',True)
            self.assertTrue(result['available']);self.assertNotIn('secret',str(result))

    def test_import_scoped_and_delete_requires_confirmation(self):
        with patch.object(credential_tools,'configuration',return_value=CFG),patch.object(credential_tools,'resolve',return_value='secret'),patch.object(credential_tools,'store') as store,patch.object(credential_tools,'delete') as delete:
            result=self.tools['sdk_credential_import']('test',CredentialRef(provider='env',name='SOURCE'),'idp')
            store.assert_called_once_with(REF|{'account':'idp'},'secret',replace=False)
            self.assertNotIn('secret',str(result))
            with self.assertRaises(ValueError):self.tools['sdk_credential_delete']('test')
            delete.assert_not_called()
            self.tools['sdk_credential_delete']('test','idp',True)
            delete.assert_called_once_with(REF|{'account':'idp'})

    def test_private_file_rejects_symlink_and_public_mode(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'secret';p.write_text('fixture');p.chmod(0o600)
            self.assertEqual(credentials.resolve({'provider':'file','path':str(p)}),'fixture')
            link=Path(d)/'link';link.symlink_to(p)
            with self.assertRaises(credentials.CredentialError):credentials.resolve({'provider':'file','path':str(link)})
            p.chmod(0o644)
            with self.assertRaises(credentials.CredentialError):credentials.resolve({'provider':'file','path':str(p)})

    def test_import_cannot_write_existing_local_namespace_even_with_replace(self):
        ref = {'provider':'keyring','service':'local-server','account':'admin'}
        with patch.object(credential_tools, 'selected', return_value=ref), patch.object(credential_tools, 'resolve') as resolve, patch.object(credential_tools, 'store') as store:
            with self.assertRaises(credentials.CredentialError):
                self.tools['sdk_credential_import']('test', CredentialRef(provider='env',name='SOURCE'), replace=True)
            resolve.assert_not_called()
            store.assert_not_called()

    def test_import_namespacing_is_deterministic_and_separates_servers(self):
        first=credentials.imported_keyring_reference('server-a/idp','admin')
        second=credentials.imported_keyring_reference('server-b/idp','admin')
        self.assertNotEqual(first,second)
        self.assertEqual(first,credentials.imported_keyring_reference('server-a/idp','admin'))
        self.assertEqual(first['service'],'kobil-sdk/import/server-a/idp')
        with self.assertRaises(credentials.CredentialError):
            credentials.imported_keyring_reference('x'*256,'admin')
