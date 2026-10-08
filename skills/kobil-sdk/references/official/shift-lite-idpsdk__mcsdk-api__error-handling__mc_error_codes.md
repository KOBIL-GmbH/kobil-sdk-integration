> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/error-handling/mc_error_codes> on 2026-09-28. Converted to Markdown; wording unchanged.

# RuntimeErrorEvent Error Codes

This runtime exeception can happen while developing and contain helpful informations or on run time. In this case app is not functional any more and triggers an automatic restart event.

SubSystem **500**  
MCSDK Error Codes caused by ASM-Service

| Code | Enum | Description |
| --- | --- | --- |
| **500000001** | GENERAL\_ERROR | General error |
| **500000002** | INVALID\_ACTION | Failed to check App Version: Invalid action |
| **500000003** | ILLEGAL\_STATE | Client session is in an illegal state |
| **500000004** | NO\_SUCH\_ALGORITHM | Cannot generate random number |
| **500000005** | CONNECTION\_NOT\_SECURED | Connection must be secured for this command |
| **500000006** | LICENCE | License error occurred |
| **500000007** | USER\_NOT\_FOUND | User does not exist |
| **500000008** | APPVERSION\_NOT\_FOUND | App version does not exist |
| **500000009** | NO\_DEVICE\_FOR\_CERT | No device found for the certificate |
| **500000010** | USER\_NOT\_MAPPED | Device's certificate is not mapped to a user |
| **500000011** | SIGNED\_CONTENT\_INVALID | This error indicates the provided signed content is either corrupted or does not match the expected signature, preventing proper verification of its integrity. |
| **500000012** | TRANSACTION\_CERT\_NOT\_FOUND | Invalid signed content |
| **500000013** | CREATE\_HASH\_FAILED | Failed to create digest |
| **500000014** | CERT\_SIGNING\_CREATION\_FAILED | Issue with certificate signing/creation |
| **500000015** | CERT\_REQUEST\_DECODING\_FAILED | Issue with certificate request decoding |
| **500000018** | DEVICE\_SIGNATURE\_INVALID\_ALGORITHM | Invalid signature algorithm |
| **500000019** | DEVICE\_SIGNATURE\_INVALID\_PUBKEY | Invalid public key |
| **500000020** | DEVICE\_SIGNATURE\_INVALID\_SIGNATURE | Invalid signature |
| **500000021** | DEVICE\_SIGNATURE\_SIGNED\_DATA\_INVALID | Signed data is invalid |
| **500000022** | DEVICETYPE\_NOT\_FOUND | Device type does not exist |
| **500000023** | CERT\_ALREADY\_IN\_DB | Certificate already exists in the database |
| **500000024** | DEVICEKEY\_ENCRYPTION\_FAILED | Cannot decrypt device key from the database |
| **500000025** | APP\_REGISTRATION\_USER\_NOT\_REGISTER\_USER | User is not authorized to register the app |
| **500000026** | USER\_NOT\_TEST\_USER | TestApp: User is not authorized to test the app |
| **500000028** | NOT\_VIRTUAL\_DEVICE | Device is not a virtual device |
| **500000029** | LOCKED\_CERTIFICATE | Device's certificate is locked |
| **500000030** | RETRIES\_EXCEEDED | Virtual device retry counter exceeded |
| **500000031** | USER\_LOCKED | User is locked (by administrator) |
| **500000032** | TRANSACTION\_INVALID\_COMMANDSTATUS | Invalid command status in TransactionResponse |
| **500000033** | USER\_TEMPORARILY\_LOCKED | User is temporarily locked (e.g., RetryCounter exceeded) |
| **500000034** | CERTIFICATE\_EXPIRED | Certificate is expired |
| **500000035** | CERTIFICATE\_NOT\_YET\_VALID | Certificate is not yet valid |
| **500000036** | DEVICE\_SIGNATURE\_CERT\_NOT\_FOUND | Certificate not found for the device |
| **500000037** | CERTIFICATE\_NOT\_MAPPED\_TO\_USER | Certificate is not mapped to a user |
| **500000038** | SESSION\_PRESUMABLY\_CLOSED | Server received data for a closed session |
| **500000039** | NO\_ISSUER\_CERTIFICATE | Issuer certificate not found |
| **500000040** | INVALID\_CERTIFICATE | Invalid certificate |
| **500000041** | NO\_OTP\_FOUND | OTP not found in session |
| **500000042** | APPNAME\_MISSING | Hardware device does not provide an app name |
| **500000044** | APPVERSION\_NOT\_REGISTERED | App version is not registered |
| **500000045** | NO\_TRANSACTION\_DATA\_STORED | No transaction data stored in session |
| **500000046** | SESSION\_CLOSED | SSMS closed the session |
| **500000047** | APPVERSION\_NOT\_CONFIGURED\_FOR\_USER | App version is not configured for the user |
| **500000048** | UPDATE\_VERSION\_MISSING | Update version is missing |
| **500000049** | NOT\_UPDATABLE\_APPVERSION\_EXPIRED | App version that doesn’t support the update process is expired |
| **500000052** | APP\_VERSION\_NOT\_FOUND | App version not found in database |
| **500000053** | DEVICE\_TEMPORARY\_LOCKED | Device is temporarily locked |
| **500000054** | TEMPLATE\_RESOLUTION\_ERROR | Error resolving template |
| **500000055** | TRANSACTION\_INVALID\_NULL | Transaction parameter is null or invalid |
| **500000056** | INVALID\_DATA | Server received invalid data |
| **500000057** | P2S\_MESSAGE\_INVALID\_SIGNATURE | Invalid signature for P2S-Message |
| **500000058** | TENANT\_CANNOT\_REGISTER | Inheritable apps can only be registered in the master tenant |
| **500000059** | INHERITABLE\_VERSION\_EXPECTED | Inheritable version must be used (e.g., session key decrypted with master’s Asmca) |
| **500000060** | INVALID\_CSR\_PROFILE | Certificate signature request's key usage and extended key usage extensions do not match defined profiles |

SubSystem **800**  
MCSDK Error Codes caused by Backend (SSMS, SCP, IdP, ABS and other services)

| Code | Enum | Description | Troubleshooting |
| --- | --- | --- | --- |
| **800000001** | kNotExistScpConfigOnStartRuntimeError | SDK config not exist | Helpful while developing see if file is installed |
| **800000002** | kUnexpectedErrorGetScpConfigOnStartRuntimeError | Error retriving SDK Config | Helpful while developing see if file is installed |
| **800000003** | kNotExistStatusGetResultEventOnStartRuntimeError | SCP Config not exist | Helpful while developing see if file is installed |
| **800000004** | kUnknownStatusGetResultEventOnStartRuntimeError | Unexpected error during get SCP Config | Helpful while developing see if file is installed |
| **800000005** | kSCPConfigJsonParseRuntimeError | Parse error of SCP Config | UC37StartMCWithoutUrls |
| **801000008** | kSdkConfigParsingFailed | Raised if it it was not possible to parse the sdk config | maybe file is corrupt or not existant |
| **801000009** | kVerifyingSdkConfigFailed | Raised if it was not possible to verify the sdk config | maybe file is corrupt |
| **800000190** | kMcConfigJsonParseRuntimeError | MC config json parse error | UC37StartMCWithoutUrls |
| **800000191** | kMcConfigJsonMissingScpSectionRuntimeError | Missing scp section in mc config json | UC37StartMCWithoutUrls |
| **800000192** | kMcConfigJsonMissingTokenIssuerUrlRuntimeError | Missing token issuer url in scp section of mc config json | UC37StartMCWithoutUrls |
| **800000193** | kMcConfigJsonMissingIamSectionRuntimeError | Missing iam section in mc config json | UC37StartMCWithoutUrls |
| **800000194** | kMcConfigJsonMissingSmartScreenSectionRuntimeError | Missing smart screen scection in mc config json | UC37StartMCWithoutUrls |
| **800000197** | kMcConfigJsonMissingIamRuntimeError | Missing client id in iam section of mc config json | UC37StartMCWithoutUrls |

For legacy reasons we needed to keep the old Subsystem/ErrorCode logic here. Given the one error code MCSDK is providing, the least six significant digits are the ErrorCode while the remaining most significant digits are the SubSystem

| Error Code | Sybsystem | Description | Troubleshooting |
| --- | --- | --- | --- |
| **6** | *32, 102, 202, 602* | The user credentials folder cannot be parsed for user credentials. Normally the path is invalid or not accessible. | Secure storage of a device not available. User should unlock device before MCSDK usage |
