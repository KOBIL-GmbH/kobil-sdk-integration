# KSSIDP login standards: kssidp and bddk

A native KSSIDP app enrolls (first activation) and signs in through two IDP clients whose
flows KOBIL defines. There are two standards. Name one explicitly; never mix their clients.

| | `kssidp` (current, default) | `bddk` (deprecated) |
|---|---|---|
| Status | Replaces BDDK. Confluence pages are DRAFT (Sep 2026) | Deprecated in IDP 5.1/5.2, removal planned for 6.0 |
| Enrollment client | `KSSIDPWebBasedEnrollment` | `BDDKEnrollment` |
| Login client | `KSSIDPWebBasedLogin` | `BDDKLogin` |
| Enrollment flow | "KSSIDP Enrollment - Multi form flow" | "BDDK Enrollment" |
| Login flow | "KSSIDP Mobile App Multi Flow Login" | "BDDK Login" |
| Enrollment pages | 3: user ID + activation code, temporary password, new password + confirmation | 1: user ID + activation code + new password |
| The administrator issues | activation code, temporary password, group `ks-users` | activation code, group `ks-users` |
| Sign-in | user ID + password, header `X-KOBIL-ASTUSERID` | same |
| Login theme | `kobil-lite` (the only theme with the KSSIDP pages on IDP 5.3.1) | not checked |

Client IDs are set per realm. The names above come from KOBIL's IDP flow exports; the public
IdpSdk overview ([official](official/shift-lite-idpsdk__development__idpsdk__idpsdk-overview.md))
lists `KssIdpEnrollment` / `KssIdpLogin` as defaults and says the real values differ per
tenant. `sdk_idp_journeys` recognises a standard by its flow, not by the client name; pass the
realm's client IDs to `sdk_login_standard_check` when they differ from the table.

Both need `useTokenBasedLogin=true`, `astServerBackend=maverick` and `iam.clientId` in
`mc_config.json` set to the **login** client, because the SDK exchanges tokens as that
client. Use `bddk` only for a deployment that already runs it, and tell the person that it
is deprecated.

## Sources

- kssidp: KOBIL IDP Confluence, "KSS-IDP Activation/Enrollment Flow" and "KSS-IDP Login
  Flow" (DRAFT), and the Nouvobanq page "Sync on Flows" that lists the flows given to
  customers. Their exports are bundled in [flows/](flows/), unchanged:
  [enrollment](flows/kssidp-enrollment-multi-form-flow.json),
  [login](flows/kssidp-mobile-app-multi-flow-login.json).
- bddk: KOBIL IDP Confluence "IDP Configuration", attachment `BDDK_Partial_Import.json`.
  It is not bundled: it is a realm partial import whose settings block holds default
  credentials. Take only its two flows and clients.
- Deprecation: KOBIL IDP Confluence "Deprecation Planning".

## Backend check (read-only)

Run `sdk_idp_journeys` (official clients carry `login_standard`), then
`sdk_login_standard_check(login_standard="kssidp")` or `"bddk"`. It checks:

- the clients, and their browser flow binding to the official flow;
- the kobil-lite theme (kssidp). This replaces `sdk_idp_theme_check`, which cannot fetch
  these login clients' first page: it starts with an AST step, so the tool answers 406
  "not checkable". Only a device validates the pages themselves;
- the official top-level step order, with every step REQUIRED;
- the step settings first activation depends on.

Do not use `sdk_activation_flow_ensure` / `sdk_activation_client_ensure` for these
standards: they build this plugin's own one-page activation journey, not the official flows.

If clients or flows are missing, stop. Give the IDP administrator the official export and
do not create a substitute. The exports' authenticator config aliases must be unique
realm-wide, so an import next to another flow that reuses an alias fails with HTTP 409.

The official BDDK export has one known gap. Its AST **link** step lacks
`read_ast_data_from_session=true`, so a fresh device fails with **513_4041** (the step reads
the all-zero client ID from the header). The kssidp export sets it. The preflight reports
the gap, and the administrator adds the setting.

## Test user (administrator tools)

1. `sdk_activation_user_ensure` creates the user in `ks-users`, or reuses an existing one
   unmodified (check an existing user's group yourself).
2. kssidp only: `sdk_activation_password_set(temporary=True)`. The user's previous password
   stops working. bddk: skip; the tester chooses the password on the enrollment page.
3. Issue the code with `sdk_activation_code_set`. Run these steps one after
   another. A clean-up of old codes that runs at the same time can delete the new code,
   and the IDP then reports "Incorrect Activation Code".
4. Hand the code and temporary password to the tester in chat. Never write them into files,
   logs or commits. After a failure, read the user's credentials before issuing another
   code (`sdk_activation_user_status`): a consumed ACTIVATION_CODE means the enrollment got
   past page 1.

## App: enrollment

Both standards start the same way:

1. Send `KSMGetAstClientDataEvent(tenantId:)` and keep the client data, AST client ID
   (the all-zero ULID `00000000000000000000000000` before activation), code challenge and
   method.
2. Build the authorization URL yourself; KSSIDP adds none of these parameters:
   `client_id` = the enrollment client, `redirect_uri` from `mc_config.json`,
   `response_type=code`, `scope=openid`, `response_mode=form_post`, `nonce`,
   `code_challenge` and `code_challenge_method` from step 1, and `acr_values=1`.
   With `acr_values` present, the token mapper copies the client ID that the activate step
   minted. Without it, the mapper logs in at token time with the pre-activation data and
   fails with 513_4036.
3. Send `X-KOBIL-ASTCLIENTDATA` and `X-KOBIL-ASTCLIENTID` on every request.

**bddk:** hand the URL and headers to `KssIdp`. It fills the one page from your field
mapping and sends `KSMSetAuthorisationCodeEvent` itself.

**kssidp:** `KssIdp` fills only the first page. It drops the temporary-password page
without any callback, whether `isMultiflow` is false or true. This was seen on iOS with
MCSDK 15.16 (KSMasterController bundle 195.1, kssidp 1.11); with `isMultiflow = true` it
did not even post page 1. So the app posts the pages itself:

- Send every request through `KSMCreateHttpCommonRequestEvent`, which applies the trusted
  certificate chain. Use `followRedirect: false`, form-encoded bodies, the AST headers and
  the IDP cookies.
- Fill each page by field name:
  - `username` → user ID
  - `activation-code` → code
  - a lone `password` → the temporary password, until that page is posted
  - `password` + `confirmPassword` → the new password
- Follow redirects until the redirect URI and read `code` from the form_post page or the
  query.
- Send `KSMSetAuthorisationCodeEvent(tenantId:, authenticationMode: .no,
  authorisationCode:, clientId: enrollment client)`. Its result OK means the device is
  activated and the user is signed in.
- If a page comes back unchanged, the IDP refused a value. Stop and show the message; never
  loop.

iOS reference, verified on an iPhone 15 Pro (MCSDK 15.16) against IDP core 5.3.1 on
2026-09-27: kssidp enrollment, sign-out and sign-in; bddk enrollment and sign-in.

- [ios/login-standards/MasterControllerSession.swift](ios/login-standards/MasterControllerSession.swift):
  the email-code session plus `LoginStandard` (set `loginStandard` once, PER APP),
  `activate(userId:activationCode:temporaryPassword:password:)`, the routing of a kssidp
  enrollment to the page runner, and plain error text. Drop-in replacement for
  `email-code/MasterControllerSession.swift`.
- [ios/login-standards/KssidpFormFlow.swift](ios/login-standards/KssidpFormFlow.swift): the page runner.
- [ios/login-standards/IdpErrorText.swift](ios/login-standards/IdpErrorText.swift): plain error messages.
- [ios/HeadlessIdpFlow.swift](ios/HeadlessIdpFlow.swift) (HTTP through the MasterController
  and the HTML reader) and [ios/IdpActivation.swift](ios/IdpActivation.swift) (KssIdp for
  bddk enrollment and for sign-in), shared with the other variants.

The activation screen asks for user ID, activation code, temporary password (kssidp only)
and the new password twice. Wiring sketch, as the session does it:

```swift
// After KSMGetAstClientDataResultEvent:
let transport = HeadlessHttpTransport(controller: masterController, certificate: trustedChain)
let flow = KssidpFormFlow(
    transport: transport,
    redirectUri: redirectUri,
    headers: ["X-KOBIL-ASTCLIENTDATA": clientData, "X-KOBIL-ASTCLIENTID": astClientId],
    credentials: .init(userId: userId, activationCode: code,
                       temporaryPassword: temporaryPassword, newPassword: newPassword))
let authorisationCode = try await flow.run(authorizationUrl: url)
masterController.receive(KSMSetAuthorisationCodeEvent(
    tenantId: tenant, authenticationMode: .no,
    authorisationCode: authorisationCode, clientId: "KSSIDPWebBasedEnrollment")) { _ in }
// Route KSMCreateHttpCommonRequestResultEvent from the global event receiver to
// transport.deliver(_:) too: the result can arrive there instead of the completion.
```

Android has no bundled or device-verified implementation. The same approach applies with
the Android SDK's HTTP common request and set-authorisation-code events. Verify it on a
device before claiming it works.

## App: sign-in (both standards)

Sign-in is one page, and `KssIdp` handles it:

- client = the login client, the same authorization URL parameters, and the extra header
  `X-KOBIL-ASTUSERID: <user ID>`;
- fields `username` and `password`.

In the kssidp login flow the AST login step runs **before** the password form. The header
must therefore be on the first request.

## Errors: show plain text, never the page

kobil-lite error pages contain
`<p id="error-subsystem">513</p><p id="error-code">4042</p><p id="error">…</p>`.
Map them to plain text, as `IdpErrorText` does:

| Code or signal | Meaning | What to tell the user |
|---|---|---|
| 513_4042 | The device isn't linked to the user ID sent. Often a stale saved or AutoFilled email | "This phone is activated for a different account." Do not reactivate |
| 513_4041 | The link step read no client ID | Backend setting; see the backend check above |
| 513_4036 | Token-time AST login failed on first activation | Check that `acr_values=1` is sent |
| "Incorrect Activation Code" | Wrong, expired or deleted code | Ask for a new code; check it wasn't consumed first |
| No answer | A wrong password can re-render the form, and KssIdp doesn't report that | App-side deadline, then "Check the user ID and password" |

Write the full error text to the device log only. On the password field use the
`.password` content type rather than `.newPassword`: iOS AutoFill of a generated strong
password there is the likely cause of wrong-password sign-ins seen in testing.

## Acceptance

Record each result separately:

- fresh enrollment; the ACTIVATION_CODE credential is consumed
- sign-out and sign-in after a restart
- sign-in with a user this device isn't linked to (513_4042, plain message)
- wrong activation code, wrong temporary password and wrong password
- cancellation

A checked backend configuration or a successful build is not acceptance.
