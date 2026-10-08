> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/error-handling/status_type> on 2026-09-28. Converted to Markdown; wording unchanged.

# Status Type Evaluation

If something goes wrong then the result event will indicate that the operation was successful or not

| enum value | Description |
| --- | --- |
| kOk | The process was completed successfully. |
| kUpdateAvailable | An update of the app is available. (Info only) |
| kAppRegistered | Will be sent from SSMS to the app when the app registration was successful. (Info only). The App must restart the SDK itself. |
| kUserCancel | The user cancelled a process, e.g. a transaction. |
| kUserConfirmationTimeout | The process was cancelled by a timeout. |
| kInvalidPin | The user entered a wrong pin. |
| kUnknownVersion | Activation and Logon process: The app has a wrong version. |
| kUnknownClientType | Activation and Logon process: The app has a wrong client type. |
| kUpdateNecessary | This version of the app was replace by a newer one and the user must update. |
| kWrongCredentials | Activation and Logon process: The user ID, activation code or the PIN are incorrect. |
| kUnknownCertificate | User removed on the ssms server |
| kInternalError | An internal error occurred during the process, usually a Runtimer Error |
| kActivationCodeExpired | Activation process: The activation code expired. |
| kLockedCertificate | User locked on ssms server |
| kLockedUser | User locked on ssms server |
| kPropertyNotExists | Requested property is not stored on SSMS or local DataBase. |
| kInvalidKeyLength | Property key is too long. |
| kNotUnique | Sent property string is not unique for this user. |
| kTextTooLong | Sent property string is too long. |
| kInvalidState | The MasterController is in a state where it cannot proceed the corresponding event. |
| kInvalidParameter | One of the parameters of the invoked event has an invalid format |
| kInvalidUserId | The given userID is invalid (e.g. no user credentials are available) |
| kUserIdAlreadyExists | User credentials already exists for the given userID at the user credential path |
| kRegisterApp | The app is not registered at SSMS |
| kMismatchedUser | The certificate does not match to the user (e.g. typing error for the userID) |
| kNegative | A negative status has been occured usually this comes with an additional errorCode and subSystem |
| kReadOnly | Requested property is a read only property |
| kTemporaryLocked | Logon process: The user ID is temporary locked by entering wrong PINs. |
| kNotSuspended | Resume has been invoked although MasterController had not been suspended before |
| kInvalidPassword | Invalid password for the keystorage was provided |
| kPasswordBlocked | Password for the keytorage is blocked |
| kAtcExpiresSoon | The ATC used for the OfflineFunctions will soon expire |
| kAtcExpired | The ATC used for the OfflineFunctions is expired |
| kNotReachable | Operation could not be completed, because connection to SSMS was lost |
| kPinBlocked | The PIN is blocked |
| kAccessDenied | The requested property cannot be accessed by the App |
| kPropertyExists | The requested property exists |
| kTenantIdAlreadySet | If the Tenant ID has already been set in the sdk config, it is not allowed to set it via doActivation. If a user still tries to set it this status code is returned with onActivationEnd \*/ |
| kUninitialized | The underlaying module necessary to execute the invoked event is uninitialised |
| kFailed | The execution of the invoked event failed. Usually this cannot be fixed from App side and a Restart is necessary |
| kLoginRequired | The execution of tehinvoked event requires an online login |
| kAlreadyInitialized | The underlaying module necessary to execute the invoked event is already initialised |
| kGlobalPinSet | Activation was successful and the global PIN for the given user had been set |
| kUpdateAvailableGlobalPinSet | An update is available for the App but the global PIN had been set |
| kInvalidToken | An invalid token had been provided for a transaction |
| kOfflineNotActivated | The invoked event needs offline capabilities which had not been activated before |
| kNotSupported | The invoked event is not supported with teh given configuration |
| kNoTokenDataAvailable | The invoked event requires vaid IDP Token data which are not available |
| kTokenDataIsOutdated | The invoked event requires vaid IDP Token data but available data is expired |
| kCannotAcquireTokenData | An error occured while trying to acquire fresh IDP tokens from IDP |
| kCannotAcquireAuthorizationCode | An error occured while trying to acquire an authorization code from IDP |
| kCannotAcquireAccessTokenForAuthorizationCode | An error occured while trying to acquire fresh IDP tokens from IDP via the an acquired authorization code |
| kServerCancel | The operation cancelled on server side, e.g. a transaction. |
| kConnectionLost | The underlying operation could not be completed due to connection issues. Used in DisplayConfirmationResult and TransactionEnd events. |
