> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/introduction/kobil_app_security> on 2026-09-28. Converted to Markdown; wording unchanged.

# KOBIL App Security

KOBIL App Security is a combination of app and server side security functions, to protect your app and the identity of the user of your app. If provides

* protection against other apps on same device ('App Shielding hardens your app')
* secure communication to server
* secure user registration
* secure user account activation and login ('Trusted Login')
* secure user transaction confirmation ('Transaction Signature' - 'TMS')
* secure communication to web server ('Trusted WebView' - 'TWV')
* secure IDP-Token ('Single Sign On') - only with KOBIL Shift Lite solution

> **Note**: One user account can have activated on multiple devices.

### Master Controller SDK

By using the MasterController SDK in your app, you can add easily security to your app.
A KOBIL Secured app is always tied together with one KOBIL Security Server installation, to prevent various security attacks. Therefore such an app always contains configuration parameter to reach securely this server, e.g. URLs and trusted TLS server certificates.
When a user account is activated, some security relevant data is stored on app side, that are only usable in combination with the server side.

### KOBIL Security Server

The KOBIL Security Server manages and protects the apps and the user accounts. Depending on the solution it does it in combination with KOBIL IDP Services. One KOBIL Security Server installation can protect multiple apps, if needed separated in multiple tenants. It is available for on premises or in cloud installations.

### PKCE Integration with KOBIL Apps

With the release of IDP version 5.1.0, KOBIL apps now require Proof Key for Code Exchange (PKCE) to add an extra layer of security in the authorization flow. PKCE protects authorization codes from interception and misuse, aligning with OAuth 2.0 and OpenID Connect standards.

#### How PKCE Works in KOBIL Apps

**PKCE Requirement**:

* As part of OpenID Connect compliance, KOBIL apps using the MasterController SDK must implement a PKCE code challenge when generating an authorization code.
* The Registration Service generates a unique PKCE code challenge and later verifies the PKCE code verifier when redeeming the authorization code, providing an `ID_TOKEN` from the central IDP (Identity Provider) service.

**SDK-Generated PKCE Codes**:

* The MasterController SDK generates a `code_challenge` and `code_verifier` for each authorization request, automating secure authorization flow handling.
* Both the `code_challenge` and the hashing method (`code_challenge_method`) are provided by the SDK and transmitted to the server.

**Authorization Flow**:

* The app sends the PKCE `code_challenge` as part of the initial authorization request.
* Upon receiving the authorization code, the app submits the `code_verifier` along with the authorization code back to the IDP, where the server verifies the match before issuing an `ID_TOKEN`.

#### iOS/Swift

The following examples illustrates how `KssIdp SDK` incorporates the PKCE `code_challenge`and `code_challenge_method` on both platforms.

```
kssidp.initiateConnection(
withURL: kssUrl.getURL(
clientId: clientId,
tenantId: config.tenantId,
codeChallange: astClientDataResultEvent.codeChallange,
codeChallangeMethod: astClientDataResultEvent.codeChallangeMethod
),
certificate: self.certificateData,
headers: headers,
tenantId: config.tenantId,
requiresSetAuthorizationCode: requiresSetAuthorizationCode,
shouldHashPin: config.shouldHashPin,
retryOnTimeout: config.networkConfig.retryOnTimeout
)
```

#### Android/Kotlin

```
initiateConnectionWithUrl(
clientId,
tenantId,
getAstClientDataResult.codeChallenge,
getAstClientDataResult.codeChallengeMethod,
httpHeaders,
actionType,
authMode,
onProvideCredentials,
onResultReceived
)
```
