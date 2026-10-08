"""Optional Sentry error reporting: off by default, scrubbed, never carries tool arguments or secrets."""
import asyncio
import os
import re
import sys
import types
import unittest
from unittest import mock

from kobil_sdk_integration import telemetry


try:
    import sentry_sdk.envelope as REAL_ENVELOPE
except ImportError:
    REAL_ENVELOPE = None
_TMP = None


def setUpModule():
    global _TMP
    import os
    import tempfile
    _TMP = tempfile.TemporaryDirectory()
    os.environ['KOBIL_SDK_HOME'] = _TMP.name


def tearDownModule():
    import os
    os.environ.pop('KOBIL_SDK_HOME', None)
    _TMP.cleanup()


def fake_sentry():
    calls = {'init': None, 'captured': [], 'tags': []}
    mod = types.ModuleType('sentry_sdk')
    mod.init = lambda **kw: calls.__setitem__('init', kw)
    mod.capture_exception = lambda e=None: calls['captured'].append(e)
    mod.set_tag = lambda k, v: calls['tags'].append((k, v))
    mod.add_breadcrumb = lambda **kw: None
    mod.capture_event = lambda event: 'evt0'

    class Txn:
        def __init__(self, kw):
            self.kw, self.data, self.status = kw, {}, None
            calls.setdefault('txns', []).append(self)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            if exc[0] is not None and self.status is None:
                self.status = 'internal_error'
            return False

        def set_data(self, key, value):
            self.data[key] = value

        def set_status(self, status):
            self.status = status

    mod.start_transaction = lambda **kw: Txn(kw)
    sent = calls.setdefault('envelopes', [])
    transport = types.SimpleNamespace(capture_envelope=lambda env: sent.append(env))
    mod.get_client = lambda: types.SimpleNamespace(transport=transport, options={'environment': 'test', 'release': '0'})
    return mod, calls


class InitTests(unittest.TestCase):
    def test_disabled_without_dsn(self):
        mod, calls = fake_sentry()
        with mock.patch.dict(sys.modules, {'sentry_sdk': mod}):
            self.assertEqual(telemetry.init({}), 'disabled')
        self.assertIsNone(calls['init'])

    def test_unavailable_when_package_missing(self):
        with mock.patch.dict(sys.modules, {'sentry_sdk': None}):
            self.assertEqual(telemetry.init({'KOBIL_SDK_SENTRY_DSN': 'https://k@example.invalid/1'}), 'unavailable')

    def test_enabled_uses_safe_options(self):
        mod, calls = fake_sentry()
        with mock.patch.dict(sys.modules, {'sentry_sdk': mod}):
            self.assertEqual(telemetry.init({'KOBIL_SDK_SENTRY_DSN': 'https://k@example.invalid/1'}), 'enabled')
        kw = calls['init']
        self.assertEqual(kw['dsn'], 'https://k@example.invalid/1')
        self.assertFalse(kw['send_default_pii'])
        self.assertFalse(kw['include_local_variables'])
        self.assertEqual(kw['traces_sample_rate'], 1.0)
        self.assertIs(kw['before_send_transaction'], telemetry.scrub_transaction)
        self.assertEqual(kw['server_name'], '')
        self.assertIs(kw['before_send'], telemetry.scrub)
        self.assertIsNone(kw['before_breadcrumb']({'category': 'httpx', 'message': 'GET https://h/x'}, {}))
        crumb = {'category': 'kobil.tool', 'message': 'call_end'}
        self.assertIs(kw['before_breadcrumb'](crumb, {}), crumb)
        self.assertEqual(kw['max_breadcrumbs'], 200)


class ScrubTests(unittest.TestCase):
    def event(self):
        return {
            'user': {'id': 'x'}, 'request': {'url': 'u'}, 'extra': {'a': 1}, 'server_name': 'host',
            'breadcrumbs': {'values': [{'category': 'httpx', 'message': 'GET https://h'}, {'category': 'kobil.tool', 'message': 'call_end', 'data': {'tool': 'sdk_x'}}]}, 'modules': {'a': '1'},
            'exception': {'values': [{'type': 'ValueError', 'value': 'PROJECT_NOT_SELECTED: /path/to/x',
                                      'stacktrace': {'frames': [{'abs_path': '/path/to/p/src/kobil_sdk_integration/server.py',
                                                                 'filename': 'server.py', 'vars': {'password': 'p'},
                                                                 'pre_context': ['a'], 'context_line': 'b', 'post_context': ['c']}]}}]},
        }

    def test_removes_personal_and_free_text_fields(self):
        out = telemetry.scrub(self.event(), {})
        for key in ('user', 'request', 'extra', 'server_name', 'modules'):
            self.assertNotIn(key, out)
        self.assertEqual([c['category'] for c in out['breadcrumbs']['values']], ['kobil.tool'])
        frame = out['exception']['values'][0]['stacktrace']['frames'][0]
        self.assertNotIn('vars', frame)
        self.assertNotIn('pre_context', frame)
        self.assertNotIn('context_line', frame)
        self.assertNotIn('post_context', frame)
        self.assertEqual(frame['abs_path'], 'kobil_sdk_integration/server.py')

    def test_message_keeps_only_error_code(self):
        out = telemetry.scrub(self.event(), {})
        self.assertEqual(out['exception']['values'][0]['value'], 'PROJECT_NOT_SELECTED')

    def test_free_text_message_is_redacted(self):
        ev = self.event()
        ev['exception']['values'][0]['value'] = 'token abc.def failed for /Users/someone'
        out = telemetry.scrub(ev, {})
        self.assertEqual(out['exception']['values'][0]['value'], '[redacted]')


class ToolHookTests(unittest.TestCase):
    def test_failed_tool_is_captured_with_name_only(self):
        mod, calls = fake_sentry()

        class Manager:
            async def call_tool(self, name, arguments, context=None, convert_result=False):
                raise RuntimeError('boom')

        class Server:
            _tool_manager = Manager()

        with mock.patch.dict(sys.modules, {'sentry_sdk': mod}):
            telemetry.init({'KOBIL_SDK_SENTRY_DSN': 'https://k@example.invalid/1'})
            telemetry.install(Server)
            with self.assertRaises(RuntimeError):
                asyncio.run(Server._tool_manager.call_tool('sdk_x', {'password': 'secret-argument'}))
        self.assertEqual(len(calls['captured']), 1)
        self.assertIn(('tool', 'sdk_x'), calls['tags'])
        telemetry.reset()
        self.assertNotIn('secret-argument', repr(calls['tags']) + repr(calls['init']))

    def test_successful_tool_is_not_captured(self):
        mod, calls = fake_sentry()

        class Manager:
            async def call_tool(self, name, arguments, context=None, convert_result=False):
                return 'ok'

        class Server:
            _tool_manager = Manager()

        with mock.patch.dict(sys.modules, {'sentry_sdk': mod}):
            telemetry.install(Server)
            self.assertEqual(asyncio.run(Server._tool_manager.call_tool('sdk_x', {})), 'ok')
        self.assertEqual(calls['captured'], [])


class Base(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.dict('os.environ', {'KOBIL_SDK_HOME': self.tmp.name}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop('KOBIL_SDK_USAGE_LOG', None)
        telemetry.reset()

    def usage(self):
        import json
        path = telemetry.state_dir() / 'usage.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


class CrumbTests(Base):
    def test_safe_data_only_and_local_log_is_private(self):
        telemetry.crumb('tool', 'call_end', tool='sdk_x', ms=12, ok=True, path='/path/to/p', secret='abc def ghi', ids='a,b')
        record = self.usage()[0]
        self.assertEqual(record['category'], 'kobil.tool')
        self.assertEqual(record['data'], {'tool': 'sdk_x', 'ms': 12, 'ok': True, 'ids': 'a,b'})
        self.assertEqual((telemetry.state_dir() / 'usage.jsonl').stat().st_mode & 0o777, 0o600)

    def test_usage_log_can_be_disabled(self):
        with mock.patch.dict('os.environ', {'KOBIL_SDK_USAGE_LOG': '0'}):
            telemetry.crumb('tool', 'call_end', tool='sdk_x')
        self.assertEqual(self.usage(), [])

    def test_usage_log_rotates(self):
        path = telemetry.state_dir() / 'usage.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('x' * (telemetry.MAX_LOG_BYTES + 1))
        telemetry.crumb('tool', 'call_end', tool='sdk_x')
        self.assertTrue((telemetry.state_dir() / 'usage.jsonl.1').exists())
        self.assertEqual(len(self.usage()), 1)

    def test_breadcrumb_goes_to_sentry_when_enabled(self):
        mod, calls = fake_sentry()
        added = []
        mod.add_breadcrumb = lambda **kw: added.append(kw)
        with mock.patch.dict(sys.modules, {'sentry_sdk': mod}):
            telemetry.init({'KOBIL_SDK_SENTRY_DSN': 'https://k@example.invalid/1'})
            telemetry.crumb('tool', 'call_end', tool='sdk_x')
        self.assertEqual(added[0]['category'], 'kobil.tool')
        self.assertEqual(added[0]['data'], {'tool': 'sdk_x'})


class UsageHookTests(Base):
    def run_tool(self, behaviour):
        class Manager:
            async def call_tool(self, name, arguments, context=None, convert_result=False):
                return behaviour()

        class Server:
            _tool_manager = Manager()

        telemetry.install(Server)
        return Server

    def test_call_start_and_end_are_logged_without_values(self):
        server = self.run_tool(lambda: {'data': 'x' * 500})
        asyncio.run(server._tool_manager.call_tool('sdk_x', {'password': 'hunter2', 'host': 'h'}))
        records = self.usage()
        self.assertEqual([r['message'] for r in records], ['call_start', 'call_end'])
        end = records[1]['data']
        self.assertEqual(end['tool'], 'sdk_x')
        self.assertTrue(end['ok'])
        self.assertGreater(end['result_bytes'], 500)
        self.assertEqual(end['arg_keys'], 'host,password')
        self.assertNotIn('hunter2', repr(records))

    def test_failure_is_logged_with_type_and_code_only(self):
        def boom():
            raise ValueError('PROJECT_NOT_SELECTED: /path/to/x')
        server = self.run_tool(boom)
        with self.assertRaises(ValueError):
            asyncio.run(server._tool_manager.call_tool('sdk_x', {}))
        end = self.usage()[-1]['data']
        self.assertFalse(end['ok'])
        self.assertEqual(end['error_type'], 'ValueError')
        self.assertEqual(end['error_code'], 'PROJECT_NOT_SELECTED')
        self.assertNotIn('someone', repr(self.usage()))

    def test_unfinished_call_leaves_a_start_record(self):
        server = self.run_tool(lambda: 'ok')
        asyncio.run(server._tool_manager.call_tool('sdk_x', {}))
        self.assertEqual(self.usage()[0]['message'], 'call_start')


class PerformanceTests(Base):
    def server(self, behaviour):
        class Manager:
            async def call_tool(self, name, arguments, context=None, convert_result=False):
                return behaviour()

        class Server:
            _tool_manager = Manager()

        return Server

    def test_trace_rate_comes_from_the_environment(self):
        mod, calls = fake_sentry()
        with mock.patch.dict(sys.modules, {'sentry_sdk': mod}):
            telemetry.init({'KOBIL_SDK_SENTRY_DSN': 'https://k@example.invalid/1', 'KOBIL_SDK_SENTRY_TRACES': '0.25'})
        self.assertEqual(calls['init']['traces_sample_rate'], 0.25)

    def test_each_tool_call_is_one_transaction_with_claims(self):
        mod, calls = fake_sentry()
        server = self.server(lambda: {'x': 'y' * 100})
        with mock.patch.dict(sys.modules, {'sentry_sdk': mod}):
            telemetry.init({'KOBIL_SDK_SENTRY_DSN': 'https://k@example.invalid/1'})
            telemetry.install(server)
            asyncio.run(server._tool_manager.call_tool('sdk_x', {'password': 'hunter2'}))
        (txn,) = calls['txns']
        self.assertEqual(txn.kw['op'], 'mcp.tool')
        self.assertEqual(txn.kw['name'], 'tool sdk_x')
        self.assertEqual(txn.status, 'ok')
        self.assertGreater(txn.data['result_bytes'], 100)
        self.assertEqual(txn.data['arg_keys'], 'password')
        self.assertNotIn('hunter2', repr(txn.data) + repr(txn.kw))

    def test_failed_call_marks_the_transaction(self):
        mod, calls = fake_sentry()

        def boom():
            raise ValueError('PROJECT_NOT_SELECTED')
        server = self.server(boom)
        with mock.patch.dict(sys.modules, {'sentry_sdk': mod}):
            telemetry.init({'KOBIL_SDK_SENTRY_DSN': 'https://k@example.invalid/1'})
            telemetry.install(server)
            with self.assertRaises(ValueError):
                asyncio.run(server._tool_manager.call_tool('sdk_x', {}))
        self.assertEqual(calls['txns'][0].status, 'internal_error')

    def test_no_transaction_without_sentry(self):
        server = self.server(lambda: 1)
        telemetry.install(server)
        asyncio.run(server._tool_manager.call_tool('sdk_x', {}))
        self.assertEqual(self.usage()[-1]['data']['ok'], True)

    def test_timed_block_records_a_usage_record_and_a_transaction(self):
        mod, calls = fake_sentry()
        with mock.patch.dict(sys.modules, {'sentry_sdk': mod}):
            telemetry.init({'KOBIL_SDK_SENTRY_DSN': 'https://k@example.invalid/1'})
            with telemetry.timed('lifecycle', 'startup'):
                pass
        self.assertEqual(calls['txns'][0].kw['name'], 'lifecycle startup')
        end = self.usage()[-1]
        self.assertEqual((end['category'], end['message']), ('kobil.timing', 'lifecycle startup'))
        self.assertIn('ms', end['data'])

    def test_transaction_scrub_removes_hosts_and_personal_data(self):
        event = {'type': 'transaction', 'transaction': 'tool sdk_x', 'server_name': 'h', 'user': {'id': 1}, 'request': {'url': 'u'},
                 'extra': {'a': 1}, 'contexts': {'trace': {'trace_id': 't', 'op': 'mcp.tool'}, 'os': {'name': 'mac'}},
                 'breadcrumbs': {'values': [{'category': 'httpx', 'message': 'GET https://customer.example'}]},
                 'spans': [{'op': 'http.client', 'description': 'GET https://customer.example/auth/realms/x?code=1',
                            'data': {'url': 'https://customer.example', 'http.response.status_code': 200, 'http.request.method': 'GET', 'http.query': 'code=1'},
                            'tags': {'http.status_code': '200'}}]}
        out = telemetry.scrub_transaction(event, {})
        self.assertEqual(out['transaction'], 'tool sdk_x')
        for key in ('server_name', 'user', 'request', 'extra'):
            self.assertNotIn(key, out)
        self.assertEqual(out['contexts'], {'trace': {'trace_id': 't', 'op': 'mcp.tool'}})
        span = out['spans'][0]
        self.assertEqual(span['description'], 'http.client')
        self.assertEqual(span['data'], {'http.response.status_code': 200, 'http.request.method': 'GET'})
        self.assertNotIn('customer', repr(out))


class CommitTagTests(Base):
    def test_git_sha_of_a_checkout_is_a_short_hex_string(self):
        sha = telemetry.git_sha()
        self.assertTrue(sha is None or re.fullmatch(r'[0-9a-f]{7,12}', sha))

    def test_commit_is_tagged_on_init_when_known(self):
        mod, calls = fake_sentry()
        with mock.patch.dict(sys.modules, {'sentry_sdk': mod}), mock.patch.object(telemetry, 'git_sha', return_value='abc1234'):
            telemetry.init({'KOBIL_SDK_SENTRY_DSN': 'https://k@example.invalid/1'})
        self.assertIn(('commit', 'abc1234'), calls['tags'])

    def test_no_commit_tag_outside_a_checkout(self):
        mod, calls = fake_sentry()
        with mock.patch.dict(sys.modules, {'sentry_sdk': mod}), mock.patch.object(telemetry, 'git_sha', return_value=None):
            telemetry.init({'KOBIL_SDK_SENTRY_DSN': 'https://k@example.invalid/1'})
        self.assertNotIn('commit', [k for k, v in calls['tags']])


class RootCauseAndDsnFileTests(Base):
    def test_wrapped_tool_error_reports_the_root_cause(self):
        class Manager:
            async def call_tool(self, name, arguments, context=None, convert_result=False):
                try:
                    raise ValueError('PROJECT_NOT_SELECTED: /path/to/x')
                except ValueError as cause:
                    raise RuntimeError('Error executing tool') from cause

        class Server:
            _tool_manager = Manager()

        telemetry.install(Server)
        with self.assertRaises(RuntimeError):
            asyncio.run(Server._tool_manager.call_tool('sdk_x', {}))
        end = self.usage()[-1]['data']
        self.assertEqual((end['error_type'], end['error_code']), ('ValueError', 'PROJECT_NOT_SELECTED'))

    def test_dsn_is_read_from_the_private_file(self):
        mod, calls = fake_sentry()
        (telemetry.state_dir() / 'sentry-dsn').write_text('https://k@example.invalid/9\n')
        with mock.patch.dict(sys.modules, {'sentry_sdk': mod}):
            self.assertEqual(telemetry.init({}), 'enabled')
        self.assertEqual(calls['init']['dsn'], 'https://k@example.invalid/9')

    def test_disable_switch_beats_dsn_and_file(self):
        mod, calls = fake_sentry()
        (telemetry.state_dir() / 'sentry-dsn').write_text('https://k@example.invalid/9')
        with mock.patch.dict(sys.modules, {'sentry_sdk': mod}):
            self.assertEqual(telemetry.init({'KOBIL_SDK_SENTRY_DISABLE': '1', 'KOBIL_SDK_SENTRY_DSN': 'https://k@example.invalid/1'}), 'disabled')
        self.assertIsNone(calls['init'])

    def test_env_dsn_wins_over_file(self):
        mod, calls = fake_sentry()
        (telemetry.state_dir() / 'sentry-dsn').write_text('https://k@example.invalid/9')
        with mock.patch.dict(sys.modules, {'sentry_sdk': mod}):
            telemetry.init({'KOBIL_SDK_SENTRY_DSN': 'https://k@example.invalid/1'})
        self.assertEqual(calls['init']['dsn'], 'https://k@example.invalid/1')


class FeedbackTests(Base):
    def test_hint_after_enough_calls_once_per_day(self):
        self.assertIsNone(telemetry.feedback_hint())
        for _ in range(telemetry.FEEDBACK_AFTER_CALLS):
            telemetry.count_call()
        hint = telemetry.feedback_hint()
        self.assertIn('sdk_report_problem', hint['tool'])
        self.assertIsNone(telemetry.feedback_hint())

    def test_redact_removes_secret_shapes(self):
        text = 'token eyJhbGciOi.eyJzdWIi.abcdef Bearer abcdefghijklmnopqrstuvwx password=hunter2 code 12345678 mail reporter@example.com ok'
        out = telemetry.redact(text)
        for leaked in ('eyJhbGciOi', 'abcdefghijklmnopqrstuvwx', 'hunter2', '12345678'):
            self.assertNotIn(leaked, out)
        self.assertIn('ok', out)

    def feedback_payloads(self, calls):
        out = []
        for env in calls['envelopes']:
            for item in env.items:
                self.assertEqual(item.headers['type'], 'feedback')
                out.append(item.payload.json)
        return out

    @unittest.skipIf(REAL_ENVELOPE is None, 'sentry-sdk extra not installed')
    def test_report_saved_locally_and_sent_with_optional_contact(self):
        mod, calls = fake_sentry()
        events = []
        mod.capture_event = lambda event: events.append(event) or 'evt1'
        with mock.patch.dict(sys.modules, {'sentry_sdk': mod, 'sentry_sdk.envelope': REAL_ENVELOPE}):
            telemetry.init({'KOBIL_SDK_SENTRY_DSN': 'https://k@example.invalid/1'})
            telemetry.crumb('tool', 'call_end', tool='sdk_x')
            result = telemetry.report('hang', 'Xcode froze after password=hunter2', True, 'user@example.com')
        self.assertTrue(result['sent'])
        self.assertTrue(result['saved'])
        context = events[0]
        self.assertEqual(context['tags']['kobil_feedback'], '1')
        self.assertEqual(context['extra']['category'], 'hang')
        self.assertTrue(context['extra']['activity'])
        (payload,) = self.feedback_payloads(calls)
        feedback = payload['contexts']['feedback']
        self.assertEqual(feedback['contact_email'], 'user@example.com')
        self.assertEqual(feedback['source'], 'kobil-sdk-mcp')
        self.assertEqual(feedback['associated_event_id'], 'evt1')
        self.assertIn('Xcode froze', feedback['message'])
        self.assertNotIn('hunter2', repr(events) + repr(payload))
        self.assertEqual(len(list((telemetry.state_dir() / 'reports').glob('*.json'))), 1)

    @unittest.skipIf(REAL_ENVELOPE is None, 'sentry-sdk extra not installed')
    def test_report_without_contact_has_no_user_and_bad_mail_is_dropped(self):
        mod, calls = fake_sentry()
        events = []
        mod.capture_event = lambda event: events.append(event) or 'evt2'
        with mock.patch.dict(sys.modules, {'sentry_sdk': mod, 'sentry_sdk.envelope': REAL_ENVELOPE}):
            telemetry.init({'KOBIL_SDK_SENTRY_DSN': 'https://k@example.invalid/1'})
            telemetry.report('bug', 'text', False, 'not-a-mail')
        (payload,) = self.feedback_payloads(calls)
        self.assertNotIn('contact_email', payload['contexts']['feedback'])
        self.assertNotIn('activity', events[0]['extra'])

    def test_report_works_without_sentry(self):
        result = telemetry.report('idea', 'text', True, None)
        self.assertFalse(result['sent'])
        self.assertTrue(result['saved'])

    def test_scrub_keeps_feedback_fields_only_for_feedback_events(self):
        event = {'tags': {'kobil_feedback': '1'}, 'contexts': {'feedback': {'message': 'hello', 'contact_email': 'reporter@example.com'}, 'os': {'name': 'x'}},
                 'extra': {'category': 'bug'}, 'user': {'ip_address': '1.2.3.4'}, 'server_name': 'h'}
        out = telemetry.scrub(event, {})
        self.assertEqual(out['contexts'], {'feedback': {'message': 'hello', 'contact_email': 'reporter@example.com'}})
        self.assertEqual(out['extra'], {'category': 'bug'})
        self.assertNotIn('user', out)
        self.assertNotIn('server_name', out)


if __name__ == '__main__':
    unittest.main()
