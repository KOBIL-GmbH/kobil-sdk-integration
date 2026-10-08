> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/enumerations> on 2026-09-28. Converted to Markdown; wording unchanged.

# Enumerations and Bitsets

### AuthenticationMode

Represents the authentication mode.

#### Objective-C - KSMAuthenticationMode

#### Java - AuthenticationMode

Values

| Java | Objective-C | Description |
| --- | --- | --- |
| NO | KSMAuthenticationModeNo | Indicates that no interactive authentication is required to access user credentials. |
| BIOMETRIC | KSMAuthenticationModeBiometric | Indicates that biometric authentication is required to access user credentials. |
| PASSWORD | KSMAuthenticationModePassword | Indicates that password authentication is required to access user credentials. |
| PIN | KSMAuthenticationModePin | Indicates that device PIN authentication is required to access user credentials. |

### BannerType

Represents the banner type.

#### Objective-C - KSMBannerType

#### Java - BannerType

Values

| Java | Objective-C | Description |
| --- | --- | --- |
| DISPLAY\_MESSAGE | KSMBannerTypeDisplayMessage | Indicates that a display message is waiting to be processed. |
| TRANSACTION | KSMBannerTypeTransaction | Indicates that a transaction is waiting to be processed. |

### ConfirmationType

Represents the transaction confirmation type

#### Objective-C - KSMConfirmationType

#### Java - ConfirmationType

Values

| Java | Objective-C | Description |
| --- | --- | --- |
| OK | KSMConfirmationTypeOk | Indicates that the transaction is successfully processed and accepted. |
| CANCEL | KSMConfirmationTypeCancel | Indicates that transaction processing is cancelled. |
| TIMEOUT | KSMConfirmationTypeTimeout | Indicates that transaction processing is timed out. |

### InitiateTransactionStatus

Represents the status of initiate transaction operations.

#### Objective-C - KSMInitiateTransactionStatus

#### Java - InitiateTransactionStatus

Values

| Java | Objective-C | Description |
| --- | --- | --- |
| OK | KSMOK | Indicates that the transaction has been initiated successfully. |
| ESTABLISHMENT\_FAILED | KSMEstablishmentFailed | Indicates that the transaction has NOT been initiated successfully. Check the error code and description in the result event. |
| TIMEOUT | KSMTimeout | Indicates that the transaction initiatiation timed-out or there was no response within the given time. Check the error code and description in the result event. |
| CLOSED | KSMClosed | Indicates that the initiated transaction connection has been closed. Check the error code and description in the result event. |
| FAILED | KSMFailed | Indicates that the initiated transaction connection has been faied. Check the error code and description in the result event. |

### KeyAccessProtectionMode

Represents the key access protection mode.

| Value | Description |
| --- | --- |
| No | Indicates that no interactive authentication is required to access keys from the device key strorage. |
| Biometric | Indicates that biometric authentication is required to access user keys from the device key strorage. |
| DeviceCredential | Indicates that device PIN is required to access user keys from the device key strorage. |

### MessageType

Represents the display message type

#### Objective-C - KSMMessageType

#### Java - MessageType

Values

| Java | Objective-C | Description |
| --- | --- | --- |
| INFO | KSMMessageTypeInfo | Indicates an info display message |
| WARNING | KSMMessageTypeWarning | Indicates an warning display message |
| ERROR | KSMMessageTypeError | Indicates an error display message |

### SdkState

Represents the SDK state.

#### Objective-C - KSMSdkState

#### Java - SdkState

Values

| Java | Objective-C | Description |
| --- | --- | --- |
| UNINITIALISED | KSMUninitialised | Indicates that the SDK has failed to initialise. Check the error code and description in the result event. |
| ACTIVATION\_REQUIRED | KSMActivationRequired | Indicates that the SDK has successfully initialised but there are no activated users. |
| LOGIN\_REQUIRED | KSMLoginRequired | Indicates that the SDK has successfully initialised, and there are already some activated users who may log in. The activated user list is provided in the result event. |
| UNIDENTIFIED | KSMUnidentified | Indicates that the SDK has successfully initialized, but some internal error occurred during user activation or deactivation. Check the error code and description in the result event. |

### StatusType

#### Objective-C - KSMEventStatusType

#### Java - StatusType

Values

| Java | Objective-C | Description |
| --- | --- | --- |
| OK | KSMOK | The process was completed successfully. |
| UPDATE\_AVAILABLE | KSMUPDATE\_AVAILABLE | An update of the app is available. (Info only) |
| APP\_REGISTERED | KSMAPP\_REGISTERED | Will be sent from SSMS to the app when the app registration was successful. (Info only). The App must restart the SDK itself. |
| USER\_CANCEL | KSMUSER\_CANCEL | The user cancelled a process, e.g. a transaction. |
| USER\_CONFIRMATION\_TIMEOUT | KSMUSER\_CONFIRMATION\_TIMEOUT | The process was cancelled by a timeout. |
| INVALID\_PIN | KSMINVALID\_PIN | The user entered a wrong pin. |
| UNKNOWN\_VERSION | KSMUNKNOWN\_VERSION | Activation and Logon process: The app has a wrong version. |
| UNKNOWN\_CLIENT\_TYPE | KSMUNKNOWN\_CLIENT\_TYPE | Activation and Logon process: The app has a wrong client type. |
| UPDATE\_NECESSARY | KSMUPDATE\_NECESSARY | This version of the app was replace by a newer one and the user must update. |
| WRONG\_CREDENTIALS | KSMWRONG\_CREDENTIALS | Activation and Logon process: The user ID, activation code or the PIN are incorrect. |
| UNKNOWN\_CERTIFICATE | KSMUNKNOWN\_CERTIFICATE | User removed on the ssms server |
| INTERNAL\_ERROR | KSMINTERNAL\_ERROR | An internal error occurred during the process, usually a Runtimer Error |
| ACTIVATION\_CODE\_EXPIRED | KSMACTIVATION\_CODE\_EXPIRED | Activation process: The activation code expired. |
| LOCKED\_CERTIFICATE | KSMLOCKED\_CERTIFICATE | User locked on ssms server |
| LOCKED\_USER | KSMLOCKED\_USER | User locked on ssms server |
| PROPERTY\_NOT\_EXISTS | KSMPROPERTY\_NOT\_EXISTS | Requested property is not stored on SSMS or local DataBase. |
| INVALID\_KEY\_LENGTH | KSMINVALID\_KEY\_LENGTH | Property key is too long. |
| NOT\_UNIQUE | KSMNOT\_UNIQUE | Sent property string is not unique for this user. |
| TEXT\_TOO\_LONG | KSMTEXT\_TOO\_LONG | Sent property string is too long. |
| INVALID\_STATE | KSMINVALID\_STATE | The MasterController is in a state where it can't proceed the corresponding event. |
| INVALID\_PARAMETER | KSMINVALID\_PARAMETER | One of the parameters of the invoked event has an invalid format |
| INVALID\_USER\_ID | KSMINVALID\_USER\_ID | The given userID is invalid (e.g. no user credentials are available) |
| USER\_ID\_ALREADY\_EXISTS | KSMUSER\_ID\_ALREADY\_EXISTS | User credentials already exists for the given userID at the user credential path |
| REGISTER\_APP | KSMREGISTER\_APP | The app isn't registered at SSMS |
| MISMATCHED\_USER | KSMMISMATCHED\_USER | The certificate doesn't match to the user (e.g. typing error for the userID) |
| NEGATIVE | KSMNEGATIVE | A negative status has been occured usually this comes with an additional errorCode and subSystem |
| READ\_ONLY | KSMREAD\_ONLY | Requested property is a read only property |
| TEMPORARY\_LOCKED | KSMTEMPORARY\_LOCKED | Logon process: The user ID is temporary locked by entering wrong PINs. |
| NOT\_SUSPENDED | KSMNOT\_SUSPENDED | Resume has been invoked although MasterController had not been suspended before |
| INVALID\_PASSWORD | KSMINVALID\_PASSWORD | Invalid password for the keystorage was provided |
| PASSWORD\_BLOCKED | KSMPASSWORD\_BLOCKED | Password for the keytorage is blocked |
| ATC\_EXPIRES\_SOON | KSMATC\_EXPIRES\_SOON | The ATC used for the OfflineFunctions will soon expire |
| ATC\_EXPIRED | KSMATC\_EXPIRED | The ATC used for the OfflineFunctions is expired |
| NOT\_REACHABLE | KSMNOT\_REACHABLE | Operation could not be completed, because connection to SSMS was lost |
| PIN\_BLOCKED | KSMPIN\_BLOCKED | The PIN is blocked |
| ACCESS\_DENIED | KSMACCESS\_DENIED | The requested property cannot be accessed by the App |
| PROPERTY\_EXISTS | KSMPROPERTY\_EXISTS | The requested property exists |
| TENANT\_ID\_ALREADY\_SET | KSMTENANT\_ID\_ALREADY\_SET | If the Tenant ID has already been set in the sdk config, it is not allowed to set it via doActivation. If a user still tries to set it this status code is returned with onActivationEnd \*/ |
| UNINITIALIZED | KSMUNINITIALIZED | The underlaying module necessary to execute the invoked event is uninitialised |
| FAILED | KSMFAILED | The execution of the invoked event failed. Usually this cannot be fixed from App side and a Restart is necessary |
| LOGIN\_REQUIRED | KSMLOGIN\_REQUIRED | The execution of tehinvoked event requires an online login |
| ALREADY\_INITIALIZED | KSMALREADY\_INITIALIZED | The underlaying module necessary to execute the invoked event is already initialised |
| GLOBAL\_PIN\_SET | KSMGLOBALPINSET | Activation was successful and the global PIN for the given user had been set |
| UPDATE\_AVAILABLE\_GLOBAL\_PIN\_SET | KSMUPDATE\_AVAILABLE\_GLOBAL\_PIN\_SET | An update is available for the App but the global PIN had been set |
| INVALID\_TOKEN | KSMINVALID\_TOKEN | An invalid token had been provided for a transaction |
| OFFLINE\_NOT\_ACTIVATED | KSMOFFLINE\_NOT\_ACTIVATED | The invoked event needs offline capabilities which had not been activated before |
| NOT\_SUPPORTED | KSMNOT\_SUPPORTED | The invoked event is not supported with teh given configuration |
| CONNECTION\_LOST | KSMCONNECTION\_LOST | The invoked event requires vaid IDP Token data which are not available |
| NO\_TOKEN\_DATA\_AVAILABLE | KSMNO\_TOKEN\_DATA\_AVAILABLE | The invoked event requires vaid IDP Token data but available data is expired |
| TOKEN\_DATA\_IS\_OUTDATED | KSMTOKEN\_DATA\_IS\_OUTDATED | An error occured while trying to acquire fresh IDP tokens from IDP |
| CANNOT\_ACQUIRE\_TOKEN\_DATA | KSMCANNOT\_ACQUIRE\_TOKEN\_DATA | An error occured while trying to acquire an authorization code from IDP |
| CANNOT\_ACQUIRE\_AUTHORIZATION\_CODE | KSMCANNOT\_ACQUIRE\_AUTHORIZATION\_CODE | An error occured while trying to acquire fresh IDP tokens from IDP via the an acquired authorisation code |
| CANNOT\_ACQUIRE\_ACCESS\_TOKEN\_FOR\_AUTHORIZATION\_CODE | KSMCANNOT\_ACQUIRE\_ACCESS\_TOKEN\_FOR\_AUTHORIZATIN\_CODE | The operation cancelled on server side, e.g. a transaction. |
| SERVER\_CANCEL | KSMSERVER\_CANCEL | The underlying operation could not be completed due to connection issues. Used in DisplayConfirmationResult and TransactionEnd events. |

### SupportedFeatures

A bitset used to inform about the supported features.

#### Objective-C - KSMSupportedFeatures

#### Java - SupportedFeatures

Values

| Java | Objective-C | Description |
| --- | --- | --- |
| SECURE\_ELEMENT bit is set | KSMSecureElement | Indicates that Secure Element is supported on the device |
