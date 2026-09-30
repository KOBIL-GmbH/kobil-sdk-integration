"""Stdio MCP with local inspection and explicitly configured AST operations."""
import hashlib
import os
from pathlib import Path, PurePath
import stat

from mcp.server.fastmcp import FastMCP
from .planner import FRAMEWORKS, plan

mcp = FastMCP("KOBILSDK", instructions="For first-time setup call sdk_onboarding_prepare with the project path, display its public recipient and copy-paste email, then wait for recipient-encrypted IDP/AST and SFTP credentials. Do not ask for private delivery keys. Use typed IDP and AST service interfaces with explicit environment and resource identifiers. Use bundled sdk_knowledge_topics/get/checklist for app integration. Respect source-review and mobile SDK qualification limits. Do not choose backend journeys from example names or create replacement flows to fit sample code.")


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
    The result includes local_build_preflight: toolchain checks (complete NDK,
    compiler versions, iOS deployment target vs installed Xcode, signing/device
    readiness, disk space) to run BEFORE long builds, so incomplete toolchains
    become precise preflight findings instead of mid-build surprises. It never
    mutates shared toolchains.
    """
    return plan(profile, capabilities if capabilities is not None else [])


_CONFIG_TEMPLATES = ("mc_config", "app_config")


def _delivery_inventory(source):
    """Classify a delivery ZIP from member names only; no member contents are read."""
    import zipfile
    names = []
    try:
        with zipfile.ZipFile(source) as archive:
            names = [i.filename for i in archive.infolist()[:10000]]
    except (zipfile.BadZipFile, OSError, RuntimeError):
        return {'inspected': False, 'platform_kinds': ['unknown'],
                'note': 'Archive member names could not be inspected; classify the delivery manually.'}
    kinds = set()
    lowered = [n.lower() for n in names]
    if any('.xcframework/' in n or n.endswith('.xcframework') for n in lowered):
        kinds.add('ios_native')
    if any(n.endswith('.aar') for n in lowered):
        kinds.add('android_native')
    if any(n.endswith('pubspec.yaml') or '/flutter' in n or n.startswith('flutter') for n in lowered):
        kinds.add('flutter')
    present = sorted({t for t in _CONFIG_TEMPLATES
                      for n in lowered if PurePath(n).name.startswith(t)})
    return {'inspected': True, 'platform_kinds': sorted(kinds) or ['unknown'],
            'config_templates_present': present,
            'config_templates_missing': [t for t in _CONFIG_TEMPLATES if t not in present],
            'note': 'Framework archives (for example the iOS xcframeworks ZIP of 15.16.803.3089231, '
                    'verified 2026-09-29) legitimately contain no mc_config/app_config templates; '
                    'configuration templates ship in the GettingStarted asset ZIPs of the same delivery. '
                    'A missing template here means fetch the matching asset ZIP before app scaffolding. '
                    'One archive or one scoped listing never proves account-wide absence of a platform '
                    'delivery; see sdk_sftp_list scope fields.'}


@mcp.tool()
def sdk_artifact_info(path: str) -> dict:
    """Hash a separately supplied SDK binary/archive; return metadata, never contents.

    Supported file suffixes: aar, jar, dll, dylib, so, zip, tar, gz, tgz.
    Framework directories must first be packaged as an archive. This does not
    verify authenticity, architecture, version compatibility or license rights.
    For ZIP deliveries a delivery_inventory is returned from member names only:
    native Android (.aar) / iOS (.xcframework) / Flutter classification plus
    presence of mc_config/app_config templates. Framework ZIPs normally carry no
    config templates; those come from GettingStarted asset ZIPs. Flag missing
    template assets before app scaffolding instead of guessing schemas.
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
    result = {"path": str(source.absolute()), "bytes": after.st_size,
              "sha256": digest.hexdigest(), "compatibility_verified": False}
    if source.suffix.lower() == ".zip":
        result["delivery_inventory"] = _delivery_inventory(source)
    return result


@mcp.tool()
def sdk_sftp_list(relative_path: str = '.') -> dict:
    """List customer SDK deliveries via configured SFTP. Read-only, no credentials in arguments.

    Requires user-provided setup selected by KOBIL_SDK_SFTP_CONNECTION, verified
    known_hosts and server-side credential references. Paths stay within remote_root.
    The response names the effective configured remote_root and requested relative
    path; that scope is NOT the full account inventory. Never conclude from one
    scoped listing that native Android/iOS SDKs are unavailable account-wide. To
    inspect another user-authorized area, select a separate connection profile
    (for example a reference profile with remote_root "/") via
    KOBIL_SDK_SFTP_CONNECTION, preserving the credential reference and known_hosts;
    never silently broaden roots or bypass confinement.
    Choose an explicit release; never assume the newest SDK is compatible.
    """
    from .sftp import list_delivery
    return list_delivery(relative_path)


@mcp.tool()
def sdk_sftp_download(relative_path: str, expected_sha512: str | None = None,
                      companion_paths: list[str] | None = None) -> dict:
    """Download one selected SDK archive, checksum sidecar or release note via SFTP.

    Pass companion_paths for the selected .sha512 sidecar and release notes; these
    land alongside the archive and the sidecar is verified automatically.
    Read-only on the server. Files are saved privately under KOBIL_SDK_DELIVERY or
    ~/.kobil-sdk/delivery, with no overwrite. Optional supplier SHA-512 is checked
    before publishing the download. No credential arguments. Follow with
    sdk_artifact_info and print the selected platform's release changelog.
    """
    from .sftp import download
    return download(relative_path, expected_sha512, companion_paths)


# Explicit service operations only; app orchestration belongs to app reference sources.
from . import idp_users, idp_secrets, idp_access, idp_extended, ast_admin, service_api, service_helpers, credential_tools, age_store, knowledge_api, native_policy, deployment_preflight, signing_preflight, environment_transfer, bundled_environment, onboarding
for _module in (idp_users, idp_secrets, idp_access, idp_extended, ast_admin, service_api, service_helpers, credential_tools, age_store, knowledge_api, native_policy, deployment_preflight, signing_preflight, environment_transfer, bundled_environment, onboarding):
    _module.register(mcp)


@mcp.tool()
async def sdk_service_catalog() -> dict:
    """List installed service tool names and coverage boundaries. No backend calls or app-flow recommendation."""
    names = sorted(t.name for t in await mcp.list_tools())
    return {'tools': names, 'tool_count': len(names),
            'app_flow_source': 'Bundled sdk_knowledge_get recipes; no external skill or source repository required. Respect per-topic qualification.',
            'coverage': 'Typed operations plus 49 explicit HTTP contracts cover 45 inspected dashboard IDP/AST routes; not every vendor endpoint.',
            'gaps': ['Arbitrary custom IDP providers', 'Observability-based cross-user client lookup'],
            'flow_selection': 'Caller selects explicit resources; service tools do not select or provision app journeys.'}


def main():
    onboarding.startup()
    mcp.run()


@mcp.tool()
def sdk_backend_status() -> dict:
    """Validate runtime connection configuration without contacting the backend.

    KOBIL_SDK_CONNECTION points to a local JSON file. Credentials are supplied
    through configured credential providers, never through this tool. Configuration
    is reloaded per call; sdk_environment_select can override the path for this process.
    """
    from .backend import configuration
    cfg = configuration()
    return {'environment': cfg['environment'], 'tenant': cfg['tenant'],
            'configured': True, 'connection_verified': False}


@mcp.tool()
def sdk_environment_select(connection_path: str, expected_current_environment: str,
                           expected_environment: str) -> dict:
    """Explicitly switch this running MCP to an existing connection JSON/age selector.

    First call sdk_backend_status; pass its environment as expected_current_environment
    and the requested target as expected_environment. Use an absolute local file path,
    never credentials. Validates profile structure (decrypting an age selector), but
    does not authenticate, contact backends, edit files or change app configuration.
    Failed validation leaves selection unchanged. Subsequent calls use the new file;
    already-created backend clients keep their original configuration. Finish ongoing
    workflows before switching. Applies only to this MCP process; restart restores
    the launcher's KOBIL_SDK_CONNECTION. Importing credentials never selects a server.
    After selection verify authentication and native preflight for the target.
    """
    from .backend import select_environment
    return select_environment(connection_path, expected_current_environment, expected_environment)


def _backend_operation(expected_environment, operation):
    from .backend import AST, configuration
    backend = AST(configuration(expected_environment))
    try:
        return operation(backend)
    finally:
        backend.close()


@mcp.tool()
def sdk_app_get(expected_environment: str, app_name: str) -> dict:
    """Read whether a named AST app exists. Does not create or modify resources.

    AST app_name is not automatically the Android applicationId or iOS bundle ID.
    Inspect versions/integrity and applicable package/signing bindings before reuse."""
    return _backend_operation(expected_environment, lambda b: b.get_app(app_name))


@mcp.tool()
def sdk_app_versions(expected_environment: str, app_name: str) -> dict:
    """Read all versions of a named app with registration user ID and security policy.

    Returns only allowlisted metadata, never user credentials or SDK config.
    Use the existing selection for reuse; this does not provision test identities.
    A new mobile bundle ID alone does not require a new AST app/version. Preserve
    registration user and integrity policy; missing binding evidence is not approval.
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
    Certificates must cover the chains actually negotiated by the mobile TLS
    clients, which can differ from desktop verification (verified 2026-09-29:
    iOS builds Let's Encrypt chains to ISRG Root X2 while desktop sees X1 via
    the cross-sign — supply both when both can appear). This trust input is for
    SDK Start and is separate from the trusted WebView pinning input.
    Output directory must exist. Returns path/hash, never JWT contents. The SDK
    must verify the signature. On Windows use a user-private directory with ACLs.
    This does not supply IDP client settings or activate a device. It does not take
    an AST app_name or mobile bundle ID. Do not infer package binding merely from
    the origin/name of a delivered JWT; verify the actual deployment contract.
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
def sdk_tls_chain_check(hosts: list[str], trust_asset_path: str) -> dict:
    """Compare the TLS chains servers actually serve against a local trust asset.

    Run this BEFORE any device round whenever trust anchors are prepared for
    SDK Start (mc_config iam.trustedSslServerCerts) or trusted-WebView pinning
    (certsDataForValidation). Pass environment https:// base URLs or host[:port]
    entries plus the local PEM bundle / DER certificate the app will pin.
    For each host the served chain (subject/issuer/SHA-256 per certificate),
    the required anchor subjects, matched anchors and MISSING anchors are
    reported. Mobile clients may terminate a cross-signed chain at the
    SELF-SIGNED variant of the top CA subject (verified 2026-09-29: akinci
    served leaf<-YE2<-Root YE<-ISRG Root X2 with X2 cross-signed by X1; iOS
    built to system X2, so an X1-only asset MUST be reported as missing X2 -
    VAL-16/VAL-36, two device rounds lost to this gap). Chain fetching alone
    skips validation so rejected chains are still visible; this tool makes no
    trust decision and NEVER disables or weakens verification in the SDK, app
    or WebView. One host's served chain does not prove other hosts or future
    deployments; check every environment host the app contacts.
    """
    from .tls_chain import check
    return check(hosts, trust_asset_path)


@mcp.tool()
def sdk_tms_trigger(expected_environment: str, user_uuid: str, text: str,
                    retrieval_timeout_seconds: int, confirmation_timeout_seconds: int,
                    require_explicit_authentication: bool, freshness_seconds: int = 3600) -> dict:
    """Create an authorized AST transaction, foreground only (push skipped).

    Writes backend state; do not retry an uncertain creation. Use a Keycloak
    recipient UUID, explicit timeouts/auth policy, and authorized content.
    freshness_seconds sets requireFreshnessOfAuthentication: the maximum age in
    seconds of the confirming device's authentication at CONFIRMATION time, not
    at trigger time. -1 disables the check; the default is 3600. 0 or other
    values below the observed confirmation latency create a transaction that is
    guaranteed to fail at confirmation (observed 2026-09-29: HTTP 403 "The
    access token is 85 seconds older than required", surfaced by the SDK only
    as errorCode 516004035 "A network error occurred"); such calls still create
    the transaction but return an explicit warning.
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
    """Read final AST result metadata; a missing result is not success.

    A not-yet-terminal transaction returns status "pending" (lowercase; mapped
    from this endpoint's HTTP 412, observed 2026-09-29). Pending is not a
    backend error: keep bounded polling and never re-trigger because of it.
    """
    from .tms import read
    return _backend_operation(expected_environment, lambda b: read(b, transaction_id, result=True))


@mcp.tool()
def sdk_tms_cancel(expected_environment: str, transaction_id: str) -> dict:
    """Request cancellation of the specified authorized transaction; verify result separately."""
    from .tms import cancel
    return _backend_operation(expected_environment, lambda b: cancel(b, transaction_id))
