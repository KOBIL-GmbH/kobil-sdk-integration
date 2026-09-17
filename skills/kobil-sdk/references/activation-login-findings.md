# First activation and login on a KSSIDP realm: verified findings (2026-09-16)

Verified on a KOBIL development realm with an iPhone 15 Pro and MC SDK with KSSIDP. Read
this before touching activation or login; every item cost a device run.

## The token-time blocker and its bypass

After a first activation the IDP's `ASTTokenMapper` performs an AST login at the token
endpoint with the client data blob captured before the activate step minted the client. AST
answers `513_4036 ast_login_with_unactivated_client` and the SDK reports
`CannotAcquireTokenData(50)`. This is KOBIL's idp-core code; no flow, client or app setting
changes it.

Bypass: put `acr_values=1` on the authorisation request. Keycloak stores it as a client-session
note and the mapper only runs the failing AST login when that note is absent; with it present
the mapper copies the minted client id from the user-session note into the token. Keycloak
does not reject an unsatisfied acr value. Cost: the token has no `amr`, so AST refuses the
signing-key upload (`public-keys`, 403, subsystem 510 code 50); the SDK logs it and continues.

## Clients and flows that work

Names are per realm. Never look for a name you saw in another realm: run `sdk_idp_journeys`
first; it classifies every client by the journey its flow runs. The names in the example
column are what the verification realm happened to use.

| Purpose | Role (find it with `sdk_idp_journeys`) | Browser flow shape | Theme / parser | Example name on the verification realm |
|---|---|---|---|---|
| First activation | the realm's activation client, named in `mc_config.json` `iam.clientId`; create one with `sdk_activation_flow_ensure` + `sdk_activation_client_ensure` if the realm has none | ast-login activate (`ast_clientid_required=true`, MLoA none) → kssidp-activation-code-verifier → ast-login link (`ast_clientid_required=false`, `read_ast_data_from_session=true`) → kssidp-delete-activation-code | `kobil-lite`, classic HTML, `isMultiflow = false` | `KOBILAPPActivation` / `KOBILAPP Device Activation` |
| Login | the realm's one-page login client, passed by the app as a client id override, not in mc_config | one step asking user identity + password (form `verify-email`, keys `userIdentity`, `password`) | `kobil-headless-v2`, JSON envelope field `jsonInput` | `IDPSubsequentLoginHeadlessV2` / `SuperApp Login V2` |

Both are the same three-step exchange: `GetAstClientDataEvent` → KSSIDP `initiateConnection`
with the app-built authorisation URL (client_id, redirect_uri, response_type=code,
scope=openid, response_mode=form_post, nonce, PKCE challenge from the client data,
`acr_values=1`) and headers `X-KOBIL-ASTCLIENTDATA` + `X-KOBIL-ASTCLIENTID` → KSSIDP posts
`SetAuthorisationCodeEvent` itself. `X-KOBIL-ASTCLIENTID` is 26 zeros before activation and
the id from `GetAstClientDataResultEvent.astClientId` afterwards. Logout is `KSMRestartEvent`;
wait for `KSMRestartResultEvent` before sending anything else.

## Rules that were learned the hard way

- A flow with two rendered pages is unreachable: Keycloak's unescaped `history.replaceState`
  URL after a POST is not XML, and KSSIDP drops the page silently. Keep flows to one page.
- A bare `ast-login-authenticator` step is broken; configure it as in the table.
- The `ast` default client scope is required or the token has no AST client id.
- Never set `pkce.code.challenge.method` on a KSSIDP client.
- Activation codes are one-time; any attempt that reaches the last step consumes one.
- The login theme must be well-formed XHTML; check a served page with `xmllint --noout`.

## Login needs an IDP password that activation never sets

The activation journey consumes a code and activates/links the AST client; it sets no
password. `sdk_activation_user_ensure` creates the user with no credential at all. The login
journey (`verify-email`: email + password) checks the IDP password, so a user without one
fails with a wrong-password answer and Keycloak counts a brute-force failure. Whatever was
typed into a "password" field on the app's activation screen was never sent to the IDP.
Issue the login password with `sdk_activation_password_set` (generated, permanent, shown
once) and hand that value to the tester. Learned 2026-09-17 from a failed login.

## Check the theme before blaming the app

`sdk_idp_theme_check(expected_environment, client_id)` fetches the client's first login page
as a browser would and parses it as strict XML, which is what KSSIDP does. Run it on the
login client (`IDPSubsequentLoginHeadlessV2`) before a device test and first whenever a login
hangs with no error: on the verification realm the readable markup is a patch inside the idp-core
pod that reverts on restart. An activation client answers 406 to a browser and is reported
as not checkable; only a device validates it.
