"""Golden-log tests: the four guidance claims checked against real, sanitized SDK log excerpts.

Fixtures under tests/fixtures/sdk_logs/ are line excerpts of decrypted MCSDK
15.16 logs recorded during the AK-539 validation (2026-10-02/05): a physical
Android device with a hardware key, an Android emulator with a software key
under ALLOW_VIRTUAL_SMART_CARD, and the hardware-policy Start failure caused
by a missing bouncycastle dependency. Realm, client ids and app paths are
neutralised; uuids and timestamps are the originals.
"""
import json
import tempfile
import unittest
from pathlib import Path

from kobil_sdk_integration import log_markers as lm

FIX = Path(__file__).parent / 'fixtures' / 'sdk_logs'


def _read(name):
    return (FIX / name).read_text(encoding='utf-8')


class Registry:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def add(fn):
            self.tools[fn.__name__] = fn
            return fn
        return add


class SignedJwtMarkerTests(unittest.TestCase):
    def test_software_key_grant_is_proven_and_key_is_software(self):
        text = _read('software_key_signedjwt.txt')
        jwt = lm.signed_jwt_grant(text)
        self.assertTrue(jwt['proven'], jwt)
        self.assertEqual(jwt['proof']['http_status'], 200)
        self.assertEqual(jwt['proof']['uuid'], 'e6c08d66-2e65-44c7-9a65-274e8840782a')
        self.assertEqual(jwt['events'][0]['client_id'], 'enrollment-client')  # holder after cold OfflineLogin
        key = lm.key_protection(text)
        self.assertEqual(key['key_kind'], 'software')
        self.assertEqual(key['security_levels'][-1]['security_level'], 0)
        self.assertFalse(key['keystore']['hardware_keystore'])

    def test_hardware_key_grant_is_proven_and_key_is_hardware(self):
        text = _read('hardware_key_signedjwt.txt')
        jwt = lm.signed_jwt_grant(text)
        self.assertTrue(jwt['proven'], jwt)
        self.assertEqual(jwt['proof']['uuid'], '05931044-4234-4305-9162-ce48a8e1a295')
        self.assertEqual(jwt['events'][0]['client_id'], 'token-client')
        key = lm.key_protection(text)
        self.assertEqual(key['key_kind'], 'hardware')
        self.assertEqual(key['security_levels'][-1]['security_level'], 2)
        self.assertTrue(key['keystore']['strong_hardware_keystore'])

    def test_grant_without_200_is_not_proven(self):
        text = _read('software_key_signedjwt.txt').replace('Success 200', 'Failed 401')
        jwt = lm.signed_jwt_grant(text)
        self.assertFalse(jwt['proven'])
        self.assertEqual(jwt['proof']['http_status'], 401)

    def test_offline_login_without_jwt_event_is_not_proven(self):
        text = '\n'.join(l for l in _read('software_key_signedjwt.txt').splitlines() if 'GetIamAccessTokenUsingJwtBearer' not in l)
        jwt = lm.signed_jwt_grant(text)
        self.assertFalse(jwt['proven'])
        self.assertIsNone(jwt['proof'])


class StartNotSupportedTests(unittest.TestCase):
    def test_bcpkix_trace_is_attributed_to_missing_dependency_not_hardware(self):
        text = _read('start_not_supported_bcpkix.txt')
        r = lm.start_not_supported(text)
        self.assertEqual(r['cause'], 'missing_dependency')
        self.assertTrue(any('JcaContentSignerBuilder' in m['class'] for m in r['missing_classes']))
        self.assertIn('NOT proof', r['note'])
        # the same log reports a TEE key: the device did have secure hardware
        self.assertEqual(lm.key_protection(text)['key_kind'], 'hardware')

    def test_not_supported_without_trace_stays_undetermined(self):
        r = lm.start_not_supported('[2026-10-05 10:00:00.000000] StartResultEvent status=NotSupported(46)')
        self.assertEqual(r['cause'], 'undetermined')

    def test_clean_log_reports_none(self):
        self.assertEqual(lm.start_not_supported(_read('hardware_key_signedjwt.txt'))['cause'], 'none')


class ExplicitTmsMarkerTests(unittest.TestCase):
    def test_holder_scope_and_freshness_verdicts(self):
        self.assertEqual(lm.explicit_tms('x TOKEN_EXCHANGE_ERROR not_allowed client is not the token holder')['verdict'], 'wrong_token_holder')
        self.assertEqual(lm.explicit_tms("HTTP 403 Required explicit authentication scope 'tms' is missing")['verdict'], 'missing_explicit_scope')
        self.assertEqual(lm.explicit_tms('error 516004035 access token is 85 seconds older than required')['verdict'], 'freshness_too_strict')
        self.assertEqual(lm.explicit_tms(_read('software_key_signedjwt.txt'))['verdict'], 'none')


class ToolTests(unittest.TestCase):
    def setUp(self):
        r = Registry()
        lm.register(r)
        self.tool = r.tools['sdk_log_markers']

    def test_tool_reads_file_and_never_copies_payload(self):
        res = self.tool(str(FIX / 'software_key_signedjwt.txt'))
        self.assertTrue(res['signed_jwt']['proven'])
        self.assertEqual(res['key_protection']['key_kind'], 'software')
        text = json.dumps(res)
        self.assertNotIn('Bearer ', text)
        self.assertNotIn('eyJ', text)

    def test_tool_rejects_missing_and_encrypted_files(self):
        with self.assertRaises(ValueError):
            self.tool('/nonexistent/ks00001.log')
        with tempfile.NamedTemporaryFile('w', suffix='.log', delete=False) as f:
            f.write('LoggingFramework Version: 36.0.3069606\n%%%abc%def%%%ghi\n')
        try:
            with self.assertRaises(ValueError):
                self.tool(f.name)
        finally:
            Path(f.name).unlink()


if __name__ == '__main__':
    unittest.main()
