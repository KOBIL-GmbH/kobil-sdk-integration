> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/tokens/tokens-overview> on 2026-09-28. Converted to Markdown; wording unchanged.

# Overview

There are two main types of tokens in KOBIL Secure Services. `MC-Token` is used to perform secured operations between MC SDK and KOBIL IDP services, while the `Token for external services` has limited privileges and provides secure operations between external services and KOBIL IDP services.

## Understanding MC Tokens for KOBIL Services

### Purpose and Components

* **MC Tokens** are designed to secure operations between the MC SDK and KOBIL IDP services, playing a vital role in the security of banking backend services.
* These tokens include three independent tokens: `access_token`, `refresh_token`, and `offline_token`, each with its own validity period to enhance security.

### Security Measures and Usage

* MC Tokens are securely hidden and exclusively shared with KOBIL Secure Services, ensuring that backend operations are securely completed without exposing sensitive token information.
* The MC SDK is engineered to never reveal the `access_token` and `refresh_token`, preventing applications that use the MC SDK from accessing these tokens. This is a crucial design choice for maintaining the security integrity of the application and its backend communications.

## Token for External Services (Exchange IAM Token)")

### Functionality and Retrieval

* The **Token for External Services** enables applications to perform secure operations with external services by exchanging an IAM token.
* Applications can obtain this token by triggering an `ExchangeIAMTokenEvent` with an `audience` parameter. The MC uses its internal access token to exchange for a new, less privileged token scoped to the given audience. This exchanged token is then used to identify users and validate their authorization status.

### Necessity and Strategic Use

* The MC internal access token (sometimes called the "god token") is strictly for MC internal usage and is never exposed to the application. This is a security requirement to protect the security server's critical functionality.
* The `ExchangeIamTokenEvent` provides a way to obtain a token suitable for external use. Using different `audiences` for various use cases adds an extra layer of security, tailoring access and permissions to specific needs.
* To inspect the claims of the internal access token without exposing it, use the `GetIamAccessTokenClaimsEvent`. See [Exchange IAM Token](shift-lite-idpsdk__development__tokens__exchange-iam-token.md) for details.

## Implementing Tokens in Your Development Work

### For MC Tokens

* Ensure your application integrates properly with the MC SDK to communicate securely with KOBIL IDP services.
* Understand that direct access to MC Tokens is not possible through your application. Focus instead on implementing secure communication and operation protocols facilitated by the MC SDK.

### For Tokens for External Services

* Implement the `ExchangeIAMTokenEvent` in your application where you need to perform secure operations with external services.
* Use the `audience` parameter effectively to specify and manage access for different functionalities, enhancing security through granularity in access control.

> **Note**: By understanding and applying these principles, you ensure your applications maintain high security standards in communications and operations with KOBIL Secure Services, aligning with the best practices in mobile application development.

---

## Use Case: Securely Fetching User Information with Token for External Services

Imagine you're developing a banking app that allows users to check their account balance, recent transactions, and update personal information. To ensure high security, the app uses KOBIL Secure Services for authentication and secure operations. After a successful login, your app receives an MC Token, which is used for secure communication within the app's backend. However, to perform operations that involve external services, such as fetching user profile information from a third-party API, you need to use the Exchange IAM Token.

## Step-by-Step Scenario

### User Logs In:

* **Alice opens her banking app** and logs in using her credentials.
* The app uses the **MC SDK** to authenticate Alice's login details with the **KOBIL IDP services**.
* Upon successful authentication, the app receives an **MC Token**. This token is securely stored and managed by the MC SDK and is not directly accessible by the app.

### Preparing to Fetch User Information:

* Alice navigates to the **profile section** of the app, intending to update her phone number.
* The app needs to fetch Alice's current information from a **third-party service** before she can make updates. However, this operation requires a secure token that can be validated by the external service.

### Exchanging the MC Token for an Exchange IAM Token:

* The app initiates an **ExchangeIAMTokenEvent** with a specific **audience parameter** that matches the external service's requirements.
* The **MC SDK processes** this event and securely exchanges the MC Token for an **Exchange IAM Token** suited for the external service.

### Fetching User Information:

* With the Exchange IAM Token, the app crafts a secure **HTTP request** to the third-party service's API.
* The token is included in the request's **authorization header**, ensuring the communication is authenticated and secure.
* The **third-party service validates** the Exchange IAM Token and, upon successful validation, returns Alice's current profile information.

### Updating User Information:

* Alice updates her phone number and **submits the changes**.
* The app sends another secure **HTTP request** to the third-party service, including the updated information and the Exchange IAM Token for validation.
* The service **updates Alice's profile** with the new phone number.

## Conclusion

In this scenario, the Exchange IAM Token acts as a secure bridge, allowing the banking app to safely interact with external services. By exchanging the MC Token for an Exchange IAM Token, the app ensures that operations like fetching and updating user information are performed securely, adhering to the high security standards required by both the app and external services. This process not only protects sensitive user data but also maintains a seamless and secure user experience.
