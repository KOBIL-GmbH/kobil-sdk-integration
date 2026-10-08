> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/mc-config-files/mc_config_json_shift> on 2026-09-28. Converted to Markdown; wording unchanged.

# MC Configuration file mc\_config.json

The `mc_config.json` file is required for all KOBIL solutions, but its content varies depending on the solution. It is an unsigned file that you can create manually.

To create this file, follow these steps:

1. Create an empty file named **mc\_config.json**.
2. Copy and paste the example below into the file, and remove what you don't need (further details below):

Example mc\_config.json for KOBIL Shift Lite solution installations

```
{
"useScp": false,
"useTokenBasedLogin": true,
"useSmartScreen": false,
"astServerBackend": "maverick",
"iam": {
"clientId": "myIdpClientId",
"serverUrl": "https://idp.foobar.com",
"redirectUri": "https://kobil/OpenIdRedirectUri",
"trustedSslServerCerts": ["assets/root_certs.pem", "asset/subCA_certs.pem"]
},
"maverick": {
"mTLS": true,
"mKex": true,
"useSEKeyForSigningTransactions": true,
"minimumKeyProtection": "ENFORCE_STRONG_HARDWARE",
"jwtSignKeySecurityPolicy": "ALLOW_VIRTUAL_SMART_CARD"
}
}
```

> **Note:** The `trustedSslServerCerts` files must be in PEM format and can contain one or more certificates. At least one Root CA certificate must be present. In case of CA transition, multiple Root CAs may be present. You can also pin SubCA or end-entity server certificates, but be aware they change more often than Root CAs, requiring app updates. For simplicity, different trust store entries in different sections of the file can point to the same file. Refer to [Trust Store Configuration](shift-lite-idpsdk__prerequisites__mc-config-files__trust_store.md) for guidance.

## Top-Level Configuration

| JSON Key | Description | Required value for Shift Lite |
| --- | --- | --- |
| **astServerBackend** | Sets the AST server backend. Values: `maverick`, `ssms`. If set to `maverick`, `useTokenBasedLogin` automatically becomes `true`. | `maverick` |
| **useTokenBasedLogin** | Enables IAM token-based login | `true` |
| **useScp** | Enables SCP functionality (chat capabilities) | `false` |
| **useSmartScreen** | Enables Smart Screen functionality | `false` |

## IAM Configuration

| JSON Key | Description |
| --- | --- |
| iam.**serverUrl** | Host URL of the IDP Server as seen from the internet. The SDK will use it for HTTP requests towards the IDP by appending the respective IDP endpoint path to it. |
| iam.**redirectUri** | The redirect URI configured as trusted "Valid redirect URI" in your IDP login client. The redirect URI will be used against the IDP token endpoint during activation/login to exchange authorization code with tokens. It is internally URL-encoded by the SDK before use. |
| iam.**trustedSslServerCerts** | List of filenames inside the app with trusted TLS server certificates used for certificate pinning in requests towards the IDP server. |

## Maverick Configuration

| JSON Key | Description | Default |
| --- | --- | --- |
| maverick.**mTLS** | Enable mTLS (mutual TLS) | `false` |
| maverick.**mKex** | Enable mKEX (mutual key exchange) | `false` |
| maverick.**useSEKeyForSigningTransactions** | Use Secure Element keys for signing transactions | `false` |
| maverick.**jwtSignKeySecurityPolicy** | Minimum key protection level for the JWT signing key. Valid values: `ALLOW_VIRTUAL_SMART_CARD`, `ENFORCE_HARDWARE`, `ENFORCE_STRONG_HARDWARE`. On desktop, only `ALLOW_VIRTUAL_SMART_CARD` is supported. ⚠️ If not set, the offline token authenticator is used for the first factor of authentication. See [First-Factor Authenticators](shift-lite-idpsdk__development__stay-logged-in.md#first-factor-authenticators). | Not set |
| maverick.**minimumKeyProtection** | Minimum key protection level for mKEX and transaction signing keys. Uses the same values as `jwtSignKeySecurityPolicy`. ℹ️ Only relevant when `maverick.mKex` and/or `maverick.useSEKeyForSigningTransactions` is `true`. Primarily used in **BDDK** setups. See the **Key Protection Levels** documentation in the **BDDK** section. ⚠️ Has no effect if neither `mKex` nor `useSEKeyForSigningTransactions` is `true`. | Not set |

### Security Policy Modes and First-Factor Authenticators

The `jwtSignKeySecurityPolicy` setting determines how the MC authenticates during the "Stay Logged In" flow. There are several first-factor authenticators the MC can use. For details on how these affect the OfflineLoginEvent and token handling, see [Stay Logged In](shift-lite-idpsdk__development__stay-logged-in.md) and [Token Types](shift-lite-idpsdk__development__tokens__token-handling__token_handling_intro.md).

If `jwtSignKeySecurityPolicy` is **not set**, the system uses the **Offline Token** mode:

* The client uses the authorization grant type `refresh_token` ([RFC 6749 §6](https://datatracker.ietf.org/doc/html/rfc6749#section-6)) and sends a refresh token of type offline.

If `jwtSignKeySecurityPolicy` **is set**, the system uses the **JWT Authentication Grant** mode:

* The client uses the authorization grant type `jwt-bearer` ([RFC 7523](https://datatracker.ietf.org/doc/html/rfc7523)) and sends a signed JWT.

#### Key Protection Levels

| Value | Description |
| --- | --- |
| `ALLOW_VIRTUAL_SMART_CARD` | MC will also work on devices without a hardware-backed keystore, while still using the strongest available one if present. The SDK prefers key storage in the following order: **Secure Element** (SE / Secure Enclave) → **Hardware Keystore** (TEE on Android; iOS only has Secure Enclave) → **Software solution**. |
| `ENFORCE_HARDWARE` | MC will only run if the device can create keys in any hardware-backed store and successfully attest them. If the device does not have a hardware-backed keystore, the `StartEvent` will fail. |
| `ENFORCE_STRONG_HARDWARE` | MC will only run if the device can create keys in a Secure Element (SE) and successfully attest them. If the device does not have a Secure Element, the `StartEvent` will fail. |

> For more details on key protection levels and restrictions in the context of **BDDK** setups, please see the **Key Protection Levels** documentation in the **BDDK Use Cases** section.
