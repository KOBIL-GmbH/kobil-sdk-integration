> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/individual_events> on 2026-09-28. Converted to Markdown; wording unchanged.

# Individual Events

### StartEvent

Initializes and configures the MasterController SDK. It should be invoked before calling most other events. Please check the status and state in the returned StartResultEvent to ensure the SDK has been successfully initialized.

#### Objective-C - KSMStartEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| locale | NSString\* | The default locale of the Application. For example, this will affect messages returned to the Application. The encoding of this string is ASCII and it must be 2 bytes long. |
| version | [KSMVersion\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#AppVersion) | The app version. |
| appName | NSString\* | The app name. To distinguish the Applications, an Application must have a name. Applications with different names may have the same version numbers. Encoding of this string is UTF-8 and it has a maximum length of 32 bytes. |
| serverBackend | NSString\* | This parameter is optional and should be used when migrating the server backend. Possible values: "maverick", "ssms". It determines the real server backend implementation used by the SDK. If set, the SDK will explicitly use it as a server backend, overriding what is provided in the MC config. The SDK remembers the chosen server backend and implicitly uses it on restart if the `serverBackend` is not explicitly specified in the [RestartEvent](#RestartEvent). |

#### Objective-C - KSMStartEventEx

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| ssmsAppConfiguration | [KSMSsmsAppConfiguration\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#BasicAppConfiguration) | Includes the SSMS app configuration (locale, app name and version). |
| mcConfig | NSString\* | MC configuration in JSON format. |
| certificateChain | NSData\* | SSL certificate chain in PEM format used to establish connections to SCP services. |
| configurationData | [KSMConfigurationData\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#ConfigurationData) | Additional configuration data, such as category, tag name, etc. |
| iamCertificateChain | NSData\* | SSL certificate chain in PEM format used to establish connections to the IDP service. |
| smartScreenCertificateChain | NSData\* | SSL certificate chain in PEM format used to establish connections to SmartScreen services. |
| serverBackend | NSString\* | This parameter is optional and should be used when migrating the server backend. Possible values: "maverick", "ssms". It determines the real server backend implementation used by the SDK. If set, the SDK will explicitly use it as a server backend, overriding what is provided in the MC config. The SDK remembers the chosen server backend and implicitly uses it on restart if the `serverBackend` is not explicitly specified in the [RestartEvent](#RestartEvent). The SDK remembers the chosen server backend and implicitly uses it on restart if the `serverBackend` is not explicitly specified in the [RestartEvent](#RestartEvent). |

#### Java - StartEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| locale | String | The default locale of the Application. For example, this will affect messages returned to the Application. The encoding of this string is ASCII and it must be 2 bytes long. |
| version | [AppVersion](shift-lite-idpsdk__mcsdk-api__composite_types.md#AppVersion) | The app version. |
| appName | String | The app name. To distinguish the Applications, an Application must have a name. Applications with different names may have the same version numbers. Encoding of this string is UTF-8 and it has a maximum length of 32 bytes. |
| mcConfig | String | MC configuration in JSON format. |
| certificateChain | String | SSL certificate chain in PEM format used to establish connections to SCP services |
| sdkConfig | byte[] | SDK configuration in XML format (for SSMS enviroment) or in JSON format (for Maverick enviroment). |
| configurationData | [ConfigurationData](shift-lite-idpsdk__mcsdk-api__composite_types.md#ConfigurationData) | Additional configuration data, such as category, tag name, etc. |
| iamCertificateChain | String | SSL certificate chain in PEM format used to establish connections to the IDP service. |
| smartScreenCertificateChain | String | SSL certificate chain in PEM format used to establish connections to SmartScreen services. |
| serverBackend | String | This parameter is optional and should be used when migrating the server backend. Possible values: "maverick", "ssms". It determines the real server backend implementation used by the SDK. If set, the SDK will explicitly use it as a server backend, overriding what is provided in the MC config. The SDK remembers the chosen server backend and implicitly uses it on restart if the `serverBackend` is not explicitly specified in the [RestartEvent](#RestartEvent). |

### StartResultEvent

Provides the status and state of the SDK after its initialization by the StartEvent.

#### Objective-C - KSMStartResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | BOOL | Set to true if an error occurred. |
| errorCode | long | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | long | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | NSString\* | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [KSMEventStatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. |
| sdkState | [KSMSdkState](shift-lite-idpsdk__mcsdk-api__enumerations.md#SdkState) | The current state of SDK. |
| userList | NSArray<[KsUserIdentifier\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#UserIdentifier)>\* | The list of activated users. |
| userDetailsList | NSArray<[KsUserDetails](shift-lite-idpsdk__mcsdk-api__composite_types.md#UserDetails)> | The list of activated user details. |
| supportedFeatures | NSUInteger | The supported features bitmap. Refer to [SupportedFeatures](shift-lite-idpsdk__mcsdk-api__enumerations.md#SupportedFeatures) to see the meaning of each bit. |

#### Java - StartResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | boolean | Set to true if an error occurred. |
| errorCode | int | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | int | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | String | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [StatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. |
| sdkState | [SdkState](shift-lite-idpsdk__mcsdk-api__enumerations.md#SdkState) | The current state of SDK. |
| userList | List<[UserIdentifier](shift-lite-idpsdk__mcsdk-api__composite_types.md#UserIdentifier)> | The list of activated users. |
| userDetailsList | List<[UserDetails](shift-lite-idpsdk__mcsdk-api__composite_types.md#UserDetails)> | The list of activated user details. |
| supportedFeatures | BitSet | The supported features bitmap. Refer to [SupportedFeatures](shift-lite-idpsdk__mcsdk-api__enumerations.md#SupportedFeatures) to see the meaning of each bit. |

### RestartEvent

Reinitializes and reconfigures the MasterController SDK. Please check the status and state in the returned RestartResultEvent to ensure the SDK has been successfully restarted.

#### Objective-C - KSMRestartEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| locale | NSString\* | The default locale of the Application. For example, this will affect messages returned to the Application. The encoding of this string is ASCII and it must be 2 bytes long. |
| version | [KSMVersion\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#AppVersion) | The app version. |
| appName | NSString\* | The app name. To distinguish the Applications, an Application must have a name. Applications with different names may have the same version numbers. Encoding of this string is UTF-8 and it has a maximum length of 32 bytes. |
| serverBackend | NSString\* | This parameter is optional and should be used when migrating the server backend. Possible values: "maverick", "ssms". It determines the real server backend implementation used by the SDK. If set, the SDK will explicitly use it as a server backend, overriding what is provided in the MC config. The SDK remembers the chosen server backend and implicitly uses it on the subsequent restart if the `serverBackend` is not explicitly specified in the [RestartEvent](#RestartEvent). |

#### Objective-C - KSMRestartEventEx

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| ssmsAppConfiguration | [KSMSsmsAppConfiguration\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#BasicAppConfiguration) | Includes the SSMS app configuration (locale, app name and version). |
| mcConfig | NSString\* | MC configuration in JSON format. |
| certificateChain | NSData\* | SSL certificate chain in PEM format used to establish connections to SCP services. |
| iamCertificateChain | NSData\* | SSL certificate chain in PEM format used to establish connections to the IDP service. |
| smartScreenCertificateChain | NSData\* | SSL certificate chain in PEM format used to establish connections to SmartScreen services. |
| serverBackend | NSString\* | This parameter is optional and should be used when migrating the server backend. Possible values: "maverick", "ssms". It determines the real server backend implementation used by the SDK. If set, the SDK will explicitly use it as a server backend, overriding what is provided in the MC config. The SDK remembers the chosen server backend and implicitly uses it on the subsequent restart if the `serverBackend` is not explicitly specified in the [RestartEvent](#RestartEvent). |

#### Java - RestartEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| locale | String | The default locale of the Application. For example, this will affect messages returned to the Application. The encoding of this string is ASCII and it must be 2 bytes long. |
| version | [AppVersion](shift-lite-idpsdk__mcsdk-api__composite_types.md#AppVersion) | The app version. |
| appName | String | The app name. To distinguish the Applications, an Application must have a name. Applications with different names may have the same version numbers. Encoding of this string is UTF-8 and it has a maximum length of 32 bytes. |
| mcConfig | String | MC configuration in JSON format. |
| certificateChain | String | SSL certificate chain in PEM format used to establish connections to SCP services |
| sdkConfig | byte[] | SDK configuration in XML format (for SSMS enviroment) or in JSON format (for Maverick enviroment). |
| iamCertificateChain | String | SSL certificate chain in PEM format used to establish connections to the IDP service. |
| smartScreenCertificateChain | String | SSL certificate chain in PEM format used to establish connections to SmartScreen services. |
| serverBackend | String | This parameter is optional and should be used when migrating the server backend. Possible values: "maverick", "ssms". It determines the real server backend implementation used by the SDK. If set, the SDK will explicitly use it as a server backend, overriding what is provided in the MC config. The SDK remembers the chosen server backend and implicitly uses it on the subsequent restart if the `serverBackend` is not explicitly specified in the [RestartEvent](#RestartEvent). |

### RestartResultEvent

Provides the status and state of the SDK after its initialization by the RestartEvent.

#### Objective-C - KSMRestartResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | BOOL | Set to true if an error occurred. |
| errorCode | long | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | long | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | NSString\* | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [KSMEventStatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. |
| sdkState | [KSMSdkState](shift-lite-idpsdk__mcsdk-api__enumerations.md#SdkState) | The current state of SDK. |
| userList | NSArray<[KsUserIdentifier\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#UserIdentifier)>\* | The list of activated users. |
| userDetailsList | NSArray<[KsUserDetails](shift-lite-idpsdk__mcsdk-api__composite_types.md#UserDetails)> | The list of activated user details. |
| supportedFeatures | NSUInteger | The supported features bitmap. Refer to [SupportedFeatures](shift-lite-idpsdk__mcsdk-api__enumerations.md#SupportedFeatures) to see the meaning of each bit. |

#### Java - RestartResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | boolean | Set to true if an error occurred. |
| errorCode | int | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | int | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | String | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [StatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. |
| sdkState | [SdkState](shift-lite-idpsdk__mcsdk-api__enumerations.md#SdkState) | The current state of SDK. |
| userList | List<[UserIdentifier](shift-lite-idpsdk__mcsdk-api__composite_types.md#UserIdentifier)> | The list of activated users. |
| userDetailsList | List<[UserDetails](shift-lite-idpsdk__mcsdk-api__composite_types.md#UserDetails)> | The list of activated user details. |
| supportedFeatures | BitSet | The supported features bitmap. Refer to [SupportedFeatures](shift-lite-idpsdk__mcsdk-api__enumerations.md#SupportedFeatures) to see the meaning of each bit. |

### GetSsmsUserListEvent

Returns the list of activated SSMS users. This event is needed for SSMS to Maverick migration use cases. Can be used only in the Maverick server backend environment. Can be invoked right after the [StartEvent](#StartEvent). Please check the returned GetSsmsUserListResultEvent to get the SSMS users.

#### Objective-C - KSMGetSsmsUserListEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| userCredentialPath | NSString\* | The path to the user credentials required to read the locally stored SSMS user list. This parameter is optional and should be specified if the path was previously customized. |

#### Java - GetSsmsUserListEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| userCredentialPath | String | The path to the user credentials required to read the locally stored SSMS user list. This parameter is optional and should be specified if the path was previously customized. |

### GetSsmsUserListResultEvent

Provides the result of the GetSsmsUserListEvent.

#### Objective-C - KSMGetSsmsUserListResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | BOOL | Set to true if an error occurred. |
| errorCode | long | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | long | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | NSString\* | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [KSMEventStatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. |
| userList | NSArray<[KsUserIdentifier\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#UserIdentifier)>\* | The SSMS user list. |

#### Java - GetSsmsUserListResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | boolean | Set to true if an error occurred. |
| errorCode | int | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | int | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | String | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [StatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. |
| userList | List<[UserIdentifier](shift-lite-idpsdk__mcsdk-api__composite_types.md#UserIdentifier)> | The SSMS user list. |

### EnrollAnonymousUserEvent

Initiates the enrollment process for an anonymous user. In anonymous enrollment, the IDP doesn't know any details about the user (such as a name or an email address), but it will be able to recognize and authenticate the user in subsequent flows. Can be used only in the Maverick server backend environment. Can be invoked right after the [StartEvent](#StartEvent). Please check the returned [StatusResultEvent](#StatusResultEvent) to find out the enrollment status.

#### Objective-C - KSMEnrollAnonymousUserEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| tenantId | NSString\* | The tenant id. The realm in terms of the IdP. |
| authenticationMode | [KSMAuthenticationMode](shift-lite-idpsdk__mcsdk-api__enumerations.md#AuthenticationMode) | The type of authentication used to protect and authenticate user credentials. |
| clientId | NSString\* | The IdP client id used in token requests. |

#### Java - EnrollAnonymousUserEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| tenantId | String | The tenant id. The realm in terms of the IdP. |
| authenticationMode | [AuthenticationMode](shift-lite-idpsdk__mcsdk-api__enumerations.md#AuthenticationMode) | The type of authentication used to protect and authenticate user credentials. |
| clientId | String | The IdP client id used in token requests. |

### EnableAuthenticationModeEvent

User can change authentication mode. Obtains a 1FA (offline token, signed JWT) using the access token from cache. Can be used only in the Maverick server backend environment. Can be invoked after the successful login by the [SetAuthorisationCodeEvent](#SetAuthorisationCodeEvent) or [OfflineLogin](#OfflineLoginEvent). Please check the returned [StatusResultEvent](#StatusResultEvent) to find out the enable authentication mode operation status.

#### Objective-C - EnableAuthenticationModeEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| authenticationMode | [AuthenticationMode](shift-lite-idpsdk__mcsdk-api__enumerations.md#AuthenticationMode) | The type of authentication used to protect and authenticate user credentials. |
| clientId | String | The IdP client id used in token requests. |

#### Java - EnableAuthenticationModeEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| authenticationMode | [AuthenticationMode](shift-lite-idpsdk__mcsdk-api__enumerations.md#AuthenticationMode) | The type of authentication used to protect and authenticate user credentials. |
| clientId | String | The IdP client id used in token requests. |

### IdpLoginRequiredEvent

Signals the App that authentication via IdP is required for the specified user to perform step-up to a stronger authentication method required, for example, for a transaction. Can be sent only in the Maverick server backend environment.

#### Objective-C - KSMIdpLoginRequiredEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| userIdentifier | [KsUserIdentifier\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#UserIdentifier) | The user to step-up. |

#### Java - IdpLoginRequiredEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| userIdentifier | [UserIdentifier](shift-lite-idpsdk__mcsdk-api__composite_types.md#UserIdentifier) | The user to step-up. |

### OfflineLoginEvent

Logs in the user using its access token. If the access token is expired, tries to refresh it using refresh token or the 1FA (offline token, signed JWT) obtained during the [SetAuthorisationCodeEvent](#SetAuthorisationCodeEvent). Can be used only in the Maverick server backend environment. Can be invoked for activated users right after the [StartEvent](#StartEvent). Please check the returned OfflineLoginResultEvent to find out the log-in status.

#### Objective-C - KSMOfflineLoginEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| userIdentifier | [KsUserIdentifier\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#UserIdentifier) | The user identifier for logging in. This parameter is optional. If not passed, the identifier of last succesfully logged-in user is used. |

#### Java - OfflineLoginEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| userIdentifier | [UserIdentifier](shift-lite-idpsdk__mcsdk-api__composite_types.md#UserIdentifier) | The user identifier for logging in. This parameter is optional. If not passed, the identifier of last succesfully logged-in user is used. |

### OfflineLoginResultEvent

Provides the result of the OfflineLoginEvent.

#### Objective-C - KSMOfflineLoginResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | BOOL | Set to true if an error occurred. |
| errorCode | long | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | long | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | NSString\* | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [KSMEventStatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. |

#### Java - OfflineLoginResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | boolean | Set to true if an error occurred. |
| errorCode | int | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | int | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | String | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [StatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. |

### GetAstClientDataEvent

Provides the AST client data required to get an authorization code that can then be exchanged for an access token during the [SetAuthorisationCodeEvent](#SetAuthorisationCodeEvent). Can be used only in the Maverick server backend environment. Can be invoked right after the [StartEvent](#StartEvent). Please check the returned GetAstClientDataResultEvent to get all data required for the user identification.

#### Objective-C - KSMGetAstClientDataEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| tenantId | NSString\* | The tenant id. The realm in terms of the IdP. |

#### Java - GetAstClientDataEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| tenantId | String | The tenant id. The realm in terms of the IdP. |

### GetAstClientDataResultEvent

Provides the result of the GetAstClientDataEvent.

#### Objective-C - KSMGetAstClientDataResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | BOOL | Set to true if an error occurred. |
| errorCode | long | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | long | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | NSString\* | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [KSMEventStatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. |
| clientData | NSString\* | The AST client data. It's encrypted and required for the user identification. |
| astClientId | NSString\* | The AST client id. It's zeros for a new user because the AST client ID is created on the server side during user registration. |
| codeChallange | NSString\* | The challenge derived from the code verifier that is sent in the authorization request, to be verified against later. Refer to the [Proof Key for Code Exchange by OAuth Public Clients](https://datatracker.ietf.org/doc/html/rfc7636#section-4.2) RFC for details. |
| codeChallangeMethod | NSString\* | The method that was used to derive code challenge. |

#### Java - GetAstClientDataResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | boolean | Set to true if an error occurred. |
| errorCode | int | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | int | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | String | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [StatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. |
| clientData | String | The AST client data. It's encrypted and required for the user identification. |
| astClientId | String | The AST client id. It's zeros for a new user because the AST client ID is created on the server side during user registration. |
| codeChallenge | String | The challenge derived from the code verifier that is sent in the authorization request, to be verified against later. Refer to the [Proof Key for Code Exchange by OAuth Public Clients](https://datatracker.ietf.org/doc/html/rfc7636#section-4.2) RFC for details. |
| codeChallengeMethod | String | The method that was used to derive code challenge. |

### SetAuthorisationCodeEvent

Completes user activation and logs the user in. Uses the given authorisation code to exchange for access/refresh tokens. Obtains a 1FA (offline token, signed JWT) using the access token that can be lately used for subsequent logins during [OfflineLoginEvent](#OfflineLoginEvent). Can be used only in the Maverick server backend environment. Can be invoked right after the [StartEvent](#StartEvent). Please check the returned SetAuthorisationCodeResultEvent to find out the log-in status.

#### Objective-C - KSMSetAuthorisationCodeEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| tenantId | NSString\* | The tenant id. The realm in terms of the IdP. |
| authenticationMode | [KSMAuthenticationMode](shift-lite-idpsdk__mcsdk-api__enumerations.md#AuthenticationMode) | The type of authentication used to protect and authenticate user credentials. |
| authorisationCode | NSString\* | The authorization code that is exchanged for access/refresh tokens by the IdP. |
| clientId | NSString\* | The IdP client id used in token requests. |

#### Java - SetAuthorisationCodeEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| tenantId | String | The tenant id. The realm in terms of the IdP. |
| authenticationMode | [AuthenticationMode](shift-lite-idpsdk__mcsdk-api__enumerations.md#AuthenticationMode) | The type of authentication used to protect and authenticate user credentials. |
| authorisationCode | String | The authorization code that is exchanged for access/refresh tokens by the IdP. |
| clientId | String | The IdP client id used in token requests. |

### SetAuthorisationCodeResultEvent

Provides the result of the SetAuthorisationCodeEvent.

#### Objective-C - KSMSetAuthorisationCodeResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | BOOL | Set to true if an error occurred. |
| errorCode | long | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | long | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | NSString\* | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [KSMEventStatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. |
| mkexKeyProtection | KSMMinimumKeyProtection | Determines the key protection used while performing mkex. Only relevant if the 'useMkex' mc\_config entry is true. |
| tmsKeyProtection | KSMMinimumKeyProtection | Determines the key protection used while signing transactions. |

#### Java - SetAuthorisationCodeResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | boolean | Set to true if an error occurred. |
| errorCode | int | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | int | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | String | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [StatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. |
| mkexKeyProtection | MinimumKeyProtection | Determines the key protection used while performing mkex. Only relevant if the 'useMkex' mc\_config entry is true. |
| tmsKeyProtection | MinimumKeyProtection | Determines the key protection used while signing transactions. |

### ExchangeIamTokenEvent

Triggers the exchange of the user's access token for an IAM token with a specified audience. Can be used only in the Maverick server backend environment. Can be invoked after the successful login by the [SetAuthorisationCodeEvent](#SetAuthorisationCodeEvent) or [OfflineLogin](#OfflineLoginEvent). Please check the returned ExchangeIamTokenResultEvent to get the token. Please make sure that the exchanged token will not contain the 'ast-client' role given the audience, if it does the result event will fail with error code 800000287.

Should work against both idp4 and idp5. Against idp4 the audience parameter will be used as client id as it was before. Against idp5 god tokens client id will be used as client id.

#### Objective-C - KSMExchangeIamTokenEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| audience | NSString\* | The intended audience (client) for the new token. Must be different from the client id used in SetAuthorisationCodeEvent. |
| forceUpdate | BOOL | This paramater is optional. By default, it's `false`. Set `true` to force the user's access token to be updated, even if it is still valid. |

#### Java - ExchangeIamTokenEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| audience | String | The intended audience (client) for the new token. Must be different from the client id used in SetAuthorisationCodeEvent. |
| forceUpdate | boolean | This paramater is optional. By default, it's `false`. Set `true` to force the user's access token to be updated, even if it is still valid. |

### ExchangeIamTokenResultEvent

Provides the result of the ExchangeIamTokenEvent.

#### Objective-C - KSMExchangeIamTokenResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | BOOL | Set to true if an error occurred. |
| errorCode | long | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | long | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | NSString\* | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [KSMEventStatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. |
| token | NSString\* | The newly acquired token for the specified audience. |

#### Java - ExchangeIamTokenResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | boolean | Set to true if an error occurred. |
| errorCode | int | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | int | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | String | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [StatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. |
| token | String | The newly acquired token for the specified audience. |

### GetInformationEvent

Returns various information with its result event GetInformationResultEvent. Can be invoked right after the StartEvent of each platform had been successfully invoked but depending on the state of the SDK the information returned in its result event may vary please see parameters of the result event for more details.

#### Objective-C - KSMGetInformationEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |

#### Java - GetInformationEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |

### GetInformationResultEvent

Provides various information asked from the SDK by the GetInformationEvent.

#### Objective-C - KSMGetInformationResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | BOOL | Set to true if an error occurred. |
| errorCode | long | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | long | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | NSString\* | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| serialNumber | NSString\* | The serial number of the users certificate. If astServerBackend parameter inside the MC Config is set to "ssms" this parameter can only be provided after an activation or after a Login. In case it is set to "maverick" this parameter will always be empty |
| sdkVersion | NSString\* | The version of the SDK. This version is also sent to the server and hence helps to identify the SDK built. |
| ssmsAppConfiguration | [KSMSsmsAppConfiguration\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#BasicAppConfiguration) | Includes the SSMS app configuration (locale, app name and version) that was passed to the SDK during the StartEvent or RestartEvent |
| appConfig | NSData\* | The app config that had been packaged into the binary. If no app config had been packaged this parameter will be empty |
| ecoConfiguration | [KSMEcoConfiguration\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#EcoConfiguration) | Includes the eco service urls (token issuer service, address book server and message router). If partially or none have been configured in the MC Config this corresponding parameter will be empty |
| loggedInUser | [KsUserIdentifier\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#UserIdentifier) | The user identifier of the currently logged in user. If astServerBackend parameter inside the MC Config is set to "ssms" this parameter can only be provided after LoginEvent or OfflineLoginEvent had been invoked successfully. In case it is set to "maverick" this parameter can only be provided after SetAuthorisationCodeEvent or OfflineLoginEvent had been invoked successfully |
| iamConfigurationData | [KsIamConfigurationData\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#IamConfigurationData) | The IAM configuration data that had been set inside the MC Config. |
| encryptionCertificate | NSData\* | If the useScp parameter is set to "true" inside the MC Config this parameter returns the used encryption certificate of the user |
| signerCertificate | NSData\* | If the useScp parameter is set to "true" inside the MC Config this parameter returns the used signing certificate of the user for the given device |
| authenticationCertificate | NSData\* | If the useScp parameter is set to "true" inside the MC Config this parameter returns the used authentication certificate of the user for the given device |

#### Java - GetInformationResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| sdkVersion | String | The version of the SDK. This version is also sent to the server and hence helps to identify the SDK built. |
| serialNumber | String | The serial number of the users certificate. If astServerBackend parameter inside the MC Config is set to "ssms" this parameter can only be provided after an activation or after a Login. In case it is set to "maverick" this parameter will always be empty |
| locale | String | The local that was passed to the SDK during the StartEvent or RestartEvent |
| version | [AppVersion](shift-lite-idpsdk__mcsdk-api__composite_types.md#AppVersion) | The app version that was passed to the SDK during the StartEvent or RestartEvent |
| appName | String | The app name that was passed to the SDK during the StartEvent or RestartEvent |
| appConfig | String | The app config that had been packaged into the binary. If no app config had been packaged this parameter will be empty |
| tokenIssuerServiceUrl | String | The url of the token issuer service. If none has been configured in the MC Config this parameter will be empty |
| addressBookServerUrl | String | The url of the address book server. If none has been configured in the MC Config this parameter will be empty |
| messageRouterUrl | String | The url of the message router. If none has been configured in the MC Config this parameter will be empty |
| loggedInUserIdentifier | [UserIdentifier](shift-lite-idpsdk__mcsdk-api__composite_types.md#UserIdentifier) | The user identifier of the currently logged in user. If astServerBackend parameter inside the MC Config is set to "ssms" this parameter can only be provided after LoginEvent or OfflineLoginEvent had been invoked successfully. In case it is set to "maverick" this parameter can only be provided after SetAuthorisationCodeEvent or OfflineLoginEvent had been invoked successfully |
| iamConfigurationData | [IamConfigurationData](shift-lite-idpsdk__mcsdk-api__composite_types.md#IamConfigurationData) | The IAM configuration data that had been set inside the MC Config. |
| encryptionCertificate | byte[] | If the useScp parameter is set to "true" inside the MC Config this parameter returns the used encryption certificate of the user |
| signerCertificate | byte[] | If the useScp parameter is set to "true" inside the MC Config this parameter returns the used signing certificate of the user for the given device |
| authenticationCertificate | byte[] | If the useScp parameter is set to "true" inside the MC Config this parameter returns the used authentication certificate of the user for the given device |

### InvalidStateEvent

A special event that can be set as a result to any event sent by UI to the SDK. Can be used by the SDK when the event is question cannot be handled in the current state of SDK. For example [ExchangeIamTokenEvent](#ExchangeIamTokenEvent) can be invoked after successful [SetAuthorisationCodeEvent](#SetAuthorisationCodeEvent) or [OfflineLogin](#OfflineLoginEvent). Invoking the [ExchangeIamTokenEvent](#ExchangeIamTokenEvent) before the mentioned events will result in invalid state event being set a result.

#### Objective-C - KSMInvalidStateEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that is set by the sdk which will contain the trace context of the event that caused the invalid state |
| errorMessage | NSString\* | A human readable error message that will contain information about invalid state |

#### Java - InvalidStateEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that is set by the sdk which will contain the trace context of the event that caused the invalid state |
| errorMessage | String | A human readable error message that will contain information about invalid state |

### StatusResultEvent

General-purpose result event to convey the status outcome of an operation or request.

#### Objective-C - KSMStatusResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | BOOL | Set to true if an error occurred. |
| errorCode | long | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | long | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | NSString\* | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [KSMEventStatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. |

#### Java - StatusResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | boolean | Set to true if an error occurred. |
| errorCode | int | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| reportId | int | The SSMS report id related to an error if any occured. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | String | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [StatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. |

### SwitchWorkspaceEvent

Switches the workspace (tenant) of the logged-in user. This allows for seamless access to the resources and functionalities unique to the workspace using a tenant-specific token.
At the moment, this tenant-specific token is only used to access SmartScreen resources.  
SwitchWorkspaceEvent can be used only in the Maverick server backend environment and can be invoked after the successful login by the [SetAuthorisationCodeEvent](#SetAuthorisationCodeEvent) or [OfflineLogin](#OfflineLoginEvent).
After restarting, MC switches back to the master/main workspace.
Please check the returned [StatusResultEvent](#StatusResultEvent) to find out the switching status.

#### Objective-C - KSMSwitchWorkspaceEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| tenantId | NSString\* | The target tenant id. The realm in terms of the IdP. |

#### Java - SwitchWorkspaceEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| tenantId | String | The target tenant id. The realm in terms of the IdP. |

### TriggerBannerEvent

A notification event that is sent by the SDK to the UI which contains the information about either a transaction or a display message. Can be sent both on maverick and ssms backed SDKs. Can be sent after the successful login by the [SetAuthorisationCodeEvent](#SetAuthorisationCodeEvent) or [OfflineLogin](#OfflineLoginEvent). If the [BannerType](shift-lite-idpsdk__mcsdk-api__enumerations.md#BannerType) is `Transaction` UI can invoke [StartTransactionEvent](#StartTransactionEvent) or if the [BannerType](shift-lite-idpsdk__mcsdk-api__enumerations.md#BannerType) is `DisplayMessage` UI can invoke [StartDisplayMessageEvent](#StartDisplayMessageEvent) in order for UI to start processing transaction or display message.

#### Objective-C - KSMTriggerBannerEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that is set by the sdk which should be used for further transaction related SDK interations. |
| bannerType | [BannerType](shift-lite-idpsdk__mcsdk-api__enumerations.md#BannerType) | An enum determining whether there is a transaction or a display message |
| payload | NSString\* | A constant string that will be set to 'Display Message Received' or 'Transaction Received' depending on the [BannerType](shift-lite-idpsdk__mcsdk-api__enumerations.md#BannerType) |
| timer | int | Transaction timeout in seconds |
| execute | BOOL | Not used. Always set to false |

#### Java - TriggerBannerEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that is set by the sdk which should be used for further transaction related SDK interations. |
| bannerType | [BannerType](shift-lite-idpsdk__mcsdk-api__enumerations.md#BannerType) | An enum determining whether there is a transaction or a display message |
| payload | String | A constant string that will be set to 'Display Message Received' or 'Transaction Received' depending on the [BannerType](shift-lite-idpsdk__mcsdk-api__enumerations.md#BannerType) |
| timer | int | Transaction timeout in seconds |
| execute | boolean | Not used. Always set to false |

### StartTransactionEvent

An event that is sent by the UI to the SDK which starts the transaction processing. Can be invoked both on maverick and ssms backed SDKs. Can be sent after the [TriggerBannerEvent](#TriggerBannerEvent) only if the [BannerType](shift-lite-idpsdk__mcsdk-api__enumerations.md#BannerType) is `Transaction`.

After the start transaction event, UI is expected to only handle the transaction, using events that are not related to transaction will result in [InvalidStateEvent](#InvalidStateEvent) with the exception of property events on maverick backed SDKs.

The next step is that the SDK will send the transaction information using the [DisplayConfirmationRequestEvent](#DisplayConfirmationRequestEvent) where UI can use the information to process the transaction.

#### Objective-C - KSMStartTransactionEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |

#### Java - StartTransactionEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |

### InitiateTransactionEvent

Use to initiate a transaction using web-sockets with the given parameters. Please check the result `InitiateTransactionResultEvent` for the status of the operation and get access to `handle` if there were no errors.

The `handle` is the identifier for the initiated transaction, it will be needed by the [InitiatedTransactionDataSendEvent](#InitiatedTransactionDataSendEvent) in order to send data and it can be used to check against the handle from [InitiatedTransactionDataReceivedEvent](#InitiatedTransactionDataReceivedEvent) to determine the initiated transaction that [InitiatedTransactionDataReceivedEvent](#InitiatedTransactionDataReceivedEvent) is for.

#### Objective-C - KSMInitiateTransactionEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| url | NSString\* | The full request url |
| certificates | NSData\* | The certificates to be used for the request |
| httpHeaders | NSDictionary\* | The key value pairs of http headers |
| content | NSString\* | The request content |
| timeout | int | The request timeout in seconds, determines how long the bidirectional connection should remain open |

#### Java - InitiateTransactionEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| url | String | The full request url |
| certificates | byte[] | The certificates to be used for the request |
| httpHeaders | Map<String, String> | The key value pairs of http headers |
| content | String | The request content |
| timeout | int | The request timeout in seconds, determines how long the bidirectional connection should remain open |

### InitiateTransactionResultEvent

Provides the result of the InitiateTransactionEvent.

#### Objective-C - KSMInitiateTransactionResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | BOOL | Set to true if an error occurred. |
| errorCode | long | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | NSString\* | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [InitiateTransactionStatus](shift-lite-idpsdk__mcsdk-api__enumerations.md#InitiateTransactionStatus) | The status of the operation. |
| handle | int | The handle for the initiated transaction |

#### Java - InitiateTransactionResultEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| hasErrorOccurred | boolean | Set to true if an error occurred. |
| errorCode | int | The error code of the error if any occurred. If `hasErrorOccurred` is false, this parameter is zero. |
| errorDescription | String | The description of the error if any occurred. If `hasErrorOccurred` is false, this parameter is empty. |
| status | [InitiateTransactionStatus](shift-lite-idpsdk__mcsdk-api__enumerations.md#InitiateTransactionStatus) | The status of the operation. |
| handle | int | The handle for the initiated transaction |

### InitiatedTransactionDataReceivedEvent

The notification event that will be sent by MasterController to the UI when a data is received or upon any connection issues.

#### Objective-C - KSMInitiatedTransactionDataReceivedEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| handle | int | The handle for the initiated transaction |
| status | [InitiateTransactionStatus](shift-lite-idpsdk__mcsdk-api__enumerations.md#InitiateTransactionStatus) | The status of the operation. |
| content | NSString\* | The received data |

#### Java - InitiatedTransactionDataReceivedEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| handle | int | The handle for the initiated transaction |
| status | [InitiateTransactionStatus](shift-lite-idpsdk__mcsdk-api__enumerations.md#InitiateTransactionStatus) | The status of the operation. |
| content | string | The received data |

### InitiatedTransactionDataSendEvent

The event that can be used by the UI to send data over the initiated transaction with the given `handle` acquired by using the [InitiateTransactionEvent](#InitiateTransactionEvent).

This event is completely async and will always return `Acknowledge` as a result.

#### Objective-C - KSMInitiatedTransactionDataSendEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| handle | int | The handle for the initiated transaction |
| content | NSString\* | The data to send |
| closeSocket | BOOL | Whether to close the initiated transaction connection after sending the data or not |

#### Java - InitiatedTransactionDataSendEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| handle | int | The handle for the initiated transaction |
| content | String | The data to send |
| closeSocket | boolean | Whether to close the initiated transaction connection after sending the data or not |

### StartDisplayMessageEvent

An event that is sent by the UI to the SDK which starts the display message processing. Can be invoked both on maverick and ssms backed environments. Can be sent after the [TriggerBannerEvent](#TriggerBannerEvent) only if the [BannerType](shift-lite-idpsdk__mcsdk-api__enumerations.md#BannerType) is `DisplayMessage`.

#### Objective-C - KSMStartDisplayMessageEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |

#### Java - StartDisplayMessageEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |

### DisplayMessageEvent

A notification event that is sent by the SDK to the UI which contains the display message body and type. Can be sent both on maverick and ssms backed SDKs. Will be sent after [StartDisplayMessageEvent](#StartDisplayMessageEvent).

#### Objective-C - KSMDisplayMessageEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that is set by the sdk which should be used for further transaction related SDK interations. |
| messageInformation | NSString\* | The display message |
| messageType | [KSMMessageType] | Type of dialog that should be shown |

#### Java - DisplayMessageEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that is set by the sdk which should be used for further transaction related SDK interations. |
| messageInformation | String | The display message |
| messageType | [MessageType] | Type of dialog that should be shown |

### DisplayConfirmationRequestEvent

A notification event that is sent by the SDK to the UI which contains the transaction body and transaction timeout in seconds. Can be sent both on maverick and ssms backed SDKs. Will be sent after [StartTransactionEvent](#StartTransactionEvent).

After the transaction is processed the UI is expected to invoke the [DisplayConfirmationEvent](#DisplayConfirmationEvent) by passing the [ConfirmationType](shift-lite-idpsdk__mcsdk-api__enumerations.md#ConfirmationType) and `transactionInformation`

#### Objective-C - KSMDisplayConfirmationRequestEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that is set by the sdk which should be used for further transaction related SDK interations. |
| transactionInformation | NSString\* | A constant string that will be set to 'Display Message Received' or 'Transaction Received' depending on the [BannerType](shift-lite-idpsdk__mcsdk-api__enumerations.md#BannerType) |
| timerValue | int | Transaction timeout in seconds |

#### Java - DisplayConfirmationRequestEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that is set by the sdk which should be used for further transaction related SDK interations. |
| transactionInformation | String | A constant string that will be set to 'Display Message Received' or 'Transaction Received' depending on the [BannerType](shift-lite-idpsdk__mcsdk-api__enumerations.md#BannerType) |
| timerValue | int | Transaction timeout in seconds |

### DisplayConfirmationEvent

An event that is sent by the UI to the SDK which contains the verdict for a transaction. Can be invoked both on maverick and ssms backed SDKs. Can be sent after the [DisplayConfirmationRequestEvent](#DisplayConfirmationRequestEvent).

After the display confirmation event is processed by the SDK, the [TransactionEndEvent](#TransactionEndEvent) will be sent to UI.

#### Objective-C - KSMDisplayConfirmationEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| confirmationType | [KSMConfirmationType](shift-lite-idpsdk__mcsdk-api__enumerations.md#ConfirmationType) | The verdict, whether the transaction is accepted, cancelled or timedout |
| transactionInformation | NSString\* | `transactionInformation` parameter from the [DisplayConfirmationRequestEvent](#DisplayConfirmationRequestEvent) |

#### Java - DisplayConfirmationEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that should be used for all interactions inside the SDK related to the event. If nothing is passed here the SDK will create a context by itself and uses it explicitly for this event. |
| confirmationType | [ConfirmationType](shift-lite-idpsdk__mcsdk-api__enumerations.md#ConfirmationType) | The verdict, whether the transaction is accepted, cancelled or timedout |
| displayData | String | `transactionInformation` parameter from the [DisplayConfirmationRequestEvent](#DisplayConfirmationRequestEvent) |

### TransactionEndEvent

A notification event that is sent by the SDK to the UI indicating that transaction processing is ended. Can be sent both on maverick and ssms backed SDKs. Can be sent after [DisplayConfirmationEvent](#DisplayConfirmationEvent) or can be sent after [StartTransactionEvent](#StartTransactionEvent) if the transaction is cancelled or timedout on server side.

#### Objective-C - KSMTransactionEndEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext\*](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that is set by the sdk which should be used for further transaction related SDK interations. |
| status | [KSMEventStatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. Can have the statuses `KSMOK`, `KSMUSER_CANCEL`, `KSMUSER_CONFIRMATION_TIMEOUT`, `KSMSERVER_CANCEL` |

#### Java - TransactionEndEvent

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceContext | [TraceContext](shift-lite-idpsdk__mcsdk-api__composite_types.md#TraceContext) | The trace context that is set by the sdk which should be used for further transaction related SDK interations. |
| status | [StatusType](shift-lite-idpsdk__mcsdk-api__enumerations.md#StatusType) | The status of the operation. Can have the statuses `OK`, `USER_CANCEL`, `USER_CONFIRMATION_TIMEOUT`, `SERVER_CANCEL` |
