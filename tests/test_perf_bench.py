"""Performance benchmark: statistics, budget check and a real offline run against generous budgets."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('KOBIL_SDK_SENTRY_ENVIRONMENT', 'tests')
SCRIPT = Path(__file__).resolve().parent.parent / 'scripts' / 'perf_bench.py'
spec = importlib.util.spec_from_file_location('perf_bench', SCRIPT)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


class StatisticsTests(unittest.TestCase):
    def test_percentiles_use_nearest_rank(self):
        values = [0.001 * n for n in range(1, 11)]
        row = bench.summarize({'x': values})['x']
        self.assertEqual((row['runs'], row['min_ms'], row['p50_ms'], row['p95_ms'], row['max_ms']), (10, 1.0, 5.0, 10.0, 10.0))

    def test_budget_default_and_per_tool(self):
        summary = {'a': {'p95_ms': 300.0}, 'b': {'p95_ms': 90.0}, 'c': {'p95_ms': 900.0}}
        problems = bench.check_budgets(summary, {'default_ms': 250, 'tools': {'c': 1000, 'b': 50}})
        self.assertEqual(sorted(p.split(':')[0] for p in problems), ['a', 'b'])

    def test_no_budget_no_problem(self):
        self.assertEqual(bench.check_budgets({'a': {'p95_ms': 5000.0}}, {}), [])

    def test_render_has_one_line_per_step(self):
        summary = bench.summarize({'a': [0.001], 'b': [0.002]})
        self.assertEqual(len(bench.render(summary, {'a': 10}).splitlines()), 3)


class RealRunTests(unittest.TestCase):
    def test_offline_run_stays_inside_the_shipped_budgets_and_writes_a_report(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'report.json'
            code = bench.main(['--runs', '3', '--no-sentry', '--out', str(out)])
            report = json.loads(out.read_text())
        self.assertEqual(code, 0)
        for step in ('server_start', 'list_tools', 'sdk_runtime_info', 'sdk_knowledge_bundle'):
            self.assertIn(step, report['summary'])
        self.assertGreater(report['result_bytes']['sdk_knowledge_bundle'], 10000)


if __name__ == '__main__':
    unittest.main()
