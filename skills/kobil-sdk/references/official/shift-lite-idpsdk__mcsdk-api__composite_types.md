> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/composite_types> on 2026-09-28. Converted to Markdown; wording unchanged.

# Composite Data Types

### AppVersion

Represents an application version set by the [StartEvent](shift-lite-idpsdk__mcsdk-api__individual_events.md#StartEvent) or [RestartEvent](shift-lite-idpsdk__mcsdk-api__individual_events.md#RestartEvent).

#### Objective-C - KSMVersion

Parameters

| Name | Type | Description |
| --- | --- | --- |
| majorVersion | int | The major version number. Typically a change in the major version number indicates a compatibility break with previous versions. |
| minorVersion | int | The minor version number. Typically a change in the minor version number indicates that new features were added, while remaining backwards compatible with previous releases. |
| buildNo | int | The build version number. Typically it indicates the unique number set by the build or CI system. |
| ssmsVersionString | NSString\* | The string representation of the version formatted as **"`majorVersion`.`minorVersion`.`buildNo`"** |

#### Java - AppVersion

Parameters

| Name | Type | Description |
| --- | --- | --- |
| major | int | The major version number. Typically a change in the major version number indicates a compatibility break with previous versions. |
| minor | int | The minor version number. Typically a change in the minor version number indicates that new features were added, while remaining backwards compatible with previous releases. |
| build | int | The build version number. Typically it indicates the unique number set by the build or CI system. |

### BasicAppConfiguration

Represents the basic configuration of the application

#### Objective-C - KSMSsmsAppConfiguration

Parameters

| Name | Type | Description |
| --- | --- | --- |
| locale | NSString\* | The local that was passed to the SDK during the StartEvent or RestartEvent. The default locale of the Application. For example, this will affect messages returned to the Application. The encoding of this string is ASCII and it must be 2 bytes long. |
| version | [KSMVersion\*](#AppVersion) | The app version that was passed to the SDK during the StartEvent or RestartEvent |
| name | NSString\* | The app name that was passed to the SDK during the StartEvent or RestartEvent. To distinguish the Applications, an Application must have a name. Applications with different names may have the same version numbers. Encoding of this string is UTF-8 and it has a maximum length of 32 bytes. |
| sdkconfig | NSData\* | The SDK config that was passed to the SDK during the StartEvent or RestartEvent |

### ConfigurationData

Provides some additional configuration data in StartEvent.

#### Objective-C - KSMConfigurationData

Parameters

| Name | Type | Description |
| --- | --- | --- |
| category | NSString\* | The category of messages/responses to tag. The tag value itself is read from the content of the corresponding messages/responses using the `tagName` as a key. |
| tagName | NSString\* | The name of the field in the message/response content that holds the tag value that will be applied to the message/response if it matches the specified `category`. |

#### Java - ConfigurationData

Parameters

| Name | Type | Description |
| --- | --- | --- |
| category | String | The category of messages/responses to tag. The tag value itself is read from the content of the corresponding messages/responses using the `tagName` as a key. |
| tagName | String | The name of the field in the message/response content that holds the tag value that will be applied to the message/response if it matches the specified `category`. |

### EcoConfiguration

Represents Eco configuration, which basically includes the Eco service URLs.

#### Objective-C - KSMEcoConfiguration

Parameters

| Name | Type | Description |
| --- | --- | --- |
| tokenIssuerServiceUrl | NSString\* | The url of the token issuer service. If none has been configured in the MC Config this parameter will be empty |
| addressBookServerUrl | NSString\* | The url of the address book server. If none has been configured in the MC Config this parameter will be empty |
| messageRouterUrl | NSData\* | The url of the message router. If none has been configured in the MC Config this parameter will be empty |
| ecoId | NSString\* | *This parameter is deprecated. The tenant id of the logged-in user is set* |
| certificateChain | NSData\* | *This parameter is deprecated. An empty value is set* |
| category | NSString\* | *This parameter is deprecated. An empty value is set* |
| tagName | NSString\* | *This parameter is deprecated. An empty value is set* |

### IamConfigurationData

Represents IDP configuration data that is set inside the MC Config during the StartEvent and RestartEvent

#### Objective-C - KsIamConfigurationData

Parameters

| Name | Type | Description |
| --- | --- | --- |
| clientId | NSString\* | The IDP client id used by the SDK in requests to the IDP service. |
| serverUrl | NSString\* | The IDP service URL. |
| certificateChain | NSData\* | The certificate chain used by the SDK to configure connections to the IDP service endpoints. |
| redirectUri | NSString\* | The redirect URI chain used by the SDK in requests to the IDP service, e.g. to get an authorization code, refresh token, etc. |

#### Java - IamConfigurationData

Parameters

| Name | Type | Description |
| --- | --- | --- |
| clientId | String | The IDP client id used by the SDK in requests to the IDP service. |
| serverUrl | String | The IDP service URL. |
| certificateChain | byte[] | The certificate chain used by the SDK to configure connections to the IDP service endpoints. |
| redirectUri | String | The redirect URI chain used by the SDK in requests to the IDP service, e.g. to get an authorization code, refresh token, etc. |

### RestEndpointIdentifier

Denotes the REST endpoint identifier to configure.

#### Objective-C - KSMRestEndpointIdentifier

#### Java - RestEndpointIdentifier

### TraceContext

Context information uniquely identifies individual requests in a distributed system and also defines a means to add and propagate provider-specific context information.

Refer to the [W3C Trace Context specification](https://www.w3.org/TR/trace-context) for additional details.

#### Objective-C - TraceContext

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceParent | NSString\* | Describes the position of the incoming request in its trace graph in a portable, fixed-length format. Its design focuses on fast parsing. Every tracing tool MUST properly set traceparent even when it only relies on vendor-specific information in tracestate |
| traceState | NSString\* | Extends traceparent with vendor-specific data represented by a set of name/value pairs. Storing information in tracestate is optional. |

#### Java - TraceContext

Parameters

| Name | Type | Description |
| --- | --- | --- |
| traceParent | String | Describes the position of the incoming request in its trace graph in a portable, fixed-length format. Its design focuses on fast parsing. Every tracing tool MUST properly set traceparent even when it only relies on vendor-specific information in tracestate |
| traceState | String | Extends traceparent with vendor-specific data represented by a set of name/value pairs. Storing information in tracestate is optional. |

### UserDetails

Represents user identity with additional details

#### Objective-C - KsUserDetails

Parameters

| Name | Type | Description |
| --- | --- | --- |
| userIdentifier | [KsUserIdentifier](#UserIdentifier) | The user identifier |
| displayUsername | NSString\* | The username of the user |
| displayEmail | NSString\* | The email of the user |

#### Java - UserDetails

Parameters

| Name | Type | Description |
| --- | --- | --- |
| userIdentifier | [UserIdentifier](#UserIdentifier) | The user identifier |
| displayUsername | NSString\* | The username of the user |
| displayEmail | NSString\* | The email of the user |

### UserIdentifier

Represents user identity

#### Objective-C - KsUserIdentifier

Parameters

| Name | Type | Description |
| --- | --- | --- |
| tenantId | NSString\* | The tenant id to which the user belongs |
| userId | NSString\* | The user id |

#### Java - UserIdentifier

Parameters

| Name | Type | Description |
| --- | --- | --- |
| tenantId | String | The tenant id to which the user belongs |
| userId | String | The user id |
