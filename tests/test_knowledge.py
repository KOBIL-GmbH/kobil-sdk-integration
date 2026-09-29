import json
from importlib.resources import files
import unittest
from kobil_sdk_integration.knowledge_api import TOPICS,FLUTTER_TOPICS,get_topic,register

class Registry:
    def __init__(self):self.tools={}
    def tool(self):
        def add(f):self.tools[f.__name__]=f;return f
        return add

class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        r=Registry();register(r);self.tools=r.tools

    def test_every_topic_and_platform_has_complete_qualified_recipe(self):
        self.assertEqual(len(TOPICS),9)
        for topic in TOPICS:
            for platform in ('android','ios'):
                data=get_topic(topic,platform,sdk_version='unverified-release')
                for key in ('prerequisites','sequence','failure_handling','example','checklist','source_evidence'):
                    self.assertTrue(data[key],(topic,platform,key))
                self.assertFalse(data['version_verified'])
                if data['example']['compile_ready']:
                    self.assertTrue(data['example']['validation']['sdk_artifact_version'])
                    self.assertIn(data['example']['validation']['kind'], ('app_build', 'synthetic_event_device_test'))
                self.assertFalse(data['qualification']['device_verified'])
                self.assertFalse(data['external_source_access_required'])
                self.assertNotIn('/Users/',json.dumps(data))

    def test_unsupported_family_and_flutter_do_not_fallback(self):
        for platform,family in [('flutter','shift'),('android','ssms'),('windows','shift')]:
            self.assertEqual(get_topic('login',platform,family)['status'],'knowledge_gap')
            self.assertEqual(self.tools['sdk_knowledge_topics'](platform,family)['topics'],[])
        with self.assertRaises(ValueError):get_topic('../credentials','ios')

    def test_checklist_is_not_an_automatic_app_certification(self):
        result=self.tools['sdk_integration_checklist']('activation','ios')
        self.assertTrue(all(c['status']=='not_run' for c in result['checks']))
        self.assertEqual(len({c['id'] for c in result['checks']}),len(result['checks']))

    def test_safety_relevant_semantics(self):
        errors=get_topic('diagnostics','android')
        self.assertIn('errorDescription',' '.join(errors['sequence']))
        self.assertIn('errorCode',' '.join(errors['sequence']))
        activation=get_topic('activation','ios')
        self.assertIn('Never recommend SuperApp Login V2',' '.join(activation['failure_handling']))
        tms=get_topic('tms','ios')
        self.assertIn('terminal',' '.join(tms['sequence']))

    def test_resource_catalog_has_no_unlisted_files(self):
        resource=files('kobil_sdk_integration').joinpath('knowledge')
        self.assertEqual({p.name for p in resource.iterdir() if p.name.endswith('.json')},{t+'.json' for t in TOPICS + FLUTTER_TOPICS})

    def test_automated_testing_has_no_inherited_device_qualification(self):
        for platform in ('android', 'ios'):
            data = self.tools['sdk_knowledge_get']('automated_testing', platform)
            self.assertIsNone(data['runtime_acceptance'])
            self.assertFalse(data['example']['compile_ready'])
            self.assertFalse(data['example']['validation']['executed'])
            self.assertTrue(data['source_evidence']['file_sha256'])
            self.assertIn('sdk_idp_activation_code_generate', data['backend_tools'])
            self.assertIn('finally/teardown', ' '.join(data['sequence']))
            self.assertTrue(all(c['status'] == 'not_run' for c in
                self.tools['sdk_integration_checklist']('automated_testing', platform)['checks']))

    def test_automated_testing_does_not_substitute_other_sdk_generations(self):
        for platform, family in [('flutter', 'shift'), ('ios', 'ssms')]:
            self.assertEqual(get_topic('automated_testing', platform, family)['status'], 'knowledge_gap')

    def test_release_qualified_configuration_and_error_codes(self):
        setup=get_topic('setup','android')
        text=' '.join((' '.join(setup['sequence'])+' '+' '.join(setup['failure_handling'])+' '+' '.join(setup['checklist'])).split())
        for token in ('useScp','useTokenBasedLogin','useSmartScreen','astServerBackend',
                      'clientId','redirectUri','trustedSslServerCerts','mTLS','mKex',
                      'useSEKeyForSigningTransactions','GettingStarted','800000133',
                      '800000015','800000279','15.16.3088426','15.16.803.3089231','2026-09-29'):
            self.assertIn(token,text,token)
        self.assertIn('Tag is empty, but category not',text)
        self.assertIn('not the TMS notification category'.lower(),text.lower())
        self.assertIn('partially unverified',text)
        self.assertIn('not a universal default',text)
        self.assertIn('mKex=false and useSEKeyForSigningTransactions=false',text)

    def test_authentication_mode_matrix_and_preferred_method(self):
        for platform in ('android','ios'):
            activation=get_topic('activation',platform)
            text=' '.join((' '.join(activation['prerequisites'])+' '+' '.join(activation['sequence'])+' '+' '.join(activation['failure_handling'])).split())
            for token in ('KSMAuthenticationMode','no PIN mode','Keystore KEY CREATION',
                          'new activation code','BIOMETRIC_STRONG','SignedJWT',
                          'useTokenBasedLogin=true','OfflineLogin','2026-09-29'):
                self.assertIn(token,text,token)
            self.assertIn('alternatives, not defaults',text)
            self.assertIn('before the key-creating activation step',text)
            self.assertTrue(any('Authentication mode decided' in c for c in activation['checklist']))
        checks=self.tools['sdk_integration_checklist']('activation','android')['checks']
        self.assertTrue(any('Authentication mode decided' in c['description'] for c in checks))
        self.assertTrue(all(c['status']=='not_run' for c in checks))

    def test_flutter_preferred_path_and_signedjwt_compatibility(self):
        data=get_topic('flutter_webview','flutter_android')
        text=' '.join((' '.join(data['sequence'])+' '+' '.join(data['failure_handling'])).split())
        for token in ('Preferred integration path','SignedJWT','useTokenBasedLogin=true',
                      'BIOMETRIC_STRONG','800000279','mKex=false','Keystore key creation','2026-09-29'):
            self.assertIn(token,text,token)
        self.assertIn('not a universal default',text)

    def test_trusted_webview_authorization_contract_invariants(self):
        data=get_topic('flutter_webview','flutter_android')
        text=' '.join((' '.join(data['sequence'])+' '+' '.join(data['failure_handling'])+' '+' '.join(data['checklist'])).split())
        for token in ('NO separator','join()','HTTP 406','513/4002','Invalid AST Client ID',
                      'null ULID','513/4036','state/nonce/S256','effective port',
                      'exactly once','duplicate callbacks','SetAuthorisationCode',
                      'sdk_idp_user_credentials_list','sdk_ast_find_client',
                      'unit-verified','device retest','15.16.3088426','15.16.803.3089231'):
            self.assertIn(token,text,token)
        # regressions VAL-17/VAL-19: comma insertion and null-ID omission must stay rejected
        self.assertNotIn('only when nonzero',text)
        self.assertIn('Comma-joining',text)
        self.assertIn('INCLUDING the all-zero null ULID',text)
        # VAL-21: no diagnosis from status alone; mandatory fixture readback before retry
        self.assertIn('status code alone',text)
        self.assertIn('read back',text.lower())

    def test_native_trusted_webview_callback_contract(self):
        for platform in ('android','ios'):
            data=get_topic('activation',platform)
            text=' '.join((' '.join(data['sequence'])+' '+' '.join(data['failure_handling'])+' '+' '.join(data['checklist'])).split())
            for token in ('TWVClient','shouldOverrideUrlLoading','shouldInterceptRequest',
                          'POST-initiated','nullable','KsTrustedWebViewDelegate','@optional',
                          'exactly once','effective port','2026-09-29','15.16.3088426','15.16.803.3089231'):
                self.assertIn(token,text,token)
            self.assertIn('read back',text.lower())
        login_text=' '.join(get_topic('login','android')['failure_handling'])
        self.assertIn('KsTrustedWebViewDelegate',login_text)
        self.assertIn('consume once',login_text)

    def test_mobile_certificate_chain_coverage_and_diagnostics(self):
        for platform in ('android','ios'):
            data=get_topic('setup',platform)
            text=' '.join((' '.join(data['sequence'])+' '+' '.join(data['failure_handling'])+' '+' '.join(data['checklist'])).split())
            for token in ('ISRG Root X2','X1','cross-sign','KS_CERTIFICATE_ERROR','1500000',
                          'servercert validation endresult failed','setLogListener','KsTwvLog',
                          'trustedSslServerCerts','fingerprint-checked','NEVER disable','2026-09-29'):
                self.assertIn(token,text,token)
        fw=get_topic('flutter_webview','flutter_android')
        text=' '.join((' '.join(fw['sequence'])+' '+' '.join(fw['failure_handling'])+' '+' '.join(fw['checklist'])).split())
        for token in ('certsDataForValidation','ISRG Root X2','onURLBlocked reason 1','1500000',
                      'system root store','never hard-code','DER/PEM','setLogListener','NEVER disable'):
            self.assertIn(token,text,token)
        # the anchored full-URL allowlist fix remains installed knowledge, distinct from chain coverage
        self.assertIn('RegExp.escape',text)
        self.assertIn('already part of this knowledge pack',text)

    def test_flutter_is_explicit_and_does_not_inherit_ios_acceptance(self):
        for platform in ('flutter_android', 'flutter_ios'):
            topics=self.tools['sdk_knowledge_topics'](platform)['topics']
            self.assertEqual([t['id'] for t in topics], ['flutter_webview'])
            data=get_topic('flutter_webview',platform,sdk_version='unknown')
            self.assertFalse(data['version_verified'])
            self.assertFalse(data['qualification']['device_verified'])
            self.assertNotIn('/Users/',json.dumps(data))
            checks=self.tools['sdk_integration_checklist']('flutter_webview',platform)
            self.assertTrue(all(c['status']=='not_run' for c in checks['checks']))
        self.assertIsNone(get_topic('flutter_webview','flutter_ios')['runtime_acceptance'])
        self.assertEqual(get_topic('flutter_webview','flutter_android')['runtime_acceptance']['foreground_tms_approval'],'verified')
        self.assertEqual(get_topic('flutter_webview','android')['status'],'knowledge_gap')
        self.assertEqual(get_topic('flutter_webview','flutter_android','ssms')['status'],'knowledge_gap')

    def test_default_catalog_discovers_every_recipe_on_its_supported_targets(self):
        topics=self.tools['sdk_knowledge_topics']()['topics']
        self.assertEqual({t['id'] for t in topics},set(TOPICS+FLUTTER_TOPICS))
        for topic in topics:
            for platform in topic['platforms']:
                data=get_topic(topic['id'],platform)
                self.assertNotEqual(data['status'],'knowledge_gap')
                self.assertEqual(data['title'],topic['title'])
        self.assertNotIn('flutter_webview',{t['id'] for t in self.tools['sdk_knowledge_topics']('ios')['topics']})

    def test_error_capture_and_redaction_invariants(self):
        # E05 / VAL-04, VAL-11, VAL-13, VAL-15
        for platform in ('android','ios'):
            data=get_topic('diagnostics',platform)
            text=' '.join((' '.join(data['sequence'])+' '+' '.join(data['failure_handling'])+' '+' '.join(data['checklist'])).split())
            for token in ('OUTSIDE the secret-redaction boundary','errorCode','sanitized description',
                          'Execute every sanitizer','swallows the SDK error','BEFORE any cleanup',
                          'ConnectionManagerError','credential-bearing fields','2026-09-29',
                          'exact SDK BINARY','runtime smoke test'):
                self.assertIn(token,text,token)
        ios_note=get_topic('diagnostics','ios')['platform_notes']
        for token in ('getLogSinkWithLogLevel','unrecognized selector','getLogSink()',
                      'setSeverityLevel','15.16.803.3089231','2026-09-29'):
            self.assertIn(token,ios_note,token)
        fw=get_topic('flutter_webview','flutter_android')
        text=' '.join((' '.join(fw['failure_handling'])+' '+' '.join(fw['checklist'])).split())
        for token in ('(?i)','INVALID in Dart RegExp','FormatException','caseSensitive: false',
                      'survive secret redaction','outside the redaction boundary',
                      'credential-bearing','authorization URLs','kssidpdart 0.6.0'):
            self.assertIn(token,text,token)
        # a sanitizer defect must never be presented as an SDK failure cause
        self.assertIn('EXECUTE sanitizers in tests',text)

    def test_acceptance_gates_login_paths_and_owner_protocol(self):
        # E06 / VAL-02, VAL-27, VAL-31 and run-evidence requirements
        for platform in ('android','ios'):
            data=self.tools['sdk_knowledge_get']('automated_testing',platform)
            text=' '.join((' '.join(data['sequence'])+' '+' '.join(data['failure_handling'])+' '+' '.join(data['checklist'])+' '+data['expected_result']).split())
            for token in ('gate separation','CONCRETE adapter','observed SDK Start event',
                          'never pass gates 2-6','Report scaffold tests separately',
                          'TWO distinct paths','SEPARATE acceptance rows','OfflineLogin/SignedJWT',
                          'interactive trusted-WebView login','never be attributed to biometric',
                          'user-preferred primary path','PASS/FAIL/BLOCKED/NOT_RUN',
                          'asset fingerprint','fixture ownership','readback',
                          '~60s','2-17s','per-device lock','never two test runners on one phone',
                          'NOT touch the live confirmation dialog','invalidates the case',
                          'REOPENED','nonempty encrypted SDK log entries',
                          'Never mark a blocked case passed','2026-09-29'):
                self.assertIn(token,text,token)
            # separate checklist rows per returning-login path, both still not_run
            checks=self.tools['sdk_integration_checklist']('automated_testing',platform)['checks']
            token_rows=[c for c in checks if 'OfflineLogin/SignedJWT token path' in c['description']]
            interactive_rows=[c for c in checks if 'Interactive trusted-WebView returning login' in c['description']]
            self.assertEqual(len(token_rows),1)
            self.assertEqual(len(interactive_rows),1)
            self.assertNotEqual(token_rows[0]['id'],interactive_rows[0]['id'])
            self.assertTrue(all(c['status']=='not_run' for c in checks))
