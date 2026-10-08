> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/base_event> on 2026-09-28. Converted to Markdown; wording unchanged.

# Base Events

| **Event Name** | **Direction** | **Result Event** | **Parameter** | **Priority** | **Resend by getStateEvent** | **Possible Enum Values** |
| --- | --- | --- | --- | --- | --- | --- |
| Start | UI->MC | StartResult | *string* **locale**, *byteArray* **version**, *string* **appName**, *string* **mcConfig**, *byteArray* **certificateChain**, *byteArray* **sdkConfig**, *ConfigurationData* **configurationData**, *byteArray* **iamCertificateChain**, *byteArray* **smartScreenCertificateChain** | default | no |  |
| Start | UI->MC | StartResult | *string* **locale**, *byteArray* **version**, *string* **appName** | default | no |  |
| Start | UI->MC | StartResult | *string* **locale**, *byteArray* **version**, *string* **appName**, *ConfigurationData* **configurationData** | default | no |  |
| StartResult | MC->UI | none | *enum<StatusType>* **status**, *enum<SdkState>* **sdkState**, *array<UserIdentifier>* **userList**, *bitmap<SupportedFeatures>* **supportedFeatures** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed |
| Restart | UI->MC | RestartResult | *string* **locale**, *byteArray* **version**, *string* **appName**, *string* **mcConfig**, *byteArray* **certificateChain**, *byteArray* **sdkConfig**, *byteArray* **iamCertificateChain**, *byteArray* **smartScreenCertificateChain** | default | no |  |
| Restart | UI->MC | RestartResult | *string* **locale**, *byteArray* **version**, *string* **appName** | default | no |  |
| RestartResult | MC->UI | none | *enum<StatusType>* **status**, *enum<SdkState>* **sdkState**, *array<UserIdentifier>* **userList**, *bitmap<SupportedFeatures>* **supportedFeatures** | default | no | *enum<StatusType>* - kOk, kInternalError, kInvalidState, kInvalidParameter, kFailed |
| GetStateEvent | UI->MC | none | none | default | no |  |
| GetInformation | UI->MC | GetInformationResult | none | default | no |  |
| GetInformationResult | MC->UI | none | *string* **sdkVersion**, *string* **serialNumber**, *string* **locale**, *byteArray* **version**, *string* **appName**, *byteArray* **appConfig**, *string* **tokenIssuerServiceUrl**, *string* **addressBookServerUrl**, *string* **messageRouterUrl**, *UserIdentifier* **loggedInUserIdentifier**, *IamConfigurationData* **iamConfigurationData**, *byteArray* **encryptedCert**, *byteArray* **signedCert**, *byteArray* **authCert** | default | no |  |
| Warning | MC->UI | none | *enum<ErrorType>* **errorType**, *string* **errorDescription**, *uint32* **errorCode** | default | no |  |
| RuntimeError | MC->UI | none | *enum<ErrorType>* **errorType**, *string* **errorDescription**, *uint32* **errorCode** | default | no |  |
| FatalError | MC->UI | none | *enum<ErrorType>* **errorType**, *string* **errorDescription**, *uint32* **errorCode** | default | no |  |
| CreateHttpCommonRequest | UI->MC | CreateHttpRequestResult | *string* **fullUrl**, *enum<HttpMethod>* **method**, *string* **content**, *string* **contentType**, *string* **userName**, *string* **password**, *byteArray* **certificateChain**, *map<string, string>* **httpHeaders**, *string* **cookieIdentifier**, *string* **accessTokenIdentifier**, *bool* **followRedirect** | default | no |  |
| CreateHttpCommonRequestResult | MC->UI | none | *enum<Status>* **status**, *int* **httpStatus**, *byteArray* **responseBody**, *map<string, string>* **responseHeaders**, *string* **cookieIdentifier**, *string* **accessTokenIdentifier** | default | no |  |
| EnableOpenCensusTracing | UI->MC | none | *bool* **enable** | default | no |  |
| Configuration | UI->MC | none | *string* **exporterUrl**, *string* **userName**, *string* **password**, *byteArray* **serverCertificate** | default | no |  |
| StartMigration | MC->UI | none | none | default | no |  |
| MigrationFinished | MC->UI | none | none | default | no |  |
| GetLoggedInUser | UI->MC | GetLoggedInUserResult | none | default | no |  |
| GetLoggedInUserResult | MC->UI | none | *UserIdentifier* **loggedInUserIdentifier** | default | no |  |
| StatusResult | MC->UI | none | *enum<StatusType>* **status** | default | no | *enum<StatusType>* - kOk, kNotSupported, kInvalidParameter, kFailed |
| RequestLicenses | UI->MC | RequestLicensesResult | none | default | no |  |
| RequestLicensesResult | MC->UI | none | none | default | no |  |
