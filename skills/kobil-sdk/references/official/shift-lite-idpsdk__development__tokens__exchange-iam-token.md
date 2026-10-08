> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/tokens/exchange-iam-token> on 2026-09-28. Converted to Markdown; wording unchanged.

# Token for External Services (Exchange IAM Token)

The `ExchangeIamTokenEvent` facilitates the exchange of an IAM token for authentication purposes. It obtains a token required for subsequent HTTP requests to your backend services, including token refresh operations.

> ⚠️ **Important:**
>
> * The result event `ExchangeIamTokenResultEvent` contains a token that can be used for authorization against your backend services.
> * The audience you use in the `ExchangeIamTokenEvent` should not be the client ID that you use in the activation and login flows.
> * The token returned in `ExchangeIamTokenResultEvent` is **not** the MC internal access token (sometimes called the "god token"). It is a less privileged token that is obtained using the internal access token and is specific to the given audience. For example, if the audience is `"MiniApp"`, the exchanged token is scoped to that audience only.

## How It Works

The Master Controller (MC) maintains an internal access token (obtained from the IDP) that is strictly for MC internal usage and is never exposed to the application. When you trigger `ExchangeIamTokenEvent` with an `audience`, the MC uses its internal access token to exchange for a new token from the IDP. This exchanged token has fewer roles and contains minimal information, making it safe to use in your application and to pass to third-party services.

### Caching Behavior

The exchanged token is cached locally. On the first call (or when the cached token has expired), the MC contacts the server to obtain a fresh token. Subsequent calls with the same audience reuse the cached token if it is still valid. You can override this behavior using the `forceUpdate` parameter.

## Exchange IAM Token Flow Diagram

![](https://www.plantuml.com/plantuml/png/ROxB2i8m44Nt_OfPsaL_e0iXQg4YWjJYVcW64rediPce-FNI1wZeTkuvzuxoFblkryVDBeVYqHZaCstnKhkMkBWHomAZjiGDfSc8PKlb_IzRKOYTJ8OCXpHHG_KAcvPOvr3MzG4gkaOA0dSh1aOCB8EAObnldoZMCHX2JNqoYnyD9-oiHg59_0EKoBgZhwKtDNuzHy4x3lG2)

## Parameters

* **audience:** Specifies the target audience for the IAM token exchange. Set this to the intended backend service or application.
* **forceUpdate:** (Optional, default: `false`) When set to `true`, forces the MC to obtain a fresh token from the server instead of reusing a cached one. This is useful when you know the current token has been invalidated (e.g., after a password change), saving a round trip from sending a request with an invalid token, receiving an error, and then requesting a new token.

## iOS/Swift

Exchange IAM Token (Swift)

```
static func getTokenWithCompletionHandler(traceParent: String? = nil, audience: String, completion: @escaping (String?) -> Void) {
let tokenEvent = KSMExchangeIamTokenEvent(audience: audience)
if let traceParent {
let state = tokenEvent.traceContext.traceState
tokenEvent.traceContext = .init(traceParent: traceParent, traceState: state)
}
MasterControllerAdapter.sharedInstance.sendEvent2MasterController(event: tokenEvent) { resultEvent in
guard let resultEvent = resultEvent as? KSMExchangeIamTokenResultEvent else {
completion(nil)
return
}
completion(resultEvent.token)
}
}
```

### Handling the Result

Handling ExchangeIamTokenResultEvent (Swift)

```
guard let resultEvent = resultEvent as? KSMExchangeIamTokenResultEvent else {
completion(nil)
return
}
completion(resultEvent.token)
```

The `KSMExchangeIamTokenResultEvent` contains a `token` property with the exchanged IAM token.

---

## GetIamAccessTokenClaims

The `GetIamAccessTokenClaimsEvent` allows you to retrieve the claims of the MC internal access token without exposing the token itself. When called, the MC obtains a fresh (up-to-date) access token from the IDP using the cached refresh token and returns the token's claims to the application.

> ⚠️ **Important:** Each `GetIamAccessTokenClaimsEvent` call triggers a server request to obtain fresh access token claims. Avoid calling this event excessively, as it incurs a network round trip on every invocation.

This is useful when you need to inspect the user's current roles, permissions, or other claims without performing a full token exchange.
