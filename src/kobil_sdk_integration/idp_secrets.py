"""Explicit credential operations with private inputs/outputs, separate from discovery."""
from contextlib import contextmanager
import hashlib
import json
import os
import re
import secrets
from uuid import UUID
from pathlib import Path
import stat
from typing import Literal
from pydantic import BaseModel, ConfigDict, model_validator
from .idp_admin import Admin
from .backend import segment, BackendError
from .idp_transport import _call

class CredentialRef(BaseModel):
    model_config=ConfigDict(extra='forbid')
    provider: Literal['env','keyring','file','age']
    name: str | None = None
    service: str | None = None
    account: str | None = None
    path: str | None = None
    store: str | None = None
    identity: str | None = None
    fallback: dict | None = None

    @model_validator(mode='after')
    def exact(self):
        from .credentials import validate_reference, CredentialError
        try:validate_reference(self.model_dump(exclude_none=True))
        except CredentialError:raise ValueError('Invalid credential reference') from None
        return self


def resolve(ref):
    from .credentials import resolve as shared_resolve, CredentialError
    try:return shared_resolve(ref.model_dump(exclude_none=True))
    except CredentialError as error:raise ValueError(str(error)) from None


@contextmanager
def output_file(path):
    """Reserve a new owner-only file before a credential rotation or token request."""
    p=Path(path).expanduser()
    try:
        fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except OSError as error:
        raise ValueError(_output_diagnosis(p,error)) from None
    try:
        with os.fdopen(fd,'w') as stream:
            yield stream,p
    except BaseException:
        p.unlink(missing_ok=True)
        raise


def _output_diagnosis(path,error):
    """Metadata-only private-output diagnosis; never inspects or reveals credential values."""
    import errno
    parent=path.parent
    detail={
        errno.EEXIST:'a file already exists at the destination; a NEW file is required so an existing private result is never overwritten',
        errno.ENOENT:'the parent directory %r does not exist; create a private directory first'%str(parent),
        errno.ENOTDIR:'a parent path component of %r is not a directory'%str(parent),
        errno.EACCES:'permission denied creating the file; check write permission and ownership of %r'%str(parent),
        errno.EPERM:'the operation is not permitted on this destination; check ownership of %r and provider/filesystem support'%str(parent),
        errno.EROFS:'the destination filesystem is read-only',
    }.get(getattr(error,'errno',None),'the destination file could not be created; verify the path, permissions and filesystem support')
    ownership=''
    try:
        info=parent.stat()
        if os.name=='posix' and info.st_uid!=os.getuid():
            ownership=' The parent directory is not owned by the current user.'
    except OSError:
        pass
    return ('Private output setup failed: '+detail+'.'+ownership+
            ' This is a LOCAL destination problem, not a backend failure: the backend request of this tool'
            ' was NOT sent, so no backend state was changed. There is no plaintext fallback; fix the'
            ' destination and rerun. No credential values are included in this diagnostic.')


def write_result(stream,path,result):
    text=json.dumps(result);stream.write(text);stream.flush()
    return {'path':str(path.absolute()),'sha256':hashlib.sha256(text.encode()).hexdigest(),
            'secret_contents_returned':False}


def register(mcp):
    @mcp.tool()
    def sdk_idp_activation_code_generate(expected_environment: str, user_uuid: str,
                                         valid_for: str = '60d', digits: int = 8,
                                         realm: str | None = None, code_reference: CredentialRef | None = None) -> dict:
        """Generate and store a numeric KOBIL ACTIVATION_CODE for an existing user UUID. Requires manage-users and server support for this credential type. Returns the generated secret once for app activation; never log or commit it. May replace an existing activation code. Does not create users, choose flows or activate devices. Credential-type readback cannot prove the exact new value was stored. Never automatically retry an uncertain write.

        Before this code is used on a device, an EXPLICIT local authentication-mode
        decision is required (enum no=0, biometric=1, password=2, pin=3; preferred:
        biometric - user decision 2026-09-29). Android binds the mode at Keystore
        KEY CREATION during activation: switching later means uninstall/key discard
        plus a FRESH activation code. Guidance without a declared mode must block
        with a prompt, never proceed on a silent default."""
        try:
            UUID(user_uuid)
        except (ValueError, TypeError, AttributeError):
            raise ValueError('Provide the existing user UUID') from None
        if not isinstance(valid_for, str) or not re.fullmatch(r'[1-9][0-9]{0,3}[mhd]', valid_for):
            raise ValueError('Validity must be 1..9999 followed by m, h or d')
        if type(digits) is not int or not 6 <= digits <= 12:
            raise ValueError('Code length must be 6..12 digits')
        dispatched = False
        try:
            with Admin(expected_environment, realm) as api:
                path = '/users/' + segment(user_uuid)
                user = api.raw('GET', path)
                if not isinstance(user, dict) or user.get('id') != user_uuid:
                    raise BackendError('The selected user could not be verified')
                code = resolve(code_reference) if code_reference else ''.join(secrets.choice('0123456789') for _ in range(digits))
                if not re.fullmatch(r'[0-9]{6,12}', code):
                    raise ValueError('Activation code reference must contain 6..12 digits')
                # Only submit the credential field; do not overwrite profile attributes.
                body = {'credentials': [{'type': 'ACTIVATION_CODE',
                        'credentialData': json.dumps({'period': valid_for}),
                        'secretData': json.dumps({'code': code})}]}
                dispatched = True
                api.raw('PUT', path, body)
                stored = api.raw('GET', path + '/credentials')
                if not isinstance(stored, list) or not any(
                        isinstance(item, dict) and item.get('type') == 'ACTIVATION_CODE'
                        for item in stored):
                    raise BackendError('Activation credential not found after write')
                return {'user_uuid': user_uuid, 'activation_code': code,
                        'valid_for': valid_for, 'credential_type_present': True,
                        'exact_value_verified': False, 'device_activated': False}
        except Exception:
            if dispatched:
                raise BackendError('Activation code write may have succeeded, but confirmation failed. Do not automatically retry; inspect user credential state first.') from None
            raise

    @mcp.tool()
    def sdk_idp_activation_code_set(expected_environment: str, user_uuid: str,
                                     code: CredentialRef, valid_for: str = '60d',
                                     realm: str | None = None) -> dict:
        """Store an explicitly supplied activation code from an env/keyring/private-file reference. Same existing-user and readback checks as generation; no default code or automatic retry. Returns metadata only. May replace a previous activation code. A failing code reference or private-file setup reports a metadata-only local diagnostic (permissions/ownership/existence) BEFORE any backend write is dispatched; the uncertain-write warning appears only after dispatch. No plaintext fallback exists."""
        result=sdk_idp_activation_code_generate(expected_environment,user_uuid,valid_for,realm=realm,code_reference=code)
        result.pop('activation_code',None)
        return result

    @mcp.tool()
    def sdk_idp_user_password_set(expected_environment: str, user_uuid: str, credential: CredentialRef,
                                  temporary: bool = True, realm: str | None = None) -> dict:
        """Explicitly reset a user's password from an env/keyring/private-file reference. Requires manage-users; temporary defaults true. No password appears in arguments/results; account reuse never invokes this implicitly."""
        with Admin(expected_environment,realm) as api:
            secret=resolve(credential)
            api.call('PUT','/users/'+segment(user_uuid)+'/reset-password',{'type':'password','value':secret,'temporary':temporary})
            return {'changed':True,'user_uuid':user_uuid,'temporary':temporary}

    @mcp.tool()
    def sdk_idp_client_secret_write(expected_environment: str, client_uuid: str, output_path: str, realm: str | None = None) -> dict:
        """Read a confidential client's existing secret into a NEW private JSON file. Requires client administration; does not rotate it. Use internal client UUID, not public clientId. Returns file metadata only. A failing output destination reports a metadata-only diagnostic (permissions/ownership/existence/provider support) and states that the backend request was not sent; no plaintext fallback."""
        with Admin(expected_environment,realm) as api, output_file(output_path) as (stream,path):
            result=api.raw('GET','/clients/'+segment(client_uuid)+'/client-secret')
            if not isinstance(result,dict) or not result.get('value'):raise BackendError('Client did not return a secret')
            return write_result(stream,path,result)

    @mcp.tool()
    def sdk_idp_client_secret_rotate(expected_environment: str, client_uuid: str, output_path: str, realm: str | None = None) -> dict:
        """Rotate one confidential client's secret and save the new value to a NEW private JSON file. Changes authentication for consumers. Never automatically retry an uncertain rotation; inspect server state first. Output-destination failures are diagnosed with metadata only BEFORE the rotation request is sent (local setup error, backend unchanged); only a post-dispatch failure reports an uncertain backend change."""
        dispatched = False
        try:
            with Admin(expected_environment,realm) as api, output_file(output_path) as (stream,path):
                dispatched = True
                result=api.raw('POST','/clients/'+segment(client_uuid)+'/client-secret')
                if not isinstance(result,dict) or not result.get('value'):
                    raise BackendError('Missing rotation result')
                return {**write_result(stream,path,result),'rotated':True}
        except Exception:
            if dispatched:
                raise BackendError('Client secret rotation may have happened but its private result could not be confirmed. Do not retry rotation; recover the current value with sdk_idp_client_secret_write to a new private file.') from None
            raise

    @mcp.tool()
    def sdk_idp_source_token_write(expected_environment: str, client_id: str, username: str,
                                   password: CredentialRef, output_path: str,
                                   client_secret: CredentialRef | None = None, realm: str | None = None) -> dict:
        """Request a user token using an explicitly configured direct-grant client and credential references; save response privately. Requires that realm/client to allow direct grant. No browser/SSO bypass or automatic retry."""
        with Admin(expected_environment,realm) as api, output_file(output_path) as (stream,path):
            form={'grant_type':'password','client_id':client_id,'username':username,'password':resolve(password)}
            if client_secret:form['client_secret']=resolve(client_secret)
            result=api.backend.send('POST',api.cfg['admin']['idp_url'].rstrip('/')+'/auth/realms/'+segment(api.realm)+'/protocol/openid-connect/token',data=form)
            if not isinstance(result,dict) or not result.get('access_token'):raise BackendError('Token endpoint returned no access token')
            return write_result(stream,path,result)

    @mcp.tool()
    def sdk_idp_token_exchange(expected_environment: str, client_id: str, audience: str,
                               subject_token: CredentialRef, output_path: str,
                               client_secret: CredentialRef | None = None, realm: str | None = None) -> dict:
        """Exchange an authorized subject access token for the requested audience and save the response privately. Realm/client must permit token exchange. Subject reference must resolve to raw token text, not a JSON response file."""
        with Admin(expected_environment,realm) as api, output_file(output_path) as (stream,path):
            form={'grant_type':'urn:ietf:params:oauth:grant-type:token-exchange','client_id':client_id,
                  'audience':audience,'subject_token':resolve(subject_token),'subject_token_type':'urn:ietf:params:oauth:token-type:access_token'}
            if client_secret:form['client_secret']=resolve(client_secret)
            result=api.backend.send('POST',api.cfg['admin']['idp_url'].rstrip('/')+'/auth/realms/'+segment(api.realm)+'/protocol/openid-connect/token',data=form)
            if not isinstance(result,dict) or not result.get('access_token'):raise BackendError('Token endpoint returned no access token')
            return write_result(stream,path,result)

    @mcp.tool()
    def sdk_idp_tenant_create(expected_environment: str, tenant: str, login_theme: str,
                              account_theme: str, provisioning_realm: str) -> dict:
        """Create a KOBIL tenant via v4_realm. Requires tenant-provisioning rights and explicitly chosen provisioning realm/themes. This is not generic Keycloak realm creation; unsupported deployments report an API error."""
        with Admin(expected_environment) as api:
            result=_call(api.backend,api.token,'POST','/auth/realms/'+segment(provisioning_realm)+'/v4_realm',
                         {'realm':tenant,'enabled':True,'loginTheme':login_theme,'accountTheme':account_theme,
                          'adminTheme':account_theme,'emailTheme':account_theme,'bruteForceProtected':True})
            return {'created':True,'tenant':tenant,'result':api._safe(result)}

    @mcp.tool()
    def sdk_idp_tms_trigger(expected_environment: str, user_uuid: str, text: str, realm: str | None = None) -> dict:
        """Trigger a KOBIL v3_user TMS transaction through the IDP route. Separate from AST sdk_tms_trigger; requires IDP TMS rights. Returns transaction metadata, not proof of device confirmation."""
        with Admin(expected_environment,realm) as api:
            result=_call(api.backend,api.token,'POST','/auth/realms/'+segment(api.realm)+'/v3_user/'+segment(user_uuid)+'/tms',{'tmsData':{'text':text,'external':False,'data':{}}})
            return {'result':api._safe(result),'device_confirmed':False}
