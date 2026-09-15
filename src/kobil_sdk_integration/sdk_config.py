"""Signed SDK configuration delivery without exposing the JWT to tool output."""
import base64
import hashlib
import os
from pathlib import Path
import re
import ssl
import stat


def certificate_bundle(paths: list[str]) -> list[str]:
    if not 1 <= len(paths) <= 50:
        raise ValueError("Provide 1 to 50 public TLS certificate files")
    bundle = []
    for name in paths:
        try:
            fd = os.open(Path(name).expanduser(), os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0))
            with os.fdopen(fd, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise ValueError()
                raw = stream.read(65537)
            if len(raw) > 65536 or b"PRIVATE KEY" in raw:
                raise ValueError()
            if b"-----BEGIN CERTIFICATE-----" in raw:
                if raw.count(b"-----BEGIN CERTIFICATE-----") != 1:
                    raise ValueError()
                raw = ssl.PEM_cert_to_DER_cert(raw.decode("ascii"))
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(raw))
            bundle.append(base64.b64encode(raw).decode("ascii"))
        except Exception:
            raise ValueError("Invalid certificate input; use one public PEM or DER certificate per file") from None
    return bundle


def write_config(certificate_paths: list[str], output_path: str, request_config) -> dict:
    """Validate inputs, reserve a new private file, then request and save the JWT.

    request_config takes {tlsBundle: [...]} and returns {sdkConfig: <JWT>}.
    Does not validate the signature: the SDK must trust the backend signer.
    """
    bundle = certificate_bundle(certificate_paths)
    output = Path(output_path).expanduser().absolute()
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            try:
                response = request_config({"tlsBundle": bundle})
            except Exception:
                # API errors can contain response bodies, admin tokens or secrets.
                raise RuntimeError("SDK configuration request failed; verify backend access and SDK config permissions") from None
            jwt = response.get("sdkConfig") if isinstance(response, dict) else None
            if not isinstance(jwt, str) or not re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", jwt):
                raise RuntimeError("Backend did not return a signed SDK configuration JWT")
            stream.write(jwt)
        return {"path": str(output), "sha256": hashlib.sha256(jwt.encode("ascii")).hexdigest(),
                "signature_verified": False}
    except BaseException:
        output.unlink(missing_ok=True)
        raise
