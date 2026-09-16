"""Bounded subprocess for OS prompts. Private pipe protocol, not a public CLI."""
import contextlib
import io
import json
import sys
from .credentials import CredentialError, SECRET_LIMIT, identifier


def native_backend():
    # Do not call keyring.get_keyring(): config, entry points and environment may
    # select unsafe or third-party providers. Instantiate only supported natives.
    try:
        if sys.platform == 'darwin':
            from keyring.backends.macOS import Keyring
        elif sys.platform == 'win32':
            from keyring.backends.Windows import WinVaultKeyring as Keyring
        elif sys.platform.startswith('linux'):
            from keyring.backends.SecretService import Keyring
        else: raise CredentialError('PROVIDER_UNAVAILABLE')
        return Keyring()
    except Exception:
        raise CredentialError('PROVIDER_UNAVAILABLE') from None


def operate(data):
    from keyring.errors import KeyringLocked, InitError, NoKeyringError
    service, account = identifier(data['service']), identifier(data['account'])
    backend = native_backend()
    try:
        credential = backend.get_credential(service, account)
        # Windows compound-target lookup can return an entry with a different
        # username. Never accept it (or overwrite it as a different identity).
        if credential is not None and credential.username != account:
            raise CredentialError('ACCESS_DENIED')
        if data['operation'] == 'get':
            return {'ok': True, 'value': credential.password if credential else None}
        if data['operation'] == 'set':
            value = data['value']
            if not isinstance(value, str) or not value or len(value) > SECRET_LIMIT or '\x00' in value:
                raise CredentialError('CONFIG_INVALID')
            if credential and data.get('replace') is not True: raise CredentialError('ALREADY_EXISTS')
            backend.set_password(service, account, value)
        elif data['operation'] == 'delete':
            if not credential: raise CredentialError('CREDENTIAL_NOT_FOUND')
            backend.delete_password(service, account)
        else: raise CredentialError('CONFIG_INVALID')
        return {'ok': True}
    except CredentialError: raise
    except KeyringLocked: raise CredentialError('STORE_LOCKED') from None
    except (InitError, NoKeyringError): raise CredentialError('PROVIDER_UNAVAILABLE') from None
    except Exception: raise CredentialError('ACCESS_DENIED') from None


def main():
    try:
        raw = sys.stdin.buffer.read(1048577)
        if len(raw) > 1048576: raise CredentialError('CONFIG_INVALID')
        # Backend diagnostics must never reach the caller or MCP stdout.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = operate(json.loads(raw))
    except CredentialError as error: result = {'ok': False, 'error': error.code}
    except Exception: result = {'ok': False, 'error': 'CONFIG_INVALID'}
    sys.stdout.write(json.dumps(result))


if __name__ == '__main__': main()
