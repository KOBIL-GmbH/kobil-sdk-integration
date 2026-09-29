"""Compare served TLS chains against a local trust asset before device runs.

Motivated by VAL-16/VAL-36 (2026-09-29): akinci *.sicher.men served
leaf <- YE2 <- Root YE <- ISRG Root X2 (X2 cross-signed by X1); iOS built the
chain to the self-signed system ISRG Root X2, so an X1-only pinning asset
failed silently to a blank WebView. Two device rounds were burned on a gap a
desktop preflight could have reported.

Chain FETCHING deliberately skips certificate validation because the goal is
to read what the server actually serves, including chains a strict client
would reject. This module makes no trust decision, changes no app or SDK
configuration and must never be used to justify disabling verification
anywhere else.
"""
import socket
import ssl
from pathlib import Path
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.hazmat.primitives import hashes

_PEM_MARKER = b"-----BEGIN CERTIFICATE-----"

VERIFICATION_NOTE = (
    "Chain fetching intentionally performs no certificate validation so that it can "
    "report exactly what the server serves; this tool makes no trust decision and "
    "never disables or weakens verification in the SDK, the app or the WebView. "
    "Mobile TLS clients may terminate a cross-signed chain at the SELF-SIGNED "
    "variant of the top CA subject (verified 2026-09-29: iOS built to system ISRG "
    "Root X2 while desktop verification used the X1 cross-sign), so the trust asset "
    "must cover the top CA SUBJECT itself, not only its cross-sign parent."
)


def parse_host(entry):
    """Accept 'host', 'host:port' or an https:// base URL; return (host, port)."""
    if not isinstance(entry, str) or not entry.strip():
        raise ValueError("Provide a hostname or https:// base URL")
    entry = entry.strip()
    if "//" in entry:
        parts = urlsplit(entry)
        if parts.scheme != "https":
            raise ValueError("Only https:// base URLs describe a TLS endpoint")
        if not parts.hostname:
            raise ValueError("The base URL has no hostname")
        return parts.hostname, parts.port or 443
    host, _, port = entry.partition(":")
    if not host:
        raise ValueError("Provide a hostname or https:// base URL")
    if port:
        if not port.isdigit() or not 0 < int(port) < 65536:
            raise ValueError("Invalid port in host entry")
        return host, int(port)
    return host, 443


def load_trust_asset(path):
    """Load a PEM bundle or a single DER certificate; return x509 certificates."""
    source = Path(path).expanduser()
    try:
        raw = source.read_bytes()
    except OSError:
        raise ValueError("Cannot read the trust asset file") from None
    if not raw:
        raise ValueError("The trust asset file is empty")
    if _PEM_MARKER in raw:
        certificates = x509.load_pem_x509_certificates(raw)
    else:
        try:
            certificates = [x509.load_der_x509_certificate(raw)]
        except ValueError:
            raise ValueError("The trust asset is neither a PEM bundle nor a DER certificate") from None
    if not certificates:
        raise ValueError("The trust asset contains no certificates")
    return certificates


def fetch_served_chain(host, port, timeout=15.0):
    """Fetch the DER certificates the server actually serves, in served order.

    Validation is intentionally disabled for FETCHING only; see module docstring.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, port), timeout=timeout) as raw:
        with context.wrap_socket(raw, server_hostname=host) as tls:
            getter = getattr(tls, "get_unverified_chain", None)
            if getter is None:  # public API exists from Python 3.13
                getter = getattr(tls._sslobj, "get_unverified_chain", None)
            if getter is None:
                raise RuntimeError("This Python build cannot expose the served certificate chain")
            chain = getter() or []
            der = []
            for certificate in chain:
                data = certificate.public_bytes(ssl.ENCODING_DER) if hasattr(certificate, "public_bytes") else certificate
                der.append(bytes(data))
            if not der:
                raise RuntimeError("The server returned no certificate chain")
            return der


def describe(certificate):
    return {
        "subject": certificate.subject.rfc4514_string(),
        "issuer": certificate.issuer.rfc4514_string(),
        "sha256_fingerprint": certificate.fingerprint(hashes.SHA256()).hex(),
        "self_signed": certificate.subject == certificate.issuer,
    }


def _required_anchor_subjects(chain):
    """Anchor subjects the trust asset must cover for this served chain.

    Every self-signed subject in the chain plus the top (last) CA subject:
    mobile clients can terminate at the self-signed variant of the top subject
    even when the server serves only its cross-signed certificate.
    """
    subjects = []
    for entry in chain:
        if entry["self_signed"] and entry["subject"] not in subjects:
            subjects.append(entry["subject"])
    top = chain[-1]
    if top["subject"] not in subjects:
        subjects.append(top["subject"])
    return subjects


def _check_host(entry, asset_certificates, fetch):
    host, port = parse_host(entry)
    der_chain = fetch(host, port)
    chain = []
    for der in der_chain:
        try:
            chain.append(describe(x509.load_der_x509_certificate(der)))
        except ValueError:
            raise ValueError("The server returned an unparseable certificate") from None
    asset = [describe(c) for c in asset_certificates]
    asset_subjects = {c["subject"] for c in asset}
    asset_fingerprints = {c["sha256_fingerprint"] for c in asset}
    required = _required_anchor_subjects(chain)
    matched, missing = [], []
    for subject in required:
        exact = any(c["subject"] == subject and c["sha256_fingerprint"] in asset_fingerprints
                    for c in chain)
        if subject in asset_subjects:
            matched.append({"subject": subject,
                            "match": "exact_certificate" if exact else "same_subject_variant"})
        else:
            missing.append(subject)
    recommended = []
    top = chain[-1]
    if not top["self_signed"] and top["issuer"] not in asset_subjects and top["issuer"] not in required:
        recommended.append({
            "subject": top["issuer"],
            "reason": "Cross-sign parent of the served top CA; other TLS clients may build "
                      "the chain through it. Supply both variants when both can appear."})
    return {
        "host": host, "port": port,
        "served_chain": chain,
        "required_anchor_subjects": required,
        "matched_anchors": matched,
        "missing_anchors": missing,
        "recommended_additional_anchors": recommended,
        "status": "missing_anchors" if missing else "ok",
    }


def check(hosts, trust_asset_path, fetch=fetch_served_chain):
    if isinstance(hosts, str):
        hosts = [hosts]
    if not isinstance(hosts, list) or not hosts or len(hosts) > 50:
        raise ValueError("Provide 1..50 hosts or https:// base URLs")
    asset_certificates = load_trust_asset(trust_asset_path)
    results, failed = [], []
    for entry in hosts:
        host, port = parse_host(entry)  # reject malformed input before any connection
        try:
            results.append(_check_host(entry, asset_certificates, fetch))
        except (OSError, RuntimeError, ssl.SSLError) as error:
            failed.append({"host": host, "port": port, "status": "fetch_failed",
                           "error": error.__class__.__name__,
                           "detail": str(error) or "connection failed"})
    return {
        "trust_asset": {"path": str(Path(trust_asset_path).expanduser().absolute()),
                        "certificates": [describe(c) for c in asset_certificates]},
        "hosts": results + failed,
        "all_hosts_ok": bool(results) and not failed and all(h["status"] == "ok" for h in results),
        "verification_note": VERIFICATION_NOTE,
    }
