"""Read-only native integration preflight; never substitutes or provisions flows."""
from typing import Literal
from .idp_admin import Admin
from urllib.parse import urlencode
from .backend import segment, realm_base_url, WEBVIEW_REQUEST_HEADERS

POLICY = {
    "paths": ["kstrustedwebview", "kssidp"],
    "kssidp": {"activation_client": "BDDKEnrollment", "login_client": "BDDKLogin",
               "use_token_based_login": True, "ast_server_backend": "maverick",
               "login_header": "X-KOBIL-ASTUSERID"},
    "kstrustedwebview": {
        "recommended_clients": {"activation_client": "KobilMobileEnrollment", "login_client": "KobilMobileLogin"},
        "client_selection": "Preserve the project's explicitly selected enrollment/login clients, including themed copies. On a realm that offers themed mobile copies (login_theme kobil-mobile, e.g. KobilMobileEnrollment/KobilMobileLogin) use them; the BDDK clients carry the plain kobil-lite theme and are NOT defaults for the WebView path (measured 2026-10-08: an agent that took BDDK* showed the desktop-styled login page in the app).",
        "theme_selection": "Inspect each selected client's login_theme and browser-flow binding; do not change shared flows or realm theme. An absent client override does not establish the effective realm theme.",
    },
    "forbidden_flow": "SuperApp Login V2",
    "missing_client_action": "blocked; do not create or substitute a flow",
}


PLAIN_THEMES = {"kobil-lite", "keycloak", "base"}


def theme_warning(path, client_id, theme):
    """Plain desktop themes in a WebView path are a presentation defect, not a blocker."""
    if path == "kstrustedwebview" and theme in PLAIN_THEMES:
        rec = POLICY["kstrustedwebview"]["recommended_clients"]
        return (f"{client_id}: login_theme {theme} is the plain desktop theme; the mobile WebView should use a "
                f"kobil-mobile themed client ({rec['activation_client']}/{rec['login_client']} where the realm offers them).")
    return None


def suitable_addresses(realm_base, client_id, redirect_uris):
    """The addresses the server accepts for this client, so the app does not assemble them itself.

    The authorization endpoint is the realm base plus /protocol/openid-connect/auth; the redirect URI must be one the
    client has registered (the first one is returned). Nothing is invented when the realm base or a redirect is missing.
    """
    redirect = next((u for u in (redirect_uris or []) if isinstance(u, str) and u and '*' not in u), None)
    out = {"redirect_uri": redirect}
    if realm_base:
        endpoint = realm_base.rstrip("/") + "/protocol/openid-connect/auth"
        out["authorization_endpoint"] = endpoint
        out["required_request_headers"] = WEBVIEW_REQUEST_HEADERS
        if redirect:
            query = urlencode({"client_id": client_id, "redirect_uri": redirect, "response_type": "code", "scope": "openid"})
            out["authorization_url_template"] = endpoint + "?" + query + "&nonce=<random>&code_challenge=<code_challenge from GetAstClientData>&code_challenge_method=<code_challenge_method from GetAstClientData>&state=<random state>"
    return out


def preflight(api, path, activation_client, login_client, use_token_based_login,
              ast_server_backend, login_header, realm_base=None):
    errors = []
    warnings = []
    if use_token_based_login is not True:
        errors.append("useTokenBasedLogin must be true; false skips IAM setup and can cause CannotAcquireTokenData(50).")
    if ast_server_backend != "maverick":
        errors.append("astServerBackend must be maverick.")
    if path == "kssidp":
        if (activation_client, login_client) != ("BDDKEnrollment", "BDDKLogin"):
            errors.append("Native KSSIDP requires BDDKEnrollment and BDDKLogin; no substitute clients.")
        if login_header != "X-KOBIL-ASTUSERID":
            errors.append("Login header must be X-KOBIL-ASTUSERID.")
    elif path != "kstrustedwebview":
        errors.append("Choose kssidp or kstrustedwebview for native mobile apps.")
    if not activation_client or not login_client:
        errors.append("Explicit activation and login clients are required; never infer WebView clients from native KSSIDP clients.")
    if errors:
        return {"status": "blocked", "errors": errors, "bindings": [], "runtime_verified": False}
    bindings = []
    for role, client_id in (("activation", activation_client), ("login", login_client)):
        clients = api.call("GET", "/clients", params={"clientId": client_id, "first": 0, "max": 2})
        if not isinstance(clients, list) or len(clients) != 1 or clients[0].get("clientId") != client_id:
            errors.append(f"{role}: client is missing or ambiguous; stop and repair configuration.")
            continue
        client = clients[0]
        if client.get("enabled") is not True or client.get("standardFlowEnabled") is not True:
            errors.append(f"{role}: client must be enabled with standard flow enabled.")
        flow_id = (client.get("authenticationFlowBindingOverrides") or {}).get("browser")
        if not flow_id:
            errors.append(f"{role}: explicit browser flow binding required for verification.")
            continue
        flow = api.call("GET", "/authentication/flows/" + segment(flow_id))
        alias = flow.get("alias") if isinstance(flow, dict) else None
        attributes = client.get("attributes") or {}
        warning = theme_warning(path, client_id, attributes.get("login_theme"))
        if warning:
            warnings.append(warning)
        bindings.append({"role": role, "client_id": client_id, "flow_alias": alias,
                         "login_theme_override": attributes.get("login_theme"),
                         "theme_warning": warning,
                         "theme_source": "client_override" if attributes.get("login_theme") else "realm_default_not_checked",
                         "redirect_uris": client.get("redirectUris", [])})
        bindings[-1].update(suitable_addresses(realm_base, client_id, client.get("redirectUris")))
        if not alias or "superapp" in alias.casefold():
            errors.append(f"{role}: missing or SuperApp flow is incompatible with this native integration.")
        if path == "kssidp" and alias != {"activation": "BDDK Enrollment", "login": "BDDK Login"}[role]:
            errors.append(f"{role}: unexpected BDDK flow binding; do not proceed.")
    return {"status": "blocked" if errors else "configuration_checked", "errors": errors,
            "warnings": warnings, "bindings": bindings, "runtime_verified": False,
            "limits": "Checks client availability and flow bindings, not every authenticator configuration, PIN policy or live app behavior. TLS trust anchors and certificate-chain coverage are not verified here; derive them from the chains actually negotiated by the mobile TLS clients. WebView uses KSTrustedWebView; verify its selected journey separately."}


def register(mcp):
    @mcp.tool()
    def sdk_native_preflight(expected_environment: str, platform: Literal["android", "ios"],
                             path: Literal["kssidp", "kstrustedwebview"],
                             activation_client: str, login_client: str,
                             use_token_based_login: bool, ast_server_backend: str,
                             login_header: str, realm: str | None = None) -> dict:
        """Required read-only native app preflight before building or activation.

        KSSIDP requires BDDKEnrollment/BDDKLogin, token-based login=true,
        maverick and X-KOBIL-ASTUSERID. WebView means KSTrustedWebView with
        explicitly selected deployment clients, including user-selected themed copies.
        Preserve those selections instead of defaulting to the BDDK examples.
        Returns for each client the addresses the server accepts (authorization_endpoint, registered redirect_uri,
        authorization_url_template), client theme overrides and redirect URIs for review; an absent
        override means the realm default is not checked. Reject missing/substituted clients
        and SuperApp bindings. Never mutate flows to make a preflight pass.
        Configuration checked is NOT live acceptance; backend/auth failures propagate.
        """
        with Admin(expected_environment, realm) as api:
            admin = api.cfg.get("admin") or {}
            base = realm_base_url(admin["idp_url"], api.realm) if admin.get("idp_url") else None
            result = preflight(api, path, activation_client, login_client,
                               use_token_based_login, ast_server_backend, login_header, realm_base=base)
        return {**result, "platform": platform, "path": path, "policy": POLICY,
                "required_followup_checks": ["sdk_deployment_preflight", "sdk_tls_chain_check"] +
                    (["sdk_ios_signing_preflight"] if platform == "ios" else []),
                "next_gate": "Before activation verify local deployment settings and TLS trust; before iOS installation verify the signed artifact against the explicitly selected team and device. Before explicit-authentication TMS rerun deployment preflight with actual token-holder and granted scope metadata. Never infer deployment mTLS or signing team from SDK samples."}
