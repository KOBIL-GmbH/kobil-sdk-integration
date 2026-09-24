"""Encrypted default delivery; no private identity or plaintext profile is packaged."""
import copy
import json
import os
from importlib.resources import files
from pathlib import Path
import tempfile

from .age_store import (absolute, atomic_write, encrypt_write, project_identity,
                        read_document, writer_lock)
from .backend import validate_configuration
from .credentials import CredentialError, SECRET_LIMIT
from .environment_transfer import slots

DEFAULT = 'akinci'


def bundle_bytes():
    return files('kobil_sdk_integration').joinpath('bundles', 'akinci.age').read_bytes()


def initialize(project_path, bundle_identity_path=None):
    project = absolute(project_path).resolve(strict=True)
    # Always prepare the receiver identity, even before a delivery key is supplied.
    project_identity(str(project))
    local = project / '.kobil-sdk'
    memory = json.loads((local / 'identity-reference.json').read_text())
    identity = memory['identity_path']
    output = local / 'environments.age'
    selector = local / 'connection.json'
    if bundle_identity_path is None:
        return {'status': 'delivery_identity_required', 'default_environment': DEFAULT,
                'project_identity_ready': True, 'connection_changed': False,
                'next_step': 'Provision the bundled delivery identity separately outside the project, then call sdk_default_initialize with its path. The project recipient key alone cannot decrypt the shipped bundle.'}
    delivery_identity = absolute(bundle_identity_path).resolve(strict=True)
    if delivery_identity.is_relative_to(project):
        raise CredentialError('CONFIG_INVALID', 'Keep the delivery private identity outside the project')
    # Installed resources may be world-readable ciphertext; stage privately for the
    # existing strict decrypt reader. No plaintext is ever written to this file.
    with tempfile.TemporaryDirectory(prefix='kobil-default-') as tmp:
        incoming = Path(tmp) / 'bundle.age'
        atomic_write(incoming, bundle_bytes())
        delivery = read_document(incoming, delivery_identity)
    if set(delivery.get('environments', {})) != {DEFAULT}:
        raise CredentialError('CONFIG_INVALID')
    profile = copy.deepcopy(delivery['environments'][DEFAULT])
    validate_configuration(profile, DEFAULT)
    if profile.get('schema_version') != 2:
        raise CredentialError('CONFIG_INVALID')
    pending = {}
    for role, container in slots(profile):
        ref = container['credential']
        if set(ref) != {'provider', 'service', 'account'} or ref['provider'] != 'keyring':
            raise CredentialError('CONFIG_INVALID')
        try:
            secret = delivery['keychain'][ref['service']][ref['account']]
        except (KeyError, TypeError):
            raise CredentialError('CONFIG_INVALID') from None
        if not isinstance(secret, str) or not secret or len(secret.encode()) > SECRET_LIMIT:
            raise CredentialError('CONFIG_INVALID')
        service = 'kobil-sdk/import/bundled/' + DEFAULT + '/' + role
        pending[service] = {'credential': secret}
        container['credential'] = {'provider': 'age', 'store': str(output),
            'identity': identity, 'service': service, 'account': 'credential'}
    validate_configuration(profile, DEFAULT)
    with writer_lock(output):
        exists = os.path.lexists(output)
        document = read_document(output, identity) if exists else {'version': 2, 'keychain': {}, 'environments': {}}
        environments = document.setdefault('environments', {})
        preserved = DEFAULT in environments
        if not preserved:
            if set(pending) & set(document['keychain']):
                raise CredentialError('ALREADY_EXISTS')
            document['keychain'].update(pending)
            environments[DEFAULT] = profile
            encrypt_write(output, identity, document, exists)
        # Never replace another selected server or existing setup. A failed
        # selector write is safe to retry: the encrypted store is retained.
        selected = False
        with writer_lock(selector):
            if not os.path.lexists(selector):
                atomic_write(selector, json.dumps({'age_environment': {
                    'store': str(output), 'identity': identity, 'environment': DEFAULT}}).encode())
                selected = True
    return {'status': 'existing_environment_preserved' if preserved else 'initialized',
            'default_environment': DEFAULT, 'store_path': str(output),
            'connection_path': str(selector), 'selector_created': selected,
            'connection_changed': False, 'secret_returned': False,
            'next_step': 'Launch with KOBIL_SDK_CONNECTION pointing to connection_path. Initialization does not switch a running session or contact the backend.'}


def register(mcp):
    @mcp.tool()
    def sdk_default_status() -> dict:
        """Describe the encrypted default bundled with this package; no decryption or backend calls."""
        cipher = bundle_bytes()
        return {'default_environment': DEFAULT, 'bundled': cipher.startswith(b'age-encryption.org/v1'),
                'private_key_bundled': False, 'initialization_tool': 'sdk_default_initialize',
                'requires_separately_provisioned_delivery_identity': True}

    @mcp.tool()
    def sdk_default_initialize(project_path: str, bundle_identity_path: str | None = None) -> dict:
        """Initialize the shipped encrypted default in project-local environments.age.

        Creates/reuses a project identity kept outside the project. Without a delivery
        identity returns setup guidance. A separately provisioned delivery identity
        decrypts the bundle; credentials are re-encrypted for the project identity.
        Preserves existing server profiles, credentials and connection selectors.
        No raw credentials, automatic backend calls, or current-session switching.
        """
        return initialize(project_path, bundle_identity_path)
