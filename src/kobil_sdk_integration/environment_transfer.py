"""Portable multi-environment transfer. Source paths never cross machines."""
import copy
import json
import os
import re
from .age_store import (absolute, atomic_write, writer_lock, read_document,
                        encrypt_write)
from .backend import validate_configuration, authentication, admin_reference, segment
from .credentials import (CredentialError, private_read, resolve, store, delete,
                          imported_keyring_reference, bounded_process, LIMIT, SECRET_LIMIT)


def encrypt_recipients(path, recipients, document):
    if not recipients or len(recipients) > 20 or len(set(recipients)) != len(recipients) or any(
            not isinstance(r, str) or not re.fullmatch(r'age1[0-9a-z]{58}', r) for r in recipients):
        raise CredentialError('CONFIG_INVALID')
    raw = json.dumps(document).encode()
    if len(raw) > LIMIT // 2:
        raise CredentialError('CONFIG_INVALID')
    args = ['age', '--encrypt']
    for public in recipients:
        args.extend(['-r', public])
    code, cipher = bounded_process(args, raw)
    if code or not cipher.startswith(b'age-encryption.org/v1'):
        raise CredentialError('STORE_FAILED')
    atomic_write(path, cipher)


def slots(profile):
    yield 'ast', profile['auth']
    if 'admin' in profile:
        yield 'idp', profile['admin']


def export_bundle(output_path, recipients, profile_files):
    if not profile_files or len(profile_files) > 50:
        raise CredentialError('CONFIG_INVALID')
    # Validate all inputs before resolving any source credential.
    profiles = {}
    for file in profile_files:
        try:
            cfg = json.loads(private_read(absolute(file)))
            validate_configuration(cfg)
            name = cfg['environment']
            if name in profiles:
                raise ValueError()
            normalized = {k: copy.deepcopy(cfg[k]) for k in
                          ('environment', 'tenant', 'ast_url', 'services') if k in cfg}
            normalized.update(schema_version=2, auth=copy.deepcopy(authentication(cfg)))
            if 'admin' in cfg:
                normalized['admin'] = {k: v for k, v in cfg['admin'].items()
                                       if k not in ('password_env', 'credential')}
                normalized['admin']['credential'] = copy.deepcopy(admin_reference(cfg['admin']))
            profiles[name] = normalized
        except CredentialError:
            raise
        except Exception:
            raise CredentialError('CONFIG_INVALID') from None
    path = absolute(output_path)
    with writer_lock(path):
        if os.path.lexists(path):
            raise CredentialError('ALREADY_EXISTS')
        # Recipient validation happens before accessing source providers.
        if not recipients or len(recipients) > 20 or len(set(recipients)) != len(recipients) or any(
                not isinstance(r, str) or not re.fullmatch(r'age1[0-9a-z]{58}', r) for r in recipients):
            raise CredentialError('CONFIG_INVALID')
        keys = {}
        for name, cfg in profiles.items():
            for role, container in slots(cfg):
                service = 'transfer/' + segment(name) + '/' + role
                keys[service] = {'credential': resolve(container['credential'])}
                container['credential'] = {'provider': 'keyring', 'service': service, 'account': 'credential'}
        encrypt_recipients(path, recipients, {'version': 2, 'keychain': keys, 'environments': profiles})
    return {'path': str(path), 'environments': sorted(profiles), 'credential_count': len(keys),
            'secret_returned': False, 'transmitted': False}


def import_bundle(store_path, identity_path, environments, namespace, output_store_path):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', namespace):
        raise CredentialError('CONFIG_INVALID')
    if not environments or len(environments) > 50 or len(set(environments)) != len(environments):
        raise CredentialError('CONFIG_INVALID')
    data = read_document(store_path, identity_path)
    profiles, pending = {}, []
    for name in environments:
        try:
            cfg = copy.deepcopy(data['environments'][name])
            validate_configuration(cfg, name)
            if cfg.get('schema_version') != 2:
                raise ValueError()
            for role, container in slots(cfg):
                ref = container['credential']
                # Treat incoming profiles as data: never resolve sender refs or paths.
                if set(ref) != {'provider', 'service', 'account'} or ref['provider'] != 'keyring':
                    raise ValueError()
                value = data['keychain'][ref['service']][ref['account']]
                if not isinstance(value, str) or not value or len(value.encode()) > SECRET_LIMIT:
                    raise ValueError()
                target = imported_keyring_reference(namespace + '/' + segment(name) + '/' + role, 'credential')
                pending.append((target, value))
                container['credential'] = target
            profiles[name] = cfg
        except Exception:
            raise CredentialError('CONFIG_INVALID') from None
    output = absolute(output_store_path)
    with writer_lock(output):
        if os.path.lexists(output):
            raise CredentialError('ALREADY_EXISTS')
        # Preflight every destination before writing. Unavailable/locked stores fail closed.
        for ref, _ in pending:
            try:
                resolve(ref)
            except CredentialError as error:
                if error.code != 'CREDENTIAL_NOT_FOUND':
                    raise
            else:
                raise CredentialError('ALREADY_EXISTS')
        created = []
        try:
            for ref, value in pending:
                store(ref, value, replace=False)
                created.append(ref)
            # Server URLs/tenant remain encrypted; recipient-local profiles use native keystore refs.
            encrypt_write(output, identity_path, {'version': 2, 'keychain': {}, 'environments': profiles}, False)
        except Exception:
            failed_cleanup = []
            for ref in reversed(created):
                try:
                    delete(ref)
                except Exception:
                    failed_cleanup.append(ref)
            if failed_cleanup:
                return {'status': 'cleanup_required', 'credential_references': failed_cleanup,
                        'secret_returned': False, 'connection_changed': False}
            raise
    return {'status': 'imported', 'store_path': str(output), 'environments': sorted(profiles),
            'credential_references': [ref for ref, _ in pending], 'secret_returned': False,
            'connection_changed': False}


def register(mcp):
    @mcp.tool()
    def sdk_age_server_bundle_export(output_path: str, recipients: list[str], profile_files: list[str]) -> dict:
        """Encrypt up to 50 explicit server profiles and their AST/IDP credentials for recipient public age keys.

        Each owner-only JSON file is a validated connection profile; credential refs may use
        the sender's Keychain, private files, env or age. Values are resolved internally.
        Normalizes legacy profiles and removes sender credential paths from the bundle.
        No private recipient key needed, no overwrite, no backend calls or file transmission.
        All recipients can read all included servers. Share only with intended recipients.
        """
        return export_bundle(output_path, recipients, profile_files)

    @mcp.tool()
    def sdk_age_server_bundle_import(store_path: str, identity_path: str, environments: list[str],
                                     namespace: str, output_store_path: str) -> dict:
        """Import explicitly selected servers from a portable age bundle into local native keystore.

        Uses the recipient's local private identity. Credentials get service names
        kobil-sdk/import/<namespace>/<encoded environment>/ast or /idp. Existing entries
        block the whole import; no replacement. New local encrypted output store retains
        server settings and rewritten keystore refs, never sender paths. Use
        sdk_age_environment_selector_write next to select an imported environment.
        Does not switch the active connection or contact backends. On failure removes
        only entries created by this call; cleanup_required lists any leftovers.
        """
        return import_bundle(store_path, identity_path, environments, namespace, output_store_path)
