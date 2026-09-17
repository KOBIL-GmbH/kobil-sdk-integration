"""First activation must be reachable from the MCP, without the portal or admin console."""
import json
import unittest

from kobil_sdk_integration.activation import (admin_token, ensure_user, find_user,
                                              set_activation_code, set_login_password,
                                              user_status)
from kobil_sdk_integration.backend import BackendError

ADMIN = {'idp_url': 'https://idp.example', 'realm': 'master', 'client_id': 'admin-cli',
         'username': 'admin', 'password_env': 'KOBIL_TEST_ADMIN_PASSWORD'}
USER = {'id': '9d6822c7-7f72-4c2a-91e8-2d098df26b49', 'username': 'tester',
        'email': 'tester@example.com', 'enabled': True, 'firstName': 'KOBIL', 'lastName': 'Test User'}


class FakeBackend:
    """Records what would be sent; the transport itself is covered by the backend tests."""

    def __init__(self, admin=ADMIN, users=(), credentials=('ACTIVATION_CODE',), groups=('ks-users',),
                 joined=('ks-users',)):
        self.cfg = {'environment': 'test', 'tenant': 'sample'}
        if admin:
            self.cfg['admin'] = admin
        self.users = list(users)
        self.credentials = list(credentials)
        self.groups = list(groups)
        self.joined = list(joined)
        self.calls = []

    def send(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if url.endswith('/protocol/openid-connect/token'):
            return {'access_token': 'admin-token'}
        if url.endswith('/credentials'):
            return [{'type': t} for t in self.credentials]
        if url.endswith('/sessions'):
            return [{'start': 1, 'lastAccess': 2, 'clients': {'id1': 'LoginClient'}}]
        if '/attack-detection/brute-force/users/' in url:
            return {'numFailures': 2, 'lastFailure': 99, 'disabled': False}
        if url.endswith('/groups') and '/users/' in url:
            return [{'name': n} for n in self.joined]
        if url.endswith('/groups'):
            return [{'id': 'group-uuid', 'name': n} for n in self.groups]
        if method == 'GET' and 'params' in kwargs:
            name = kwargs['params']['username']
            return [u for u in self.users if u['username'] == name]
        if method == 'GET':
            return dict(self.users[0]) if self.users else {}
        if method == 'POST':
            self.users.append(dict(USER, username=kwargs['json']['username']))
            return {}
        return {}

    def sent(self, method):
        return [c for c in self.calls if c[0] == method]


class AdminAccessTests(unittest.TestCase):
    def setUp(self):
        import os
        os.environ['KOBIL_TEST_ADMIN_PASSWORD'] = 'not-the-real-one'

    def test_missing_admin_block_is_explained(self):
        with self.assertRaises(BackendError):
            admin_token(FakeBackend(admin=None))

    def test_missing_credential_in_environment_is_refused(self):
        import os
        del os.environ['KOBIL_TEST_ADMIN_PASSWORD']
        with self.assertRaises(BackendError):
            admin_token(FakeBackend())

    def test_password_travels_only_in_the_token_request(self):
        backend = FakeBackend()
        self.assertEqual(admin_token(backend), 'admin-token')
        method, url, kwargs = backend.calls[0]
        self.assertEqual((method, url), ('POST', 'https://idp.example/auth/realms/master/protocol/openid-connect/token'))
        self.assertEqual(kwargs['data']['password'], 'not-the-real-one')
        self.assertEqual(kwargs['data']['grant_type'], 'password')


class ActivationUserTests(unittest.TestCase):
    def setUp(self):
        import os
        os.environ['KOBIL_TEST_ADMIN_PASSWORD'] = 'not-the-real-one'

    def test_existing_user_is_reused_and_not_modified(self):
        backend = FakeBackend(users=[USER])
        result = ensure_user(backend, 'tester')
        self.assertEqual((result['created'], result['user_uuid']), (False, USER['id']))
        self.assertEqual(backend.sent('POST'), backend.calls[:1])  # only the token request
        self.assertEqual(backend.sent('PUT'), [])

    def test_new_user_is_created_without_a_password(self):
        backend = FakeBackend()
        result = ensure_user(backend, 'kobilapp-tester1')
        self.assertTrue(result['created'])
        creation = [c for c in backend.calls if c[0] == 'POST' and c[1].endswith('/users')][0]
        self.assertNotIn('credentials', creation[2]['json'])
        self.assertTrue(creation[2]['json']['enabled'])
        self.assertEqual(creation[2]['json']['attributes'], {'status': ['REGISTERED']})

    def test_new_user_joins_the_group_and_membership_is_verified(self):
        backend = FakeBackend()
        result = ensure_user(backend, 'kobilapp-tester1')
        self.assertEqual(result['groups'], ['ks-users'])
        join = backend.sent('PUT')[0]
        self.assertTrue(join[1].endswith('/groups/group-uuid'))

    def test_membership_that_did_not_take_effect_is_an_error(self):
        with self.assertRaises(BackendError):
            ensure_user(FakeBackend(joined=()), 'kobilapp-tester1')

    def test_unknown_group_is_refused_before_the_user_is_created(self):
        backend = FakeBackend(groups=('other-group',))
        with self.assertRaises(BackendError):
            ensure_user(backend, 'kobilapp-tester1')
        self.assertEqual([c for c in backend.calls if c[0] == 'POST' and c[1].endswith('/users')], [])

    def test_malformed_identity_is_refused(self):
        for bad in ({'username': 'ab'}, {'username': 'has space'}, {'email': 'not-an-email'},
                    {'first_name': 'Robert");--'}, {'group': 'ks users'}):
            with self.assertRaises(ValueError):
                ensure_user(FakeBackend(), **{'username': 'tester', **bad})

    def test_user_absent_after_creation_is_an_error(self):
        backend = FakeBackend()
        backend.send = lambda method, url, **kw: (
            {'access_token': 'admin-token'} if url.endswith('token')
            else [{'id': 'group-uuid', 'name': 'ks-users'}] if url.endswith('/groups')
            else [] if 'params' in kw else {})
        with self.assertRaises(BackendError):
            ensure_user(backend, 'kobilapp-tester1')


class ActivationCodeTests(unittest.TestCase):
    def setUp(self):
        import os
        os.environ['KOBIL_TEST_ADMIN_PASSWORD'] = 'not-the-real-one'

    def test_code_is_generated_here_and_stored_as_a_credential(self):
        backend = FakeBackend(users=[USER])
        result = set_activation_code(backend, USER['id'])
        self.assertTrue(result['activation_code'].isdigit())
        self.assertEqual(len(result['activation_code']), 8)
        update = [c for c in backend.calls if c[0] == 'PUT'][0][2]['json']
        credential = update['credentials'][0]
        self.assertEqual(credential['type'], 'ACTIVATION_CODE')
        self.assertEqual(json.loads(credential['secretData'])['code'], result['activation_code'])
        self.assertEqual(json.loads(credential['credentialData'])['period'], '60d')

    def test_each_issue_is_a_fresh_secret(self):
        codes = {set_activation_code(FakeBackend(users=[USER]), USER['id'])['activation_code']
                 for _ in range(5)}
        self.assertEqual(len(codes), 5)

    def test_profile_fields_are_sent_back_unchanged(self):
        backend = FakeBackend(users=[USER])
        set_activation_code(backend, USER['id'])
        update = [c for c in backend.calls if c[0] == 'PUT'][0][2]['json']
        self.assertEqual(update['username'], USER['username'])
        self.assertTrue(update['enabled'])

    def test_a_code_that_was_not_stored_is_never_returned(self):
        with self.assertRaises(BackendError):
            set_activation_code(FakeBackend(users=[USER], credentials=('password',)), USER['id'])

    def test_unknown_user_is_refused(self):
        backend = FakeBackend(users=[dict(USER, id='11111111-2222-3333-4444-555555555555')])
        with self.assertRaises(BackendError):
            set_activation_code(backend, USER['id'])

    def test_malformed_arguments_are_refused(self):
        for bad in ({'user_uuid': 'tester'}, {'valid_for': 'forever'}, {'valid_for': '0d'},
                    {'digits': 4}, {'digits': True}):
            with self.assertRaises(ValueError):
                set_activation_code(FakeBackend(users=[USER]), **{'user_uuid': USER['id'], **bad})

    def test_lookup_rejects_a_malformed_username(self):
        with self.assertRaises(ValueError):
            find_user(FakeBackend(), 'a b')


if __name__ == '__main__':
    unittest.main()


class LoginPasswordTests(unittest.TestCase):
    def setUp(self):
        import os
        os.environ['KOBIL_TEST_ADMIN_PASSWORD'] = 'adm'

    def test_password_is_generated_here_and_meets_the_realm_policy(self):
        backend = FakeBackend(users=[USER], credentials=('password',))
        result = set_login_password(backend, USER['id'])
        password = result['password']
        self.assertEqual(len(password), 14)
        self.assertTrue(any(c.isupper() for c in password))
        self.assertTrue(any(c.islower() for c in password))
        self.assertTrue(any(c.isdigit() for c in password))
        put = backend.sent('PUT')
        self.assertEqual(len(put), 1)
        self.assertTrue(put[0][1].endswith('/users/%s/reset-password' % USER['id']))
        self.assertEqual(put[0][2]['json'], {'type': 'password', 'value': password, 'temporary': False})
        self.assertEqual(result['credential_types'], ['password'])

    def test_each_call_is_a_fresh_secret(self):
        values = {set_login_password(FakeBackend(users=[USER], credentials=('password',)), USER['id'])['password']
                  for _ in range(5)}
        self.assertEqual(len(values), 5)

    def test_a_password_that_was_not_stored_is_never_returned(self):
        with self.assertRaises(BackendError):
            set_login_password(FakeBackend(users=[USER]), USER['id'])

    def test_unknown_user_is_refused(self):
        backend = FakeBackend(users=[dict(USER, id='11111111-2222-3333-4444-555555555555')])
        with self.assertRaises(BackendError):
            set_login_password(backend, USER['id'])
        self.assertEqual(backend.sent('PUT'), [])

    def test_malformed_arguments_are_refused(self):
        for bad in ({'user_uuid': 'nope'}, {'length': 4}, {'length': '14'}, {'length': 65}):
            with self.assertRaises(ValueError):
                set_login_password(FakeBackend(users=[USER], credentials=('password',)),
                                   **{'user_uuid': USER['id'], **bad})


class UserStatusTests(unittest.TestCase):
    def setUp(self):
        import os
        os.environ['KOBIL_TEST_ADMIN_PASSWORD'] = 'adm'

    def test_status_reports_credentials_sessions_and_failures(self):
        result = user_status(FakeBackend(users=[USER], credentials=('password',)), USER['id'])
        self.assertEqual(result['credential_types'], ['password'])
        self.assertEqual(result['sessions'], [{'start_ms': 1, 'last_access_ms': 2, 'clients': ['LoginClient']}])
        self.assertEqual(result['failed_logins'], 2)
        self.assertFalse(result['locked'])

    def test_status_is_read_only(self):
        backend = FakeBackend(users=[USER])
        user_status(backend, USER['id'])
        self.assertEqual([c[0] for c in backend.calls if c[0] != 'GET'], ['POST'])  # only the token request

    def test_unknown_user_and_malformed_uuid_are_refused(self):
        with self.assertRaises(BackendError):
            user_status(FakeBackend(users=[dict(USER, id='11111111-2222-3333-4444-555555555555')]), USER['id'])
        with self.assertRaises(ValueError):
            user_status(FakeBackend(users=[USER]), 'nope')
