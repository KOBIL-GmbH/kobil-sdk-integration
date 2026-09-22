import json
from importlib.resources import files
import unittest
from kobil_sdk_integration.knowledge_api import TOPICS,get_topic,register

class Registry:
    def __init__(self):self.tools={}
    def tool(self):
        def add(f):self.tools[f.__name__]=f;return f
        return add

class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        r=Registry();register(r);self.tools=r.tools

    def test_every_topic_and_platform_has_complete_qualified_recipe(self):
        self.assertEqual(len(TOPICS),8)
        for topic in TOPICS:
            for platform in ('android','ios'):
                data=get_topic(topic,platform,sdk_version='unverified-release')
                for key in ('prerequisites','sequence','failure_handling','example','checklist','source_evidence'):
                    self.assertTrue(data[key],(topic,platform,key))
                self.assertFalse(data['version_verified'])
                if data['example']['compile_ready']:
                    self.assertTrue(data['example']['validation']['sdk_artifact_version'])
                    self.assertIn(data['example']['validation']['kind'], ('swift_typecheck', 'synthetic_event_device_test'))
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
        self.assertEqual({p.name for p in resource.iterdir() if p.name.endswith('.json')},{t+'.json' for t in TOPICS})
