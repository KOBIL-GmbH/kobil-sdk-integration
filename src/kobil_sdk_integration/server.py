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
            "runtime_verification": "partial_native_android_ios; see skill platform/version evidence",
            "next_step": "Read sdk_docs() for the method, then sdk_plan() with the customer profile."}


@mcp.tool()
def sdk_plan(profile: dict, capabilities: list[str] | None = None) -> dict:
    """Plan dependencies and optional provider offers. Never installs or contacts providers.

    Profile fields and accepted values:
      framework: kotlin | swift | flutter
      targets: ["android"] and/or ["ios"] (swift: ios only, kotlin: android only)
      backend: ast-shift | ssms            (AST/Shift is "ast-shift", not "ast")
      artifact_source: local | sftp | teamcity  (the delivery bundled with this MCP is "local")
    Optional provider lists: distribution, observability, diagnostics, testing,
    infrastructure, documentation, issue_tracking. capabilities names provider groups
    (distribution, observability, diagnostics, testing, infrastructure, issue-tracking,
    documentation), not SDK features such as activation or login. No credentials.
    Adapter readiness is reported per module; an unrecognised value is reported as a gap.
    """
    result = plan(profile, capabilities if capabilities is not None else [])
    result["next_step"] = ("Acquire the SDK binaries for the selected targets, then sdk_backend_verify() "
                           "to confirm the connection before any backend write.")
    return result


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
            'configured': True, 'connection_verified': False,
            'next_step': 'This only reads the local file. Call sdk_backend_verify() to prove '
                         'the credential works and the token carries the required role.'}


def _backend_operation(expected_environment, operation):
    from .backend import AST, configuration
    backend = AST(configuration(expected_environment))
    try:
        return operation(backend)
    finally:
        backend.close()


@mcp.tool()
def sdk_app_get(expected_environment: str, app_name: str) -> dict:
    """Read whether a named AST app exists, with its categories; for a missing app, the
    category values this tenant already uses (values only). Does not create or modify."""
    result = _backend_operation(expected_environment, lambda b: b.get_app(app_name))
    result['next_step'] = ('Missing app: sdk_app_ensure() with categories such as ["tms"]. Existing app: '
                           'sdk_app_versions() to see which platform/version registrations already exist.')
    return result


@mcp.tool()
def sdk_app_versions(expected_environment: str, app_name: str) -> dict:
    """Read all versions of a named app with registration user ID and security policy.

    Returns only allowlisted metadata, never user credentials or SDK config.
    Use the existing selection for reuse; this does not provision test identities.
    """
    result = _backend_operation(expected_environment, lambda b: b.list_versions(app_name))
    result['next_step'] = ('Reuse a registration whose platform and version match the build. '
                           'Keep the registration user recorded on the version; do not replace it with an activation user. Whether AST requires that user for a version\'s first device activation is not verified in this release.')
    return result


@mcp.tool()
def sdk_app_ensure(expected_environment: str, app_name: str, categories: list[str]) -> dict:
    """Reuse an AST app or create it if absent. This writes backend state.

    app_name is the app the user is building (a new app gets its own name, e.g. the product
    name), never another app found with sdk_app_get unless the user names it.

    Existing app settings are never overwritten. categories are the push-notification
    categories the app subscribes to: "tms" for transaction confirmation and "chat" for
    messaging are the values seen in use; sdk_app_get() reports the values this tenant
    already uses. A device app that confirms transactions needs at least ["tms"].
    Concurrent administrators can race; failed writes are not retried automatically.
    """
    result = _backend_operation(expected_environment, lambda b: b.ensure_app(app_name, categories))
    result['next_step'] = 'Register the platform version with sdk_app_version_ensure().'
    return result


@mcp.tool()
def sdk_app_version_ensure(expected_environment: str, app_name: str, platform: str,
                           version: str, register_user_id: str, check_integrity: bool) -> dict:
    """Reuse or register an AST app version. This writes backend state.

    Supply the exact backend platform string and an explicit integrity policy.
    No defaults disable integrity. Conflicting settings or incomplete listings
    fail without writes. register_user_id is the tenant user recorded as the version's
    registration user; any existing tenant user is acceptable to the backend. When none
    is known, create a dedicated one with sdk_activation_user_ensure (for example
    "<app>-registrar") and pass its user_uuid; keep it separate from the user that
    activates devices.
    """
    result = _backend_operation(expected_environment, lambda b: b.ensure_version(
        app_name, platform, version, register_user_id, check_integrity))
    result['integrity_enforced'] = bool(check_integrity)
    result['next_step'] = (
        'Obtain the signed configuration with sdk_config_write(), then sdk_mc_config() for the '
        'app-side file. The app version string and identifier must match this registration. '
        'Keep the registration user recorded on the version; do not replace it with an activation user. Whether AST requires that user for a version\'s first device activation is not verified in this release. '
        + ('Integrity is ON: a rebuilt debug binary changes its digest and activation then fails; '
           'register a separate version for development if that blocks you.' if check_integrity else
           'Integrity is OFF: acceptable while developing, never for a release build.'))
    return result


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
                    require_explicit_authentication: bool, freshness_seconds: int,
                    data: dict[str, str] | None = None) -> dict:
    """Create an authorized AST transaction, foreground only (push skipped).

    Writes backend state; do not retry an uncertain creation. Use a Keycloak
    recipient UUID, explicit timeouts/auth policy, and authorized content.
    Returns ID/status only; does not approve the transaction or verify signing.

    freshness_seconds is the maximum age of the user's access token when the phone
    answers; -1 disables the check. 0 does NOT disable it: the backend then refuses
    every answer with 403 code 4035 ("access token is N seconds older than required")
    and the transaction ends failed on the device. Use -1 for a plain foreground test.

    require_explicit_authentication=True needs two things first, or the transaction ends
    failed on the phone with nothing on screen: mc_config.json iam.clientId must be the
    client that issued the login tokens (see sdk_mc_config), and that client must offer
    the "tms" scope (sdk_tms_scope_ensure). The SDK then gets the fresh "tms" token by a
    silent token exchange; it does not ask an IDP-login user for a PIN.

    Every accepted transaction is signed by the device (AST "Message Sign"), so this is
    also how to ask for a document signature: put the document name and its SHA-256 in
    data (e.g. {"requestType": "signature", "documentName": ..., "documentSha256": ...})
    and reference them in text as Mustache placeholders ({{documentName}}). data is
    optional string key-value pairs; sdk_tms_result reports whether a signature exists.
    """
    from .tms import trigger
    return _backend_operation(expected_environment, lambda b: trigger(
        b, user_uuid, text, retrieval_timeout_seconds, confirmation_timeout_seconds,
        require_explicit_authentication, freshness_seconds, data))


@mcp.tool()
def sdk_display_message_send(expected_environment: str, user_uuid: str, text: str,
                             timeout_seconds: int, data: dict[str, str] | None = None) -> dict:
    """Send a one-way display message to the user's activated app (POST /display-message).

    The app receives TriggerBanner (display message) -> sends StartDisplayMessage ->
    receives DisplayMessage with the text. Nothing is confirmed or signed. Writes backend
    state; do not resend an uncertain request. Foreground only (push skipped).
    timeout_seconds is how long clients may still fetch it. Returns the message ID only;
    delivery is verified on the device, not by this call.
    """
    from .tms import display_message
    return _backend_operation(expected_environment, lambda b: display_message(
        b, user_uuid, text, timeout_seconds, data))


@mcp.tool()
def sdk_tms_test_sequence(expected_environment: str, user_uuid: str, steps: list[str] | None = None,
                          delay_seconds: int = 30, confirmation_timeout_seconds: int = 120) -> dict:
    """Send a device test sequence: a display message, a signature request and a payment.

    steps is any order of "message", "signature", "payment" (default all three, in that
    order), delay_seconds apart (5–300). The first is sent at once; the call returns
    immediately with a run_id, and the rest are sent in the background. Read progress and
    the transaction IDs with sdk_tms_test_sequence_status; check each transaction's outcome
    with sdk_tms_result. Content is generic sample data using the documented data keys
    (requestType, documentName/documentSha256, amount/currency/merchant; the message has
    data.title "Support"). Transactions are foreground only, without explicit
    authentication, freshness -1. Writes backend state: a failed step is recorded and not
    retried. The app must be open and logged in on the device.
    """
    from .backend import configuration
    from .tms import display_message, recipient, trigger
    from .tms_sequence import RUNS
    configuration(expected_environment)
    user_uuid = recipient(user_uuid)

    def send_message(text, data, timeout):
        return _backend_operation(expected_environment, lambda b: display_message(b, user_uuid, text, timeout, data))

    def send_transaction(text, data, timeout):
        return _backend_operation(expected_environment, lambda b: trigger(
            b, user_uuid, text, timeout, timeout, False, -1, data))

    return RUNS.start(send_message, send_transaction, steps, delay_seconds, confirmation_timeout_seconds)


@mcp.tool()
def sdk_tms_test_sequence_status(run_id: str) -> dict:
    """Progress of a sdk_tms_test_sequence run: per step whether it was sent, when, and its ID."""
    from .tms_sequence import RUNS
    return RUNS.status(run_id)


@mcp.tool()
def sdk_tms_status(expected_environment: str, transaction_id: str) -> dict:
    """Read AST transaction status; excludes payload, identities and signatures."""
    from .tms import read
    return _backend_operation(expected_environment, lambda b: read(b, transaction_id))


@mcp.tool()
def sdk_tms_result(expected_environment: str, transaction_id: str) -> dict:
    """Read final AST result metadata; a missing result is not success.

    For an accepted transaction it also reports the device signature as evidence
    (signed_data_present, size and SHA-256 of the CMS) without returning the CMS.
    """
    from .tms import read
    return _backend_operation(expected_environment, lambda b: read(b, transaction_id, result=True))


@mcp.tool()
def sdk_tms_cancel(expected_environment: str, transaction_id: str) -> dict:
    """Request cancellation of the specified authorized transaction; verify result separately."""
    from .tms import cancel
    return _backend_operation(expected_environment, lambda b: cancel(b, transaction_id))


@mcp.tool()
def sdk_docs(section: str | None = None, offset: int = 0) -> dict:
    """Integration method, recipes and reference source, for clients that cannot load skills.

    Call with no section first: it returns the section index and the workflow (only this
    call lists the sections). Then read the section for the task (platforms, tms, sdk-delivery, modules, log-export, ios).
    Reference source files are sections named by path, e.g.
    "ios/email-code/MasterControllerSession.swift". The official KOBIL documentation is the
    "official" section (index) and "official/<page>" sections. When a result has next_offset,
    call again with that offset to get the rest of the section.
    """
    from .docs import read
    return read(section, offset)


@mcp.tool()
def sdk_official_docs_search(query: str, limit: int = 20, scope: str = 'all') -> dict:
    """Search the bundled official KOBIL MCSDK documentation (Shift Lite - IdpSdk and the MCSDK
    introduction, copied from developer.kobil.com) and this plugin's guides. Answer SDK
    questions from these pages and cite the source URL of official results.

    scope: "all" (default), "official" or "guides". Each result has kind "official" or
    "guide"; up to `limit` of each. A guide records what was verified on a device, such as a
    feature the iOS SDK lacks, which the official pages do not say. Read a page with
    sdk_docs(section=...). The "official" section lists every page and the known places where
    the documentation differs from the shipped iOS 15.16 headers; sdk_api_lookup checks a
    name against the delivered SDK itself.
    """
    from .docs import search
    return search(query, limit, scope)


@mcp.tool()
def sdk_api_lookup(name: str, version: str | None = None, limit: int = 50) -> dict:
    """Does the delivered iOS SDK have this class, event, method or constant? Reads the release.

    Searches the headers of the installed iOS release (sdk_artifacts_list) for one identifier,
    case-insensitive (e.g. "KSMClearIamTokenCacheEvent", "Chat", "suspend"), and returns each
    header line with framework, file and line number. For every class declared there it
    reports whether the binary exports it: some classes are declared but missing, and an app
    using them fails to link. version picks the release when several are installed. Needs
    Xcode (xcrun nm) for the binary check. The headers and binary decide what compiles, not
    the documentation.
    """
    from .sdkapi import lookup
    return lookup(name, version=version, limit=limit)


@mcp.tool()
def sdk_platforms(expected_environment: str) -> dict:
    """List the platform values this tenant accepts. Read-only; no admin rights needed."""
    from .discovery import platforms
    return _backend_operation(expected_environment, platforms)


@mcp.tool()
def sdk_backend_verify(expected_environment: str) -> dict:
    """Prove the credential works and report which roles reach the token. No writes.

    Authentication succeeding is not enough: AST needs a role that only travels on a
    requested scope. This is the check to run before any backend write.
    """
    from .discovery import token_roles
    result = _backend_operation(expected_environment, token_roles)
    has_role = any('ks-management' in r or r in ('Admin', 'AstServicesAdmin')
                   for r in result.get('client_roles_in_token', []))
    result['ready_for_backend_writes'] = has_role
    result['next_step'] = ('Proceed with sdk_app_get()/sdk_app_ensure().' if has_role else
                           'No AST role in the token. Add the optional scope that carries it to '
                           'oauth.scope in the connection file, then run this again.')
    return result


@mcp.tool()
def sdk_idp_clients(expected_environment: str, client_ids: list[str] | None = None) -> dict:
    """Report which IDP flow clients exist, so the app names a real one. Read-only.

    Probes the token endpoint with an unknown account: an absent client answers
    invalid_client. No real user is touched and nothing is written. Prefer
    sdk_idp_journeys, which also finds and classifies the clients; use this only
    to check named client ids when the admin block is not configured.
    """
    from .backend import configuration
    from .discovery import idp_clients
    cfg = configuration(expected_environment)
    result = idp_clients(cfg, client_ids)
    result['next_step'] = ('Pass the client that issues the login tokens to sdk_mc_config() as client_id: '
                           'the login client for email-code apps (see sdk_mc_config and references/tms.md).')
    return result


@mcp.tool()
def sdk_artifacts_install(source_zip: str, expected_sha512: str | None = None,
                          version: str | None = None) -> dict:
    """Verify a delivered iOS SDK zip against its SHA-512 and extract it into the local store.

    The store (~/.kobil-sdk/artifacts, or KOBIL_SDK_ARTIFACTS) keeps one folder per release
    with the debug and release framework sets and a manifest. Verification uses the .sha512
    file KOBIL ships next to the zip, or expected_sha512; an unverified zip is refused.
    Idempotent per version. Nothing is downloaded: bring the zip KOBIL delivered.
    """
    from .artifacts import install_ios_zip
    result = install_ios_zip(source_zip, None, expected_sha512, version)
    result['next_step'] = ('sdk_ios_project_integrate() with the Xcode project and its app target; '
                           'the debug set is used while developing.')
    return result


@mcp.tool()
def sdk_artifacts_import(delivery_dir: str | None = None) -> dict:
    """Install every SDK zip KOBIL delivered, from the delivery folder, into the local store.

    The delivery folder is where KOBIL's release landed (an SFTP mirror, a shared folder, a
    manual drop): KOBIL_SDK_DELIVERY, ~/.kobil-sdk/delivery, or delivery_dir. Each
    MCSDK_iOS_*.zip and MCSDK_Android_*.zip is verified against its .sha512 sidecar and
    extracted once; the changelog, README and risk notes next to it are kept in the store.
    Nothing is downloaded. Idempotent.
    """
    from .artifacts import import_delivery
    result = import_delivery(delivery_dir)
    result['next_step'] = ('sdk_artifacts_notes() to show the release changelog, then '
                           'sdk_ios_project_integrate() for an iOS project.')
    return result


@mcp.tool()
def sdk_artifacts_notes(platform: str, version: str | None = None, document: str = 'CHANGELOG.md') -> dict:
    """Return a delivered release document from the store: CHANGELOG.md, README.md or risks.json.

    The delivery recipe asks for the release notes to be shown after the SDK is installed;
    this serves them from the store so the zip is not needed again. Reads only.
    """
    from .artifacts import release_notes
    return release_notes(platform, version, document)


@mcp.tool()
def sdk_artifacts_list() -> dict:
    """List the SDK releases in the local store, both platforms, with paths and checksums. Reads only."""
    from .artifacts import installed_all, store_root
    records = installed_all()
    return {'store': str(store_root()), 'releases': records,
            'next_step': ('sdk_ios_project_integrate() when a release is present; sdk_artifacts_install() '
                          'with the delivered zip otherwise.')}


@mcp.tool()
def sdk_ios_project_integrate(project_path: str, target_name: str, version: str | None = None,
                              variant: str = 'debug', marketing_version: str = '1.0.0',
                              deployment_target: str | None = None,
                              usage_descriptions: dict[str, str] | None = None) -> dict:
    """Add the four XCFrameworks to an Xcode app target as Embed & Sign, with the bridging header.

    Copies the framework set from the store to a Frameworks folder next to the .xcodeproj
    (outside the synchronised source folder, so Xcode lists each framework once), writes
    <Target>-Bridging-Header.h, and edits project.pbxproj: file references in a "KOBIL SDK"
    group, link entries in the target's Frameworks phase, embed build files with
    code-sign-on-copy in an Embed Frameworks phase, the bridging-header build setting and the
    marketing version. Verified by reading
    the file back. Idempotent. Build once afterwards before adding code.

    The app target is limited to iPhone and iPad (SUPPORTED_PLATFORMS iphoneos
    iphonesimulator, device family 1,2, no Mac Catalyst or visionOS): the SDK has no other
    slices. usage_descriptions adds Info.plist privacy strings the project lacks, keyed
    NSFaceIDUsageDescription (Face ID sign-in), NSCameraUsageDescription (profile photo) or
    NSPhotoLibraryUsageDescription, with the user-facing sentence as value; an existing
    string is never overwritten. Calling again with new usage_descriptions adds only those.
    Xcode reloads the project after the edit and cancels a build started before; wait for
    the reload, then build. Do not edit project.pbxproj by hand for these. When the local
    store is empty, the delivery bundled with this MCP is imported first, so no install
    step and no paths are needed.
    """
    from .artifacts import ensure_ios_release
    from .xcodeproj import integrate
    release, folder, imported = ensure_ios_release(None, None, version, variant)
    result = integrate(project_path, target_name, folder, marketing_version, deployment_target, usage_descriptions)
    result['sdk_version'] = release
    result['variant'] = variant
    if imported is not None:
        result['imported_delivery'] = imported
    result['next_step'] = ('Build the project. Then add the three bundle files (certificate, sdk_config.jwt, '
                           'mc_config.json) to the target folder and copy the Swift reference sources.')
    return result


@mcp.tool()
def sdk_trusted_certificate_write(expected_environment: str, output_path: str,
                                  host: str | None = None) -> dict:
    """Write the root certificate the SDK must trust to a NEW PEM file, and prove it fits.

    Reads the verified TLS chain of the IDP host (or `host`), keeps its self-signed root,
    saves it, then checks every backend host in the connection file with a context that
    trusts only that file. Use the file name in sdk_mc_config (certificate_file) and the
    path in sdk_config_write (certificate_paths). Reads only from the network.
    """
    from .certificate import write_root_certificate
    from .backend import configuration
    cfg = configuration(expected_environment)
    result = write_root_certificate(cfg, output_path, host)
    result['next_step'] = ('sdk_config_write() with this path in certificate_paths, then sdk_mc_config() '
                           'with certificate_file="%s".' % result['file_name'])
    return result


@mcp.tool()
def sdk_mc_config(expected_environment: str, client_id: str, certificate_file: str,
                  idp_url: str | None = None, key_policy: str = 'ALLOW_VIRTUAL_SMART_CARD',
                  output_path: str | None = None) -> dict:
    """Generate the app-side mc_config.json content, and save it when output_path is given.

    client_id: the SDK also uses iam.clientId for every later token exchange (explicit-
    authentication TMS answers, KSMExchangeIamTokenEvent). Keycloak lets a public client
    exchange only tokens it holds itself, so it must be the client that issued the login
    tokens, or those exchanges fail with 403 "Client is not the holder of the token".
    - App activates by email code or another app-driven journey (the email-code reference):
      pass the LOGIN client. The activation journeys name their own client in the
      authorisation URL and in KSMSetAuthorisationCodeEvent, so they are unaffected.
      Device-verified 2026-09-27.
    - App uses an official login standard (kssidp or bddk): pass the standard's LOGIN
      client (KSSIDPWebBasedLogin or BDDKLogin); the enrollment client is named per request.
    - App activates through KSSIDP's activation-code journey: that journey reads this value,
      so pass the activation-code client from sdk_idp_journeys; explicit-authentication TMS
      and token exchange then need the login to use that client too (not verified).
    acr_values=1 belongs only on requests KSSIDP runs (the activation-code journey and the
    one-page login). Never send it on the email-code journeys. See the skill's
    activation-login-findings reference.
    certificate_file is the trusted certificate's name as bundled with the app; the SDK
    resolves it by that exact name. key_policy: ALLOW_VIRTUAL_SMART_CARD (devices without
    a secure element), ENFORCE_HARDWARE or ENFORCE_STRONG_HARDWARE.
    idp_url: leave empty; it is the IDP host of the connection file (admin.idp_url, else
    oauth.token_url before /auth/realms/). Never copy it from another app's mc_config.json.
    """
    from .appconfig import mc_config, write_mc_config
    from .backend import configuration
    from .themecheck import idp_base_url
    cfg = configuration(expected_environment)
    result = mc_config(cfg, idp_url or idp_base_url(cfg), client_id, certificate_file, key_policy)
    if output_path is not None:
        # The generator returns the file text under 'content'; save exactly that.
        result = dict(result)
        result['path'] = write_mc_config(result['content'], output_path)
        result['next_step'] = 'Add the saved file to the app bundle; it must sit next to the certificate it names.'
    return result


@mcp.tool()
def sdk_tms_scope_ensure(expected_environment: str, client_id: str) -> dict:
    """Prepare the realm for explicit-authentication transactions (additive IDP write).

    Creates the realm client scope "tms" if missing and adds it as an OPTIONAL scope of
    client_id, which must be mc_config.json iam.clientId (the login client). Without it the
    phone's answer is refused with 403 code 4034 "Required explicit authentication scope
    'tms' is missing" and the transaction ends failed with nothing on screen. Needs the
    optional admin block in the connection file. Device-verified 2026-09-27.
    """
    from .idpflow import ensure_tms_scope
    result = _backend_operation(expected_environment, lambda b: ensure_tms_scope(b, client_id))
    result.setdefault('next_step', 'sdk_tms_trigger(require_explicit_authentication=True, freshness_seconds=-1) '
                                   'to a logged-in test user, then sdk_tms_result().')
    return result


@mcp.tool()
def sdk_activation_user_ensure(expected_environment: str, username: str, email: str | None = None,
                               first_name: str = 'KOBIL', last_name: str = 'Test User',
                               group: str = 'ks-users') -> dict:
    """Create the passwordless tenant user that will activate the app on a device.

    Use a dedicated activation user: the registration user recorded on the version is a
    separate role and must not be replaced by it. An existing user is reused unmodified.
    Needs the optional admin block in the connection file.
    """
    from .activation import ensure_user
    result = _backend_operation(expected_environment,
                                lambda b: ensure_user(b, username, email, first_name, last_name, group))
    result['next_step'] = ('kssidp login standard: sdk_activation_password_set(temporary=True), then '
                           'sdk_activation_code_set(); the tester chooses the login password on the '
                           'third enrollment page. bddk: only sdk_activation_code_set(). Activation-code '
                           'journey: sdk_activation_password_set() (permanent), then sdk_activation_code_set().')
    return result


@mcp.tool()
def sdk_activation_password_set(expected_environment: str, user_uuid: str, length: int = 14,
                                temporary: bool = False) -> dict:
    """Set the IDP password an activated user needs, generated here and returned once.

    temporary=False (default): the permanent login password. The one-page activation
    journey and sdk_activation_user_ensure set none, so without it the first login fails.
    temporary=True: the temporary password the kssidp login standard's enrollment asks
    for on its second page; the tester then chooses the real password on the third page.
    The bddk standard needs neither (the tester chooses the password during enrollment).
    Replaces any existing password. Storage is confirmed by reading the credential back.
    """
    from .activation import set_login_password
    result = _backend_operation(expected_environment,
                                lambda b: set_login_password(b, user_uuid, length, temporary))
    result['next_step'] = (('Give the tester this temporary password for the second enrollment page. '
                            'sdk_activation_code_set() next, run after this call and never in parallel '
                            'with anything that deletes codes.') if temporary else
                           ('Give the tester this password for the login screen (email + password). '
                            'sdk_activation_code_set() next if no code has been issued yet.'))
    return result


@mcp.tool()
def sdk_login_standard_check(expected_environment: str, login_standard: str = 'kssidp',
                             activation_client: str | None = None,
                             login_client: str | None = None) -> dict:
    """Check the realm against one of KOBIL's official native login standards. Reads only.

    Native (KSSIDP) apps use one of two standards, each defined by KOBIL's official IDP
    flow exports:
    - kssidp (current): clients KSSIDPWebBasedEnrollment / KSSIDPWebBasedLogin, flows
      "KSSIDP Enrollment - Multi form flow" / "KSSIDP Mobile App Multi Flow Login", theme
      kobil-lite. Enrollment: user ID + activation code, temporary password, new password
      (three pages; the app must post pages 2 and 3 natively).
    - bddk (deprecated in IDP 5.1/5.2, removal planned for 6.0): BDDKEnrollment /
      BDDKLogin, flows "BDDK Enrollment" / "BDDK Login". Enrollment: user ID + activation
      code + new password on one page. Only for deployments that already run BDDK.
    Client names default to the standard's own. Checks each client's flow binding, theme,
    the official step order and the step settings a first activation depends on (the
    link step's read_ast_data_from_session, whose absence gives 513_4041). A blocked
    result means: ask the IDP administrator to import the official export; never build
    or edit a flow to make this pass. Read the skill's references/login-standards.md.
    """
    from .login_standards import check_realm
    result = _backend_operation(expected_environment,
                                lambda b: check_realm(b, login_standard, activation_client, login_client))
    if result['status'] == 'configuration_checked':
        result['next_step'] = ('sdk_mc_config(client_id=<login client>), then per test user: '
                               'sdk_activation_user_ensure(), '
                               + ('sdk_activation_password_set(temporary=True), '
                                  if login_standard == 'kssidp' else '')
                               + 'sdk_activation_code_set(). App code: references/login-standards.md.')
    return result


@mcp.tool()
def sdk_activation_code_set(expected_environment: str, user_uuid: str, valid_for: str = '60d',
                            digits: int = 8) -> dict:
    """Issue a one-time activation code for the first enrolment of a device.

    The code is generated by this tool and returned once; it is never taken as an
    argument. valid_for is a period such as 30m, 12h or 60d. Storage is confirmed by
    reading the credential back before the code is handed out.
    """
    from .activation import set_activation_code
    result = _backend_operation(expected_environment,
                                lambda b: set_activation_code(b, user_uuid, valid_for, digits))
    result['next_step'] = ('Launch the app, wait for ACTIVATION_REQUIRED, then enter this username and '
                           'code. Login standards: the new password chosen during enrollment is the login '
                           'password. Activation-code journey: a password typed on the activation screen '
                           'is not sent to the IDP; the login password comes from sdk_activation_password_set().')
    return result


@mcp.tool()
def sdk_activation_user_status(expected_environment: str, user_uuid: str) -> dict:
    """Read what the IDP records for a test user: credentials, sessions, failed logins.

    The reliable record of a device flow when the app's console is silent: a login leaves a
    session for the login client, a wrong password raises the failure count, an activation
    consumes the ACTIVATION_CODE credential. Reads only; needs the admin block.
    """
    from .activation import user_status
    result = _backend_operation(expected_environment, lambda b: user_status(b, user_uuid))
    result['next_step'] = ('Compare with what the app claims. No session and no failure means the '
                           'request never reached the IDP; look at the app side.')
    return result


@mcp.tool()
def sdk_activation_flow_ensure(expected_environment: str, alias: str, steps: list[str] | None = None,
                               description: str | None = None,
                               step_config: dict[str, dict] | None = None) -> dict:
    """Create the IDP browser flow that consumes an activation code, or read the existing one.

    Without such a flow a realm cannot activate a device however correct the app is: the
    client's journey decides which form the SDK is asked to fill. The default is the flow
    verified on a device: AST activate, code page, AST link, delete code, with the two AST
    steps configured separately (step_config keys "provider" or "provider#N"). Additive
    only; an existing flow is returned unmodified. Needs the admin block in the connection
    file.
    """
    from .idpflow import ensure_flow
    result = _backend_operation(expected_environment,
                                lambda b: ensure_flow(b, alias, steps, 'REQUIRED', description, step_config))
    result.setdefault('next_step', 'sdk_activation_client_ensure() to bind a client to this flow.')
    return result


@mcp.tool()
def sdk_activation_client_ensure(expected_environment: str, client_id: str, flow_alias: str,
                                 login_theme: str = 'kobil-lite',
                                 redirect_uri: str = 'https://kobil/OpenIdRedirectUri',
                                 ast_client_scope: str = 'ast') -> dict:
    """Create the public IDP client the app names in mc_config.json, bound to an activation flow.

    login_theme decides the markup the SDK has to parse. Pick a theme whose template is
    well-formed: a strict XHTML parser rejects a page with unbalanced tags and the SDK
    then fails before any credential is sent. Additive only.
    """
    from .idpflow import ensure_client
    result = _backend_operation(expected_environment,
                                lambda b: ensure_client(b, client_id, flow_alias, login_theme,
                                                        redirect_uri, ast_client_scope))
    result.setdefault('next_step', 'sdk_mc_config() with this client id, then rebuild the app.')
    return result


@mcp.tool()
def sdk_idp_theme_check(expected_environment: str, client_id: str,
                        redirect_uri: str = 'https://kobil/OpenIdRedirectUri') -> dict:
    """Check that the login page an IDP client serves is one KSSIDP can parse. Reads only.

    KSSIDP parses login pages as strict XML and drops a malformed page silently: no result,
    no error, the app waits forever. Run this for the login client before a device test,
    and first whenever a login hangs on a spinner. An activation client, and a login-standard
    client such as KSSIDPWebBasedLogin, answer 406 to a browser request; that is reported as
    not checkable, not as a failure. For kssidp, sdk_login_standard_check checks the theme.
    """
    from .themecheck import check_login_page
    result = _backend_operation(expected_environment,
                                lambda b: check_login_page(b, client_id, redirect_uri))
    if result.get('checked') and result.get('well_formed') and result.get('json_input_has_type') is not False:
        result['next_step'] = 'The theme is readable; proceed with the device test.'
    elif result.get('checked'):
        result['next_step'] = ('Reapply the theme patch in the idp-core pod, then run this again; '
                               'do not debug the app until it passes.')
    else:
        result['next_step'] = ('Validate this client on a device; a browser cannot reach its first page. '
                               'For a kssidp login client, sdk_login_standard_check is the backend '
                               'check (it covers the kobil-lite theme).')
    return result


@mcp.tool()
def sdk_idp_journeys(expected_environment: str, client_ids: list[str] | None = None) -> dict:
    """Find this realm's activation-code, login and email-code clients, whatever they are named.

    Run this before naming any client: a realm can call its activation client and flow
    anything, and an example name from another realm will simply not exist here. Reads the
    clients with a browser-flow override and classifies each flow. Disclosure is minimal:
    four fields per activation or login client, only a count of anything else, never
    secrets, redirect URIs or attributes. Pass client_ids to read only those clients.
    Reads only; needs the admin block, whose holder already sees the whole realm.
    """
    from .idpflow import discover_journeys
    result = _backend_operation(expected_environment, lambda b: discover_journeys(b, client_ids))
    if result['activation'] or result['email_code']:
        result['next_step'] = ('Activation-code journey: sdk_mc_config() with client_id = one of the activation '
                               'clients. Email-code journey: run the email_code clients natively, no code or '
                               'password to issue. Keep a login client for the app\'s login override.')
    else:
        result['next_step'] = ('No activation journey here: sdk_activation_flow_ensure() and '
                               'sdk_activation_client_ensure() create one, then sdk_mc_config().')
    return result


@mcp.tool()
def sdk_activation_flow_describe(expected_environment: str, alias: str) -> dict:
    """Read one IDP browser flow's steps in order. Reads only; changes nothing."""
    from .idpflow import describe_flow
    return _backend_operation(expected_environment, lambda b: describe_flow(b, alias))


@mcp.tool()
def sdk_activation_step_config(expected_environment: str, alias: str, provider: str,
                               config: dict, occurrence: int = 1) -> dict:
    """Set one flow step's authenticator configuration, and verify it by reading it back.

    An authenticator with no configuration runs on its own defaults, which are not the ones
    an activation needs. The AST step is the common case: unconfigured it demands a client
    id header that a device cannot have before its first activation, and the SDK then
    reports HTTP 406 with IDP subsystem 580. occurrence selects the Nth step running this
    provider, in flow order: the working activation flow runs ast-login-authenticator twice,
    first as activate, then as link.
    """
    from .idpflow import configure_step
    result = _backend_operation(expected_environment,
                                lambda b: configure_step(b, alias, provider, config, None, occurrence))
    result['next_step'] = 'Retry the activation on the device; no app rebuild is needed.'
    return result
