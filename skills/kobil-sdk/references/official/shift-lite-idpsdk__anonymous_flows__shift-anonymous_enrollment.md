> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/anonymous_flows/shift-anonymous_enrollment> on 2026-09-28. Converted to Markdown; wording unchanged.

# Anonymous Enrollment

## What is Anonymous Enrollment?

Anonymous Enrollment is a process that allows a device to receive an access token with the lowest access level. This token is "anonymous" because it does not contain any personal user data (e.g., username or email). Instead, it provides a minimal access token that can be used to request an `IAMAccessToken` for further authorization with third-party applications.

### Why Use Anonymous Enrollment?

* **Privacy-Friendly:** No sensitive personal data is transmitted upfront.
* **Quick Onboarding:** Ideal for scenarios where user identity is not immediately required.

---

## Setup and Requirements

### MC-SDK Integration

Ensure the MC-SDK is properly integrated into your project. For details, refer to our [API overview documentation](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-kssidp/development/api_overview).

### IDP Configuration

Ensure that you have a client configured on your IDP setup that allows anonymous enrollment. By default, the system uses `AnonymousUserEnrollment` with a Device enrollment browser flow. For detailed instructions, see our [IDP Setup Documentation](https://developer.kobil.com/docs/idp-docs/access-management/idp-flows/anonymous-enrollment/).

---

## Anonymous Enrollment Flow

When the MC-SDK detects that activation is required (i.e., `sdkState == ActivationRequired`), trigger the anonymous enrollment process using the `EnrollAnonymousUserEvent`. As a result, you should receive the status `OK` from MCSDK.

### Event Flow Diagram

![](https://www.plantuml.com/plantuml/png/pPD1Rjim44NtEiKiRK2zW04LKLm7DH8bXUqikfoGevWmHIgSeTfqrKFqX3r9GKbEfRH8jzq84EVp_wz7we85WyJ6GkcyUsvyPDYuuArjo0bSMVyboyI8fRS4gCG7ADCpQp68KQP59r2sxUpzsZyOMwq16QhrRFBPnt29waHEPrbHm9K9B723qQaZ_Fp-0suzVA3EA4enfaCX3KMHzPdmxdsAMi4-VKoVMhPjMgtMu-Ac8oSBRDjRR2Y7ZW8Rxt9W2XsTatDG56IPLUkvuuuusj621ILo3gnFUq6X0eSwnhiTFKKJIESGcO8rBCjiMcJ0zeBndYaCda8EdMnr3XZbI4wCwWqhhoa7PGsbwUjU4ldFOiNTzR87k8yFJ4yndT64uXcX3OJw-Nz3QVsZ-IV5kxgsnj5DqWu-IRVL2LjjACmof-8tO1tyYHnilgeZkaU21TP20UZtDVS1-dBB7jJaICSjMsnwZv5Dr8QSebcLrzA_aP0q62hTCusrQXzWf0e93h7mfCRaprd1nyFXqra4YpBAqGVphRzCAxWa31JE8PDzBnrtnArtJDa5EHqR-mi0)

### iOS/Swift

Triggering KSMEnrollAnonymousUserEvent (Swift)

```
public func triggerEnrollAnonymousUser(tenant: String, authenticationMode: KSMAuthenticationMode, clientId: String, completion: @escaping (KsEvent) -> Void) {
let tokenRequest = KSMEnrollAnonymousUserEvent(tenantId: tenant, authenticationMode: authenticationMode, clientId: clientId)
masterControllerAdapter.sendEvent2MasterController(tokenRequest) { event in
guard let returnedEvent = event else { return }
completion(returnedEvent)
}
}
```

### Android/Kotlin

Triggering EnrollAnonymousUserEvent (Kotlin)

```
fun triggerEnrollAnonymousUserEvent(authMode: AuthenticationMode, clientId: String, tenantId: String) {
val enrollAnonymousUserEvent = EnrollAnonymousUserEvent(tenantId, authMode, clientId)
mcEventHandler?.postEvent(enrollAnonymousUserEvent)?.then {
// handle result
}
}
```

> ⚠️ **Important:** If you are using KSSIDP via `com.kobil.kssidp.wrapper.masterController.EventListener`, make sure your `onEventReceived` handles the result event. Don't forget to register your listener with `KssIdp.addEventListener(yourEventListenerImpl)`. If you are using the MC wrapper directly via `com.kobil.wrapper.SynchronousEventHandler`, make sure your `executeEvent` override handles it. See [Communication with the MasterController](shift-lite-idpsdk__development__master-controller-handler.md) for details.

### Request Parameters

| Parameter | Type | Description |
| --- | --- | --- |
| `tenantId` | String | Provided by the backend services. |
| `authenticationMode` | AuthenticationMode | Determines how the token is stored. Options: `.no`, `.password`, `.biometric`. See [authentication modes](shift-lite-idpsdk__development__tokens__token-handling__auth_modes_and_biometry.md). |
| `clientId` | String | The client identifier configured on the IDP for anonymous enrollment. |

---

## Offline Login After Enrollment

After a successful anonymous enrollment, the device is activated. On subsequent app launches, the MC-SDK returns `sdkState == loginRequired`. At this point, use the **OfflineLoginEvent** to re-authenticate. For details and implementation examples, see [Stay Logged In](shift-lite-idpsdk__development__stay-logged-in.md).

---

## After Enrollment and Login

Once enrollment and login are complete, trigger the **ExchangeIamTokenEvent** for every authentication operation to securely obtain an `IAMAccessToken`. For details on how token exchange works, caching behavior, and how to inspect token claims, see [Exchange IAM Token](shift-lite-idpsdk__development__tokens__exchange-iam-token.md).

---

## Event Reference

| Event | Description | Reference |
| --- | --- | --- |
| **StartEvent** | Triggered when the app starts communicating with the Master Controller. Determines if the user needs to activate or log in. | [Documentation](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-kssidp/development/start) · [API Reference](https://developer.kobil.com/api/ast#tag/StartEvent) |
| **EnrollAnonymousUserEvent** | Triggered when `sdkState == ActivationRequired`. Registers the device anonymously and retrieves an initial access token. | [API Reference](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-kssidp/mcsdk-api/ast_event_list#ast-client-management) |
| **OfflineLoginEvent** | Triggered when `sdkState == loginRequired` or after successful enrollment. Authenticates the user using stored offline tokens. | [API Reference](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-kssidp/mcsdk-api/ast_event_list#offline-login) |
| **ExchangeIamTokenEvent** | Triggered for every authentication operation to securely exchange the initial token for an `IAMAccessToken`. | [Documentation](shift-lite-idpsdk__development__tokens__exchange-iam-token.md) · [API Reference](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-kssidp/mcsdk-api/ast_event_list#other-events) |
| **CreateHttpCommonRequest** | Used to securely communicate with backend servers via encrypted HTTP requests and responses. | [Documentation](shift-lite-idpsdk__development__http-common-request.md) · [API Reference](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-kssidp/mcsdk-api/base_event) |
| **RestartEvent** | Triggered to reset the SDK state or reinitialize communication with the Master Controller. | [Documentation](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-kssidp/development/start/#restartevent) · [API Reference](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-kssidp/mcsdk-api/base_event) |
