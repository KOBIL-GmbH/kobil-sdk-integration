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
| First activation | the realm's activation client, named in `mc_config.json` `iam.clientId` for KSSIDP activation-code apps (email-code apps name the login client there instead, see tms.md); create one with `sdk_activation_flow_ensure` + `sdk_activation_client_ensure` if the realm has none | ast-login activate (`ast_clientid_required=true`, MLoA none) → kssidp-activation-code-verifier → ast-login link (`ast_clientid_required=false`, `read_ast_data_from_session=true`) → kssidp-delete-activation-code | `kobil-lite`, classic HTML, `isMultiflow = false` | `<App>Activation` / `<App> Device Activation` (names of your choosing) |
| Login | the realm's one-page login client, passed by the app as a client id override; also `iam.clientId` in email-code apps, because the SDK exchanges the login tokens as that client | one step asking user identity + password (form `verify-email`, keys `userIdentity`, `password`) | `kobil-headless-v2`, JSON envelope field `jsonInput` | `IDPSubsequentLoginHeadlessV2` / `SuperApp Login V2` |

Both are the same three-step exchange: `GetAstClientDataEvent` → KSSIDP `initiateConnection`
with the app-built authorisation URL (client_id, redirect_uri, response_type=code,
scope=openid, response_mode=form_post, nonce, PKCE challenge from the client data,
`acr_values=1`) and headers `X-KOBIL-ASTCLIENTDATA` + `X-KOBIL-ASTCLIENTID` → KSSIDP posts
`SetAuthorisationCodeEvent` itself. `X-KOBIL-ASTCLIENTID` is 26 zeros before activation and
the id from `GetAstClientDataResultEvent.astClientId` afterwards. Logout is `KSMRestartEvent`;
wait for `KSMRestartResultEvent` before sending anything else.

## Rules that were learned the hard way

- A flow with two rendered pages is unreachable through KSSIDP: Keycloak's unescaped
  `history.replaceState` URL after a POST is not XML, and KSSIDP drops the page silently.
  Keep KSSIDP flows to one page. Multi-page journeys run natively instead (see below).
- A bare `ast-login-authenticator` step is broken; configure it as in the table.
- The `ast` default client scope is required or the token has no AST client id.
- Never set `pkce.code.challenge.method` on a KSSIDP client.
- Activation codes are one-time; any attempt that reaches the last step consumes one.
- The login theme must be well-formed XHTML; check a served page with `xmllint --noout`.

## Email-code journeys: activation with no admin-issued code or password (2026-09-26)

Many realms already have KOBIL's self-service journeys on the
`kobil-headless-v2` theme. `sdk_idp_journeys` lists them under `email_code` with a purpose.
Example steps on the verification realm:

| Purpose | Steps (enabled) | Example name |
|---|---|---|
| registration | configure-uid → create-account → email-verification → configure-ud → configure-pwd → … | `IDPRegistrationHeadlessV2` |
| login (first login on a device) | verify-uid (email + password) → email-verification | `IDPLoginHeadlessV2` |
| password_reset | etan (emailed code) → configure-pwd | `IDPForgotPasswordHeadlessV2` |

- They activate a device with no backend change. The verify-identity or eTAN step activates
  the AST client itself and the email step links the user, so the token carries the minted
  id without `acr_values`. Do not send it.
- They have two or more pages, so KSSIDP cannot run them (see the rules above). Run them
  natively: `references/ios/HeadlessIdpFlow.swift` and the
  "Email-code activation" section of `references/ios/README.md`.
- An end user needs no password from `sdk_activation_password_set`. Registration makes the
  user choose one; for an existing account the forgot-password journey sets one by emailed
  code. That is also how an account created by an administrator with only an email gets its
  first password.
- The registration journey answers an email that already has an account with a notice
  ("Verified Email Address… please log in") whose buttons name the next journey. Handle the
  buttons; a dead end here looks like a broken activation.
- After an activating `SetAuthorisationCodeResult` Ok the MasterController is logged in
  (state Running, messaging registered). Route to the logged-in screen. The next launch
  reports LoginRequired with the one user.
- Offering an email-code activation does not justify creating an activation-code flow or
  client. Check `sdk_idp_journeys` first; only a realm with neither kind needs
  `sdk_activation_flow_ensure`.

## Login needs an IDP password that activation never sets

This section applies to the activation-code journey. The activation journey consumes a code and activates/links the AST client; it sets no
password. `sdk_activation_user_ensure` creates the user with no credential at all. The login
journey (`verify-email`: email + password) checks the IDP password, so a user without one
fails with a wrong-password answer and Keycloak counts a brute-force failure. Whatever was
typed into a "password" field on the app's activation screen was never sent to the IDP.
Issue the login password with `sdk_activation_password_set` (generated, permanent, shown
once) and hand that value to the tester. Learned 2026-09-17 from a failed login.

## Check the theme before blaming the app

`sdk_idp_theme_check(expected_environment, client_id)` fetches the client's first login page
as a browser would and parses it as strict XML, which is what KSSIDP does. Run it on the
login client `sdk_idp_journeys` reports (`IDPSubsequentLoginHeadlessV2` on the verification
realm) before a device test and first whenever a login
hangs with no error: on the verification realm the readable markup is a patch inside the idp-core
pod that reverts on restart. An activation client answers 406 to a browser and is reported
as not checkable; only a device validates it.

## Warning 800000015 after activation and login (observed 2026-09-26)

MCSDK iOS 15.16 raises `KSMWarningEvent` errorType 27, code 800000015 ("App Config cannot
be read from database") right after every successful activation and login on the
email-code realm. Activation, login, logout and relaunch all succeeded regardless. Its
meaning is not documented here; record it, do not treat it as the cause of a failure
without further evidence.
