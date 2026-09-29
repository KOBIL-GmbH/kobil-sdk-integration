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
