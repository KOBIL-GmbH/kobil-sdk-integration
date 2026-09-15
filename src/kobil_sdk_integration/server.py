"""Stdio MCP with local inspection and explicitly configured AST operations."""
import hashlib
import os
from pathlib import Path
import stat

from mcp.server.fastmcp import FastMCP
from .planner import FRAMEWORKS, plan

mcp = FastMCP("KOBILSDK")


@mcp.tool()
def sdk_targets() -> dict:
    """List required integration targets; no native runtime coverage is claimed."""
    return {"frameworks": {k: sorted(v) for k, v in FRAMEWORKS.items()},
            "feature_scope": "All public KOBIL SDK features, subject to version/platform support",
            "runtime_verification": "pending"}


@mcp.tool()
def sdk_plan(profile: dict, capabilities: list[str] | None = None) -> dict:
    """Plan dependencies and optional provider offers. Never installs or contacts providers.

    Profile fields: framework, targets, backend, artifact_source; optional provider
    lists: distribution, observability, diagnostics, testing, infrastructure,
    documentation, issue_tracking. No credentials. Adapter readiness is reported per module.
    """
    return plan(profile, capabilities if capabilities is not None else [])


@mcp.tool()
def sdk_artifact_info(path: str) -> dict:
    """Hash a separately supplied SDK binary/archive; return metadata, never contents.

    Supported file suffixes: aar, jar, dll, dylib, so, zip, tar, gz, tgz.
    Framework directories must first be packaged as an archive. This does not
    verify authenticity, architecture, version compatibility or license rights.
    """
    source = Path(path).expanduser()
    if source.suffix.lower() not in {".aar", ".jar", ".dll", ".dylib", ".so", ".zip", ".tar", ".gz", ".tgz"}:
        raise ValueError("Expected a supported SDK binary/archive file")
    try:
        # Opening non-blocking avoids hangs on a FIFO disguised as an artifact.
        fd = os.open(source, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0))
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError("Expected a regular file")
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError("Artifact changed during inspection")
    except OSError:
        raise ValueError("Cannot read the SDK artifact") from None
    return {"path": str(source.absolute()), "bytes": after.st_size,
            "sha256": digest.hexdigest(), "compatibility_verified": False}


def main():
    mcp.run()


@mcp.tool()
def sdk_backend_status() -> dict:
    """Validate runtime connection configuration without contacting the backend.

    KOBIL_SDK_CONNECTION points to a local JSON file. Credentials are supplied
    through named environment variables, never through tool arguments/results.
    """
    from .backend import configuration
    cfg = configuration()
    return {'environment': cfg['environment'], 'tenant': cfg['tenant'],
            'configured': True, 'connection_verified': False}


def _backend_operation(expected_environment, operation):
    from .backend import AST, configuration
    backend = AST(configuration(expected_environment))
    try:
        return operation(backend)
    finally:
        backend.close()


@mcp.tool()
def sdk_app_ensure(expected_environment: str, app_name: str, categories: list[str]) -> dict:
    """Reuse an AST app or create it if absent. This writes backend state.

    Existing app settings are never overwritten. Categories must come from the
    requested SDK feature/backend contract. Concurrent administrators can race;
    failed writes are not retried automatically.
    """
    return _backend_operation(expected_environment, lambda b: b.ensure_app(app_name, categories))


@mcp.tool()
def sdk_app_version_ensure(expected_environment: str, app_name: str, platform: str,
                           version: str, register_user_id: str, check_integrity: bool) -> dict:
    """Reuse or register an AST app version. This writes backend state.

    Supply the exact backend platform string and an explicit integrity policy.
    No defaults disable integrity. Conflicting settings or incomplete listings
    fail without writes. Select a valid registration user from backend policy.
    """
    return _backend_operation(expected_environment, lambda b: b.ensure_version(
        app_name, platform, version, register_user_id, check_integrity))


@mcp.tool()
def sdk_config_write(expected_environment: str, certificate_paths: list[str], output_path: str) -> dict:
    """Request backend-signed SDK config and save to a NEW private local JWT file.

    Supply 1–50 trusted public TLS certificates, one PEM/DER certificate per file.
    Output directory must exist. Returns path/hash, never JWT contents. The SDK
    must verify the signature. On Windows use a user-private directory with ACLs.
    This does not supply IDP client settings or activate a device.
    """
    from .sdk_config import write_config
    return _backend_operation(expected_environment, lambda b: write_config(
        certificate_paths, output_path, lambda body: b.request('POST', '/sdkconfig', body)))
