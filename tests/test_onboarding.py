import json,os,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from kobil_sdk_integration.onboarding import prepare,startup

@unittest.skipUnless(shutil.which('age-keygen'),'age required')
class OnboardingTests(unittest.TestCase):
    def test_request_is_public_reusable_and_preserves_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);home=root/'home';home.mkdir();project=root/'project';project.mkdir()
            with patch.dict(os.environ,{'HOME':str(home)}):
                first=prepare(str(project));local=project/'.kobil-sdk'
                connection=local/'connection.json';connection.write_text('existing-settings')
                again=prepare(str(project))
                self.assertEqual(first['recipient'],again['recipient'])
                self.assertIn(first['recipient'],first['email_body'])
                self.assertIn('SFTP',first['email_body'])
                self.assertFalse(first['email_sent'])
                self.assertNotIn('AGE-SECRET-KEY-',json.dumps(first))
                self.assertEqual(connection.read_text(),'existing-settings')
                self.assertTrue(Path(first['request_file']).is_file())
                key=Path(json.loads((local/'identity-reference.json').read_text())['identity_path'])
                self.assertFalse(key.is_relative_to(project))
    def test_startup_never_guesses_cwd(self):
        with patch.dict(os.environ,{},clear=True),patch('kobil_sdk_integration.onboarding.prepare') as call:
            startup();call.assert_not_called()
    def test_startup_uses_project_setting(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ,{'KOBIL_SDK_PROJECT':tmp},clear=True),patch('kobil_sdk_integration.onboarding.prepare') as call:
                startup();call.assert_called_once_with(tmp)


class ConfiguredConnection(unittest.TestCase):
    def test_prepare_skips_when_connection_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            connection = os.path.join(tmp, 'connection.json')
            open(connection, 'w').write('{}')
            with patch.dict(os.environ, {'KOBIL_SDK_CONNECTION': connection}, clear=True):
                result = prepare(tmp)
            self.assertEqual(result['status'], 'connection_already_configured')
            self.assertFalse(os.path.exists(os.path.join(tmp, '.kobil-sdk', 'credential-request.txt')))

    def test_startup_writes_nothing_when_connection_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            connection = os.path.join(tmp, 'connection.json')
            open(connection, 'w').write('{}')
            with patch.dict(os.environ, {'KOBIL_SDK_PROJECT': tmp, 'KOBIL_SDK_CONNECTION': connection}, clear=True):
                startup()
            self.assertFalse(os.path.exists(os.path.join(tmp, '.kobil-sdk', 'credential-request.txt')))

    def test_prepare_runs_when_connection_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.mkdir(os.path.join(tmp, '.kobil-sdk'))
            with patch.dict(os.environ, {'KOBIL_SDK_CONNECTION': os.path.join(tmp, 'missing.json')}, clear=True), \
                 patch('kobil_sdk_integration.onboarding.project_identity', return_value={'recipient': 'age1x', 'recipient_file': 'r'}):
                result = prepare(tmp)
            self.assertEqual(result['status'], 'credential_delivery_requested')
