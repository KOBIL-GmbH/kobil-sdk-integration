"""Compare served TLS chains against a local trust asset before device runs.

Motivated by VAL-16/VAL-36 (2026-09-29): a test environment served
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
import datetime
import hashlib
import ipaddress
import socket
import ssl
from pathlib import Path
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization

DEFAULT_EXPIRY_WARNING_DAYS = 14
_MAX_PATH_DEPTH = 9
# Served top CAs (cross-signed by a root that is in the trust asset) that an iPhone (iOS 26.7.1) and a
# simulator (iOS 27.0) accepted with only the issuing root in the PEM, tested 2026-10-08 against a
# host serving leaf <- YR1 <- Root YR <- ISRG Root X1. Anything not listed keeps the strict rule
# (VAL-16/VAL-36: akinci Root X2 with an X1-only PEM fails on iOS).
IOS_DEVICE_TESTED_CROSS_SIGNED_TOPS = {
    "CN=Root YR,O=ISRG,C=US": "CN=ISRG Root X1,O=Internet Security Research Group,C=US",
}
PLATFORMS = ("ios", "android")
_PROBLEM_ORDER = ("missing_anchors", "hostname_mismatch", "expired", "path_invalid")

_PEM_MARKER = b"-----BEGIN CERTIFICATE-----"

# ssl.ENCODING_DER is not exported by every supported interpreter (absent on
# the bundled CPython 3.11); the _ssl constant is the stable fallback.
try:
    _DER_ENCODING = ssl.ENCODING_DER
except AttributeError:  # pragma: no cover - depends on the interpreter build
    import _ssl

    _DER_ENCODING = _ssl.ENCODING_DER

VERIFICATION_NOTE = (
    "Chain fetching intentionally performs no certificate validation so that it can "
    "report exactly what the server serves; this tool makes no trust decision and "
    "never disables or weakens verification in the SDK, the app or the WebView. "
    "Mobile TLS clients may terminate a cross-signed chain at the SELF-SIGNED "
    "variant of the top CA subject (verified 2026-09-29: iOS built to system ISRG "
    "Root X2 while desktop verification used the X1 cross-sign), so the trust asset "
    "must cover the top CA subject AND public key, not only its cross-sign parent. "
    "Per host it also checks the leaf hostname against the subjectAltName, the validity "
    "dates of the served leaf and of the matched asset anchors at check time, and runs a "
    "simplified desktop path check that follows the KOBIL Confluence procedure for trusted_certs.pem "
    "(the file alone must carry the chain to a self-signed root, as "
    "wget --ca-certificate or openssl verify would require; the SDK's native CertificateValidator "
    "uses OpenSSL chain verification without a partial-chain flag in the mirrored source). "
    "The path check follows subject, signature, validity and CA flag only; it covers no name "
    "constraints, revocation or policy, and it is not a statement about iOS, Android, "
    "KSTrustedWebView or SDK runtime acceptance. An ok result therefore means: asset coverage, "
    "hostname, validity and desktop path agree at the time of the check, nothing more. "
    "For iOS KSTrustedWebView 9.7.3000479, certsDataForValidation needs PEM "
    "trust-store bytes; do not convert those bytes to DER. "
    "platform=ios (default) applies the strict anchor rule above. platform=android lets the "
    "desktop path result decide, because the Android WebView proxy and the SDK core hand the "
    "PEM to the same native OpenSSL validator (source review of the mirrored sources; "
    "not verified on a device): a chain ending at a self-signed root in the file is accepted "
    "even when the server serves a cross-signed top CA, and the strict gap is reported as a "
    "warning only. On iOS the self-signed variant of a served top CA that is cross-signed by a "
    "root in the file is required except for Root YR (signed by ISRG Root X1), which loaded "
    "once on an iPhone and a simulator with only ISRG Root X1 in the PEM (2026-10-08), "
    "so that gap is a warning; other tops keep the strict rule."
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
                data = certificate.public_bytes(_DER_ENCODING) if hasattr(certificate, "public_bytes") else certificate
                der.append(bytes(data))
            if not der:
                raise RuntimeError("The server returned no certificate chain")
            return der


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def _usable_at(certificate, now):
    return certificate.not_valid_before_utc <= now <= certificate.not_valid_after_utc


def describe(certificate, now=None):
    now = now or _utcnow()
    remaining = certificate.not_valid_after_utc - now
    return {
        "subject": certificate.subject.rfc4514_string(),
        "issuer": certificate.issuer.rfc4514_string(),
        "sha256_fingerprint": certificate.fingerprint(hashes.SHA256()).hex(),
        "self_signed": certificate.subject == certificate.issuer,
        "spki_sha256": hashlib.sha256(certificate.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).hexdigest(),
        "not_before": certificate.not_valid_before_utc.isoformat(),
        "not_after": certificate.not_valid_after_utc.isoformat(),
        "days_until_expiry": int(remaining.total_seconds() // 86400),
        "expired": not _usable_at(certificate, now),
    }


def _san_names(certificate):
    """Return (dns_names, ip_addresses) from the subjectAltName extension."""
    try:
        san = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        return [], []
    return (list(san.get_values_for_type(x509.DNSName)),
            [str(address) for address in san.get_values_for_type(x509.IPAddress)])


def _name_matches(pattern, host):
    pattern, host = pattern.lower().rstrip("."), host.lower().rstrip(".")
    if pattern.startswith("*."):
        label, _, rest = host.partition(".")
        return bool(label) and bool(rest) and rest == pattern[2:]
    return pattern == host


def hostname_match(host, leaf):
    """Match the host against the leaf subjectAltName only (CN is ignored, as modern clients do)."""
    dns_names, ip_addresses = _san_names(leaf)
    try:
        address = str(ipaddress.ip_address(host))
    except ValueError:
        address = None
    if address is not None:
        matches = address in ip_addresses
    else:
        matches = any(_name_matches(name, host) for name in dns_names)
    return {"matches": matches, "names": dns_names + ip_addresses}


def _directly_issued(certificate, issuer):
    try:
        certificate.verify_directly_issued_by(issuer)
    except (ValueError, TypeError, InvalidSignature, UnsupportedAlgorithm):
        return False
    return True


def _is_ca(certificate):
    try:
        return bool(certificate.extensions.get_extension_for_class(x509.BasicConstraints).value.ca)
    except x509.ExtensionNotFound:
        return False


def desktop_path_check(served, asset, now):
    """Simplified desktop path check: does the file alone carry the served chain to a self-signed root?

    Follows subject, signature, validity and CA flag. The first served certificate is the leaf;
    the other served certificates are only intermediates and are never trusted. Only certificates
    from the trust asset can end the path, and only when they are self-signed.
    """
    leaf = served[0]
    if not _usable_at(leaf, now):
        return {"result": "invalid", "terminates_at": None, "failed_on_expiry": True,
                "detail": "The served leaf certificate is expired or not yet valid."}
    asset_fingerprints = {c.fingerprint(hashes.SHA256()) for c in asset}
    candidates = list(asset) + [c for c in served[1:] if c.fingerprint(hashes.SHA256()) not in asset_fingerprints]
    state = {"expired_candidate": False}

    def build(certificate, depth, seen):
        if depth > _MAX_PATH_DEPTH:
            return None
        for candidate in candidates:
            fingerprint = candidate.fingerprint(hashes.SHA256())
            if fingerprint in seen or candidate.subject != certificate.issuer or not _is_ca(candidate):
                continue
            if not _directly_issued(certificate, candidate):
                continue
            if not _usable_at(candidate, now):
                state["expired_candidate"] = True
                continue
            trusted = fingerprint in asset_fingerprints
            if trusted and candidate.subject == candidate.issuer:
                return candidate.subject.rfc4514_string()
            found = build(candidate, depth + 1, seen | {fingerprint})
            if found:
                return found
        return None

    terminus = build(leaf, 0, {leaf.fingerprint(hashes.SHA256())})
    if terminus:
        return {"result": "valid", "terminates_at": terminus, "failed_on_expiry": False, "detail": ""}
    return {"result": "invalid", "terminates_at": None, "failed_on_expiry": state["expired_candidate"],
            "detail": "No path from the served leaf to a self-signed certificate in the trust asset "
                      "(the Confluence procedure expects the file to hold the self-signed root(s); "
                      "intermediates or cross-signed certificates alone cannot end a path)"
                      + (", and a certificate on the way is expired." if state["expired_candidate"] else ".")}


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


def _validity(chain_certificates, chain, matched_asset, now, warning_days):
    """Expired/expiring served certificates and matched asset anchors at check time."""
    described = [(c, d) for c, d in zip(chain_certificates, chain)] + matched_asset
    expired, expiring_soon = [], []
    for _, entry in described:
        if entry["expired"]:
            if entry["subject"] not in expired:
                expired.append(entry["subject"])
        elif entry["days_until_expiry"] <= warning_days and entry["subject"] not in expiring_soon:
            expiring_soon.append(entry["subject"])
    return {"expired": expired, "expiring_soon": expiring_soon, "warning_days": warning_days}


def _check_host(entry, asset_certificates, fetch, now, warning_days, strict_anchors=True):
    host, port = parse_host(entry)
    der_chain = fetch(host, port)
    chain_certificates = []
    for der in der_chain:
        try:
            chain_certificates.append(x509.load_der_x509_certificate(der))
        except ValueError:
            raise ValueError("The server returned an unparseable certificate") from None
    chain = [describe(c, now) for c in chain_certificates]
    asset = [describe(c, now) for c in asset_certificates]
    asset_subjects = {c["subject"] for c in asset}
    asset_fingerprints = {c["sha256_fingerprint"] for c in asset}
    required = _required_anchor_subjects(chain)
    matched, missing, matched_asset = [], [], []
    for subject in required:
        exact = any(c["subject"] == subject and c["sha256_fingerprint"] in asset_fingerprints
                    for c in chain)
        same_key = any(c["subject"] == subject and a["subject"] == subject
                       and c["spki_sha256"] == a["spki_sha256"]
                       for c in chain for a in asset)
        if exact or same_key:
            matched.append({"subject": subject,
                            "match": "exact_certificate" if exact else "same_subject_and_key_variant"})
            for certificate, entry_asset in zip(asset_certificates, asset):
                if entry_asset["subject"] == subject and any(
                        c["subject"] == subject and c["spki_sha256"] == entry_asset["spki_sha256"]
                        for c in chain):
                    matched_asset.append((certificate, entry_asset))
        else:
            missing.append(subject)
    recommended = []
    top = chain[-1]
    if not top["self_signed"] and top["issuer"] not in asset_subjects and top["issuer"] not in required:
        recommended.append({
            "subject": top["issuer"],
            "reason": "Cross-sign parent of the served top CA; other TLS clients may build "
                      "the chain through it. Supply both variants when both can appear."})
    hostname = hostname_match(host, chain_certificates[0])
    validity = _validity(chain_certificates, chain, matched_asset, now, warning_days)
    path = desktop_path_check(chain_certificates, asset_certificates, now)
    warnings = []
    problems = []
    tolerated = [m for m in missing if m == top["subject"] and not top["self_signed"]
                 and IOS_DEVICE_TESTED_CROSS_SIGNED_TOPS.get(m) == top["issuer"]]
    if missing and strict_anchors and len(tolerated) == len(missing):
        warnings.append("Strict iOS anchor coverage is not met (missing self-signed variant of: %s), but "
                        "Root YR cross-signed by ISRG Root X1 was accepted on an iPhone and a simulator with "
                        "ISRG Root X1 in the file (device-tested once, 2026-10-08). Not verified for other iOS versions "
                        "or inside the SDK's own validator." % ", ".join(missing))
    elif missing and strict_anchors:
        problems.append("missing_anchors")
    elif missing:
        warnings.append("Strict iOS anchor coverage is not met (missing self-signed variant of: %s); "
                        "Android validates the path over the file instead, so the desktop path result decides. "
                        "iOS would need these anchors." % ", ".join(missing))
    if not hostname["matches"]:
        problems.append("hostname_mismatch")
    must_be_valid = {chain[0]["subject"]} | {e["subject"] for _, e in matched_asset}
    if any(subject in must_be_valid for subject in validity["expired"]) or path["failed_on_expiry"]:
        problems.append("expired")
    elif validity["expired"]:
        warnings.append("Served certificate(s) expired but not required by the checked path: "
                        + ", ".join(validity["expired"]))
    if path["result"] != "valid" and not path["failed_on_expiry"]:
        problems.append("path_invalid")
    if validity["expiring_soon"]:
        warnings.append("Certificate(s) expire within %d days: %s"
                        % (warning_days, ", ".join(validity["expiring_soon"])))
    problems.sort(key=_PROBLEM_ORDER.index)
    return {
        "host": host, "port": port,
        "served_chain": chain,
        "required_anchor_subjects": required,
        "matched_anchors": matched,
        "missing_anchors": missing,
        "recommended_additional_anchors": recommended,
        "hostname_match": hostname,
        "validity": validity,
        "desktop_path_check": {k: path[k] for k in ("result", "terminates_at", "detail")},
        "problems": problems,
        "warnings": warnings,
        "status": problems[0] if problems else "ok",
    }


def check(hosts, trust_asset_path, fetch=fetch_served_chain, now=None,
          expiry_warning_days=DEFAULT_EXPIRY_WARNING_DAYS, platform="ios"):
    if platform not in PLATFORMS:
        raise ValueError("platform must be one of: " + ", ".join(PLATFORMS))
    if isinstance(hosts, str):
        hosts = [hosts]
    if not isinstance(hosts, list) or not hosts or len(hosts) > 50:
        raise ValueError("Provide 1..50 hosts or https:// base URLs")
    if isinstance(expiry_warning_days, bool) or not isinstance(expiry_warning_days, int) \
            or not 0 <= expiry_warning_days <= 3650:
        raise ValueError("expiry_warning_days must be an integer between 0 and 3650")
    if now is None:
        now = _utcnow()
    elif not isinstance(now, datetime.datetime) or now.tzinfo is None:
        raise ValueError("now must be a timezone-aware datetime")
    asset_certificates = load_trust_asset(trust_asset_path)
    results, failed = [], []
    for entry in hosts:
        host, port = parse_host(entry)  # reject malformed input before any connection
        try:
            results.append(_check_host(entry, asset_certificates, fetch, now, expiry_warning_days,
                                       strict_anchors=platform == "ios"))
        except (OSError, RuntimeError, ssl.SSLError) as error:
            failed.append({"host": host, "port": port, "status": "fetch_failed",
                           "error": error.__class__.__name__,
                           "detail": str(error) or "connection failed"})
    return {
        "trust_asset": {"path": str(Path(trust_asset_path).expanduser().absolute()),
                        "certificates": [describe(c, now) for c in asset_certificates]},
        "hosts": results + failed,
        "all_hosts_ok": bool(results) and not failed and all(h["status"] == "ok" for h in results),
        "desktop_path_all_valid": bool(results) and not failed
                                  and all(h["desktop_path_check"]["result"] == "valid" for h in results),
        "platform": platform,
        "expiry_warning_days": expiry_warning_days,
        "checked_at": now.isoformat(),
        "verification_scope": "asset_coverage_only",
        "runtime_acceptance_verified": False,
        "certificate_path_verified": False,
        "verification_note": VERIFICATION_NOTE,
    }
