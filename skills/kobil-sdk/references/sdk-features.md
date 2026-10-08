# MCSDK features beyond activation, login, TMS and signing (iOS 15.16)

This guide covers the rest of the MCSDK iOS 15.16 delivery (KSMasterController, KSTrustedWebView
9.7, hnb CallMonitor). Every Swift signature here comes from the SDK's own interface
(`xcrun swift-synthesize-interface` on the delivered XCFrameworks). The symbols were checked in
the binaries with `nm`. Do not guess a name that isn't listed here; check the interface instead
(see [Finding a Swift name](#finding-a-swift-name)).

**How far each feature was checked:**

| Level | Meaning |
|---|---|
| **device** | The SDK answered on an iPhone, running 15.16 against the Maverick/AST backend |
| **compiled** | The reference code compiles and links for iOS against 15.16, but was never run |
| **interface** | Only the event sequence from the header; no reference code |
| **broken** | Declared in the header, but missing from the binary. Using it fails at link time |
| **needs backend** | Needs a server feature this backend doesn't have; unverifiable here |

Reference code (copy it, don't rewrite it):

| File | What it gives you |
|---|---|
| `ios/sdk-requests/SdkFeatureRequests.swift` | One-request calls: state, users, device, licences, locales, auth mode, push, IAM, decrypt, data store, update info |
| `ios/sdk-requests/SdkFlows.swift` | Change PIN, add / reactivate / delete users, offline and token login, anonymous users, workspace, nonce, properties, REST endpoints, tracing, SSMS OTP, app-initiated transactions, update, HTTP through the SDK, upload |
| `ios/sdk-requests/SdkStatusMonitor.swift` | `@Observable` connection, SSE, busy, chat, migration and IDP-login-required state. Call `SdkStatusMonitor.shared.start()` before the session starts |
| `ios/TransactionCenter.swift` + `ios/ui/TransactionSecretSheet.swift` | Transactions that need the SDK PIN or a token: `secretRequest`, `provideSecret`, `cancelSecret`, with retries and the deadline |
| `ios/ui/DeviceSecurityView.swift` | A "Device and security" screen: status, device name, users (swipe to remove), sign-in mode, change PIN, update check, licences |
| `ios/platform/SecureWebView.swift` | SwiftUI host for the trusted web view |
| `ios/platform/CallGuard.swift` | Scam-call protection modifier |
| `ios/platform/PushRegistration.swift` | APNs token and SetPushToken after login |
| `ios/tests/SdkFeatureTests.swift` | Swift Testing tests for the PIN/token answer and the helpers |

Every file extends or uses the **email-code** `MasterControllerSession`: it relies on
`awaitResult(of:timeout:requiresLogin:extract:)`, `awaitStatus`, `post(_:requiresLogin:)`,
`loggedInUser()` and `certificateChain`, which are internal there. With the activation-code
variant, port those members first. The whole set (email-code variant plus these files) was
built and linked for device and simulator on its own, with no app code.

### What the developer asks for → where to look

| Request | Use |
|---|---|
| "Settings screen", "device and security", "show my devices / users" | `DeviceSecurityView` |
| "Wallet", "saved cards", "pay with a card" | app-side, not an SDK call: `ios/wallet/` and [wallet.md](wallet.md) |
| "Face ID login", "use password instead" | `BiometricSignIn` (ios/platform) on a Shift realm; `enableAuthenticationMode(_:)` only when the IDP has the biometric scopes |
| "Change PIN" | `changePin(current:new:)` + `ChangePinSheet` (PIN mode only) |
| "Second account on the phone", "switch user" | `addUser`, `activatedUsers()`, then the normal login flow |
| "Log out and remove this device", "deactivate" | `deleteUser(userId:)` for the last user |
| "Push notifications" | `ios/platform/PushRegistration.swift`: `PushAppDelegate` registers with APNs, `.sendsPushToken(to: session)` calls `setPushToken(_:)` after every login; add the Push Notifications capability. The APNs key in the push service is backend setup |
| "Call my own API with the user's token" | `iamAccessTokenIdentifier` + `httpRequest(accessTokenIdentifier:)`, or `exchangeIamToken` + URLSession |
| "Upload a file" | `upload(_:fileName:data:mimeType:)` (JSON/base64; multipart is broken, see below) |
| "Show offline banner", "spinner while the SDK works" | `SdkStatusMonitor.isOnline`, `.isBusy` |
| "Payment asks for PIN" | `TransactionSecretSheet` on `TransactionCenter.secretRequest` |
| "Force app update" | `updateInformation()`, `performUpdate()`, `openUpdateInfo()` |
| "Open our portal securely in the app" | `SecureWebView` |
| "Warn when on a call while approving" | `.callGuard()` |
| "Mute chats" | Not possible on 15.16 (missing symbols) |
| "Chat send/receive" | Not in the iOS MCSDK (see [TMS](tms.md#chat-is-not-in-the-ios-mcsdk)) |
| Android or Flutter for any of the above | No reference code yet; map the same event names to the Kotlin/Dart API and verify on a device |

## One-request, one-result calls (`SdkFeatureRequests.swift`)

| Feature | Call in the reference | SDK events | Needs login | Level |
|---|---|---|---|---|
| SDK state (new in 15.16) | `sdkState()` | `KSMGetSdkStateEvent(ssmsUserCredentialPath: nil)` → `KSMGetSdkStateResultEvent.sdkState` (`KSMSdkState`: `.activationRequired/.loginRequired/.uninitialised/.unidentified/.loggedIn`) | no | **device** (2026-09-27, before login: state 1 = `.loginRequired`) |
| Users on this device | `activatedUsers()` | `KSMGetUserListEvent(ssmsUserCredentialPath:)` → `(status, userList: [KsUserListEntry])`; `entry.userDetails.userIdentifier/displayUsername/displayEmail`, `isSsmsUser` | no | **device** (1 user) |
| Logged-in user | `loggedInUserIdentifier()` | `KSMGetLoggedInUserEvent()` → `.userIdentifier` | yes | **device** (2026-09-27) |
| Device id and name | `deviceInformation(for:)`, `setDeviceName(_:)` | `KSMGetDeviceInformationEvent(userIdentifier:)` → `(deviceId, deviceName)`; `KSMSetDeviceNameEvent(deviceName:)` → `KSMSetDeviceNameResultEvent.status` | yes | **needs backend (SSMS)**. Device, 2026-09-27: with `astServerBackend` "maverick" the SDK answers `KSMInvalidStateEvent` before and after login, without a network call: the flow reads the SSMS user store, which has no entry for a Maverick user. The reference turns it into a clear `SdkRequestError.failed`. It still fails right after a successful `SetDeviceName`. **`SetDeviceName`: device** (2026-09-27): works on Maverick; the SDK stores the name and sends `PUT /v1/tenants/<tenant>/clients/<astClientId>/details` to AST (HTTP 200). Nothing on Maverick reads the name back, so keep your own copy if you display it |
| Third-party licences | `thirdPartyLicenses()` | `KSMRequestLicensesEvent()` → `.licenses: [AnyHashable: Any]` (converted to `[String: String]` inside the handler; the dictionary isn't Sendable) | no | **device** (12 licences) |
| App update check | `updateInformation()` | `KSMGetUpdateInformationEvent()` → `KSMUpdateInformationEvent(updateStatus, updateUrl, infoUrl, updateType, digest, expiresInSeconds)`. `.KSMUPDATE_AVAILABLE` or `.KSMUPDATE_NECESSARY` means a newer app version is wanted. Then `KSMUpdateEvent` → `KSMUpdateResultEvent(KSMUpdateStatus)`, and `KSMOpenInfoUrlEvent` | yes | **needs backend (SSMS)**. Device, 2026-09-27: the SDK hands the request to its SSMS module (`ast_pathfinder/ssms`), which has no handler with `astServerBackend` "maverick" (log: AstPathfinder "Executor not exists for event: GetUpdateInformationEvent"), so it answers `KSMInvalidStateEvent` before and after login. No AST app-version policy changes this; the request never reaches the network. The reference turns it into a clear `SdkRequestError.failed` |
| Locales | `setLocales(_:)` | `KSMSetLocalesEvent(locales:)` → `KSMStatusResultEvent`. The header says "supported only for Maverick" | no | compiled |
| Face ID sign-in (app-side) | `BiometricSignIn` in `ios/platform/BiometricSignIn.swift` | No SDK event. After a successful password login the app keeps the password in the Keychain (`.biometryCurrentSet`, `WhenPasscodeSetThisDeviceOnly`); "Sign in with Face ID" reads it with Face ID and calls the same `login(userId:password:)`. Keep the account name outside the item (the reference uses UserDefaults): reading even the attributes of a `.biometryCurrentSet` item without a prompt fails with -25308 (`errSecInteractionNotAllowed`), device-checked 2026-09-27. Tokens stay with mc_config `iam.clientId`, so TMS explicit auth and `exchangeIamToken` keep working. Re-enrolling Face ID deletes the item (the reference reports it and falls back to the password). Needs `NSFaceIDUsageDescription`. No backend change | no | **device** (2026-09-27, a Shift development realm); the account-name-in-UserDefaults fix for -25308 is compiled, its device re-check is pending |
| Face ID / password mode (SDK-native) | `enableAuthenticationMode(_:)` | `KSMEnableAuthenticationModeEvent(authenticationMode: .no/.biometric/.password)` → `KSMStatusResultEvent`, then `KSMLoginWithTokenEvent(withoutParameters: user, authenticationMode: .biometric)`. `.biometric` needs `NSFaceIDUsageDescription` and **IDP configuration a Shift realm lacks**: the SDK asks for an offline token with scope `fpt_auth_offline offline_access`, creates a Secure Enclave key and registers it (`PostAuthGrantSigningKey`, a backend write), then logs in with the `jwt-bearer` grant and scope `bio_auth_grant_SE`. The 15.x changelog also names scopes `face_auth_grant_SE` / `fpt_auth_grant_SE` with second factor "none". Checked 2026-09-27 on a Shift development realm: none of these scopes exist, so use the app-side row above. Do not log in through a different client (for example `IDPBiometricAppLockHeadlessV2`): the SDK exchanges tokens with `iam.clientId` and fails with "Client is not the holder of the token" | yes | compiled |
| Push token | `setPushToken(_:)` | `KSMSetPushTokenEvent(pushToken:)` → `KSMSetPushTokenResultEvent.status`. The token **must carry the provider prefix**: `"APN:"` + hex for native iOS, `"FCM:"` for native Android, `"FCMF:"` for Flutter on either platform. Without one the MasterController prepends `"GCM:"` and no push arrives. Send it after every successful login. | yes | compiled; **needs backend** (APNs key for this app in the push service) |
| Verify push content | `verifyPushContent(_:)` | `KSMVerifyPushContentEvent(userIdentifier:content:)` → `(status, content)`. The header says it is for "ssms ast_pathfinder crypto" payloads | yes | compiled; **needs backend** |
| IAM token for your backend | `exchangeIamToken(audience:forceUpdate:)` | `KSMExchangeIamTokenEvent(audience:forceUpdate:)` → `.token: String`. Never log it | yes | **device** (2026-09-27, 1527-char token). Needs `iam.clientId` = the login client (tms.md) and an unlocked phone (keychain -25308 → status 39) |
| IAM access-token identifier | `iamAccessTokenIdentifier(audience:scope:clientId:)` | `KSMGetIamAccessTokenEvent(audience:withScope:withClientId:)` returns an **identifier**, not the token. Pass it as `accessTokenIdentifier:` to `KSMCreateHttpCommonRequestEvent` and the SDK adds the token | yes | compiled |
| IAM authorization-code identifier | `iamAuthorizationCodeIdentifier(...)` | `KSMGetIamAuthorizationCodeEvent`, same pattern | yes | compiled |
| Clear the IAM token cache | `clearIamTokenCache(_:)` | `KSMClearIamTokenCacheEvent(clear: .clearAll/.clearAccessAndRefresh/.clearOffline, with: user)` → `KSMClearIamTokenCacheResultEvent` (no fields) | yes | compiled |
| Delete tokens by audience | `deleteIamTokens(audiences:)` | `KSMDeleteIamTokenByAudienceEvent` → `KSMStatusResultEvent` | yes | compiled |
| Decrypt data | `decrypt(_:)` | `KSMDecryptDataEvent(encryptedData:)` → `(status, decryptedData, openSslErrorCode)`. Never log the plaintext | yes | compiled; needs server-side encrypted data |
| Global data store | `globalValue(forKey:)`, `setGlobalValue(_:forKey:)` | `KSMGetDataEntryEvent(key:)` / `KSMSetDataEntryEvent(key:withValue:)` (`KSMDataModelRequestStatus`). **Global and unencrypted**, shared by all users. For per-user encrypted data, use `KSMSetUserDataEntryEvent` (see [signing](signing.md)) | no | **device** (read of an absent key: `.notExists`) |

`KSMStatusResultEvent(status:)` answers six requests: `EnableAuthenticationMode`, `SetLocales`,
`DeleteIamTokenByAudience`, `ProvideNonce`, `EnrollAnonymousUser` and `SwitchWorkspace`. The
event doesn't say which request it answers, so send only one of them at a time. The reference
code's `awaitStatus` relies on this.

### Wiring

```swift
// Before login; the phase only needs Start to have succeeded.
let state = try await session.sdkState()
let users = try await session.activatedUsers()

// After login: a token for your own backend.
let token = try await session.exchangeIamToken(audience: "userPortalPublic")  // PER APP audience

// Push (ios/platform/PushRegistration.swift): in the App
@UIApplicationDelegateAdaptor(PushAppDelegate.self) private var pushDelegate
// and on the root view, so SetPushToken follows every successful login:
ContentView().sendsPushToken(to: session)
```

The official Push Localization page recommends app-side localization (the push carries
`title-loc-key` / `loc-key` found in the app's strings). Call `setLocales(_:)` after
SetPushToken only if the server localizes instead.

## Flows and administrative calls (`SdkFlows.swift`)

Multi-step flows are a dialogue: the app sends a Start event, the MasterController answers
with a request event, and the app replies with a Provide event. `SdkResultRouter` gives every
awaited event to its caller first, so a flow is two `awaitResult` calls in a row. Where the
SDK also offers a one-event "direct form", the reference uses it. **None of these ran on a
device**: they need PIN mode, a second test user, an SSMS backend or a server endpoint that
this backend doesn't have. Level: compiled (built and linked, device and simulator).

| Feature | Call | Sequence |
|---|---|---|
| Change PIN | `changePin(current:new:)` | `KSMStartChangePinEvent()` → MC: `KSMStartSetNewPinEvent` → `KSMProvideSetNewPinEvent(currentPin:andPin:)` → `KSMChangePinResultEvent(status, retryCounter)`. PIN mode only (`jwtSignKeySecurityPolicy`, see [platforms](platforms.md)); the IDP-login variant has no SDK PIN |
| Add a user | `addUser(userId:activationCode:pin:autoLogin:)`, `addUser(userId:token:autoLogin:)` | `KSMAddUserEvent(userIdentifier:activationCode:pin:enableAutoLogin:)` / `KSMAddUserWithTokenEvent(userIdentifier:token:enableAutoLogin:)` → `KSMAddUserResultEvent(status)`. Stepwise form: `KSMStartAddUserEvent` → `KSMStartAddUserUserIdAndCodeOnlyEvent` → `KSMProvideActivationCodeAndUserIdForAddUserEvent` → `KSMStartAddUserSetPinEvent` → `KSMProvideSetPinForAddUserEvent(pin:andEnableAutLogin:)` |
| Switch user | `activatedUsers()` | List the users, then log in the chosen one with the normal login flow |
| Reactivation | `reactivate(userId:activationCode:pin:autoLogin:)` | `KSMReactivationEvent` → `KSMReactivationResultEvent(reactivationStatus)`. Stepwise: `KSMStartReactivationEvent` → `…UserIdAndCodeOnly` → `KSMProvideActivationCodeAndUserIdForReactivationEvent` → `…SetPin` → `KSMProvideSetPinForReactivationEvent` |
| Delete a user / deactivate the device | `deleteUser(userId:)` → `(sdkState, remainingUserIds)` | `KSMDeleteUserEvent(userIdentifier:)` → `KSMDeleteUserResultEvent(status, sdkState, userList)`. Stepwise: `KSMStartDeleteUserEvent` → `KSMStartSetUserIdToDeleteEvent` → `KSMProvideSetUserIdToDeleteEvent`. Deleting the last user returns the SDK to `.activationRequired`; there is no separate "deactivate device" event |
| Transaction needing a PIN or token | `TransactionCenter.provideSecret(_:)` / `cancelSecret()` | MC: `KSMTransactionPinRequiredRequestEvent(timerValue)` → `KSMProvidePinEvent(confirmationType: .ok/.cancel, andPin:)` → `KSMProvidePinResultEvent(status, retryCounter)`. Token: `KSMTransactionTokenRequiredRequestEvent` → `KSMProvideTokenEvent(confirmationType:andToken:)` → `KSMProvideTokenResultEvent`. A `.KSMINVALID_PIN` with retries left keeps the sheet open. Needs a TMS mode with a PIN, which [TMS](tms.md) never verified |
| Offline login | `offlineLogin(userId:)` → AST client id | `KSMOfflineLoginEvent(userIdentifier:)` → `KSMOfflineLoginResultEvent(status, astClientId)`. Needs offline tokens (`.clearOffline` removes them). The official Login and Stay Logged In pages recommend trying it first on LOGIN_REQUIRED and falling back to the IDP login; it is not valid with PASSWORD/PIN mode, and whether a user stays signed in is a security decision. The reference sessions do not call it automatically: add it only when the customer wants "stay logged in", and check on a device that logout (which clears the IAM token cache) still ends in the sign-in screen |
| Login with a token | `loginWithToken(userId:mode:accessToken:authorizationCode:)` | `KSMLoginWithTokenEvent(parameters:authenticationMode:iamAccessToken:authorizationCode:)`. No result event; the normal login events follow. During activation: `KSMProvideTokenAndUserIdEvent` |
| Anonymous users | `createAnonymousUser(tenantId:)`, `enrollAnonymousUser(tenantId:mode:clientId:)` | `KSMCreateAnonymousUserEvent` → `(userId, tenantId, activationCode)`, deleted locally at the next restart; `KSMEnrollAnonymousUserEvent` → `KSMStatusResultEvent`. **Needs backend** support |
| Workspace switch | `switchWorkspace(tenantId:)` | `KSMSwitchWorkspaceEvent(tenantId:)` → `KSMStatusResultEvent` |
| Webhook nonce | `provideNonce(_:action:)` | `KSMProvideNonceEvent(nonce:action:)` → `KSMStatusResultEvent`. Header: Maverick only |
| Properties | `property(_:owner:)`, `setProperty(_:data:type:owner:ttl:flags:)` | `KSMGetPropertyEvent(propertyKey:with: .device/.user/.group)` → `KSMGetPropertyResultEvent(status, propertyData, propertyType, propertyTtl, propertyFlags)`; `KSMSetPropertyEvent` → `KSMSetPropertyResultEvent` |
| REST endpoint | `configureRestEndpoint(_:url:certificateChain:)` | `KSMConfigureRestEndpointEvent(restEndpointData: KsRestEndpointData(restEndpointIdentifier: .IAM/.smartScreenService/.astService/.pushService, serverUrl:, certificateChain:))` → `KSMAcknowledgeEvent` |
| Tracing | `setServerTracing(_:)`, `setOpenCensusTracing(_:)` | `KSMEnableServerTracingEvent` / `KSMDisableServerTracingEvent` (no result); `KSMEnableOpenCensusTracingEvent(tracingEnabled:)` → `KSMAcknowledgeEvent` |
| SSMS OTP | `generateOtp(optionalData:pin:)` | `KSMGenerateOtpEvent(optionalData:pin:)` → `KSMGenerateOtpResultEvent(status, otp, retry_counter, retry_delay)`. **Needs an SSMS backend** |
| App-initiated transaction | `initiateTransaction(url:certificates:headers:content:timeoutSeconds:)` → handle; `sendOnTransaction(handle:content:closeSocket:)` → reply | `KSMInitiateTransactionEvent` → `KSMInitiateTransactionResultEvent(status, handle)`; `KSMInitiatedTransactionDataSendEvent` → `KSMAcknowledgeEvent`, then `KSMInitiatedTransactionDataReceivedEvent(handle, status, content)`. Needs a server endpoint that speaks this protocol |
| App update | `performUpdate()`, `openUpdateInfo()` | `KSMUpdateEvent` → `KSMUpdateResultEvent(updateStatus)`; `KSMOpenInfoUrlEvent` → `KSMOpenInfoUrlResultEvent(status)` (`KSMUpdateStatus`) |
| HTTP through the SDK | `httpRequest(_:method:body:contentType:headers:accessTokenIdentifier:certificate:)` | `KSMCreateHttpCommonRequestEvent(fullUrl:httpMethod:content:contentType:userName:password:certificate:httpHeaders:cookieIdentifier:accessTokenIdentifier:)` → `KSMCreateHttpCommonRequestResultEvent(status, httpStatus, response, …)`. The same event carries the email-code activation on the device (`HeadlessIdpFlow.swift`), so the transport itself is **device**-verified; the `accessTokenIdentifier` path is compiled only |
| File upload | `upload(_:fileName:data:mimeType:…)` | JSON body with base64 content through `httpRequest`. The SDK's multipart type `KsHttpMultiPart` is **broken** (below) |

**Explicit-authentication transactions** (`require_explicit_authentication=true`) are
device-verified (2026-09-27, ACCEPTED and signed). For an IDP-login user the SDK
satisfies them with a silent token exchange and does **not** raise the PIN or token
request above. They need `iam.clientId` = the login client and the `tms` scope
(`sdk_tms_scope_ensure`); see tms.md. The PIN and token requests belong to
SDK-PIN users, which the verification backend does not have, so they stay untested.

**`KSMInvalidStateEvent`**: a request the SDK will not run in its current state is
answered with this event on the event channel instead of its result event. The
reference `awaitResult` fails fast with `SdkRequestError.invalidState(message)`. The
event names no request, so keep one request in flight. On Maverick, `GetDeviceInformation` and
`GetUpdateInformation` always get it: they are SSMS-only. To see why the SDK refused a
request, read the SDK console log around the request: `[QSM] Processing: <Event>. Current
states: ...` shows the state, and an `Executor not exists` or `Unexpected result` line shows
which module had no handler.

## Notifications the MasterController sends by itself

These have no request. `SdkStatusMonitor.swift` publishes all of them; it observes the
event stream through `SdkResultRouter` without consuming anything:

| Event | Meaning |
|---|---|
| `KSMServerConnectionEvent.connectionStatus` | `KSMConnectionState`: `.KSMConnected`, `.KSMDisconnected`, `.KSMConnectionLost`, `.KSMReconnected`, `.KSMReachable`, `.KSMNotReachable` |
| `KSMSseStreamStatusEvent.status` | `KSMSseStatus` of the server-sent-events stream that delivers TMS |
| `KSMBusyEvent` / `KSMIdleEvent` | The MC is working or has finished; use them for a spinner |
| `KSMChatInitialisedEvent`, `KSMChatNotInitialisedEvent`, `KSMChatOfflineInitialisedEvent` | Chat status only. `KSMIsChatInitialisedEvent` has no result event, and there is no send or receive API (see [TMS](tms.md#chat-is-not-in-the-ios-mcsdk)) |
| `KSMStartMigrationEvent` / `KSMMigrationFinishedEvent` | Migration of local data after a major SDK update; it starts during chat initialisation. Keep the user out of flows until it finishes |
| `KSMIdpLoginRequiredEvent(userIdentifier)` | The IDP session expired; run the login flow again |

## Declared but not in the binary (broken)

Every class declared in the 15.16 headers was checked against the symbols the
KSMasterController binaries export (device debug and release, simulator). All of the 194
`@interface`s are exported except these 12, so code that uses them compiles but fails to link with
`Undefined symbols: _OBJC_CLASS_$_…`:

- **Muting (11):** `KSMGetMutedEntriesEvent`, `KSMGetMutedEntriesResultEvent`, `KSMMuteAllEvent`,
  `KSMMuteCategoryEvent`, `KSMMuteConversationEvent`, `KSMMuteUnmuteResultEvent`,
  `KSMMuteUserEvent`, `KSMUnmuteAllEvent`, `KSMUnmuteCategoryEvent`,
  `KSMUnmuteConversationEvent`, `KSMUnmuteUserEvent`.
- **Multipart upload (1):** `KsHttpMultiPart`, so the `multiPartContent:` initialisers of
  `KSMCreateHttpCommonRequestEvent` can't be used either.

Don't build these on 15.16; use the upload alternative above, and tell the user that the
missing symbols have to be reported to KOBIL. To check a newer delivery, list every declared
class that the binary doesn't export:

```sh
FW=<delivery>/debug/KSMasterController.xcframework/ios-arm64/KSMasterController.framework
nm -gU "$FW/KSMasterController" | sed -n 's/.*_OBJC_CLASS_\$_//p' | sort -u > exported.txt
grep -ho '@interface [A-Za-z]*' "$FW"/Headers/*.h | awk '{print $2}' | sort -u > declared.txt
comm -23 declared.txt exported.txt
```

## Trusted web view (`ios/platform/SecureWebView.swift`)

- **Creation.** `KsTrustedWebView.createInstance(with: KsTrustedWebViewConfiguration, frame:)`, then
  `loadUrl(_:)`.
- **Configuration.**
  - `urlInternalWhiteList` lists the hosts that stay inside the view.
  - `urlExternalWhiteList` lists the hosts handed to `shouldHandleExternalUrl`.
  - `certsDataForValidation: [Data]` holds the pinned certificates.
  - Also: `allowHttpConnection`, `browsingMode` (`.secureBrowsing` is the default, the other is `.freeBrowsing`), `customUrlSchemes`,
    `mimeTypesToDownload`, `allowsInlineMediaPlayback`.
- **All 15 `KsTrustedWebViewDelegate` methods are required.** The header marks none of them
  `@optional`. The reference implements every one.
- **Implement only the completion-handler form of `didReceive challenge`.** Its async twin has
  the same Objective-C selector, so implementing both is a compile error.
- **Blocked URLs.** A refused URL arrives at `onURLBlocked(url, reason: KSWEBVIEWERROR, …)`,
  for example `.KS_CALLED_URL_NOT_IN_URL_WHITELISTS` or `.KS_CERTIFICATE_ERROR`.
- **Special commands.** `KSSPECIALCOMMAND` (close the web view, AST activate/login/logout)
  arrives at `onSpecialCommandTriggered(_:parameters:)`. The reference ignores it: wire it only
  if the web content sends these commands.
- **Secure browsing needs pinned certificates.** With `certsDataForValidation` empty, every
  page is blocked with `KS_CERTIFICATE_TRUSTSTORE_PARSING_ERROR` (reason 2). Pass the root
  of the site's chain as PEM file bytes (the SDK's ISRG Root X1 PEM works for Let's Encrypt
  sites). The reference makes `pinnedCertificates` a required parameter; `.freeBrowsing`
  turns the extra pinning off.
- **Status: device** (2026-09-27, iPhone 15 Pro). An allow-listed Let's Encrypt site with the
  ISRG Root X1 PEM pinned loaded with no error. A site off the allow-list was blocked with
  `KS_CALLED_URL_NOT_IN_URL_WHITELISTS` (reason 0).

```swift
SecureWebView(
    url: URL(string: "https://portal.example.com/")!,       // PER APP
    internalHosts: ["portal.example.com"],                   // PER APP
    pinnedCertificates: [rootPEM],                           // PER APP: root of the site's chain
    onBlocked: { url, reason in /* show a message; do not retry */ }
)
```

## Scam-call protection (`ios/platform/CallGuard.swift`)

- **API.** `hnb.CallMonitor.sharedInstance()` with `startMonitoring(withAcknowledgeIn:)` (minimum 0 s) or
  `startMonitoring(withTerminateIn:)` (minimum 1 s), and `stopMonitoring()`.
- **Alert.** By default it draws its own `UIAlertController`. To draw your own UI instead, set a
  `CallMonitorDelegate` (`callMonitorDidDetectCall(flow:initialRemaining:onUserAction:)`).
- **Usage.** Put `.callGuard()` on the approval and signing screens.
- **CallKit.** The header says CallKit must be linked. The reference builds and links without adding it.
- **Status.** Compiled and linked; not run during a real phone call.

## What the MCP does and doesn't do

The KOBILSDK MCP server configures the backend for:
- activation, login, apps and versions, and TMS triggering (accept, reject, timeout, cancel);
- display messages;
- the IDP checks.

**It has no tools for:**
- sending a push through APNs;
- multi-user administration;
- PIN-mode TMS;
- SSMS;
- web-view or mini-app configuration.

For those features, the backend part is the customer's own work. Don't claim it is set up.

## Finding a Swift name

Some enums drop the `KSM` prefix in Swift, and others keep it:

| Enum | Swift cases |
|---|---|
| `KSMEncryption`, `KSMDataModelRequestStatus`, `KSMAuthenticationMode`, `KSMSdkState`, `KSMConfirmationType`, `KSMInitiateTransactionStatus`, `KSMClearIamTokenCacheBehavior` | prefix dropped: `.encrypted`, `.success`, `.biometric`, `.loggedIn`, `.ok`, `.clearAll` |
| `KSMEventStatusType`, `KSMConnectionState` | prefix kept: `.KSMOK`, `.KSMUPDATE_AVAILABLE`, `.KSMINVALID_PIN`, `.KSMConnected` |
| `KSMUpdateStatus` | upper case, no prefix: `.OK`, `.CANCELLED` |

When unsure, generate the interface and search it:

```sh
xcrun swift-synthesize-interface -module-name KSMasterController.KsMacroEvents \
  -F <dir containing KSMasterController.framework> -target arm64-apple-ios17.0 \
  -sdk "$(xcrun --sdk iphoneos --show-sdk-path)" > KsMacroEvents.swift
```

Then confirm the result with `XcodeRefreshCodeIssuesInFile`.
