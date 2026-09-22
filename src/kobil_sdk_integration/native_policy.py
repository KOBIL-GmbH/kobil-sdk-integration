"""Read-only native integration preflight; never substitutes or provisions flows."""
from typing import Literal
from .idp_admin import Admin
from .backend import segment

POLICY = {
    "paths": ["kstrustedwebview", "kssidp"],
    "kssidp": {"activation_client": "BDDKEnrollment", "login_client": "BDDKLogin",
               "use_token_based_login": True, "ast_server_backend": "maverick",
               "login_header": "X-KOBIL-ASTUSERID"},
    "forbidden_flow": "SuperApp Login V2",
    "missing_client_action": "blocked; do not create or substitute a flow",
}


def preflight(api, path, activation_client, login_client, use_token_based_login,
              ast_server_backend, login_header):
    errors = []
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
        bindings.append({"role": role, "client_id": client_id, "flow_alias": alias})
        if not alias or "superapp" in alias.casefold():
            errors.append(f"{role}: missing or SuperApp flow is incompatible with this native integration.")
        if path == "kssidp" and alias != {"activation": "BDDK Enrollment", "login": "BDDK Login"}[role]:
            errors.append(f"{role}: unexpected BDDK flow binding; do not proceed.")
    return {"status": "blocked" if errors else "configuration_checked", "errors": errors,
            "bindings": bindings, "runtime_verified": False,
            "limits": "Checks client availability and flow bindings, not every authenticator configuration, PIN policy or live app behavior. WebView uses KSTrustedWebView; verify its selected journey separately."}


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
        explicitly selected deployment clients. Reject missing/substituted clients
        and SuperApp bindings. Never mutate flows to make a preflight pass.
        Configuration checked is NOT live acceptance; backend/auth failures propagate.
        """
        with Admin(expected_environment, realm) as api:
            result = preflight(api, path, activation_client, login_client,
                               use_token_based_login, ast_server_backend, login_header)
        return {**result, "platform": platform, "path": path, "policy": POLICY}
