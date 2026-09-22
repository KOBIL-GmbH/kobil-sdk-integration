"""Manage only credentials selected by the current connection profile."""
from typing import Literal
from .backend import configuration, authentication, admin_reference
from .credentials import resolve, store, delete, CredentialError, require_import_namespace
from .idp_secrets import CredentialRef


def selected(environment, service):
    cfg=configuration(environment)
    if service=='ast':return authentication(cfg)['credential']
    if service=='idp' and cfg.get('admin'):return admin_reference(cfg['admin'])
    raise ValueError('Select a configured ast or idp service')


def register(mcp):
    @mcp.tool()
    def sdk_credential_status(expected_environment: str, service: Literal['ast','idp'] = 'ast', probe: bool = False) -> dict:
        """Inspect the selected profile's credential provider. Default does not unlock the store or contact the backend. probe resolves the credential server-side and returns presence/error status only. No secret or secret fingerprint is returned. Use sdk_backend_auth_test separately to test authentication."""
        ref=selected(expected_environment,service)
        result={'service':service,'provider':ref['provider'],'configured':True,'credential_checked':probe,'backend_checked':False}
        if probe:
            try:resolve(ref);result['available']=True
            except CredentialError as error:result.update(available=False,error_code=error.code)
        return result

    @mcp.tool()
    def sdk_credential_import(expected_environment: str, source: CredentialRef,
                               service: Literal['ast','idp'] = 'ast', replace: bool = False) -> dict:
        """Import one server-side credential reference into the native keystore entry selected by the current profile. Source may be a private file, age envelope, environment or keystore reference; no raw secret arguments. Destination must be keyring under kobil-sdk/import/. Other destinations fail before resolving the source; update the selected profile explicitly to an imported credential reference. Existing entries are preserved unless replace=true. Does not delete source files, switch profiles or alter backend accounts. OS authorization may be required."""
        ref=selected(expected_environment,service)
        require_import_namespace(ref)
        value=resolve(source.model_dump(exclude_none=True))
        store(ref,value,replace=replace)
        return {'stored':True,'service':service,'provider':'keyring','backend_changed':False}

    @mcp.tool()
    def sdk_credential_delete(expected_environment: str, service: Literal['ast','idp'] = 'ast', confirm: bool = False) -> dict:
        """Delete only the native keystore entry selected for this connection/service. Requires confirm=true. This removes a local credential, not a backend account. Profile and any configured age fallback remain; fallback may still allow authentication."""
        if confirm is not True:raise ValueError('Set confirm=true to delete the selected local credential')
        ref=selected(expected_environment,service)
        delete(ref)
        return {'deleted':True,'service':service,'fallback_configured':'fallback' in ref,'backend_changed':False}
