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
    """List integration targets and point to scoped native runtime evidence."""
    return {"frameworks": {k: sorted(v) for k, v in FRAMEWORKS.items()},
            "feature_scope": "All public KOBIL SDK features, subject to version/platform support",
            "runtime_verification": "partial_native_android_ios; see skill platform/version evidence"}


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

    KOBIL_SDK_CONNECTION points to a local JSON file. Credentials resolve locally through configured references or legacy runtime
    environment variables, never through tool arguments/results.
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
def sdk_app_get(expected_environment: str, app_name: str) -> dict:
    """Read whether a named AST app exists. Does not create or modify resources."""
    return _backend_operation(expected_environment, lambda b: b.get_app(app_name))


@mcp.tool()
def sdk_app_versions(expected_environment: str, app_name: str) -> dict:
    """Read all versions of a named app with registration user ID and security policy.

    Returns only allowlisted metadata, never user credentials or SDK config.
    Use the existing selection for reuse; this does not provision test identities.
    """
    return _backend_operation(expected_environment, lambda b: b.list_versions(app_name))


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
    from .backend import https_url, segment
    def deliver(backend):
        services = backend.cfg.get('services')
        if not isinstance(services, list) or not 1 <= len(services) <= 50:
            raise ValueError('Configure the SDK service endpoints before requesting a signed configuration')
        names = set()
        for service in services:
            if not isinstance(service, dict) or set(service) != {'name', 'url'}:
                raise ValueError('Each SDK service requires a name and HTTPS URL')
            segment(service['name'])
            https_url(service['url'])
            if service['name'] in names:
                raise ValueError('Duplicate SDK service name')
            names.add(service['name'])
        return write_config(certificate_paths, output_path, lambda body: backend.request(
            'POST', '/sdkconfig', {**body, 'astUrl': backend.cfg['ast_url'], 'services': services}))
    return _backend_operation(expected_environment, deliver)


@mcp.tool()
def sdk_tms_trigger(expected_environment: str, user_uuid: str, text: str,
                    retrieval_timeout_seconds: int, confirmation_timeout_seconds: int,
                    require_explicit_authentication: bool, freshness_seconds: int) -> dict:
    """Create an authorized AST transaction, foreground only (push skipped).

    Writes backend state; do not retry an uncertain creation. Use a Keycloak
    recipient UUID, explicit timeouts/auth policy, and authorized content.
    Returns ID/status only; does not approve the transaction or verify signing.
    """
    from .tms import trigger
    return _backend_operation(expected_environment, lambda b: trigger(
        b, user_uuid, text, retrieval_timeout_seconds, confirmation_timeout_seconds,
        require_explicit_authentication, freshness_seconds))


@mcp.tool()
def sdk_tms_status(expected_environment: str, transaction_id: str) -> dict:
    """Read AST transaction status; excludes payload, identities and signatures."""
    from .tms import read
    return _backend_operation(expected_environment, lambda b: read(b, transaction_id))


@mcp.tool()
def sdk_tms_result(expected_environment: str, transaction_id: str) -> dict:
    """Read final AST result metadata; a missing result is not success."""
    from .tms import read
    return _backend_operation(expected_environment, lambda b: read(b, transaction_id, result=True))


@mcp.tool()
def sdk_tms_cancel(expected_environment: str, transaction_id: str) -> dict:
    """Request cancellation of the specified authorized transaction; verify result separately."""
    from .tms import cancel
    return _backend_operation(expected_environment, lambda b: cancel(b, transaction_id))


@mcp.tool()
def sdk_idp_status() -> dict:
    """Validate optional IDP configuration locally; never resolves secrets or contacts a backend."""
    from .idp import configuration
    cfg = configuration()
    return {'environment': cfg['environment'], 'realm': cfg['realm'], 'configured': True,
            'connection_verified': False, 'test_provisioning_enabled': cfg['allow_test_provisioning']}


def _idp_operation(expected_environment, operation):
    from .idp import IDP, configuration
    backend = IDP(configuration(expected_environment))
    try:
        return operation(backend)
    finally:
        backend.close()


@mcp.tool()
def sdk_idp_user_get(expected_environment: str, username: str) -> dict:
    """Read one exact IDP username; returns only ID/existence/enabled metadata."""
    return _idp_operation(expected_environment, lambda b: b.user_get(username))


@mcp.tool()
def sdk_idp_test_user_create(expected_environment: str, username: str) -> dict:
    """Create an explicitly requested passwordless test user; never change existing users.

    Requires configured IDP test provisioning permission. If creation fails, inspect
    exact user lookup before retrying; a failed response may have committed.
    """
    return _idp_operation(expected_environment, lambda b: b.user_create(username))


@mcp.tool()
def sdk_idp_activation_write(expected_environment: str, username: str, user_id: str,
                             output_path: str, period: str = '1d', replace_existing: bool = False) -> dict:
    """Generate and set a random activation code for an unactivated test user.

    Requires explicit user authorization. Delivers only to a new 0600 file in a
    private 0700 directory. Never read the code into chat. Register-user IDs are
    unrelated. No password/PIN is generated. Existing activation credentials need
    explicit replacement; enrolled users are refused. Unknown write outcome must
    not be retried automatically. POSIX file delivery only in this preview.
    """
    return _idp_operation(expected_environment, lambda b: b.activation_write(
        username, user_id, output_path, period, replace_existing))
