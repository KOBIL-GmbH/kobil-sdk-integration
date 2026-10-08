> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/ast_event_list> on 2026-09-28. Converted to Markdown; wording unchanged.

# AST Events

### **Activation**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| StartActivationUserIdAndCodeOnly | MC->UI | none | none | default | yes |  | SSMS |
| ProvideActivationCodeAndUserId | UI->MC | none | *UserIdentifier* **userIdentifier**, *string* **activationCode** | default | no |  | SSMS |
| ProvideTokenAndUserId | UI->MC | none | *UserIdentifier* **userIdentifier**, *string* **token**, *bool* **autoLogin** | default | no |  | SSMS |
| StartActivationSetPIN | MC->UI | none | none | default | yes |  | SSMS |
| ProvideSetPIN | UI->MC | none | *string* **PIN**, *bool* **autoLogin** | default | no |  | SSMS |
| Activate | UI->MC | LoginResult if auto-login is requested. Otherwise, ActivationResult | *UserIdentifier* **userIdentifier**, *string* **activationCode**, *string* **PIN**, *bool* **autoLogin** | default | no |  | SSMS |
| ActivateWithToken | UI->MC | LoginResult if auto-login is requested. Otherwise, ActivationResult | *UserIdentifier* **userIdentifier**, *string* **token**, *bool* **autoLogin** | default | no |  | SSMS |
| ActivationResult | MC->UI | none | *enum<StatusType>* **status** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed, kUpdateAvailable, kUpdateNecessary, kAppRegistered, kInvalidActivationCode, kUnknownVersion, kUnknownClientType, kWrongCredentials, kActivationCodeExpired, kLockedUser, kUserIdAlreadyExists, kMismatchedUser, kNotReachable ,kTenantIdAlreadySet, kGlobalPinSet, kUpdateAvailableGlobalPinSet | SSMS |

### **Login**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| StartLogin | MC->UI | none | *array<UserIdentifier>* **userIdentifiers** | default | yes |  | SSMS |
| Login | UI->MC | none | *UserIdentifier* **userIdentifier**, *string* **PIN** | default | no |  | SSMS |
| LoginWithToken | UI->MC | none | *UserIdentifier* **userIdentifier**, *enum<AuthenticationMode>* **authMode** | default | no |  | SSMS |
| LoginWithToken | UI->MC | none | *UserIdentifier* **userIdentifier**, *enum<AuthenticationMode>* **authMode**, *string* **iamAccessToken**, *string* **authCode** | default | no |  | SSMS |
| LoginResult | MC->UI | none | *enum<StatusType>* **status**, *string* **otp**, *UserIdentifier* **userIdentifier**, *int* **retryCounter**, *int* **retryDelay** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed, kUpdateAvailable, kUpdateNecessary, kUnknownVersion, kUnknownClientType, kWrongCredentials, kUnknownCertificate, kLockedCertificate, kLockedUser, kRegisterApp, kTemporaryLocked, kNotReachable, kNoTokenDataAvailable, kCannotAcquireTokenData | SSMS |

### **Offline Login**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OfflineLogin | UI->MC | OfflineLoginResult | none | default | no |  |  |
| OfflineLogin | UI->MC | OfflineLoginResult | *UserIdentifier* **userIdentifier** | default | no |  |  |
| OfflineLoginResult | MC->UI | none | enum<StatusType> **status** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed, kInvalidUserId, kTemporaryLocked, kPinBlocked, kLoginRequired, kOfflineNotActivated, kNoTokenDataAvailable, kCannotAcquireTokenData |  |

### **Reactivation**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| StartReactivation | UI->MC | none | none | default | no |  | SSMS |
| StartReactivationUserIdAndCodeOnly | MC->UI | none | none | default | yes |  | SSMS |
| ProvideActivationCodeAndUserIdForReactivation | UI->MC | none | *UserIdentifier* **userIdentifier**, *string* **activationCode** | default | no |  | SSMS |
| StartReactivationSetPIN | MC->UI | none | none | default | yes |  | SSMS |
| ProvideSetPINForReactivation | UI->MC | none | *string* **PIN**, *bool* **autoLogin** | default | no |  | SSMS |
| Reactivation | UI->MC | LoginResult if auto-login is requested. Otherwise, ReactivationResult | *UserIdentifier* **userIdentifier**, *string* **activationCode**, *string* **PIN**, *bool* **autoLogin** | default | no |  | SSMS |
| ReactivationResult | MC->UI | none | *enum<StatusType>* **status** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed, kUpdateAvailable, kUpdateNecessary, kUnknownVersion, kUnknownClientType, kWrongCredentials, kUnknownCertificate, kActivationCodeExpired, kLockedCertificate, kLockedUser, kNotReachable | SSMS |

### **Add User**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| StartAddUser | UI->MC | none | none | default | no |  | SSMS |
| StartAddUserUserIdAndCodeOnly | MC->UI | none | none | default | yes |  | SSMS |
| ProvideActivationCodeAndUserIdForAddUser | UI->MC | none | *UserIdentifier* **userIdentifier**, *string* **activationCode** | default | no |  | SSMS |
| ProvideTokenAndUserIdForAddUser | UI->MC | none | *UserIdentifier* **userIdentifier**, *string* **token**, *bool* **autoLogin** | default | no |  | SSMS |
| StartAddUserSetPIN | MC->UI | none | none | default | yes |  | SSMS |
| ProvideSetPINForAddUser | UI->MC | none | *string* **PIN**, *bool* **autoLogin** | default | no |  | SSMS |
| AddUser | UI->MC | LoginResult if auto-login is requested. Otherwise, AddUserResult | *UserIdentifier* **userIdentifier**, *string* **activationCode**, *string* **PIN**, *bool* **autoLogin** | default | no |  | SSMS |
| AddUserWithToken | UI->MC | LoginResult if auto-login is requested. Otherwise, AddUserResult | *UserIdentifier* **userIdentifier**, *string* **token**, *bool* **autoLogin** | default | no |  | SSMS |
| AddUserResult | MC->UI | none | *enum<StatusType>* **status** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed, kUpdateAvailable, kUpdateNecessary, kInvalidActivationCode, kUnknownVersion, kUnknownClientType, kWrongCredentials, kActivationCodeExpired, kLockedUser, kUserIdAlreadyExists, kMismatchedUser, kNotReachable, kTenantIdAlreadySet, kGlobalPinSet, kUpdateAvailableGlobalPinSet | SSMS |

### **Delete User**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| StartDeleteUser | UI->MC | none | none | default | no |  |  |
| StartSetUserIdToDelete | MC->UI | none | none | default | yes |  |  |
| ProvideSetUserIdToDelete | UI->MC | none | *UserIdentifier* **userIdentifier** | default | no |  |  |
| DeleteUser | UI->MC | DeleteUserResult | *UserIdentifier* **userIdentifier** | default | no |  |  |
| DeleteUserResult | MC->UI | none | *enum<StatusType>* **status**, *enum<SdkState>* **sdkState**, *array<UserIdentifier>* **userList** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed |  |

### **Transaction**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TriggerBanner | MC->UI | none | *enum<BannerType>* **bannerType**, *string* **payload**, *int* **timer**, *bool* **execute** | default | no |  |  |
| StartTransaction | UI->MC | none | none | default | no |  |  |
| TransactionPINRequiredRequest | MC->UI | none | *int* **timerValue** | default | yes |  |  |
| ProvidePIN | UI->MC | none | *enum<ConfirmationType>* **confirmationType**, *string* **PIN** | default | no |  |  |
| ProvidePINResult | MC->UI | none | *enum<StatusType>* **status**, *int* **retryCounter** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed, kUserCancel, kUserConfirmationTimeout, kInvalidPin, kTemporaryLocked, kNotReachable |  |
| DisplayConfirmationRequest | MC->UI | none | *int* **timerValue**, *string* **transactionInformation** | default | yes |  |  |
| DisplayConfirmation | UI->MC | none | *enum<ConfirmationType>* **confirmationType**, *string* | default | no |  |  |
| DisplayConfirmationResult | MC->UI | none | *enum<StatusType>* **status** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed, kUserCancel, kUserConfirmationTimeout, kNotReachable, kServerCancel |  |
| TransactionTokenRequiredRequest | MC->UI | none | int *timerInformation* | default | yes |  |  |
| ProvideToken | UI->MC | none | enum<ConfirmationType> \*confirmationType, \*string *token* | default | no |  |  |
| ProvideTokenResult | MC->UI | none | enum<StatusType> *status* | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed, kUserCancel, kUserConfirmationTimeout, kNotReachable, kInvalidToken, kServerCancel |  |
| TransactionEnd | MC->UI | none | *enum<StatusType>* **status** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kFailed, kUserConfirmationTimeout, kNotReachable, kServerCancel |  |

### **Get Property**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GetProperty | UI->MC | GetPropertyResult | *string* **key**, *enum<PropertyOwnerType>* **property\_owner** | default | no |  |  |
| GetPropertyResult | MC->UI | none | *enum<StatusType>* **status**, *uint32*, *byteArray* **data**, *enum<PropertyType>* **property\_type**, *uint32* **property\_ttl**, *uint32* **property\_flags** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed, kPropertyNotExists, kInvalidKeyLength, kNotReachable, kAccessDenied, kUninitialized |  |

### **Set Property**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SetProperty | UI->MC | SetPropertyResult | *string* **key**, *byteArray* **data**, *enum<PropertyType>* **property\_type**, *enum<PropertyOwnerType>* **property\_owner**, *uint32* **property\_ttl**, *uint32* **property\_flags** | default | no |  |  |
| SetPropertyResult | MC->UI | none | *enum<StatusType>* **status**, *uint32* **set\_property\_result\_sub\_system**, *uint32* **set\_property\_result\_error\_code** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed, kNotReachable, kUninitialized, kReadOnly, kInvalidKeyLength, kNotUnique, kTextTooLong, kNegative, kAccessDenied |  |

### **Push Token**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SetPushToken | UI->MC | SetPushTokenResult | *string* **pushToken** | default | no |  |  |
| SetPushTokenResult | MC->UI | none | *enum<StatusType>* **status** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed, kNotReachable, kUninitialized |  |

### **Change PIN**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| StartChangePIN | UI->MC | none | none | default | no |  |  |
| StartSetNewPIN | MC->UI | none | none | default | yes |  |  |
| ProvideSetNewPIN | UI->MC | none | *string* **currentPIN**, *string* **newPIN** | default | no |  |  |
| ChangePINResult | MC->UI | none | *enum<StatusType>* **status**, *int* **retryCounter** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed, kUserCancel, kInvalidPin, kInvalidNewPinFormat, kTemporaryLocked, kNotReachable |  |

### **Display Message**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| StartDisplayMessage | UI->MC | none | none | default | no |  |  |
| DisplayMessage | MC->UI | none | *string* **messageInformation** | default | no |  |  |

### **Update**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GetUpdateInformation | UI->MC | UpdateInformation | none | default | no |  | SSMS |
| UpdateInformation | MC->UI | none | *enum<StatusType>* **status**, *string* **updateUrl**, *string* **infoUrl**, *enum<UpdateType>* **updateType**, *byteArray* **updateDigest**, *uint32* **expiresInSeconds** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kFailed, kUpdateAvailable, kUpdateNecessary |  |
| Update | UI->MC | none | none | default | no |  | SSMS |
| UpdateResult | MC->UI | none | *enum<UpdateStatus>* **updateStatus** | default | no |  |  |
| OpenInfoUrl | UI->MC | OpenInfoUrlResult | none | default | no |  | SSMS |
| OpenInfoUrlResult | MC->UI | none | *enum<StatusType>* **status** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kFailed |  |
| ExecuteUpdate | UI->MC | none | none | default | no |  | SSMS |
| ExecuteUpdateResult | MC->UI | none | *enum<UpdateStatus>* **updateStatus** | default | no |  |  |

### **Anonymous User**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CreateAnonymousUser | UI->MC | CreateAnonymousUserResult | *string* **tenantId** | default | yes |  | SSMS |
| CreateAnonymousUserResult | MC->UI | none | *string* **userId**, *string* **tenantId**, *string* **activationCode** | default | no |  |  |

### **Device Name**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SetDeviceName | UI->MC | SetDeviceNameResult | *string* **deviceName** | default | no |  |  |
| SetDeviceNameResult | MC->UI | none | *enum<StatusType>* **status** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed, kNotReachable, kUninitialized |  |

### **Request Token**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RequestToken | UI->MC | RequestTokenResult | *string* **audience** | default | no |  | SSMS |
| RequestTokenResult | MC->UI | none | *enum<StatusType>* **status**, *string* **token** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed, kNotReachable, kUninitialized |  |

### **Device Information**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GetDeviceInformation | UI->MC | GetDeviceInformationResult | *UserIdentifier* **userIdentifier** | default | no |  | SSMS |
| GetDeviceInformationResult | MC->UI | none | *string* **deviceId**, *string* **deviceName** | default | no |  |  |

### **AST Client Management**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GetAstClientData | UI->MC | GetAstClientDataResult | *string* **tenantId** | default | no |  | Maverick |
| GetAstClientDataResult | MC->UI | none | enum<StatusType> **status**, *string* **clientData**, *string* **astClientId**, *string* **codeChallenge**, *string* **codeChallengeMethod** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kFailed |  |
| SetAuthorisationCode | UI->MC | SetAuthorisationCodeResult | *string* **tenantId**, *enum<AuthenticationMode>* **authMode**, *string* **authCode**, *string* **clientId** | default | no |  | Maverick, Mobile |
| SetAuthorisationCode | UI->MC | SetAuthorisationCodeResult | *string* **tenantId**, *string* **authCode**, *string* **clientId** | default | no |  | Maverick, Desktop |
| SetAuthorisationCodeResult | MC->UI | none | enum<StatusType> **status** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kFailed, kCannotAcquireTokenData |  |
| EnrollAnonymousUser | UI->MC | StatusResult | *string* **tenantId**, *enum<AuthenticationMode>* **authMode**, *string* **clientId** | default | no |  | Maverick |

### **Verify Push Content**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| VerifyPushContent | UI->MC | VerifyPushContentResult | *UserIdentifier* **userIdentifier**, *byteArray* **content** | default | no |  | SSMS |
| VerifyPushContentResult | MC->UI | none | *enum<StatusType>* **status**, *byteArray* **content** | default | no |  |  |

### **Offline Functions**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GenerateOtp | UI->MC | GenerateOtpResult | *byteArray* **optionalData**, *UserIdentifier* **userIdentifier**, *string* **pin** | default | no |  | SSMS |
| GenerateOtpResult | MC->UI | none | *enum<StatusType>* **status**, *string* **otp**, *int* **rertyCounter**, *int* **rertyDelay** | default | no |  |  |
| GenerateSecureSequence | UI->MC | GenerateSecureSequenceResult | *byteArray* **optionalData**, *UserIdentifier* **userIdentifier**, *string* **pin** | default | no |  | SSMS |
| GenerateSecureSequenceResult | MC->UI | none | *enum<StatusType>* **status**, *byteArray* **secureSequence**, *int* **rertyCounter**, *int* **rertyDelay** | default | no |  |  |
| GetResynchronizationData | UI->MC | GetResynchronizationDataResult | *UserIdentifier* **userIdentifier**, *string* **pin** | default | no |  | SSMS |
| GetResynchronizationDataResult | MC->UI | none | *enum<StatusType>* **status**, *string* **otp**, *uint16* atc, *int* **rertyCounter**, *int* **rertyDelay** | default | no |  |  |
| EnableAtcResynchronizationDuringNextLogin | UI->MC | none | none | default | none |  | SSMS |

### **Other Events**

| Event Name | Direction | Result Event | Parameter | Priority | Resend by getStateEvent | Possible Enum Values | Environment Restriction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Acknowledge | MC->UI | none | none | default | yes |  |  |
| Cancel | UI->MC | none | none | default | no |  |  |
| Busy | MC->UI | none | none | default | yes |  |  |
| Idle | MC->UI | none | none | default | yes |  |  |
| ServerConnection | MC->UI | none | *enum<ConnectionState>* **connectionState** | default | no |  |  |
| DecryptDataEvent | UI->MC | DecryptDataResultEvent | *byteArray* **encryptedData** | default | no |  |  |
| DecryptDataResultEvent | MC->UI | none | *enum<StatusType>*, *byteArray* **decryptedData**, *uint64* **opensslErrorCode** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed |  |
| GetIAMAccessToken | UI->MC | GetIAMAccessTokenResult | *string* **audience**, *string* **scope**, *string* **client\_id** | default | no |  | SSMS |
| GetIAMAccessTokenResult | MC->UI | none | enum<StatusType> **status**, *string* **access\_token\_identifier** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kFailed, kCannotAcquireTokenData, kCannotAcquireAccessTokenForAuthorizationCode |  |
| GetIamAuthorizationCode | UI->MC | GetIamAuthorizationCodeResult | *string* **audience**, *string* **scope**, *string* **client\_id** | default | no |  | SSMS |
| GetIamAuthorizationCodeResult | MC->UI | none | enum<StatusType> **status**, *string* **auth\_code\_identifier** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kFailed, kCannotAcquireTokenData |  |
| LoginTokenClaimsAvailable | MC->UI | none | *map<string, string>* **claims** | default | no |  |  |
| GetIamAccessTokenClaims | UI->MC | GetIamAccessTokenClaimsResult | none | default | no |  |  |
| GetIamAccessTokenClaimsResult | MC->UI | none | enum<StatusType> **status**, *map<string, string>* **claims** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kFailed, kNoTokenDataAvailable |  |
| ExchangeIamToken | UI->MC | ExchangeIamTokenResult | *string* **audience**, *bool* **forceUpdate** | default | no |  | Maverick |
| ExchangeIamTokenResult | MC->UI | none | *string* **token** | default | no |  |  |
| SetLocales | UI->MC | StatusResult | *array<string>* **locales** | default | no |  | Maverick |
| ProvideNonce | UI->MC | StatusResult | *string* **nonce**, *string* **action** | default | no |  | Maverick |
| ClearIamTokenCache | UI->MC | ClearIamTokenCacheResult | *UserIdentifier* **userIdentifier**, *enum<ClearBehavior>* **clearBehavior** | default | no |  |  |
| ClearIamTokenCacheResult | MC->UI | none | none | default | no |  |  |
