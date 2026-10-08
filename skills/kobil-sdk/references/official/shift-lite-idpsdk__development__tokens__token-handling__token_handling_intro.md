> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/tokens/token-handling/token_handling_intro> on 2026-09-28. Converted to Markdown; wording unchanged.

# Token Types

In a **KOBIL Shift Lite** or **KOBIL Digitanium+** environment, there are 4 types of tokens:

| **Token** | **Usage** | **MC Storage** | **IDP Parameter** |
| --- | --- | --- | --- |
| **Access Token** | Used for authentication against KOBIL services. Has the shortest lifetime (e.g., 2 minutes). After expiration, MC obtains a new token using the Refresh Token. | In Memory | Access Token Lifespan, ... |
| **Refresh Token** | Used at runtime to update the Access Token when expired. Has a longer lifetime than the Access Token (e.g., 30 minutes). After expiration, MC obtains a new token using the Offline Token. | In Memory | SSO Session Max, ... |
| **Offline Token** | Used for obtaining a new set of tokens when the app has not been used for an extended time and other tokens have expired. The MC requests and securely stores these tokens. During verification, the IDP checks that the identical Offline Token is presented and is still valid. Depending on the Authentication Mode, the user can either continue using the app or must perform biometric authentication. Has the longest lifetime (e.g., 90 days). After expiration, the user must perform an online login to the IDP with their credentials. Offline Tokens are a special kind of Refresh Token with scope `offline_access`. | Persistent | Offline Session Idle, ... |
| **Authorization-Grant Token (Signed JWT)** | Used for obtaining a new set of tokens as an alternative to Offline Tokens. The MC generates a key pair where the private key is protected using OS-level security (e.g., biometrics) and the public key is registered in the AST backend. When requesting tokens, the MC creates and signs a JWT with the private key (`jwt-bearer` grant type). The IDP verifies the signature against the stored public key. This method is expected to replace Offline Tokens in the future. Enabled via `maverick.jwtSignKeySecurityPolicy` in the `mc_config.json`. | Persistent | Offline Session Idle, ... |

> Both the Offline Token and the Authorization-Grant Token transmit AST-Client-Data, enabling verification of app integrity and device binding.

Which token type is used for re-authentication depends on the `maverick.jwtSignKeySecurityPolicy` setting in your `mc_config.json`. For details on how these tokens affect the login flow and the available first-factor authenticators, see the **Stay Logged In** documentation.

**KOBIL Digitanium+** uses either Refresh Token, Offline Token, or Authorization-Grant Token.

## Token Lifetime Hierarchy

It is important that the configured token lifetimes follow this hierarchy:  
**Access Token** < **Refresh Token** < **Offline Token**

## Token Rejection and Fallback

The Security Server can reject token updates at any time. For example, when the change PIN flow disables all user tokens for all devices on the server side. In such cases, you must perform an online login.

## Deleting Tokens

You can delete tokens stored by the SDK using the ClearIamTokenCacheEvent as described in the [**Logout section for KOBIL Shift Lite and KOBIL Digitanium+**](shift-lite-idpsdk__development__logout_digitanium+_shift.md).
