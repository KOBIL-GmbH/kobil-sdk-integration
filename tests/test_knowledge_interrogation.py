"""Question isolation, semantic review integrity and registered knowledge retrieval.

These tests validate the interview harness, not a model's reasoning quality.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest

from kobil_sdk_integration import knowledge_api

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('skill_blindtest', ROOT / 'scripts/skill_blindtest.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class InterviewTests(unittest.TestCase):
    def setUp(self):
        self.scenarios = runner.load_scenarios()

    def test_scenarios_are_unique_and_have_reviewable_expectations(self):
        ids = [s['id'] for s in self.scenarios]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 46)
        for sc in self.scenarios:
            with self.subTest(scenario=sc['id']):
                self.assertTrue(sc['prompt'].strip())
                self.assertGreater(len(sc['review_criteria'][0]), 90)
                self.assertNotIn('Verify the decision, cited shipped knowledge', sc['review_criteria'][0])
                self.assertTrue(sc['qualification'])
                for source in sc['source_paths']:
                    self.assertTrue((ROOT / source).is_file(), source)
                self.assertTrue(sc.get('expect_all') or sc.get('expect_any'))

    def test_reader_packets_never_contain_answer_key(self):
        for retrieval in (True, False):
            packet = runner.reader_packet(self.scenarios, retrieval)
            for item in packet['scenarios']:
                self.assertEqual(set(item), {'id', 'prompt'})
            self.assertEqual(len(packet['scenarios']), len(self.scenarios))
        self.assertIn('No external source checkouts', runner.reader_packet([], True)['rules'])

    def test_packet_cli_does_not_leak_rubrics(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(runner.main(['--packet', 'retrieval']), 0)
        packet = json.loads(out.getvalue())
        self.assertNotIn('review_criteria', out.getvalue())
        self.assertEqual(packet['mode'], 'retrieval')

    def test_semantic_reviews_are_bound_to_actual_answer(self):
        scenarios = self.scenarios[:1]
        answer = 'A reviewed answer with a decision and cited evidence.'
        answers = {scenarios[0]['id']: answer}
        review = {'answer_sha256': hashlib.sha256(answer.encode()).hexdigest(),
                  'scenario_sha256': runner.scenario_digest(scenarios[0]),
                  'candidate_sha256': runner.candidate_digest(),
                  'verdict': 'pass', 'reviewer': 'independent reviewer',
                  'rationale': 'Verified against scenario criteria',
                  'source_evidence': 'references/signing-policy.md'}
        reviews = {scenarios[0]['id']: review}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.review_answers(answers, reviews, scenarios), 0)
            self.assertEqual(runner.review_answers({}, reviews, scenarios), 1)
            changed_scenario = dict(scenarios[0], prompt='Changed requirement')
            self.assertEqual(runner.review_answers(answers, reviews, [changed_scenario]), 1)
            self.assertEqual(runner.review_answers({scenarios[0]['id']: 'changed'}, reviews, scenarios), 1)
            for field in ('reviewer', 'rationale', 'source_evidence', 'verdict', 'scenario_sha256', 'candidate_sha256'):
                bad = dict(review, **{field: ''})
                self.assertEqual(runner.review_answers(answers, {scenarios[0]['id']: bad}, scenarios), 1)

    def test_keyword_success_is_not_semantic_acceptance(self):
        scenarios = [{'id': 'case', 'expect_all': ['ALLOW_VIRTUAL_SMART_CARD']}]
        answers = {'case': 'Never use ALLOW_VIRTUAL_SMART_CARD; disable all checks.'}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.judge(answers, scenarios), 0)
            self.assertEqual(runner.review_answers(answers, {}, scenarios), 1)


class Registry:
    def __init__(self): self.tools = {}
    def tool(self):
        def add(fn):
            self.tools[fn.__name__] = fn
            return fn
        return add


class KnowledgeRetrievalTests(unittest.TestCase):
    def setUp(self):
        registry = Registry()
        knowledge_api.register(registry)
        self.tools = registry.tools

    def test_discover_then_retrieve_every_advertised_target_topic(self):
        for platform in ('android', 'ios', 'flutter_android', 'flutter_ios'):
            catalog = self.tools['sdk_knowledge_topics'](platform=platform)
            self.assertTrue(catalog['topics'])
            for topic in catalog['topics']:
                with self.subTest(platform=platform, topic=topic['id']):
                    result = self.tools['sdk_knowledge_get'](topic=topic['id'], platform=platform)
                    self.assertNotEqual(result['status'], 'knowledge_gap')
                    self.assertFalse(result['external_source_access_required'])

    def test_native_bundle_does_not_certify_unknown_delivery(self):
        result = self.tools['sdk_knowledge_bundle'](platform='ios', sdk_version='unqualified-version')
        self.assertFalse(result['version_verified'])
        self.assertEqual(result['order'], ['setup', 'activation', 'login', 'tms', 'logs', 'diagnostics'])
        self.assertFalse(result['external_source_access_required'])

    def test_flutter_reader_must_discover_its_own_recipe(self):
        self.assertEqual(self.tools['sdk_knowledge_bundle'](platform='flutter_ios')['status'], 'knowledge_gap')
        catalog = self.tools['sdk_knowledge_topics'](platform='flutter_ios')
        self.assertEqual([t['id'] for t in catalog['topics']], ['flutter_webview'])

    def test_unknown_target_and_family_never_inherit_mobile_proof(self):
        for args in ({'platform': 'windows'}, {'platform': 'android', 'sdk_family': 'ssms'}):
            self.assertEqual(self.tools['sdk_knowledge_topics'](**args)['status'], 'knowledge_gap')


if __name__ == '__main__':
    unittest.main()
