> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/stay-logged-in> on 2026-09-28. Converted to Markdown; wording unchanged.

# Stay Logged In

The **"Stay Logged In"** feature allows users to remain authenticated even after the mobile app has been running in the background for an extended period or has been closed entirely. Users don't need to perform a standard login (typically involving password entry) during this period. While this increases user convenience, it must be carefully evaluated based on the application's security requirements.

KOBIL's solution ensures that **app integrity and security** are maintained across all implementation variants. Additionally, the app continues to be securely bound to the same mobile device through KOBIL's **device binding** mechanism.

## Optional Biometric Protection

The "Stay Logged In" feature can be used in two ways:

* **Without additional protection:** The user is automatically logged back in without user interaction, for example, after restarting the app or bringing it back to the foreground after a long period of inactivity.
* **With biometric protection:** The device prompts the user to authenticate using a biometric method (e.g., facial recognition) before reactivating the session.

## Time Limitation

The feature **can and should be time-limited** to ensure that after a predefined duration, a standard login is required again. This approach encourages regular use of the login password, reducing the likelihood that users will forget it.

There are two technical implementations for this feature:

1. **Offline Tokens:**
   The session duration can be configured in KOBIL IDP using the `Offline Session Max` parameter. Additionally, the `Offline Session Max Limited` parameter must be enabled.
2. **Authorization-Grant Tokens (Signed JWT):**
   As an alternative, this method uses a signed JWT for re-authentication. The MC generates a key pair, stores the private key securely on the device, and registers the public key with the backend. When re-authenticating, the MC signs a JWT with the private key. In the long term, this approach is expected to replace the use of offline tokens.

Which implementation is used depends on the `maverick.jwtSignKeySecurityPolicy` setting in your [mc\_config.json](shift-lite-idpsdk__prerequisites__mc-config-files__mc_config_json_shift.md). For more details on token types, see [Token Types](shift-lite-idpsdk__development__tokens__token-handling__token_handling_intro.md).

## First-Factor Authenticators

The MC supports several first-factor authenticators that determine how the user re-authenticates when using the "Stay Logged In" feature:

### Offline Token

The client uses the authorization grant type `refresh_token` ([RFC 6749 §6](https://datatracker.ietf.org/doc/html/rfc6749#section-6)) and sends a refresh token of type offline. This is the default when `maverick.jwtSignKeySecurityPolicy` is NOT set in mc\_config.

| AuthenticationMode | Scope | Description |
| --- | --- | --- |
| `.NO` | `no_auth_offline` | Access to the offline token requires no authentication. |
| `.BIOMETRIC` | `bio_auth_offline` | Access to the offline token requires biometry-based authentication. Biometry verification is performed offline. |

### Authorization-Grant / Signed JWT

The client uses the authorization grant type `jwt-bearer` ([RFC 7523](https://datatracker.ietf.org/doc/html/rfc7523)) and sends a signed JWT. This is the mechanism behind **Authorization-Grant Tokens** described above. It is enabled by setting `maverick.jwtSignKeySecurityPolicy` in the [mc\_config.json](shift-lite-idpsdk__prerequisites__mc-config-files__mc_config_json_shift.md). The following scopes are added to the JWT payload, depending on how the signing key is protected on the client:

| AuthenticationMode | Scope | Description |
| --- | --- | --- |
| `.NO` | `no_auth_grant` | Access to the signing key requires no authentication. |
| `.BIOMETRIC` | `bio_auth_grant` | Biometry-protected signing key. Biometry verification is performed offline. Used when `jwtSignKeySecurityPolicy` is `ALLOW_VIRTUAL_SMART_CARD` and no hardware-backed keystore is available on the device. |
| `.BIOMETRIC` | `bio_auth_grant_SE` | Same as `bio_auth_grant`, but the JWT signing key is stored in a Secure Element (hardware-backed keystore). Used when the device has a hardware-backed keystore. |

The `_SE` variant corresponds to hardware-backed key storage as described in the [Key Protection Levels](shift-lite-idpsdk__prerequisites__mc-config-files__mc_config_json_shift.md#key-protection-levels) section.

> ⚠️ **Important:** When `AuthenticationMode.BIOMETRIC` is used, the resulting scope (`bio_auth_offline`, `bio_auth_grant`, or `bio_auth_grant_SE`) directly affects the **OfflineLoginEvent**. The user must authenticate with biometrics before the offline login can proceed.

## OfflineLoginEvent

To utilize the Stay Logged In feature, you need to trigger an OfflineLoginEvent. If a valid offline token (or authorization-grant token) is stored for the activated user and the OfflineLogin succeeds, the MC will return a Status OK, meaning the session was validated successfully.

> ⚠️ **Important:** The OfflineLoginEvent cannot be used with `AuthenticationMode.PASSWORD` or `AuthenticationMode.PIN` (set via `SetAuthorisationCodeEvent`). These authentication modes require user interaction through the IDP login flow and are not compatible with offline re-authentication.

> **Note:** When OfflineLoginResult returns with StatusType **!=** OK, we recommend performing an IDP login using the **same** authentication mode as before.
>
> **Example:** Biometry is enabled → OfflineLogin fails with StatusType **!=** OK → open IDP login page and perform login with AuthenticationMode.BIOMETRIC in your SetAuthorisationCodeEvent.
>
> When login fails repeatedly (for example, due to an unrecognized fingerprint), we suggest asking the user how to proceed and whether they want to change the authentication mode.

## Implementation Examples

### iOS/Swift

For Swift, this can be implemented as follows:

IAMLogin (Swift)

```
func performLoginOffline(loginRequest: LoginOfflineRequest, completion: @escaping (ActionResult) -> Void) {
let userIdentifier = KsUserIdentifier(tenantId: loginRequest.tenant, userId: loginRequest.userId)
let offlineEvent = KSMOfflineLoginEvent(userIdentifier: userIdentifier)
let timer = CallTimer(event: offlineEvent)
MasterControllerAdapter.sharedInstance.sendEvent2MasterController(event: offlineEvent) { newEvent in
let duration = timer.stop()
if let offlineResult = newEvent as? KSMOfflineLoginResultEvent {
let status = self.handleLoginOfflineStatus(status: offlineResult.status)
if status.success {
self.handleGetInformation(completion: { getInformationEvent in
guard let getInformationEvent else { return }
let loginResult = KSMLoginResultEvent(
loginStatus: .KSMOK,
andOtp: "",
with: getInformationEvent.loggedInUser,
withRetryCounter: 0,
withRetryDelay: 0
)
let actionResult = ActionResult(title: "Offline Login",
success: status.success,
error: status.errorText,
duration: duration,
event: loginResult)
EventLogObject(actionResult: actionResult, component: self.localizedTable)
completion(actionResult)
})
} else {
let actionResult = ActionResult(title: "Offline Login",
success: status.success,
error: status.errorText,
duration: duration,
event: nil)
EventLogObject(actionResult: actionResult, component: self.localizedTable)
completion(actionResult)
}
}
}
}
```

### Android/Kotlin

For Kotlin, here is the corresponding implementation:

IAMLogin (Kotlin)

```
fun triggerOfflineLoginEvent(userIdentifier: UserIdentifier) {
val offlineLoginEvent = OfflineLoginEvent(userIdentifier)
synchronousEventHandler?.postEvent(offlineLoginEvent)?.then {
logDebug("received OfflineLoginResultEvent: $it", "triggerOfflineLoginEvent")
// handle result
}
}
```

### Flutter/Dart

For Flutter, the offline login can be implemented using the McWrapperApi:

OfflineLogin (Flutter/Dart)

```
Future<void> performOfflineLogin(String username) async {
try {
// user identifier for the offline login
final userIdentifier = UserIdentifierT()
..userId = username
..tenantId = Environment.current.appConfig.tenantId;
final offlineLoginEvent = OfflineLoginEventT(
userIdentifier: userIdentifier
);
// Get McWrapperApi from service locator
final mcApi = locator<McWrapperApi>();
// Send offline login event
final response = await mcApi.send(offlineLoginEvent);
response.fold(
(error) {
print("❌ Offline login error: $error");
// Fallback to regular IDP login...
},
(result) {
if (result is OfflineLoginResultEventT) {
if (result.status == StatusType.ok) {
print("✅ Offline login successful");
// User is logged in, proceed to main app...
} else {
print("⚠️ Offline login failed, status: ${result.status}");
// Perform regular IDP login with same auth mode as before...
}
}
},
);
} catch (e) {
print("❌ Offline login exception: $e");
// Handle exception and fallback to regular IDP login...
}
}
// Usage example
void handleAppResume() {
performOfflineLogin("user@example.com");
}
```
