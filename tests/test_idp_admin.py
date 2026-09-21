import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from mcp.server.fastmcp import FastMCP
from kobil_sdk_integration.idp_admin import Admin, redact, load_private_json
from kobil_sdk_integration.idp_users import register, UserProfile
from kobil_sdk_integration.idp_secrets import CredentialRef, resolve, output_file

CFG={'environment':'test','tenant':'sample','admin':{'password_env':'TEST_ADMIN'},'token_env':'TEST_TOKEN'}

class AdminTests(unittest.TestCase):
    def make(self):
        with patch('kobil_sdk_integration.idp_admin.configuration',return_value=CFG),patch('kobil_sdk_integration.idp_admin.AST'):
            return Admin('test')
    def test_environment_guard_precedes_auth(self):
        with patch('kobil_sdk_integration.idp_admin.configuration',side_effect=ValueError('Active environment mismatch')),patch('kobil_sdk_integration.idp_admin.AST') as backend:
            with self.assertRaises(ValueError):Admin('wrong')
            backend.assert_not_called()
    def test_realm_encoded_and_token_closed(self):
        with patch('kobil_sdk_integration.idp_admin.configuration',return_value=CFG),patch('kobil_sdk_integration.idp_admin.AST') as cls,patch('kobil_sdk_integration.idp_admin.admin_token',return_value='token'):
            with Admin('test','realm/other') as a:self.assertTrue(a.prefix.endswith('realm%2Fother'))
            cls.return_value.close.assert_called_once();self.assertIsNone(a.token)
    def test_page_probe_and_completion(self):
        a=self.make();a.call=MagicMock(return_value=[{'id':str(i)} for i in range(3)])
        result=a.page('/users',first=4,max_results=2)
        self.assertEqual(result['next_offset'],6);self.assertFalse(result['complete']);self.assertEqual(len(result['items']),2)
        a.call.assert_called_once_with('GET','/users',params={'first':4,'max':3})
    def test_ignored_pagination_fails(self):
        a=self.make();a.call=MagicMock(return_value=[{}, {}, {}, {}])
        with self.assertRaisesRegex(RuntimeError,'ignored pagination'):a.page('/users',max_results=2)
    def test_full_collection_local_slice(self):
        a=self.make();a.call=MagicMock(return_value=[1,2,3])
        self.assertEqual(a.page('/roles',1,2,paginated=False)['items'],[2,3])
    def test_update_preserves_unknown_and_secret_config(self):
        a=self.make();a.raw=MagicMock(side_effect=[{'id':'x','config':{'clientSecret':'private','other':'keep'},'unrelated':True},{}])
        a.update('/x',{'config':{'new':'value'}},{'config'})
        self.assertEqual(a.raw.call_args.args[2],{'id':'x','config':{'clientSecret':'private','other':'keep','new':'value'},'unrelated':True})
    def test_redaction_nested_and_configured_values(self):
        a=self.make();a.token='bearer-value'
        with patch.dict(os.environ,{'TEST_ADMIN':'hidden-password'}):
            r=a._safe({'config':{'bindCredential':'hidden','clientSecret':'hidden'},'note':'hidden-password bearer-value'})
        self.assertNotIn('hidden',str(r));self.assertNotIn('bearer-value',str(r))
    def test_profile_rejects_credential_mutation(self):
        with self.assertRaises(ValueError):UserProfile(username='test',credentials=[{}])
    def test_private_ref_and_file_permissions(self):
        with self.assertRaises(ValueError):CredentialRef(provider='env',name='X',path='/bad')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'credential';p.write_text('secret');p.chmod(0o600)
            self.assertEqual(resolve(CredentialRef(provider='file',path=str(p))),'secret')
            p.chmod(0o644)
            with self.assertRaises(ValueError):resolve(CredentialRef(provider='file',path=str(p)))
            p.write_text('{}');p.chmod(0o600);self.assertEqual(load_private_json(str(p)),{})
    def test_private_output_no_overwrite_and_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'out'
            with self.assertRaises(RuntimeError):
                with output_file(str(p)):raise RuntimeError('failed before output')
            self.assertFalse(p.exists())
            p.write_text('keep')
            with self.assertRaises(ValueError):
                with output_file(str(p)):pass
            self.assertEqual(p.read_text(),'keep')
    def test_user_schema_tools_registered(self):
        import asyncio
        m=FastMCP('test');register(m)
        tools=asyncio.run(m.list_tools())
        self.assertEqual(len(tools),14)
        names={t.name for t in tools};self.assertIn('sdk_idp_user_search',names)
