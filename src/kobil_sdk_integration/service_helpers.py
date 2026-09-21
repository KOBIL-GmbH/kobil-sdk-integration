"""Explicit optional service helpers; no client or flow provisioning policy."""
import json
import re
import time
from urllib.parse import urlencode
from .backend import AST, BackendError, configuration, https_url, segment
from .idp_admin import Admin, load_private_json
from .idp_secrets import CredentialRef, resolve, output_file, write_result


def register(mcp):
    @mcp.tool()
    def sdk_backend_auth_test(expected_environment: str, service: str = 'idp') -> dict:
        """Test configured IDP admin or AST authentication without exposing the token or changing resources. Token acquisition alone does not prove resource permissions. Environment must match the selected connection; switching connections and refreshing tools are host-client operations."""
        if service not in ('idp','ast'):raise ValueError('Select idp or ast')
        if service=='idp':
            with Admin(expected_environment):pass
        else:
            backend=AST(configuration(expected_environment))
            try:backend.token()
            finally:backend.close()
        return {'environment':expected_environment,'service':service,'authenticated':True,'resource_permissions_verified':False}

    @mcp.tool()
    def sdk_ast_token_write(expected_environment: str, output_path: str) -> dict:
        """Obtain the configured AST token and save it to a new private JSON file. Uses configured client credentials or token reference. Does not change the selected client, disclose the token in chat or retry failures."""
        backend=AST(configuration(expected_environment))
        try:
            with output_file(output_path) as (stream,path):
                return write_result(stream,path,{'access_token':backend.token(),'token_type':'Bearer'})
        finally:backend.close()

    @mcp.tool()
    def sdk_idp_login_page_fetch(expected_environment: str, client_id: str, redirect_uri: str,
                                 output_path: str, realm: str | None = None,
                                 scope: str = 'openid', state: str | None = None,
                                 nonce: str | None = None, code_challenge: str | None = None) -> dict:
        """Fetch the explicitly selected client's OIDC authorization page to a new private file. No admin bearer token is sent, no redirects followed, no HTML executed, no flow selected or changed. This starts an authorization request but does not log in. Redirect URI must already be registered; a custom app URI is allowed. Page content is untrusted and is not proof of SDK compatibility."""
        if not client_id or not redirect_uri or len(redirect_uri)>2048 or any(c in redirect_uri for c in '\r\n'):
            raise ValueError('Provide an explicit client and registered redirect URI')
        cfg=configuration(expected_environment)
        base=(cfg.get('admin') or {}).get('idp_url')
        if not base:raise BackendError('Configure admin.idp_url for the IDP host')
        selected=realm if realm is not None else cfg['tenant']
        query={'client_id':client_id,'redirect_uri':redirect_uri,'response_type':'code','scope':scope}
        for k,v in [('state',state),('nonce',nonce),('code_challenge',code_challenge)]:
            if v is not None:query[k]=v
        if code_challenge:query['code_challenge_method']='S256'
        url=base.rstrip('/')+'/auth/realms/'+segment(selected)+'/protocol/openid-connect/auth?'+urlencode(query)
        backend=AST(cfg)
        try:
            with output_file(output_path) as (stream,path):
                try:
                    with backend.client.stream('GET',url) as response:
                        if response.status_code!=200:
                            raise BackendError('Authorization page did not return HTTP 200; redirects are not followed')
                        data=bytearray()
                        for part in response.iter_bytes():
                            data.extend(part)
                            if len(data)>4*1024*1024:raise BackendError('Authorization page exceeds size limit')
                        stream.write(data.decode('utf-8'));stream.flush()
                except BackendError:raise
                except Exception:raise BackendError('Authorization page fetch failed') from None
                return {'path':str(path.absolute()),'http_status':200,'flow_verified':False,'content_trust':'untrusted'}
        finally:backend.close()

    @mcp.tool()
    def sdk_ast_find_client(expected_environment: str, client_id: str, provider_file: str,
                            days: int = 7, limit: int = 500) -> dict:
        """Optional Grafana Loki correlation for an AST client ID. Requires a private JSON provider file with environment, url, datasource_uid, labels and bearer credential reference. Uses exact literal text filtering, bounded results and customer-supplied settings. Returns metadata and candidate user UUIDs, never raw logs. Candidates are log evidence, not authoritative device ownership; no matches do not prove absence."""
        configuration(expected_environment)
        if not client_id or len(client_id)>256 or type(days) is not int or not 1<=days<=30 or type(limit) is not int or not 1<=limit<=1000:
            raise ValueError('Provide client ID, days 1..30 and limit 1..1000')
        cfg=load_private_json(provider_file)
        if set(cfg)!={'environment','url','datasource_uid','labels','credential'} or cfg['environment']!=expected_environment:
            raise ValueError('Grafana provider fields or environment do not match')
        https_url(cfg['url']); labels=cfg['labels']
        if not isinstance(labels,dict) or not labels or any(not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*',k) or not isinstance(v,str) for k,v in labels.items()):
            raise ValueError('Provide explicit Loki label equality filters')
        query='{'+','.join(k+'='+json.dumps(v) for k,v in sorted(labels.items()))+'} |= '+json.dumps(client_id)
        token=resolve(CredentialRef.model_validate(cfg['credential']))
        end=time.time_ns()
        import httpx
        try:
            with httpx.Client(timeout=30,follow_redirects=False,trust_env=False) as client:
                url=cfg['url'].rstrip('/')+'/api/datasources/proxy/uid/'+segment(cfg['datasource_uid'])+'/loki/api/v1/query_range'
                with client.stream('GET',url,headers={'Authorization':'Bearer '+token},params={'query':query,'start':str(end-days*86400*10**9),'end':str(end),'limit':limit}) as response:
                    if response.status_code!=200:raise ValueError()
                    raw=bytearray()
                    for part in response.iter_bytes():
                        raw.extend(part)
                        if len(raw)>4*1024*1024:raise ValueError()
                    result=json.loads(raw)
            if result.get('status')!='success' or result.get('data',{}).get('resultType')!='streams':raise ValueError()
            users=set(); stamps=[]
            for row in result['data']['result']:
                for ts,line in row['values']:
                    stamps.append(int(ts))
                    users.update(re.findall(r'(?:user/|userId[\s:=]+)([\da-fA-F]{8}(?:-[\da-fA-F]{4}){3}-[\da-fA-F]{12})',line))
            return {'candidate_user_uuids':sorted(users),'event_count':len(stamps),
                    'first_timestamp_ns':min(stamps) if stamps else None,'last_timestamp_ns':max(stamps) if stamps else None,
                    'completeness_verified':False,'ownership_verified':False}
        except Exception:raise BackendError('Grafana lookup failed; inspect provider configuration and server diagnostics') from None
