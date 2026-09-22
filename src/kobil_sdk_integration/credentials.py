"""Local credential references. Values never form part of the MCP interface."""
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading

LIMIT = 1024 * 1024
SECRET_LIMIT = 65536
CODES = {'CONFIG_INVALID', 'CREDENTIAL_NOT_FOUND', 'STORE_LOCKED', 'ACCESS_DENIED',
         'PROVIDER_UNAVAILABLE', 'AGE_DECRYPT_FAILED', 'STORE_FAILED', 'ALREADY_EXISTS'}


class CredentialError(RuntimeError):
    def __init__(self, code):
        self.code = code if code in CODES else 'ACCESS_DENIED'
        super().__init__(self.code + ': use local credential setup; no secret values are returned')


def identifier(value):
    if not isinstance(value, str) or not value or len(value) > 256 or any(ord(c) < 32 for c in value):
        raise CredentialError('CONFIG_INVALID')
    return value


def validate_reference(ref, nested=False):
    if not isinstance(ref, dict):
        raise CredentialError('CONFIG_INVALID')
    provider = ref.get('provider')
    if not isinstance(provider, str): raise CredentialError('CONFIG_INVALID')
    fields = {'env': {'provider', 'name'}, 'keyring': {'provider', 'service', 'account'},
              'age': {'provider', 'store', 'identity', 'service', 'account'}, 'file': {'provider', 'path'}}.get(provider)
    if not fields or set(ref) - fields - ({'fallback'} if provider == 'keyring' and not nested else set()) or fields - set(ref):
        raise CredentialError('CONFIG_INVALID')
    if provider == 'env':
        if not isinstance(ref['name'], str) or not re.fullmatch(r'[A-Z][A-Z0-9_]*', ref['name']):
            raise CredentialError('CONFIG_INVALID')
    elif provider == 'file':
        if not isinstance(ref['path'], str) or not Path(ref['path']).expanduser().is_absolute():
            raise CredentialError('CONFIG_INVALID')
    else:
        identifier(ref['service']); identifier(ref['account'])
    if provider == 'age':
        for key in ('store', 'identity'):
            if not isinstance(ref[key], str) or not Path(ref[key]).is_absolute():
                raise CredentialError('CONFIG_INVALID')
    if 'fallback' in ref:
        validate_reference(ref['fallback'], nested=True)
        if ref['fallback']['provider'] != 'age':
            raise CredentialError('CONFIG_INVALID')
    return ref


def bounded_process(argv, data=b'', timeout=30, env=None):
    """Bound pipe output and runtime; never include child output in exceptions."""
    try:
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, env=env)
    except OSError:
        raise CredentialError('PROVIDER_UNAVAILABLE') from None
    buffers = [bytearray(), bytearray()]
    overflow = threading.Event()
    def drain(stream, buffer):
        try:
            while chunk := stream.read(4096):
                if len(buffer) + len(chunk) > LIMIT:
                    overflow.set(); process.kill(); break
                buffer.extend(chunk)
        finally:
            stream.close()
    def feed():
        try:
            process.stdin.write(data)
            process.stdin.close()
        except (OSError, BrokenPipeError):
            pass
    threads = [threading.Thread(target=drain, args=(process.stdout, buffers[0]), daemon=True),
               threading.Thread(target=drain, args=(process.stderr, buffers[1]), daemon=True),
               threading.Thread(target=feed, daemon=True)]
    for thread in threads: thread.start()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill(); process.wait()
        raise CredentialError('ACCESS_DENIED') from None
    finally:
        for thread in threads: thread.join(timeout=1)
    if overflow.is_set() or any(thread.is_alive() for thread in threads):
        raise CredentialError('ACCESS_DENIED')
    return process.returncode, bytes(buffers[0])


def native_call(operation, ref, value=None, replace=False):
    payload = {'operation': operation, 'service': ref['service'], 'account': ref['account'],
               'value': value, 'replace': replace}
    worker_env = {k:v for k,v in os.environ.items() if not k.startswith('KEYRING_') and k not in {'KEYCHAIN_PATH', 'PYTHON_KEYRING_BACKEND'}}
    code, output = bounded_process([sys.executable, '-I', '-m', 'kobil_sdk_integration.credential_worker'],
                                  json.dumps(payload).encode(), timeout=120, env=worker_env)
    try:
        result = json.loads(output)
        if code or not result.get('ok'):
            raise CredentialError(result.get('error', 'ACCESS_DENIED'))
        return result.get('value')
    except (ValueError, AttributeError):
        raise CredentialError('ACCESS_DENIED') from None


def private_read(path):
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
        with os.fdopen(fd, 'rb') as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > LIMIT:
                raise CredentialError('CONFIG_INVALID')
            if os.name == 'posix' and (info.st_uid != os.getuid() or info.st_mode & 0o077):
                raise CredentialError('ACCESS_DENIED')
            data = handle.read(LIMIT + 1)
            if len(data) > LIMIT: raise CredentialError('CONFIG_INVALID')
            return data
    except OSError:
        raise CredentialError('ACCESS_DENIED') from None


def age_read(ref):
    # Only native age identities; disallow plugins and interactive passphrase inputs.
    identity = private_read(ref['identity'])
    try:
        keys = [line for line in identity.decode().splitlines() if line and not line.startswith('#')]
        if not keys or any(not re.fullmatch(r'AGE-SECRET-KEY-1[0-9A-Z]+', line) for line in keys):
            raise CredentialError('CONFIG_INVALID')
        ciphertext = private_read(ref['store'])
        # age receives only the explicit prevalidated identity path, never key bytes
        # in argv. Ciphertext and plaintext travel through private captured pipes.
        code, output = bounded_process(['age', '--decrypt', '--identity', ref['identity']], ciphertext)
        if code: raise CredentialError('AGE_DECRYPT_FAILED')
        data = json.loads(output)
        if not isinstance(data, dict) or (set(data)-{'version', 'keychain', 'environments'} or not {'version','keychain'} <= set(data)) or type(data['version']) is not int or data['version'] != 2:
            raise ValueError()
        services = data['keychain']
        if not isinstance(services, dict): raise ValueError()
        accounts = services.get(ref['service'], {})
        if not isinstance(accounts, dict): raise ValueError()
        return accounts.get(ref['account'])
    except CredentialError:
        raise
    except Exception:
        raise CredentialError('AGE_DECRYPT_FAILED') from None


def resolve(ref):
    validate_reference(ref)
    provider = ref['provider']
    if provider == 'env': value = os.environ.get(ref['name'])
    elif provider == 'age': value = age_read(ref)
    elif provider == 'file':
        try:value=private_read(Path(ref['path']).expanduser()).decode().rstrip('\r\n')
        except CredentialError:raise
        except Exception:raise CredentialError('CONFIG_INVALID') from None
    else:
        value = native_call('get', ref)
    if value is None or value == '':
        if 'fallback' in ref: return resolve(ref['fallback'])
        raise CredentialError('CREDENTIAL_NOT_FOUND')
    if not isinstance(value, str) or len(value) > SECRET_LIMIT or '\x00' in value:
        raise CredentialError('CONFIG_INVALID')
    return value


def store(ref, value, replace=False):
    validate_reference(ref)
    if ref['provider'] != 'keyring': raise CredentialError('CONFIG_INVALID')
    if not isinstance(value, str) or not value or len(value) > SECRET_LIMIT or '\x00' in value:
        raise CredentialError('CONFIG_INVALID')
    native_call('set', ref, value, replace)


def delete(ref):
    validate_reference(ref)
    if ref['provider'] != 'keyring': raise CredentialError('CONFIG_INVALID')
    native_call('delete', ref)
