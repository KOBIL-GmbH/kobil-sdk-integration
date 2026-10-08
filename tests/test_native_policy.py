import unittest
from kobil_sdk_integration.native_policy import preflight

class API:
    def __init__(self, alias=None, missing=False):
        self.alias=alias;self.missing=missing;self.calls=[]
    def call(self, method, path, params=None):
        self.calls.append((method,path))
        assert method=='GET'
        if path=='/clients':
            if self.missing:return []
            return [{'clientId':params['clientId'],'enabled':True,'standardFlowEnabled':True,
                     'authenticationFlowBindingOverrides':{'browser':params['clientId']}}]
        return {'alias':self.alias or ('BDDK Enrollment' if path.endswith('BDDKEnrollment') else 'BDDK Login')}

class NativePolicyTests(unittest.TestCase):
    def run_check(self, api=None, **changes):
        args=dict(path='kssidp',activation_client='BDDKEnrollment',login_client='BDDKLogin',
                  use_token_based_login=True,ast_server_backend='maverick',login_header='X-KOBIL-ASTUSERID')
        args.update(changes)
        return preflight(api or API(),**args)
    def test_valid_native_bindings_read_only_not_runtime_acceptance(self):
        api=API();r=self.run_check(api)
        self.assertEqual(r['status'],'configuration_checked');self.assertFalse(r['runtime_verified'])
        self.assertEqual(len(api.calls),4)
        self.assertIn('certificate-chain coverage are not verified here',r['limits'])
    def test_incident_client_names_cannot_be_reused(self):
        api=API();r=self.run_check(api,login_client='AK539SdkValidationLogin')
        self.assertEqual(r['status'],'blocked');self.assertEqual(api.calls,[])
    def test_even_correct_client_name_cannot_hide_superapp_binding(self):
        self.assertEqual(self.run_check(API(alias='SuperApp Login V2'))['status'],'blocked')
    def test_missing_client_blocks(self):
        self.assertEqual(self.run_check(API(missing=True))['status'],'blocked')
    def test_invalid_config_and_header_block(self):
        for change in [dict(use_token_based_login=False),dict(login_header='userId'),dict(ast_server_backend='ssms')]:
            self.assertEqual(self.run_check(**change)['status'],'blocked')
    def test_webview_requires_explicit_clients_and_rejects_superapp(self):
        self.assertEqual(self.run_check(path='kstrustedwebview',login_client='')['status'],'blocked')
        self.assertEqual(self.run_check(API(alias='SuperApp Login V2'),path='kstrustedwebview')['status'],'blocked')
        self.assertEqual(self.run_check(API(alias='Customer Trusted WebView'),path='kstrustedwebview')['status'],'configuration_checked')

    def test_webview_preserves_themed_clients_and_reports_presentation_metadata(self):
        class ThemedAPI(API):
            def call(self, method, path, params=None):
                result=super().call(method,path,params)
                if path=='/clients':
                    result[0]['attributes']={'login_theme':'customer-mobile'}
                    result[0]['redirectUris']=['https://kobil/OpenIdRedirectUri']
                return result
        api=ThemedAPI(alias='Customer Trusted WebView')
        result=self.run_check(api,path='kstrustedwebview',activation_client='StyledEnrollment',login_client='StyledLogin')
        self.assertEqual(result['status'],'configuration_checked')
        self.assertEqual([b['client_id'] for b in result['bindings']],['StyledEnrollment','StyledLogin'])
        for binding in result['bindings']:
            self.assertEqual(binding['login_theme_override'],'customer-mobile')
            self.assertEqual(binding['theme_source'],'client_override')
            self.assertEqual(binding['redirect_uris'],['https://kobil/OpenIdRedirectUri'])
        self.assertFalse(result['runtime_verified'])
        self.assertTrue(all(method=='GET' for method,_ in api.calls))

    def test_absent_theme_override_does_not_invent_effective_theme(self):
        result=self.run_check()
        for binding in result['bindings']:
            self.assertIsNone(binding['login_theme_override'])
            self.assertEqual(binding['theme_source'],'realm_default_not_checked')

class ThemeWarningTests(unittest.TestCase):
    """2026-10-08 Xcode run: BDDK* clients carry the plain kobil-lite theme; the themed copies exist."""
    def make(self, theme):
        class API2(API):
            def call(self, method, path, params=None):
                result=super().call(method,path,params)
                if path=='/clients' and theme is not None:
                    result[0]['attributes']={'login_theme':theme}
                return result
        return API2(alias='Customer Trusted WebView')
    def run_webview(self, theme, **changes):
        args=dict(path='kstrustedwebview',activation_client='BDDKEnrollment',login_client='BDDKLogin',
                  use_token_based_login=True,ast_server_backend='maverick',login_header='X-KOBIL-ASTUSERID')
        args.update(changes)
        return preflight(self.make(theme),**args)
    def test_plain_theme_is_reported_as_warning_not_block(self):
        r=self.run_webview('kobil-lite')
        self.assertEqual(r['status'],'configuration_checked')
        self.assertTrue(any('kobil-lite' in w and 'kobil-mobile' in w for w in r['warnings']))
        self.assertTrue(all(b['theme_warning'] for b in r['bindings']))
    def test_mobile_theme_has_no_warning(self):
        r=self.run_webview('kobil-mobile')
        self.assertEqual(r['warnings'],[])
        self.assertTrue(all(b['theme_warning'] is None for b in r['bindings']))
    def test_webview_policy_recommends_the_themed_copies(self):
        from kobil_sdk_integration.native_policy import POLICY
        rec=POLICY['kstrustedwebview']['recommended_clients']
        self.assertEqual((rec['activation_client'],rec['login_client']),('KobilMobileEnrollment','KobilMobileLogin'))
        self.assertIn('kobil-lite',POLICY['kstrustedwebview']['client_selection'])
    def test_native_kssidp_path_has_no_theme_warning(self):
        api=self.make('kobil-lite'); api.alias=None
        r=preflight(api,path='kssidp',activation_client='BDDKEnrollment',login_client='BDDKLogin',
                    use_token_based_login=True,ast_server_backend='maverick',login_header='X-KOBIL-ASTUSERID')
        self.assertEqual(r['status'],'configuration_checked'); self.assertEqual(r['warnings'],[])
