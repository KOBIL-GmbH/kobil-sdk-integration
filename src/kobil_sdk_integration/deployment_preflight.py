"""Read-only checks of app configuration against explicit deployment evidence."""
import json
import os
import stat
from typing import Literal
from pathlib import Path

MAX_CONFIG_BYTES = 1024 * 1024


def read_config(path):
    """Bounded regular-file read; never return raw config or parser diagnostics."""
    fd = None
    try:
        target = Path(path).expanduser()
        if not target.is_absolute() or target.is_symlink():
            raise ValueError()
        fd = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_CONFIG_BYTES:
            raise ValueError()
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            fd = None
            raw = stream.read(MAX_CONFIG_BYTES + 1)
        if len(raw.encode("utf-8")) > MAX_CONFIG_BYTES:
            raise ValueError()
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (OSError, ValueError, TypeError, UnicodeError):
        raise ValueError("Provide an absolute path to a readable regular mc_config JSON object (maximum 1 MiB); symlinks are not accepted.") from None
    finally:
        if fd is not None:
            os.close(fd)


def check(mc_config_path, expected_mtls, expected_token_client=None,
          granted_scopes=None, require_explicit_authentication=False,
          granted_scope_stage="current"):

    config = read_config(mc_config_path)
    errors = []
    warnings = []
    if granted_scope_stage not in ("current", "explicit_auth"):
        errors.append("Choose current or explicit_auth token scope evidence stage.")
    if type(expected_mtls) is not bool:
        errors.append("Deployment mTLS choice is required from verified deployment evidence; do not inherit an unrelated SDK sample value.")
    maverick = config.get("maverick")
    actual_mtls = maverick.get("mTLS") if isinstance(maverick, dict) else None
    if type(actual_mtls) is not bool:
        errors.append("mc_config.maverick.mTLS must be an explicit JSON boolean.")
    elif type(expected_mtls) is bool and actual_mtls != expected_mtls:
        errors.append("mTLS does not match the selected deployment. Unsupported TLS client-certificate issuance can produce server 510000015 despite SDK errorCode 0. Do not change TLS policy without deployment evidence.")
    if type(require_explicit_authentication) is not bool:
        errors.append("require_explicit_authentication must be an explicit boolean.")
    iam = config.get("iam")
    client = iam.get("clientId") if isinstance(iam, dict) else None
    binding_checked = False
    if expected_token_client is not None:
        if not isinstance(expected_token_client, str) or not expected_token_client.strip() or len(expected_token_client) > 256:
            errors.append("Provide the token-holder client identifier as metadata, never an access token.")
        elif client != expected_token_client:
            errors.append("iam.clientId differs from the token-holder client. Token exchange may fail with HTTP 403 / 700000022: Client is not the holder of the token. Separate enrollment and interactive-login clients must not be treated as interchangeable token owners.")
        else:
            binding_checked = True
    elif require_explicit_authentication is True:
        errors.append("Explicit-authentication TMS requires known token-holder client metadata before dispatch.")
    scope_checked = False
    if require_explicit_authentication is True:
        valid_scopes = isinstance(granted_scopes, list) and all(isinstance(s, str) and s and len(s) <= 256 and not any(c.isspace() for c in s) for s in granted_scopes)
        if granted_scopes is not None and not valid_scopes:
            errors.append("Provide actual granted scope names as a list, not an access token or realm scope catalog.")
        elif granted_scope_stage == "explicit_auth":
            if not valid_scopes or "tms" not in granted_scopes:
                errors.append("Explicit-authentication token lacks required scope tms (516004034). Do not retry with explicit authentication disabled or grant a scope blindly; verify the deployment step-up authentication contract.")
            else:
                scope_checked = True
        else:
            warnings.append("Current-token scopes do not prove explicit TMS authorization. The SDK may obtain tms during token exchange or step-up; inspect that resulting token and rerun with granted_scope_stage=explicit_auth. Do not require a pre-granted tms scope or change backend permissions blindly.")
    return {"status": "blocked" if errors else "configuration_checked", "errors": errors, "warnings": warnings,
            "token_binding_checked": binding_checked, "explicit_tms_scope_checked": scope_checked,
            "evidence_source": "caller-supplied deployment and token metadata compared with local mc_config",
            "runtime_verified": False, "backend_capability_verified": False,
            "limits": "No backend request, token signature validation or proof of explicit authentication. Scope presence is necessary but not sufficient. Preserve server TLS validation, pinning and the selected key-protection/authentication policy."}


def register(mcp):
    @mcp.tool()
    def sdk_deployment_preflight(mc_config_path: str, expected_mtls: bool,
                                 expected_token_client: str | None = None,
                                 granted_scopes: list[str] | None = None,
                                 require_explicit_authentication: bool = False,
                                 granted_scope_stage: Literal["current", "explicit_auth"] = "current") -> dict:
        """Check actual mc_config before activation and before explicit-authentication TMS.

        Supply verified deployment mTLS choice, not a sample default. Before TMS
        supply token-holder client and actual granted scope NAMES, never tokens.
        Current-token scopes are not a pre-grant requirement. Use explicit_auth
        stage for the exchange/step-up result; missing tms then blocks. No backend calls, mutations,
        credential output, automatic scope grants or authentication downgrade.
        Configuration checked is not live acceptance or backend capability proof.
        """
        return check(mc_config_path, expected_mtls, expected_token_client,
                     granted_scopes, require_explicit_authentication, granted_scope_stage)
