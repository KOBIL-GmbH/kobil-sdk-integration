import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from kobil_sdk_integration import service_helpers as helpers, service_api, idp_secrets
from kobil_sdk_integration.backend import BackendError

class Registry:
    def __init__(self):self.tools={}
    def tool(self):
        def add(f):self.tools[f.__name__]=f;return f
        return add

class HelpersTests(unittest.TestCase):
    def setUp(self):
        r=Registry();helpers.register(r);self.tools=r.tools

    def test_new_route_contracts_encode_ids_and_preserve_payload(self):
        cases=[('v3_user_get','GET',{'username':'a/b'},'/v3_user/a%2Fb'),
               ('v3_user_delete','DELETE',{'username':'a/b'},'/v3_user/a%2Fb'),
               ('v3_user_search','GET',{},'/v3_user/getusers'),
               ('authenticator_providers','GET',{},'/authentication/authenticator-providers'),
               ('flow_execution_create','POST',{'alias':'a/b'},'/flows/a%2Fb/executions/execution'),
               ('execution_config_create','POST',{'execution':'x'},'/executions/x/config'),
               ('authenticator_config_get','GET',{'config':'c'},'/config/c'),
               ('authenticator_config_update','PUT',{'config':'c'},'/config/c')]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'body';p.write_text('{"config":{"custom":"value"}}');p.chmod(0o600)
            for op,method,ids,suffix in cases:
                out=service_api.prepare('idp',op,ids,{},str(p) if method in ('POST','PUT') else None,'selected')
                self.assertEqual(out[0],method);self.assertTrue(out[1].endswith(suffix));self.assertIn('/selected/',out[1])
                if method in ('POST','PUT'):self.assertEqual(out[3],{'config':{'custom':'value'}})

    def test_ast_token_private_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d,patch.object(helpers,'configuration',return_value={}),patch.object(helpers,'AST') as cls:
            cls.return_value.token.return_value='fixture-secret'
            p=Path(d)/'token.json'
            result=self.tools['sdk_ast_token_write']('test',str(p))
            self.assertNotIn('fixture-secret',str(result));self.assertEqual(p.stat().st_mode&0o777,0o600)
            with self.assertRaises(ValueError):self.tools['sdk_ast_token_write']('test',str(p))
            self.assertEqual(cls.return_value.token.call_count,1)

    def test_login_fetch_does_not_send_admin_token_or_follow_redirect(self):
        with tempfile.TemporaryDirectory() as d,patch.object(helpers,'configuration',return_value={'tenant':'r','admin':{'idp_url':'https://idp.example'}}),patch.object(helpers,'AST') as cls:
            response=cls.return_value.client.stream.return_value.__enter__.return_value
            response.status_code=302
            with self.assertRaises(BackendError):self.tools['sdk_idp_login_page_fetch']('test','client','app://callback',str(Path(d)/'page'))
            self.assertFalse((Path(d)/'page').exists())
            cls.return_value.token.assert_not_called()
            args,kwargs=cls.return_value.client.stream.call_args
            self.assertEqual(kwargs,{})
            self.assertIn('client_id=client',args[1])

    def test_grafana_environment_mismatch_precedes_credentials(self):
        with patch.object(helpers,'configuration'),patch.object(helpers,'load_private_json',return_value={'environment':'other'}),patch.object(helpers,'resolve') as resolve:
            with self.assertRaises(ValueError):self.tools['sdk_ast_find_client']('test','device','provider')
            resolve.assert_not_called()

    def test_grafana_literal_query_and_metadata_only(self):
        cfg={'environment':'test','url':'https://grafana.example','datasource_uid':'uid','labels':{'namespace':'customer'},'credential':{'provider':'env','name':'TOKEN'}}
        with patch.object(helpers,'configuration'),patch.object(helpers,'load_private_json',return_value=cfg),patch.object(helpers,'resolve',return_value='fixture-token'),patch('httpx.Client') as cls:
            client=cls.return_value.__enter__.return_value
            response=client.stream.return_value.__enter__.return_value;response.status_code=200
            response.iter_bytes.return_value=[json.dumps({'status':'success','data':{'resultType':'streams','result':[{'values':[['123','userId=12345678-1234-4234-8234-123456789abc secret-text']]}]}}).encode()]
            result=self.tools['sdk_ast_find_client']('test','a.*"','provider')
            self.assertEqual(result['event_count'],1);self.assertNotIn('secret-text',str(result))
            query=client.stream.call_args.kwargs['params']['query']
            self.assertTrue(query.endswith('|= '+json.dumps('a.*"')))
            self.assertFalse(result['ownership_verified'])

    def test_supplied_activation_code_not_returned(self):
        r=Registry();idp_secrets.register(r);uid='12345678-1234-4234-8234-123456789abc'
        with patch.object(idp_secrets,'Admin') as cls,patch.object(idp_secrets,'resolve',return_value='123456'):
            cls.return_value.__enter__.return_value.raw.side_effect=[{'id':uid},None,[{'type':'ACTIVATION_CODE'}]]
            result=r.tools['sdk_idp_activation_code_set']('test',uid,idp_secrets.CredentialRef(provider='env',name='CODE'))
            self.assertNotIn('activation_code',result)

    def test_auth_test_checks_selected_service_without_returning_token(self):
        with patch.object(helpers,'configuration',return_value={}),patch.object(helpers,'AST') as cls:
            cls.return_value.token.return_value='secret'
            result=self.tools['sdk_backend_auth_test']('test','ast')
            self.assertTrue(result['authenticated']);self.assertFalse(result['resource_permissions_verified'])
            self.assertNotIn('secret',str(result));cls.return_value.close.assert_called_once()
            with self.assertRaises(ValueError):self.tools['sdk_backend_auth_test']('test','other')
