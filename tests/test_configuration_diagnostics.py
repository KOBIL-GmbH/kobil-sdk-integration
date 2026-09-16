import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kobil_sdk_integration.backend import BackendError, configuration


class ConfigurationDiagnosticsTests(unittest.TestCase):
    def assert_failure(self, code, path=None):
        with self.assertLogs('kobil_sdk_integration.backend', level='WARNING') as logs:
            with self.assertRaises(BackendError) as caught:
                configuration(path=path)
        self.assertTrue(str(caught.exception).startswith(code + ':'))
        self.assertEqual(len(logs.output), 1)
        self.assertIn(code, logs.output[0])
        self.assertNotIn('fixture-private', str(caught.exception) + logs.output[0])

    def test_missing_selection(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assert_failure('CONNECTION_NOT_SELECTED')

    def test_file_and_json_errors(self):
        with tempfile.TemporaryDirectory(prefix='fixture-private') as folder:
            p = Path(folder) / 'connection.json'
            self.assert_failure('CONNECTION_FILE_NOT_FOUND', p)
            self.assert_failure('CONNECTION_FILE_UNREADABLE', Path(folder))
            p.write_text('{"password":"fixture-private"')
            self.assert_failure('CONNECTION_JSON_INVALID', p)
            p.write_bytes(b'\xff')
            self.assert_failure('CONNECTION_FILE_UNREADABLE', p)
            with patch.object(Path, 'read_text', side_effect=PermissionError('fixture-private')):
                self.assert_failure('CONNECTION_FILE_UNREADABLE', p)

    def test_schema_and_fields_do_not_resolve_credentials(self):
        with tempfile.TemporaryDirectory() as folder, patch('kobil_sdk_integration.credentials.resolve') as resolve:
            p = Path(folder) / 'connection.json'
            for body, code in [({'schema_version': 99}, 'CONNECTION_SCHEMA_UNSUPPORTED'),
                               ([], 'CONNECTION_FIELDS_INVALID'),
                               ({'environment': 'fixture-private'}, 'CONNECTION_FIELDS_INVALID')]:
                p.write_text(json.dumps(body))
                self.assert_failure(code, p)
            resolve.assert_not_called()
