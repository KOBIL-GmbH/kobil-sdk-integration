"""Obtain the trusted root certificate the SDK pins the backend hosts to.

mc_config.json names a PEM file bundled with the app (trustedSslServerCerts) and the
signed SDK configuration carries the same certificates; the SDK refuses a host whose
chain does not end in one of them. No tool supplied that file before: the developer had
to know which root the deployment uses and fetch it by hand. This reads the verified
chain of the IDP host, keeps its self-signed root, writes it as PEM, and proves that
every backend host in the connection file chains to that root.
"""
import hashlib
import os
import socket
import ssl
from pathlib import Path
from urllib.parse import urlsplit

from .backend import BackendError


def certificate_record(cert):
    """A plain record of one certificate from a verified chain.

    The private chain accessor yields certificate objects with get_info(); the public one
    (Python 3.13) yields DER bytes, whose names are read through the interpreter's own
    decoder from a private temporary file.
    """
    import _ssl
    if isinstance(cert, (bytes, bytearray)):
        der = bytes(cert)
        pem = ssl.DER_cert_to_PEM_cert(der)
        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.pem', delete=True) as handle:
            handle.write(pem)
            handle.flush()
            info = ssl._ssl._test_decode_cert(handle.name)
    else:
        der = cert.public_bytes(_ssl.ENCODING_DER)
        pem = cert.public_bytes(_ssl.ENCODING_PEM)
        info = cert.get_info()
    return {'pem': pem, 'subject': _name(info.get('subject')), 'issuer': _name(info.get('issuer')),
            'not_after': info.get('notAfter'), 'sha256': hashlib.sha256(der).hexdigest()}


def _name(rdns):
    parts = {}
    for rdn in rdns or ():
        for key, value in rdn:
            parts[key] = value
    return parts.get('commonName') or ', '.join('%s=%s' % kv for kv in parts.items())


def fetch_verified_chain(host, port=443, timeout=15):
    """The chain the local trust store accepted for this host, leaf first."""
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as raw, \
                context.wrap_socket(raw, server_hostname=host) as tls:
            private = getattr(getattr(tls, '_sslobj', None), 'get_verified_chain', None)
            getter = private or tls.get_verified_chain
            return [certificate_record(c) for c in getter()]
    except (OSError, ssl.SSLError, AttributeError) as exc:
        raise BackendError('Cannot read the TLS chain of %s: %s' % (host, exc.__class__.__name__)) from None


def select_root(chain):
    """The self-signed root of a chain; the last certificate when none is self-signed."""
    if not chain:
        raise BackendError('The host presented no verified certificate chain')
    for record in chain:
        if record['subject'] == record['issuer']:
            return record
    return chain[-1]


def backend_hosts(cfg):
    """Every host the SDK will talk to, from the connection file, in a stable order."""
    urls = [cfg.get('ast_url')] + [s.get('url') for s in cfg.get('services') or [] if isinstance(s, dict)]
    admin = cfg.get('admin') or {}
    urls.append(admin.get('idp_url') or (cfg.get('oauth') or {}).get('token_url'))
    hosts = []
    for url in urls:
        host = urlsplit(url).hostname if isinstance(url, str) else None
        if host and host not in hosts:
            hosts.append(host)
    return hosts


def host_trusts_root(host, cafile, port=443, timeout=15):
    """True when a context that trusts only this file completes a handshake with the host."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(cafile=str(cafile))
    try:
        with socket.create_connection((host, port), timeout=timeout) as raw, \
                context.wrap_socket(raw, server_hostname=host):
            return True
    except (OSError, ssl.SSLError):
        return False


def write_root_certificate(cfg, output_path, host=None, fetch=fetch_verified_chain, verify=host_trusts_root):
    """Write the IDP host's root certificate to a NEW PEM file and check every backend host against it."""
    hosts = backend_hosts(cfg)
    if host is not None:
        if not isinstance(host, str) or not host or '/' in host or ' ' in host:
            raise ValueError('Provide a bare host name')
    target = host or (hosts[-1] if hosts else None)
    if not target:
        raise BackendError('The connection file names no host to read a certificate from')
    path = Path(output_path).expanduser()
    if not path.parent.is_dir():
        raise ValueError('Output directory must exist')
    if path.exists():
        raise ValueError('Output file already exists; choose a new file name')
    root = select_root(fetch(target))
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(root['pem'])
    trusted = [h for h in hosts if verify(h, path)]
    untrusted = [h for h in hosts if h not in trusted]
    return {'path': str(path), 'file_name': path.name, 'subject': root['subject'],
            'sha256': root['sha256'], 'not_after': root['not_after'], 'read_from': target,
            'hosts_trusting_this_root': trusted, 'hosts_not_trusting_this_root': untrusted,
            'note': ('Bundle this file with the app under exactly this name, pass the name to '
                     'sdk_mc_config as certificate_file and the path to sdk_config_write in '
                     'certificate_paths. A host listed as not trusting it needs its own root '
                     'in both places.')}
