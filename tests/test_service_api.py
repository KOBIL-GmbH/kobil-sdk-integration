import asyncio
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from kobil_sdk_integration import service_api as api
from kobil_sdk_integration.server import mcp


class ServiceTests(unittest.TestCase):
    def payload(self, root, data):
        p=Path(root)/'payload.json';p.write_text(json.dumps(data));p.chmod(0o600);return str(p)

    def test_version_registration_removal_keeps_architecture_query(self):
        with patch.object(api,'configuration',return_value={}), patch.object(api,'AST') as cls:
            cls.return_value.request.return_value={}
            api.ast_request('test','version_unregister',{'version':'v/1'},{'architectureName':'arm64'})
            cls.return_value.request.assert_called_once_with('DELETE','/versions/v%2F1/register?architectureName=arm64',None)
            cls.return_value.close.assert_called_once()

    def test_architectures_is_read_only_and_path_is_encoded(self):
        method,path,query,body=api.prepare('ast','architecture_list',{'platform':'iOS'},None,None)
        self.assertEqual((method,path,body),('GET','/platforms/iOS/architectures',None))

    def test_activation_payload_is_forwarded_without_flow_provisioning(self):
        data={'credentials':[{'type':'ACTIVATION_CODE','credentialData':'{"period":"1d"}','secretData':'{"code":"fixture"}'}]}
        with tempfile.TemporaryDirectory() as d:
            p=self.payload(d,data)
            method,path,q,body=api.prepare('idp','v3_user_update',{'username':'test@example.org'},None,p,'sample')
            self.assertEqual((method,path),('PUT','/auth/realms/sample/v3_user/test%40example.org/update'))
            self.assertEqual(body,data)

    def test_realm_update_has_no_smtp_preset_or_other_added_fields(self):
        data={'smtpServer':{'host':'smtp.example.org','port':'587'}}
        with tempfile.TemporaryDirectory() as d:
            method,path,q,body=api.prepare('idp','realm_update',{},None,self.payload(d,data),'selected')
            self.assertEqual((method,path,body),('PUT','/auth/admin/realms/selected',data))

    def test_client_permission_route_uses_uuid_not_flow_choice(self):
        with tempfile.TemporaryDirectory() as d:
            method,path,q,body=api.prepare('idp','client_management_permissions',{'client':'client-uuid'},None,self.payload(d,{'enabled':True}),'r')
            self.assertEqual(path,'/auth/admin/realms/r/clients/client-uuid/management/permissions')
            self.assertEqual(body,{'enabled':True})

    def test_unknown_operation_and_extra_identifiers_fail_without_backend(self):
        with patch.object(api,'AST') as cls:
            for op,ids,q in [('https://elsewhere.example',{},{}),('device_get',{'device':'x','realm':'other'},{}),('app_list',{}, {'token':'x'}),('version_unregister',{'version':'x'}, {})]:
                with self.assertRaises(ValueError):api.ast_request('e',op,ids,q)
            cls.assert_not_called()

    def test_payload_mode_and_pagination_are_validated(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.payload(d,{})
            Path(p).chmod(0o644)
            with self.assertRaises(ValueError):api.prepare('ast','version_create',{},None,p)
        for value in (True,-1,201,'100'):
            with self.assertRaises(ValueError):api.prepare('ast','app_list',{}, {'pageSize':value},None)

    def test_no_orchestration_helpers_or_dependencies(self):
        names={t.name for t in asyncio.run(mcp.list_tools())}
        self.assertTrue({'sdk_idp_service_request','sdk_ast_service_request','sdk_service_operations'}<=names)
        self.assertFalse({'sdk_idp_journeys','sdk_activation_flow_ensure','sdk_activation_client_ensure'}&names)
        root=Path(api.__file__).parent
        self.assertFalse((root/'activation.py').exists())
        self.assertFalse((root/'idpflow.py').exists())
        for p in root.glob('*.py'):
            self.assertNotIn('from .activation import',p.read_text())

    def test_every_route_is_fixed_relative_and_has_exact_identifiers(self):
        import string
        self.assertEqual(len(api.ROUTES),49)
        for name,spec in api.ROUTES.items():
            placeholders={v for _,v,_,_ in string.Formatter().parse(spec['path']) if v}
            self.assertEqual(placeholders,set(spec['identifiers'])|({'realm'} if name.startswith('idp.') else set()))
            self.assertTrue(spec['path'].startswith('/'))
            self.assertNotIn('://',spec['path'])

    def test_inventory_reports_partial_failures_and_next_page(self):
        with patch.object(api,'Admin') as admin, patch.object(api,'AST') as backend:
            admin.return_value.__enter__.return_value.page.return_value={'items':[{'id':'u1'},{'id':'u2'}], 'next_offset':2,'complete':False}
            backend.return_value.request.side_effect=[[{'id':'d1'}],RuntimeError('private failure')]
            tool=asyncio.run(mcp.list_tools())
            self.assertIn('sdk_ast_device_inventory',{t.name for t in tool})
            result=asyncio.run(mcp.call_tool('sdk_ast_device_inventory',{'expected_environment':'e','max_users':2}))
            # FastMCP returns content + structured result in current protocol implementation.
            rendered=str(result)
            self.assertIn('device_request_failed',rendered)
            self.assertIn('next_user_offset',rendered)
            self.assertNotIn('private failure',rendered)
            backend.return_value.close.assert_called_once()

    def test_dashboard_route_map_has_no_unimplemented_target(self):
        import re
        root=Path(__file__).resolve().parents[1]
        data=json.loads((root/'docs/dashboard-interface-coverage.json').read_text())
        self.assertEqual(len(data['routes']),45)
        names={t.name for t in asyncio.run(mcp.list_tools())}
        for route in data['routes']:
            targets=re.split(r'\s*[+/]\s*',route['mcp_operation'])
            for target in targets:
                self.assertTrue(target in names or target in api.ROUTES,target)
        self.assertIn('sdk_idp_refresh_token_write',names)
