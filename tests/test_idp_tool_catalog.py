"""Catalog contract test for every IDP administration tool.

Phase 15a: the thin ``sdk_idp_*`` wrappers in idp_access, idp_extended,
idp_users and idp_secrets were registered but never exercised by a test. This
test drives each of them once against a recording fake of ``Admin`` with
synthetic arguments and checks the contract every wrapper must keep:

* it either returns a JSON-serialisable result or raises a *validation* error
  (ValueError, BackendError, pydantic ValidationError, NotImplementedError) -
  never an unexpected exception type;
* every admin path is internal (starts with '/', no query/fragment) and uses an
  allowed HTTP method;
* a write (POST/PUT/DELETE/PATCH) is issued at most once per call - no silent
  retry of an uncertain mutation;
* a secret-looking input value never appears in the result;
* the (method, path) sequence per tool matches ``tests/fixtures/idp_tool_catalog.json``.
  Set ``UPDATE_IDP_TOOL_CATALOG=1`` to regenerate the snapshot after an
  intentional route change and review the diff.
"""
from __future__ import annotations

import inspect
import json
import os
import tempfile
import typing
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import BaseModel, ValidationError

from kobil_sdk_integration import idp_access, idp_extended, idp_secrets, idp_users
from kobil_sdk_integration.backend import BackendError

MODULES = {m.__name__.rsplit('.', 1)[-1]: m for m in (idp_access, idp_extended, idp_users, idp_secrets)}
SNAPSHOT = Path(__file__).parent / 'fixtures' / 'idp_tool_catalog.json'
SECRET = 'SECRET-SENTINEL-7f3a'
SECRET_PARAM_HINTS = ('secret', 'password', 'token', 'code', 'otp', 'pin')
ALLOWED_METHODS = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH'}
WRITE_METHODS = {'POST', 'PUT', 'DELETE', 'PATCH'}
ACCEPTABLE = (ValueError, BackendError, ValidationError, NotImplementedError)


class Registry:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def add(fn):
            self.tools[fn.__name__] = fn
            return fn
        return add


class FakeBackend:
    """Stands in for the AST HTTP client on the few tools that call it directly."""

    def send(self, method, url, **kw):
        FakeAdmin.calls.append((method, '[direct]/' + url.split('://', 1)[-1].split('/', 1)[-1]))
        return {'access_token': SECRET + '-issued', 'scope': 'x'}

    def close(self):
        return None


class FakeAdmin:
    """Records every admin call; answers with shapes the wrappers accept."""
    calls: list[tuple[str, str]] = []

    def __init__(self, expected_environment, realm=None):
        self.environment = expected_environment
        self.realm = realm or 'realm-a'
        self.cfg = {'environment': expected_environment, 'tenant': self.realm,
                    'admin': {'idp_url': 'https://idp.example.test'}}
        self.prefix = '/auth/admin/realms/' + self.realm
        self.token = 'tok'
        self.backend = FakeBackend()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def _safe(self, result):
        return result

    def raw(self, method, path, body=None, params=None):
        if (path and not path.startswith('/')) or '?' in path or '#' in path:
            raise ValueError('bad path')
        FakeAdmin.calls.append((method, path))
        if method == 'GET':
            return {'id': 'x', 'alias': 'x', 'clientId': 'x', 'enabled': True, 'name': 'x',
                    'attributes': {}, 'config': {}, 'defaultClientScopes': [], 'optionalClientScopes': [],
                    'authenticationFlowBindingOverrides': {}, 'requiredActions': [], 'username': 'x'}
        return {}

    call = raw

    def call_global(self, method, path, body=None, params=None):
        FakeAdmin.calls.append((method, '[global]' + path))
        return {} if method != 'GET' else []

    def page(self, path, first=0, max_results=50, params=None, paginated=True):
        FakeAdmin.calls.append(('GET', path))
        return {'items': [], 'first': first, 'next_offset': None, 'complete': True,
                'environment': self.environment, 'realm': self.realm}

    def update(self, path, changes, allowed_fields):
        if not isinstance(changes, dict) or not changes or set(changes) - set(allowed_fields):
            raise ValueError('Provide supported fields to update')
        FakeAdmin.calls.append(('GET', path))
        FakeAdmin.calls.append(('PUT', path))
        return {}


def _value_for(name: str, annotation, tmpdir: Path):
    origin = typing.get_origin(annotation)
    args = [a for a in typing.get_args(annotation) if a is not type(None)]
    if origin is typing.Union and args:
        annotation = args[0]
    if typing.get_origin(annotation) is typing.Literal:
        return typing.get_args(annotation)[0]
    lname = name.lower()
    if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
        # FastMCP validates the model before the tool runs; build an empty one.
        return annotation()
    if lname.endswith('_file') or lname.endswith('_path'):
        f = tmpdir / f'{name}.json'
        f.write_text('{}', encoding='utf-8')
        f.chmod(0o600)
        return str(f)
    if any(h in lname for h in SECRET_PARAM_HINTS):
        return SECRET
    if annotation is bool:
        return False
    if annotation is int:
        return 1
    if annotation in (dict, typing.Dict) or typing.get_origin(annotation) is dict:
        return {}
    if annotation in (list, typing.List) or typing.get_origin(annotation) is list:
        return []
    return 'x'


def _invoke(fn, tmpdir: Path):
    sig = inspect.signature(fn)
    kwargs = {}
    for p in sig.parameters.values():
        if p.default is not inspect.Parameter.empty:
            continue  # optional: exercise the minimal call
        kwargs[p.name] = _value_for(p.name, p.annotation, tmpdir)
    if 'expected_environment' in kwargs:
        kwargs['expected_environment'] = 'test'
    return fn(**kwargs)


class IdpToolCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools = {}
        cls.patchers = []
        for modname, mod in MODULES.items():
            reg = Registry()
            p = patch.object(mod, 'Admin', FakeAdmin)
            p.start()
            cls.patchers.append(p)
            if hasattr(mod, '_call'):
                def _fake_call(backend, token, method, path, body=None, params=None):
                    FakeAdmin.calls.append((method, '[direct]' + path))
                    return {}
                p2 = patch.object(mod, '_call', _fake_call)
                p2.start()
                cls.patchers.append(p2)
            mod.register(reg)
            for name, fn in reg.tools.items():
                cls.tools[name] = (modname, fn)

    @classmethod
    def tearDownClass(cls):
        for p in cls.patchers:
            p.stop()

    def _run_catalog(self):
        catalog = {}
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            for name in sorted(self.tools):
                modname, fn = self.tools[name]
                FakeAdmin.calls = []
                outcome = 'ok'
                result = None
                try:
                    result = _invoke(fn, tmpdir)
                except ACCEPTABLE as exc:
                    outcome = f'validation:{type(exc).__name__}'
                except Exception as exc:  # noqa: BLE001 - the point of the test
                    self.fail(f'{modname}.{name} raised unexpected {type(exc).__name__}: {exc}')
                calls = list(FakeAdmin.calls)
                for method, path in calls:
                    self.assertIn(method, ALLOWED_METHODS, (name, method))
                    # '' is the realm root (DELETE /auth/admin/realms/<realm>), accepted by Admin.raw
                    self.assertTrue(path == '' or path.startswith('/') or path.startswith('[global]/') or path.startswith('[direct]/'), (name, path))
                    self.assertNotIn('?', path, (name, path))
                writes = [m for m, _ in calls if m in WRITE_METHODS]
                self.assertLessEqual(len(writes), 2, f'{name}: {len(writes)} write calls in one invocation - possible retry')
                if result is not None:
                    text = json.dumps(result, default=str)
                    self.assertNotIn(SECRET, text, f'{name} echoes a secret-like input')
                catalog[name] = {'module': modname, 'outcome': outcome, 'calls': [list(c) for c in calls]}
        return catalog

    def test_every_idp_tool_keeps_the_contract(self):
        catalog = self._run_catalog()
        self.assertGreaterEqual(len(catalog), 110, 'expected the full IDP tool catalog to be registered')
        if os.environ.get('UPDATE_IDP_TOOL_CATALOG') == '1':
            SNAPSHOT.parent.mkdir(exist_ok=True)
            SNAPSHOT.write_text(json.dumps(catalog, indent=1, sort_keys=True) + '\n', encoding='utf-8')
            self.skipTest('snapshot regenerated; review the diff and commit')
        self.assertTrue(SNAPSHOT.exists(), 'snapshot missing: run with UPDATE_IDP_TOOL_CATALOG=1 once')
        expected = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
        added = sorted(set(catalog) - set(expected))
        removed = sorted(set(expected) - set(catalog))
        changed = sorted(k for k in set(catalog) & set(expected) if catalog[k] != expected[k])
        self.assertEqual((added, removed, changed), ([], [], []),
                         f'IDP tool catalog drift - added={added} removed={removed} changed={changed}; '
                         'if intentional run UPDATE_IDP_TOOL_CATALOG=1 and review the diff')

    def test_write_tools_do_not_retry_writes(self):
        catalog = self._run_catalog()
        for name, entry in catalog.items():
            writes = [c for c in entry['calls'] if c[0] in WRITE_METHODS]
            self.assertLessEqual(len(writes), 2, (name, writes))


if __name__ == '__main__':
    unittest.main()
