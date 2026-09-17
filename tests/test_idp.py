import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import httpx
from kobil_sdk_integration.idp import IDP, configuration
from kobil_sdk_integration.backend import BackendError

CFG={'schema_version':2,'environment':'test','realm':'example','admin_url':'https://idp.example/auth/admin',
     'allow_test_provisioning':True,'auth':{'type':'bearer','credential':{'provider':'env','name':'TEST_IDP_TOKEN'}}}
USER={'username':'test-user','id':'user-id','enabled':True}

class IDPTests(unittest.TestCase):
 def client(self, handler):
  b=IDP(CFG);b.client.close();b.client=httpx.Client(transport=httpx.MockTransport(handler));b.token=lambda:'test-token'
  self.addCleanup(b.close);return b
 def test_connection_lazy_and_mismatch(self):
  with tempfile.TemporaryDirectory() as d,patch('kobil_sdk_integration.credentials.resolve') as resolve:
   p=Path(d)/'cfg';p.write_text(json.dumps(CFG))
   with patch.dict(os.environ,{'KOBIL_SDK_IDP_CONNECTION':str(p)}):
    self.assertEqual(configuration('test'),CFG)
    with self.assertRaises(BackendError):configuration('different')
    p.write_text(json.dumps(CFG|{'secret':'hidden'}))
    with self.assertRaises(BackendError) as e:configuration()
    self.assertNotIn('hidden',str(e.exception))
   resolve.assert_not_called()
 def test_missing_idp_does_not_use_ast_connection(self):
  with patch.dict(os.environ,{},clear=True):
   with self.assertRaisesRegex(BackendError,'NOT_SELECTED'):configuration()
 def test_exact_lookup_and_no_private_fields(self):
  def handler(req):
   self.assertEqual(req.url.params['exact'],'true')
   return httpx.Response(200,json=[USER|{'email':'private','credentials':['hidden']}])
  self.assertEqual(self.client(handler).user_get('test-user'),{'username':'test-user','user_id':'user-id','exists':True,'enabled':True})
  with self.assertRaises(BackendError):self.client(lambda r:httpx.Response(200,json=[USER|{'username':'other'}])).user_get('test-user')
 def test_create_only_after_exact_absence(self):
  requests=[]
  def handler(r):
   requests.append(r.method)
   if r.method=='POST':
    self.assertEqual(json.loads(r.content),{'username':'test-user','enabled':True});return httpx.Response(201)
   return httpx.Response(200,json=[] if len(requests)==1 else [USER])
  self.assertTrue(self.client(handler).user_create('test-user')['created']);self.assertEqual(requests,['GET','POST','GET'])
 def test_existing_or_unauthorized_does_not_create(self):
  for response in [httpx.Response(200,json=[USER]),httpx.Response(403)]:
   calls=[]
   def handler(r):calls.append(r.method);return response
   with self.assertRaises(BackendError):self.client(handler).user_create('test-user')
   self.assertEqual(calls,['GET'])
 def test_activation_private_delivery_and_unknown_outcome(self):
  for status in [204,500]:
   calls=[];sent=[]
   def handler(r):
    calls.append(r.method)
    if r.method=='PUT':sent.append(json.loads(r.content));return httpx.Response(status)
    return httpx.Response(200,json=[] if r.url.path.endswith('/credentials') else [USER])
   with tempfile.TemporaryDirectory() as d:
    folder=Path(d).resolve();folder.chmod(0o700);p=folder/'identity.json'
    result=self.client(handler).activation_write('test-user','user-id',str(p))
    saved=json.loads(p.read_text());code=saved['activation_code']
    self.assertRegex(code,r'^\d{8}$');self.assertNotIn(code,json.dumps(result))
    self.assertEqual(json.loads(sent[0]['credentials'][0]['secretData'])['code'],code)
    self.assertEqual(p.stat().st_mode & 0o777,0o600)
    self.assertEqual(result['status'],'issued' if status==204 else 'unknown')
    self.assertEqual(calls,['GET','GET','PUT'])
 def test_refuse_enrolled_existing_credentials_and_output_collision(self):
  for credentials in [[{'type':'password'}],[{'type':'ACTIVATION_CODE'}],[]]:
   calls=[]
   def handler(r):calls.append(r.method);return httpx.Response(200,json=credentials if r.url.path.endswith('/credentials') else [USER])
   with tempfile.TemporaryDirectory() as d:
    p=Path(d).resolve()/'existing';p.write_text('preserve')
    with self.assertRaises((BackendError,FileExistsError)):self.client(handler).activation_write('test-user','user-id',str(p))
    self.assertEqual(p.read_text(),'preserve');self.assertNotIn('PUT',calls)
 def test_wrong_identity_or_disabled_prevents_write(self):
  for user in [USER|{'enabled':False},USER|{'id':'another'}]:
   calls=[]
   def handler(r):calls.append(r.method);return httpx.Response(200,json=[user])
   with self.assertRaises(BackendError):self.client(handler).activation_write('test-user','user-id','/unused')
   self.assertEqual(calls,['GET'])
 def test_test_provisioning_gate(self):
  b=self.client(lambda r:self.fail('network called'));b.cfg['allow_test_provisioning']=False
  with self.assertRaises(BackendError):b.user_create('test-user')
 def test_unsafe_directory_prevents_put(self):
  calls=[]
  def handler(r):calls.append(r.method);return httpx.Response(200,json=[] if r.url.path.endswith('/credentials') else [USER])
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d).resolve();folder.chmod(0o755)
   with self.assertRaises(ValueError):self.client(handler).activation_write('test-user','user-id',str(folder/'identity'))
   self.assertNotIn('PUT',calls)
