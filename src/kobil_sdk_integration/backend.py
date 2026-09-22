"""Customer-configured AST operations. Credentials never enter tool arguments."""
import json
import os
import re
from pathlib import Path
from urllib.parse import quote, urlsplit

import httpx


class BackendError(RuntimeError):
    pass


def segment(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ValueError('Expected a non-empty identifier of at most 256 characters')
    if any(ord(c) < 32 for c in value) or value in {'.', '..'}:
        raise ValueError('Invalid identifier')
    return quote(value, safe='')


def https_url(value):
    if not isinstance(value, str):
        raise ValueError('Expected an HTTPS URL')
    u = urlsplit(value)
    if u.scheme != 'https' or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise ValueError('Expected HTTPS URL without credentials, query or fragment')
    return value.rstrip('/')


def authentication(cfg):
    """Normalize legacy/v2 AST authentication without reading credentials."""
    from .credentials import validate_reference
    if 'schema_version' in cfg:
        if type(cfg['schema_version']) is not int or cfg['schema_version'] != 2 or 'oauth' in cfg or 'token_env' in cfg:
            raise ValueError('Invalid authentication schema')
        auth = cfg['auth']
        fields = {'type', 'credential'}
        if auth.get('type') == 'oauth_client_credentials':
            fields |= {'token_url', 'client_id'}
            https_url(auth['token_url']); segment(auth['client_id'])
            if 'scope' in auth: fields.add('scope')
        elif auth.get('type') != 'bearer': raise ValueError('Invalid authentication mode')
        if set(auth) != fields: raise ValueError('Invalid authentication fields')
    else:
        if 'auth' in cfg or bool(cfg.get('token_env')) == bool(cfg.get('oauth')):
            raise ValueError('Ambiguous authentication')
        if cfg.get('token_env'):
            auth = {'type':'bearer','credential':{'provider':'env','name':cfg['token_env']}}
        else:
            oauth=cfg['oauth']
            if set(oauth)-{'token_url','client_id','client_secret_env','scope'} or not {'token_url','client_id','client_secret_env'} <= set(oauth): raise ValueError()
            https_url(oauth['token_url']); segment(oauth['client_id'])
            auth={'type':'oauth_client_credentials','token_url':oauth['token_url'],'client_id':oauth['client_id'],
                  'credential':{'provider':'env','name':oauth['client_secret_env']}}
            if 'scope' in oauth:auth['scope']=oauth['scope']
    if 'scope' in auth and (not isinstance(auth['scope'],str) or not re.fullmatch(r'[A-Za-z0-9 _:.-]{1,200}',auth['scope'])):
        raise ValueError('Invalid OAuth scope')
    validate_reference(auth['credential'])
    return auth


def admin_reference(admin):
    from .credentials import validate_reference
    if ('password_env' in admin) == ('credential' in admin):raise ValueError('Select one administrator credential reference')
    ref=admin.get('credential') if 'credential' in admin else {'provider':'env','name':admin['password_env']}
    return validate_reference(ref)


def configuration(expected_environment=None, path=None):
    try:
        source = Path(path or os.environ['KOBIL_SDK_CONNECTION']).expanduser()
        cfg = json.loads(source.read_text())
        if set(cfg)-{'environment','tenant','ast_url','token_env','oauth','services','admin','schema_version','auth'}:raise ValueError()
        segment(cfg['environment']); segment(cfg['tenant']); https_url(cfg['ast_url'])
        authentication(cfg)
        if 'admin' in cfg:
            admin=cfg['admin']
            required={'idp_url','realm','client_id','username'}
            if not required<=set(admin) or set(admin)-required-{'password_env','credential'}:raise ValueError()
            https_url(admin['idp_url']);segment(admin['realm']);segment(admin['client_id'])
            if not isinstance(admin['username'],str) or not re.fullmatch(r'[A-Za-z0-9._@+-]{1,120}',admin['username']):raise ValueError()
            admin_reference(admin)
    except Exception:
        raise BackendError('Invalid connection configuration; see backend setup documentation') from None
    if expected_environment is not None and expected_environment != cfg['environment']:
        raise ValueError('Active environment mismatch')
    return cfg


class AST:
    def __init__(self, cfg):
        self.cfg = cfg
        self.root = '/v1/tenants/' + segment(cfg['tenant'])
        self.client = httpx.Client(timeout=30, follow_redirects=False, trust_env=False)

    def close(self):
        self.client.close()

    def token(self):
        from .credentials import resolve, CredentialError
        auth=authentication(self.cfg)
        try:secret=resolve(auth['credential'])
        except CredentialError as error:raise BackendError(str(error)) from None
        if auth['type']=='bearer':return secret
        form={'grant_type':'client_credentials','client_id':auth['client_id'],'client_secret':secret}
        if auth.get('scope'):form['scope']=auth['scope']
        result=self.send('POST',auth['token_url'],data=form)
        token=result.get('access_token') if isinstance(result,dict) else None
        if not isinstance(token,str) or not token:raise BackendError('Backend authentication did not return an access token')
        return token

    def send(self, method, url, allow_not_found=False, **kwargs):
        try:
            with self.client.stream(method, url, **kwargs) as response:
                if response.status_code == 404 and allow_not_found:
                    return None
                if response.status_code >= 300:
                    category = {400: 'invalid_request', 401: 'authentication_failed', 403: 'permission_denied',
                                404: 'resource_or_api_not_found', 405: 'operation_not_supported',
                                409: 'conflict', 429: 'rate_limited'}.get(response.status_code, 'backend_error')
                    raise BackendError('Backend request failed (HTTP %d; %s)' % (response.status_code, category))
                raw = bytearray()
                for part in response.iter_bytes():
                    raw.extend(part)
                    if len(raw) > 4 * 1024 * 1024:
                        raise BackendError('Backend response exceeds size limit')
                return json.loads(raw) if raw else {}
        except BackendError:
            raise
        except Exception:
            raise BackendError('Backend transport or response failure; inspect server-side diagnostics') from None

    def request(self, method, path, body=None, allow_not_found=False):
        return self.send(method, self.cfg['ast_url'] + self.root + path,
                         headers={'Authorization': 'Bearer ' + self.token()}, json=body, allow_not_found=allow_not_found)

    def ensure_app(self, name, categories):
        path = '/apps/' + segment(name)
        if not categories or any(not isinstance(c, str) or not c.strip() for c in categories):
            raise ValueError('Provide at least one app category')
        existing = self.request('GET', path, allow_not_found=True)
        if existing is not None:
            if not isinstance(existing, dict) or existing.get('appName') != name:
                raise BackendError('Unrecognized app response; refusing to create')
            return {'app_name': name, 'created': False, 'settings_verified': False}
        self.request('POST', path, {'categories': categories})
        return {'app_name': name, 'created': True, 'settings_verified': False}

    def get_app(self, name):
        value = self.request('GET', '/apps/' + segment(name), allow_not_found=True)
        if value is None:
            return {'app_name': name, 'exists': False}
        if not isinstance(value, dict) or value.get('appName') != name:
            raise BackendError('Unrecognized app response')
        return {'app_name': name, 'exists': True}

    def _version_rows(self, app_name):
        segment(app_name)
        rows, expected_total = [], None
        for page in range(1, 101):
            response = self.request('GET', '/versions?appName=' + segment(app_name) + '&pageSize=100&page=' + str(page))
            if not isinstance(response, dict):
                raise BackendError('Unrecognized version list response')
            batch = response.get('data', response.get('content'))
            total = response.get('totalCount', response.get('totalElements'))
            if not isinstance(batch, list) or any(not isinstance(r, dict) or not all(k in r for k in ('appName', 'platform', 'versionStr')) for r in batch):
                raise BackendError('Unrecognized version entries')
            if type(total) is not int or total < 0:
                raise BackendError('Missing version count; refusing automatic registration')
            if expected_total is not None and total != expected_total:
                raise BackendError('Version listing changed during pagination')
            expected_total = total
            rows.extend(batch)
            if len(rows) == total and response.get('last') is not False:
                break
            if not batch or len(rows) >= total:
                raise BackendError('Version listing is incomplete')
        else:
            raise BackendError('Version listing exceeds automatic pagination limit')
        return rows

    def list_versions(self, app_name):
        versions = []
        for row in self._version_rows(app_name):
            if row['appName'] != app_name:
                raise BackendError('Version response does not match requested app')
            required = ('platform', 'versionStr', 'registerUserId')
            if any(not isinstance(row.get(k), str) or not row[k] for k in required):
                raise BackendError('Incomplete version registration metadata')
            if type(row.get('isCheckIntegrity')) is not bool or type(row.get('versionLock')) is not bool:
                raise BackendError('Incomplete version policy metadata')
            versions.append({'platform': row['platform'], 'version': row['versionStr'],
                             'register_user_id': row['registerUserId'],
                             'check_integrity': row['isCheckIntegrity'], 'locked': row['versionLock']})
        return {'app_name': app_name, 'versions': versions}

    def ensure_version(self, app_name, platform, version, register_user_id, check_integrity):
        segment(app_name)
        segment(platform)
        segment(version)
        if not 3 <= len(app_name) <= 255 or len(platform) > 100 or not re.fullmatch(r'\d+\.\d+\.\d+', version):
            raise ValueError('Use app name length 3–255, platform length 1–100 and version major.minor.patch')
        if not register_user_id or len(register_user_id) > 255:
            raise ValueError('A registration user ID is required')
        if type(check_integrity) is not bool:
            raise ValueError('Choose an explicit boolean integrity policy')
        rows = self._version_rows(app_name)
        matches = [r for r in rows if r.get('appName', app_name) == app_name
                   and r.get('platform') == platform and r.get('versionStr') == version]
        if len(matches) > 1:
            raise BackendError('Duplicate versions exist; reconcile backend state')
        if matches:
            row = matches[0]
            if row.get('isCheckIntegrity') != check_integrity or row.get('registerUserId', '') != register_user_id or row.get('versionLock', False):
                raise BackendError('Existing version settings conflict; no changes made')
            return {'app_name': app_name, 'platform': platform, 'version': version, 'created': False}
        body = {'appName': app_name, 'platform': platform, 'versionStr': version,
                'registerUserId': register_user_id, 'versionLock': False,
                'isCheckIntegrity': check_integrity}
        self.request('POST', '/versions', body)
        return {'app_name': app_name, 'platform': platform, 'version': version, 'created': True}
