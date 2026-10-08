> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/app-lifecycle/add-app/add_app> on 2026-09-28. Converted to Markdown; wording unchanged.

# Add App in Security Server in KOBIL Shift Lite

### Collect needed Push Notification parameters

1. Define which Credentials are needed:

| Client platform | Needed Credentials |
| --- | --- |
| Android, Flutter apps on Android/iOS | Android Firebase API-Key ([deprecated legacy FCM](https://firebase.google.com/docs/cloud-messaging/migrate-v1)) |
| Android, Flutter apps on Android/iOS | [Firebase Service Account Json](https://firebase.google.com/docs/admin/setup#initialize_the_sdk_in_non-google_environments) (requires min. Shift 0.167) |
| iOS (without Flutter apps) | Apple Push Notification Service (APNs) |
| Huawei | Huawei Push Kit (HPK) |

2. If needed, collect 'Google Firebase Cloud Messaging (FCM)' credentials:

| Credentials Parameter | How to get |
| --- | --- |
| Android Firebase API-Key  ([deprecated legacy FCM](https://firebase.google.com/docs/cloud-messaging/migrate-v1)) | Token to authenticate on server side to FCM, this is not the app device push token.  Get it rom FCM WebUI \ Cloud Message API (Legacy) \ Server Key |
| [Firebase Service Account Json](https://firebase.google.com/docs/admin/setup#initialize_the_sdk_in_non-google_environments) | A private key file in JSON format used to authenticate on server side to FCM.  Download from FCM WebUI |

3. If needed, collect 'Apple Push Notification Service (APNs)' credentials:

| Credentials Parameter | How to get |
| --- | --- |
| iOS Apns Certificate, iOS Apns Private Key | Public certificate and private key to authenticate to APNs, see [Apple documentation](https://developer.apple.com/documentation/usernotifications/setting_up_a_remote_notification_server/establishing_a_certificate-based_connection_to_apns):   1. Locally create a key pair in a PKCS#12 file (public key and private key) with MacOS Keychain tool.  2. For the public key:   2.1 Locally create a CSR (aka Certificate Signing Request; PKCS#10 PEM encoded; includes the public key) from the PKCS#12 file with MacOS Keychain tool.  2.2 Upload the Certificate Signing Request to Apple.   2.3 Download the resulting certificate (.cer file, binary DER encoded).   2.4 Locally import the certificate with MacOS Keychain tool.  2.5 Locally export with MacOS Keychain tool to the PKCS#12 file `cert.p12`.  2.6 Locally export the certificate (PEM encoded) from the PKCS#12 file. Unfortunately, Apple still uses the outdated RC2 algorithm in creating PKCS#12 files, which is unsupported by OpenSSL version 3.0 and newer (at least by default), so this export is either done (for older versions of openssl) by issuing: `openssl pkcs12 -clcerts -nokeys -in cert.p12 -out apns_cert.p12` or, if you have a modern version of OpenSSL: `openssl pkcs12 -clcerts -nokeys -legacy -in cert.p12 -out apns_cert.p12`. 2.7. Use `apns_cert.p12` as 'iOS Apns Certificate' inside the portal.   2.8 For cURL: please use following command to convert certificate to base64 format and compose datauri parameter that will be used in cURL JSON `echo -n "data:application/x-x509-ca-cert;base64," > cert_datauri.txt && base64 < apns_cert.p12 | tr -d '\n' >> cert_datauri.txt`.   Strip `-----BEGIN CERTIFICATE-----\n` and `\n-----END CERTIFICATE-----\n`.  3. For the private key:   3.1 Locally export the password encrypted private key file (PEM encoded) from the PKCS#12 file. Be sure to set a PEM pass phrase here. The pass phrase must be 4 or more characters in length or this will not work. You will need that pass phrase added here in order to remove it in the next step, which again takes one of two forms depending on your openssl version, either: `openssl pkcs12 -nocerts -in cert.p12 -out apns_key_encrypted.key` or: `openssl pkcs12 -nocerts -legacy -in cert.p12 -out apns_key_encrypted.key`.  3.2 Transfer it to an unencrypted file (independent of openssl version): `openssl rsa -in apns_key_encrypted.key -out key_unencrypted.p8`.   3.3 Use `key_unencrypted.p8` as 'iOS Apns Private Key' inside the portal.   3.4 For cURL: or cURL: please use following command to convert certificate to base64 format and compose datauri parameter that will be used in cURL JSON `echo -n "data:application/octet-stream;base64," > cert_datauri_key.txt && base64 < key_unencrypted.p8 | tr -d '\n' >> cert_datauri_key.txt`.   Strip `-----BEGIN RSA PRIVATE KEY-----\n` and `\n-----END RSA PRIVATE KEY-----\n`. |
| iOS Bundle ID | Unique identifier of the app in Apple's eco system |
| iOS Development | Apple's Push Notification service has different endpoints for development/test/staging and production (end user) stages:   true - [development endpoint](https://api.development.push.apple.com)   false - [production endpoint](https://api.push.apple.com) |

4. If needed, collect 'Huawei Push Kit (HPK)' credentials:

| Credentials Parameter | How to get |
| --- | --- |
| HPK Client ID | Client identifier (name) to authenticate to HPK |
| HPK Client Secret | Password to authenticate to HPK |

### Add App via KOBIL Portal

1. In KOBIL Portal, go to App Management \ Apps and press 'Add New App':
   ![](https://developer.kobil.com/assets/images/add_app_Shift1-2b6ebc7ff9e6ef1588d73a89983e9e92.png)
2. Enter AstAppName ('App Name') and the needed credentials for the Push Notification provider:
   ![](https://developer.kobil.com/assets/images/add_app_Shift2-1643be693339a4808e49146780f16e34.png)

* Note that the files need to have the correct extensions (p8 for the file with the key, p12 for the file with the cert) so KOBIL Portal can use these files. For some older versions, e.g. Shift 0.64, files with p8 extension are not accepted for the key, there, you have to rename apns\_key\_unencrypted.p8 to apns\_key\_unencrypted.p12.
* Mark 'iOS Development' when push notifications should be sent via Apple's development gateway. Do not mark it, if you need the gateway used for released apps.
* Delete apns\_key\_unencrypted.p8 and apns\_key\_unencrypted.p12.

> **Note**: For additional details see KOBIL Portal documentation.

### Add App via cURL CLI

An important prerequisite for sending requests via cURL is to obtain an authorization token to "prove" to the server that you are allowed to add an app or to register an app version. [Here is a detailed description on how to obtain such an authorization token](shift-lite-idpsdk__prerequisites__auth_token_shift.md).

##### Add an App

```
curl -X POST https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/apps/$appName -H "Accept: application/json" -H 'Content-Type: application/json' -d '{
"categories": ["tms"],
"androidApiKey": "A...",
"fcmServiceAccountJSON": "base64EncodedFirebaseServiceAccountJSON",
"iosApnsCertificate": "data:application/x-x509-ca-cert;base64...",
"iosApnsPrivateKey": "data:application/octet-stream;base64...",
"iosBundleId": "com.company.name",
"iosIsDevelopment": $devVersion,
"hpkClientId": "",
"hpkClientSecret": ""
}' -H 'Authorization: Bearer $token'
```

> **your-environment.shift.company.com** should be replaced by the suitable host name of your environment. While the request to get an authorization token will use the subdomain **idp** all your other requests should use the subdomain **asts**.  
> **$yourTenantName** should the the tenant for which you want to add the apps. For a short discussion of tenants see the corresponding section of the [overview](shift-lite-idpsdk__prerequisites__app-lifecycle__add-app__add_app_overview.md#tenants).  
> **$appName** should be the name of your app.  
> **$devVersion** is a boolean (i.e. either `true` or `false`) indicating whether push messages should be sent via Apple's development gateway, or whether to use the gateway used for released apps.  
> **$token** should be an authorization token of a user with the correct permissions / roles to add apps.

> **Note**:
> In KOBIL Shift Lite we use always the push notification category "tms".
> Push notification credentials are optional, but if one of the fields for iOS/APNs credentials is provided,
> it is mandatory to provide all the iOS credentials, otherwise the request will fail.
> Same for other platform type, Android/FCM and Huawei/HPK.

> `iosApnsCertificate` and `iosApnsPrivateKey` must be base64-encoded String. Please check file `cert_datauri_key.txt` and `cert_datauri.txt` that were generated from ateps above. See above for how to generate them.
> `fcmServiceAccountJSON`must be also in base64-encoded String.

##### Get Information for an existing App

Example use: To check if push notification credentials are already configured or not you can send following request to get the information of an existing app.

```
curl https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/apps/$appName -H "Accept: application/json" -H 'Authorization: Bearer $token'
```

##### Update existing App

Example use: If push notification credentials are not configured for an existing App, you can provide the push credentials by updating the app with following request:

```
curl -X PUT https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/apps/$appName -H "Accept: application/json" -H 'Content-Type: application/json' -d '{
"categories": ["tms"],
"androidApiKey": "A...",
"iosApnsCertificate": "data:application/x-x509-ca-cert;base64...",
"iosApnsPrivateKey": "data:application/octet-stream;base64...",
"iosBundleId": "com.company.name",
"iosIsDevelopment": $devVersion,
"hpkClientId": "",
"hpkClientSecret": ""
}' -H 'Authorization: Bearer $token'
```
