"""Read-only verification of an actual signed iOS app; never signs or installs."""
from datetime import datetime, timezone
from pathlib import Path
import plistlib
import re
import subprocess
import tempfile
from xml.parsers.expat import ExpatError

_TIMEOUT = 20
_LIMITS = ("Artifact checks only: does not establish device trust, installation, SDK "
           "compatibility or runtime acceptance. Entitlements require profile authorization; "
           "wildcards are supported only for app identifiers, keychain groups and app groups. "
           "No signing or installation performed.")


def _run(argv):
    # Do not return command output: profiles and diagnostics can contain private data.
    return subprocess.run(argv, capture_output=True, timeout=_TIMEOUT, check=False)


def _plist(result):
    for data in (result.stdout, result.stderr):
        if not isinstance(data, bytes):
            continue
        start = data.find(b"<?xml")
        if start >= 0:
            data = data[start:]
        try:
            value = plistlib.loads(data)
            if isinstance(value, dict):
                return value
        except (ValueError, TypeError, plistlib.InvalidFileException, ExpatError):
            pass
    return None


# Wildcard interpretation is deliberately limited to these Apple identifier grants.
_WILDCARD_ENTITLEMENTS = frozenset({
    "application-identifier", "keychain-access-groups",
    "com.apple.security.application-groups",
})


def _authorized(value, allowance, wildcard=False):
    """Conservative plist subset matching; unknown/missing authorization blocks."""
    if type(value) is not type(allowance):
        return False
    if isinstance(value, dict):
        # Nested grants use exact strings: no generic wildcard policy for structures.
        return all(key in allowance and _authorized(item, allowance[key])
                   for key, item in value.items())
    if isinstance(value, list):
        return all(any(_authorized(item, grant, wildcard) for grant in allowance)
                   for item in value)
    if isinstance(value, str) and wildcard and "*" in allowance:
        return (allowance.count("*") == 1 and allowance.endswith("*")
                and "*" not in value and value.startswith(allowance[:-1]))
    return value == allowance


def preflight(app_path: str, expected_team_id: str, device_udid: str | None = None) -> dict:
    """Fail closed on missing or inconsistent artifact signing evidence."""
    errors = []
    checks = {}
    result = {"status": "blocked", "errors": errors, "checks": checks,
              "runtime_verified": False, "limits": _LIMITS}
    if not isinstance(expected_team_id, str) or not re.fullmatch(r"[A-Z0-9]{10}", expected_team_id):
        errors.append("INVALID_EXPECTED_TEAM_ID")
        return result
    if device_udid is not None and (not isinstance(device_udid, str) or not re.fullmatch(r"[A-Za-z0-9-]{8,80}", device_udid)):
        errors.append("INVALID_DEVICE_UDID")
        return result
    try:
        app = Path(app_path).expanduser().resolve(strict=True)
        profile_path = app / "embedded.mobileprovision"
        if app.suffix != ".app" or not app.is_dir() or not profile_path.is_file():
            errors.append("APP_OR_EMBEDDED_PROFILE_MISSING")
            return result
    except (OSError, ValueError, RuntimeError, TypeError):
        errors.append("APP_UNREADABLE")
        return result

    commands = [
        ("signature", ["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)]),
        ("metadata", ["/usr/bin/codesign", "--display", "--verbose=4", str(app)]),
        ("entitlements", ["/usr/bin/codesign", "--display", "--entitlements", ":-", str(app)]),
        ("profile", ["/usr/bin/security", "cms", "-D", "-i", str(profile_path)]),
    ]
    outputs = {}
    for name, argv in commands:
        try:
            output = _run(argv)
        except (OSError, subprocess.SubprocessError):
            errors.append(name.upper() + "_UNAVAILABLE")
            continue
        if output.returncode != 0:
            errors.append(name.upper() + "_FAILED")
            continue
        outputs[name] = output
    checks["codesign_verified"] = "signature" in outputs
    if len(outputs) != len(commands):
        return result

    metadata = (outputs["metadata"].stdout + b"\n" + outputs["metadata"].stderr).decode("utf-8", "replace")
    def field(name):
        values = re.findall(r"^" + re.escape(name) + r"=(.*)$", metadata, re.MULTILINE)
        return values[0].strip() if len(values) == 1 else None
    team = field("TeamIdentifier")
    bundle = field("Identifier")
    entitlements = _plist(outputs["entitlements"])
    profile = _plist(outputs["profile"])
    if not entitlements or not profile:
        errors.append("SIGNING_PLIST_UNREADABLE")
        return result

    def verify(name, ok):
        checks[name] = bool(ok)
        if not ok:
            errors.append(name.upper() + "_MISMATCH_OR_UNKNOWN")

    # codesign writes DER files, never exposed in the response. TemporaryDirectory
    # creates a private directory and removes all extracted certificates on exit.
    leaf = None
    try:
        with tempfile.TemporaryDirectory(prefix="signing-preflight-") as directory:
            prefix = str(Path(directory) / "certificate-")
            extracted = _run(["/usr/bin/codesign", "--display", "--extract-certificates=" + prefix, str(app)])
            if extracted.returncode == 0:
                leaf = Path(prefix + "0").read_bytes()
            else:
                errors.append("CERTIFICATE_EXTRACTION_FAILED")
    except (OSError, subprocess.SubprocessError):
        errors.append("CERTIFICATE_EXTRACTION_UNAVAILABLE")
    certificates = profile.get("DeveloperCertificates")
    verify("signer_certificate_authorized", bool(leaf) and isinstance(certificates, list)
           and bool(certificates) and all(isinstance(cert, bytes) and cert for cert in certificates)
           and leaf in certificates)

    verify("signed_team", team == expected_team_id)
    verify("profile_team", profile.get("TeamIdentifier") == [expected_team_id])
    verify("entitlement_team", entitlements.get("com.apple.developer.team-identifier") == expected_team_id)
    app_identifier = entitlements.get("application-identifier")
    prefixes = profile.get("ApplicationIdentifierPrefix")
    prefixes_valid = (isinstance(prefixes, list) and bool(prefixes)
                      and all(isinstance(p, str) and re.fullmatch(r"[A-Z0-9]{10}", p)
                              for p in prefixes))
    verify("profile_application_identifier_prefix", prefixes_valid)
    verify("signed_application_identifier", isinstance(bundle, str) and bool(bundle)
           and isinstance(app_identifier, str) and prefixes_valid
           and any(app_identifier == prefix + "." + bundle for prefix in prefixes))
    profile_entitlements = profile.get("Entitlements")
    if not isinstance(profile_entitlements, dict):
        profile_entitlements = {}
    verify("profile_entitlement_team", profile_entitlements.get("com.apple.developer.team-identifier") == expected_team_id)
    verify("signed_entitlements_authorized", all(
        key in profile_entitlements and (
            (isinstance(value, bool) and isinstance(profile_entitlements[key], bool)
             and (not value or profile_entitlements[key])) if key == "get-task-allow"
            else _authorized(value, profile_entitlements[key], key in _WILDCARD_ENTITLEMENTS))
        for key, value in entitlements.items()))
    allowed_identifier = profile_entitlements.get("application-identifier")
    identifier_ok = False
    if (isinstance(allowed_identifier, str) and isinstance(app_identifier, str) and prefixes_valid
            and any(allowed_identifier.startswith(prefix + ".") for prefix in prefixes)):
        # Apple's profile app identifiers are exact or have a trailing wildcard.
        if "*" not in allowed_identifier:
            identifier_ok = app_identifier == allowed_identifier
        elif allowed_identifier.count("*") == 1 and allowed_identifier.endswith("*"):
            identifier_ok = app_identifier.startswith(allowed_identifier[:-1])
    verify("profile_application_identifier", identifier_ok)
    expires = profile.get("ExpirationDate")
    valid_expiry = isinstance(expires, datetime)
    if valid_expiry:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        valid_expiry = expires > datetime.now(timezone.utc)
    verify("profile_unexpired", valid_expiry)
    if device_udid is not None:
        devices = profile.get("ProvisionedDevices")
        verify("device_eligible", profile.get("ProvisionsAllDevices") is True or
               (isinstance(devices, list) and all(isinstance(d, str) for d in devices) and device_udid in devices))
    else:
        checks["device_eligible"] = "not_requested"
    if not errors:
        result["status"] = "artifact_checked"
    return result


def register(mcp):
    @mcp.tool()
    def sdk_ios_signing_preflight(app_path: str, expected_team_id: str,
                                  device_udid: str | None = None) -> dict:
        """Verify an actual signed .app before installation (macOS, read-only).

        Supply the customer's explicitly selected Apple team. Checks codesign,
        signed/profile team, signing certificate authorization, profile-authorized
        entitlements and application identifier, provisioning expiration,
        and optionally device eligibility. Missing evidence blocks; no fallback,
        signing, installation, profile contents or raw command output are returned.
        artifact_checked does not prove device trust or runtime success.
        """
        return preflight(app_path, expected_team_id, device_udid)
