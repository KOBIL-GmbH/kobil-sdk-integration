> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/idpsdk/idpsdk-overview> on 2026-09-28. Converted to Markdown; wording unchanged.

# IdpSdk Overview

The **IdpSdk** (`IdpSdkNativeInterface`) can be considered an "add-on" to the MC-SDK for **KOBIL Shift Lite flows**. It handles the communication between your app and the IDP to obtain an authorization code, which the MC-SDK then exchanges for an IDP token used to activate or authenticate the user account with the Security Server.

---

## Background

In a KOBIL Shift Lite environment, activating or logging in a user requires the app to authenticate against the IDP and retrieve an authorization code. The MC-SDK needs this code to obtain the token set (Access Token, Refresh Token, Offline Token) described in [Token Types](shift-lite-idpsdk__development__tokens__token-handling__token_handling_intro.md).

The IDP identifies the client using AST client data (`X-KOBIL-ASTCLIENTDATA` / `X-KOBIL-ASTCLIENTID`) retrieved from the MC-SDK via `GetAstClientDataEvent`. The authorization code is returned once the IDP has verified the user's credentials.

In the **TWV** (Trusted Web View) variant of Shift Lite, this credential exchange happens in a real browser webview — the user fills in a login form, and the authorization code is extracted from the redirect URL. The IdpSdk replaces the webview with a fully programmatic approach: it fetches and parses the XHTML form defined for each flow client, determines which credential fields are required, and calls back your app to provide them — no webview needed.

---

## How it works

Each IDP flow has a `clientId` (e.g. `KssIdpEnrollment`, `KssIdpLogin`) which maps to an XHTML form on the IDP that defines the required credential fields. The IdpSdk:

1. Fetches and parses the XHTML for the given `clientId`.
2. Calls `IdpSdkInteractionInterface.provideCredentials` with the list of required fields (`interactionData.inputFieldIds`).
3. Your app fills in the values (username, password, activation code, etc.) and returns them.
4. The IdpSdk completes the IDP communication and resolves with an authorization code.

Your app then passes the authorization code to the MC-SDK via `SetAuthorisationCodeEvent` to complete the flow.

---

## provideCredentials Behaviour

### Field IDs depend on the IDP client configuration

The field IDs in `interactionData.inputFieldIds` are determined by the XHTML form configured on the IDP for the given `clientId` — they are not fixed by the IdpSdk. `IdpSdkConstants` covers the most commonly used fields in standard KOBIL flow clients, but custom IDP configurations may request additional or different fields. When using custom fields, ensure your app's `provideCredentials` implementation aligns with your IDP setup:

| Constant | Field |
| --- | --- |
| `IdpSdkConstants.USERNAME` | Username |
| `IdpSdkConstants.PASSWORD` | Password |
| `IdpSdkConstants.ACTIVATION_CODE` | One-time activation code |
| `IdpSdkConstants.NEW_PASSWORD` | New password (change password flow) |
| `IdpSdkConstants.CURRENT_PASSWORD` | Current password (change password flow) |

If a custom `clientId` is used, the field names may differ — check the IDP configuration to confirm which field IDs will be requested.

### provideCredentials can be called multiple times

For multi-step IDP flows, the SDK may call `provideCredentials` more than once during a single `getAuthorizationCode` invocation, each time providing the fields required for that step. Your implementation must be able to handle repeated calls.

### Returning an error cancels the flow

Returning an `IdpSdkProvideCredentialsResult` containing an `IdpSdkError` cancels the flow. The error is propagated back to the `CompletableFuture<IdpSdkResult>` returned by `getAuthorizationCode` — check `idpSdkResult.hasError()` to handle it.

---

## Relationship to the MC-SDK

The IdpSdk does not replace the MC-SDK — it sits alongside it. Your app still owns the full MC event loop:

1. **`GetAstClientDataEvent`** — post to the MC-SDK to obtain the AST client data required by the IdpSdk.
2. **`IdpSdkNativeInterface.getAuthorizationCode`** — call with the AST client data; the IdpSdk handles IDP communication and calls `provideCredentials` when credentials are needed.
3. **`SetAuthorisationCodeEvent`** — post the returned authorization code to the MC-SDK to complete authentication and receive tokens.

---

## Supported standard flows

| Flow | Default `clientId` |
| --- | --- |
| Activation / Enrollment | `KssIdpEnrollment` |
| Login | `KssIdpLogin` |
| Change Password | `KssIdpChangePassword` |
| Forgot Password | `KssIdpForgotPassword` |

> **Note:** The `clientId` values above are the defaults for standard KOBIL installations. The actual values are IDP setup-specific and may differ per tenant — verify the correct client IDs with your IDP configuration.

See the individual flow pages for implementation details, or [Initialization](shift-lite-idpsdk__development__idpsdk__idpsdk-initialization.md) to get started.
