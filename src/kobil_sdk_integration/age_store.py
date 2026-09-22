"""Local encrypted store authoring. Plaintext exists only in bounded memory/pipes."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import tempfile
from .credentials import (CredentialError, private_read, bounded_process, identifier,
                          resolve, store as keyring_store, LIMIT)


def absolute(value):
    p=Path(value).expanduser()
    if not p.is_absolute():raise CredentialError('CONFIG_INVALID')
    return p


def recipient(identity):
    identity=absolute(identity)
    data=private_read(identity)
    try:
        keys=[line for line in data.decode().splitlines() if line and not line.startswith('#')]
        if len(keys)!=1 or not re.fullmatch(r'AGE-SECRET-KEY-1[0-9A-Z]+',keys[0]):raise ValueError()
        code,out=bounded_process(['age-keygen','-y',str(identity)])
        value=out.decode().strip()
        if code or not re.fullmatch(r'age1[0-9a-z]+',value):raise ValueError()
        return value
    except Exception:raise CredentialError('CONFIG_INVALID') from None


def read_document(store,identity):
    # Preserve access errors and identify the input without exposing file contents.
    try:
        recipient(identity)
    except CredentialError as error:
        if error.code == 'ACCESS_DENIED':
            raise CredentialError('ACCESS_DENIED', 'private identity: check existence, ownership, owner-only permissions and symlinks; key matching has not been checked') from None
        raise
    try:
        ciphertext = private_read(absolute(store))
    except CredentialError as error:
        if error.code == 'ACCESS_DENIED':
            raise CredentialError('ACCESS_DENIED', 'encrypted bundle/store: check existence, ownership, owner-only permissions and symlinks; decryption has not been attempted') from None
        raise
    code,out=bounded_process(['age','--decrypt','--identity',str(absolute(identity))],ciphertext)
    try:
        if code:raise ValueError()
        data=json.loads(out)
        if not isinstance(data,dict) or set(data)-{'version','keychain','environments'} or type(data.get('version')) is not int or data['version']!=2 or not isinstance(data.get('keychain'),dict) or not isinstance(data.get('environments',{}),dict):raise ValueError()
        return data
    except Exception:raise CredentialError('AGE_DECRYPT_FAILED') from None


@contextmanager
def writer_lock(path):
    lock=path.with_name(path.name+'.lock')
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except OSError:raise CredentialError('STORE_FAILED') from None
    try:yield
    finally:os.close(fd);lock.unlink(missing_ok=True)


def atomic_write(path,data,replace=False):
    """Same-directory atomic publication; create refuses even dangling symlinks."""
    temp=None
    try:
        fd,temp=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
        with os.fdopen(fd,'wb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        if replace:os.replace(temp,path)
        else:os.link(temp,path)
    except FileExistsError:raise CredentialError('ALREADY_EXISTS') from None
    except OSError:raise CredentialError('STORE_FAILED') from None
    finally:
        if temp:Path(temp).unlink(missing_ok=True)


def encrypt_write(path,identity,data,replace):
    raw=json.dumps(data).encode()
    if len(raw)>LIMIT//2:raise CredentialError('CONFIG_INVALID')
    code,cipher=bounded_process(['age','--encrypt','-r',recipient(identity)],raw)
    if code or not cipher.startswith(b'age-encryption.org/v1'):raise CredentialError('STORE_FAILED')
    atomic_write(path,cipher,replace)


def register(mcp):
    @mcp.tool()
    def sdk_age_identity_create(identity_path: str) -> dict:
        """Generate a native age identity in a NEW mode0600 file. Returns only its public recipient. Keep the identity separate from encrypted stores; losing it prevents recovery. Existing files are never replaced."""
        path=absolute(identity_path)
        code,data=bounded_process(['age-keygen'])
        if code or b'AGE-SECRET-KEY-' not in data:raise CredentialError('STORE_FAILED')
        # The only plaintext file written is the explicitly requested private identity.
        atomic_write(path,data)
        return {'identity_path':str(path),'recipient':recipient(path),'created':True}

    @mcp.tool()
    def sdk_age_store_create(store_path: str, identity_path: str) -> dict:
        """Create a NEW encrypted age store for credentials and named environments. Uses one explicitly selected native identity; existing files are never replaced. No backend or OS keystore changes."""
        path=absolute(store_path)
        with writer_lock(path):encrypt_write(path,identity_path,{'version':2,'keychain':{},'environments':{}},False)
        return {'store_path':str(path),'created':True}

    @mcp.tool()
    def sdk_age_credential_put(store_path: str, identity_path: str, service: str,
                               account: str, source: dict, replace: bool = False) -> dict:
        """Store a password/token from an env, private-file, keyring or age reference inside the encrypted store. Suitable for AST/IDP and SFTP/SCP passwords. No raw password argument; source is a credential-reference object. Existing entries require replace=true. Only the selected entry changes; source is retained. Re-encrypts to the selected identity only."""
        identifier(service);identifier(account);path=absolute(store_path)
        with writer_lock(path):
            data=read_document(path,identity_path)
            entries=data['keychain'].setdefault(service,{})
            if not isinstance(entries,dict):raise CredentialError('CONFIG_INVALID')
            if account in entries and not replace:raise CredentialError('ALREADY_EXISTS')
            entries[account]=resolve(source)
            encrypt_write(path,identity_path,data,True)
        return {'stored':True,'service':service,'account':account,'secret_returned':False}

    @mcp.tool()
    def sdk_age_environment_put(store_path: str, identity_path: str, environment: str,
                                profile_file: str, replace: bool = False) -> dict:
        """Store a named, validated AST/IDP connection profile inside the encrypted store. Input is an owner-only JSON file containing URLs, tenant and credential references, not inline passwords. Name must match its environment field. Does not switch the active MCP connection. Existing names require replace=true."""
        from .backend import validate_configuration
        identifier(environment)
        try:profile=json.loads(private_read(absolute(profile_file)))
        except CredentialError:raise
        except Exception:raise CredentialError('CONFIG_INVALID') from None
        validate_configuration(profile,environment)
        path=absolute(store_path)
        with writer_lock(path):
            data=read_document(path,identity_path)
            environments=data.setdefault('environments',{})
            if environment in environments and not replace:raise CredentialError('ALREADY_EXISTS')
            environments[environment]=profile
            encrypt_write(path,identity_path,data,True)
        return {'stored':True,'environment':environment,'connection_changed':False}

    @mcp.tool()
    def sdk_age_store_list(store_path: str, identity_path: str) -> dict:
        """Decrypt locally and list environment names and service/account labels only. No passwords, tokens, server URLs, full profiles or secret fingerprints returned."""
        data=read_document(store_path,identity_path)
        return {'environments':sorted(data.get('environments',{})),
                'credentials':[{'service':s,'account':a} for s,entries in data['keychain'].items() for a in entries]}

    @mcp.tool()
    def sdk_age_environment_export(store_path: str, identity_path: str, environment: str,
                                   output_path: str) -> dict:
        """Export one reference-only backend profile to a NEW private file for KOBIL_SDK_CONNECTION. No credential values are copied out. Does not switch the current connection or restart the host. Identity/store paths in its references remain as originally supplied."""
        from .backend import validate_configuration
        data=read_document(store_path,identity_path)
        profile=data.get('environments',{}).get(environment)
        validate_configuration(profile,environment)
        output=absolute(output_path)
        atomic_write(output,json.dumps(profile,indent=2).encode())
        return {'path':str(output),'environment':environment,'connection_changed':False}


    @mcp.tool()
    def sdk_age_environment_selector_write(store_path: str, identity_path: str, environment: str,
                                           output_path: str) -> dict:
        """Create a NEW private selector file for KOBIL_SDK_CONNECTION. Only encrypted-store/identity paths and environment name are written; server settings stay encrypted. Verifies the named profile without resolving passwords. Does not change or restart the host's current MCP session."""
        from .backend import validate_configuration
        data=read_document(store_path,identity_path)
        validate_configuration(data.get('environments',{}).get(environment),environment)
        selector={'age_environment':{'store':str(absolute(store_path)),
                                    'identity':str(absolute(identity_path)),'environment':environment}}
        output=absolute(output_path)
        atomic_write(output,json.dumps(selector,indent=2).encode())
        return {'path':str(output),'environment':environment,'settings_encrypted':True,'connection_changed':False}


    @mcp.tool()
    def sdk_age_transfer_export(output_path: str, recipients: list[str], entries: list[dict]) -> dict:
        """Export explicitly selected credential references into a NEW age file encrypted to destination PUBLIC recipients (age1...). Each entry has service, account and source (env/file/keyring/age reference). Supports Mac-to-Mac or Mac-to-Windows transfer without sharing private identities. No automatic credential enumeration, overwrite or file transmission. All recipients can decrypt all included entries; verify intended public recipients before export."""
        if not recipients or len(recipients)>20 or len(set(recipients))!=len(recipients) or any(
                not isinstance(r,str) or not re.fullmatch(r'age1[0-9a-z]{58}',r) for r in recipients):
            raise CredentialError('CONFIG_INVALID')
        if not entries or len(entries)>100:raise CredentialError('CONFIG_INVALID')
        from .credentials import validate_reference
        seen=set()
        for entry in entries:
            if not isinstance(entry,dict) or set(entry)!={'service','account','source'}:raise CredentialError('CONFIG_INVALID')
            pair=(identifier(entry['service']),identifier(entry['account']))
            if pair in seen:raise CredentialError('CONFIG_INVALID')
            seen.add(pair);validate_reference(entry['source'])
        path=absolute(output_path)
        with writer_lock(path):
            if os.path.lexists(path):raise CredentialError('ALREADY_EXISTS')
            data={'version':2,'keychain':{}}
            for entry in entries:
                data['keychain'].setdefault(entry['service'],{})[entry['account']]=resolve(entry['source'])
            raw=json.dumps(data).encode()
            if len(raw)>LIMIT//2:raise CredentialError('CONFIG_INVALID')
            argv=['age','--encrypt']
            for public in recipients:argv.extend(['-r',public])
            code,cipher=bounded_process(argv,raw)
            if code or not cipher.startswith(b'age-encryption.org/v1'):raise CredentialError('STORE_FAILED')
            atomic_write(path,cipher)
        return {'path':str(path),'entry_count':len(entries),'recipient_count':len(recipients),
                'secret_returned':False,'transmitted':False}

    @mcp.tool()
    def sdk_age_credential_import_keyring(store_path: str, identity_path: str, service: str,
                                          account: str, destination_service: str,
                                          destination_account: str, replace: bool = False) -> dict:
        """Decrypt one explicitly named entry and import it into the local native keystore: macOS Keychain, Windows Credential Manager or Linux Secret Service. Private destination identity stays on this machine. destination_service is a label: the actual service is kobil-sdk/import/<label>. Returns the exact credential_reference for the local profile; never reuses the source service. Never enumerates/imports the whole store. Existing destination entries require replace=true. No secret values returned; encrypted source retained. OS authorization may be required."""
        source={'provider':'age','store':str(absolute(store_path)),'identity':str(absolute(identity_path)),
                'service':identifier(service),'account':identifier(account)}
        from .credentials import imported_keyring_reference
        target=imported_keyring_reference(destination_service,destination_account)
        value=resolve(source)
        keyring_store(target,value,replace=replace)
        return {'imported':True,'service':target['service'],'account':target['account'],
                'provider':'keyring','credential_reference':target,'secret_returned':False}
