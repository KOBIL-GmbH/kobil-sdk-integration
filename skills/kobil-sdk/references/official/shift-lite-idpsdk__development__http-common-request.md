> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/http-common-request> on 2026-09-28. Converted to Markdown; wording unchanged.

# CreateHttpCommonRequestEvent

## Overview

`CreateHttpCommonRequestEvent` This is an event that allows developers to send HTTP requests with various configurations, including authentication, custom headers, and SSL certificates.
Please note that `CreateHttpCommonRequestEvent` **cannot be used** while a restart is in progress.

---

### iOS/Swift

The Swift implementation is encapsulated within the `KSMCreateHttpCommonRequestEvent` class.

### **Initialization**

```
let event = KSMCreateHttpCommonRequestEvent(
fullUrl: String,
httpMethod: KSMCreateHttpCommonRequestHttpMethod,
content: String,
contentType: String,
userName: String,
password: String,
certificate: Data,
httpHeaders: [AnyHashable : Any]
)
let event = KSMCreateHttpCommonRequestEvent(
fullUrl: String,
httpMethod: KSMCreateHttpCommonRequestHttpMethod,
multiPartContent: [KsHttpMultiPart],
contentType: String,
userName: String,
password: String,
certificate: Data,
httpHeaders: [AnyHashable : Any]
)
let event = KSMCreateHttpCommonRequestEvent(
fullUrl: String,
httpMethod: KSMCreateHttpCommonRequestHttpMethod,
content: String,
contentType: String,
userName: String,
password: String,
certificate: Data,
httpHeaders: [AnyHashable : Any],
cookieIdentifier: String
)
let event = KSMCreateHttpCommonRequestEvent(
fullUrl: String,
httpMethod: KSMCreateHttpCommonRequestHttpMethod,
content: String,
contentType: String,
userName: String,
password: String,
certificate: Data,
timeout: UnsafeMutablePointer<UInt>,
isRetry: UnsafeMutablePointer<ObjCBool>,
httpHeaders: [AnyHashable : Any]
)
let event = KSMCreateHttpCommonRequestEvent(
fullUrl: String,
httpMethod: KSMCreateHttpCommonRequestHttpMethod,
multiPartContent: [KsHttpMultiPart],
contentType: String,
userName: String,
password: String,
certificate: Data,
httpHeaders: [AnyHashable : Any],
cookieIdentifier: String
)
let event = KSMCreateHttpCommonRequestEvent(
followRedirect: Bool,
fullUrl: String,
httpMethod: KSMCreateHttpCommonRequestHttpMethod,
content: String,
contentType: String,
userName: String,
password: String,
certificate: Data,
httpHeaders: [AnyHashable : Any],
cookieIdentifier: String
)
let event = KSMCreateHttpCommonRequestEvent(
fullUrl: String,
httpMethod: KSMCreateHttpCommonRequestHttpMethod,
content: String,
contentType: String,
userName: String,
password: String,
certificate: Data,
timeout: UnsafeMutablePointer<UInt>,
isRetry: UnsafeMutablePointer<ObjCBool>,
httpHeaders: [AnyHashable : Any],
cookieIdentifier: String
)
let event = KSMCreateHttpCommonRequestEvent(
fullUrl: String,
httpMethod: KSMCreateHttpCommonRequestHttpMethod,
content: String,
contentType: String,
userName: String,
password: String,
certificate: Data,
httpHeaders: [AnyHashable : Any],
cookieIdentifier: String,
accessTokenIdentifier: String
)
let event = KSMCreateHttpCommonRequestEvent(
followRedirect: Bool,
fullUrl: String,
httpMethod: KSMCreateHttpCommonRequestHttpMethod,
multiPartContent: [KsHttpMultiPart],
contentType: String,
userName: String,
password: String,
certificate: Data,
httpHeaders: [AnyHashable : Any],
cookieIdentifier: String
)
let event = KSMCreateHttpCommonRequestEvent(
fullUrl: String,
httpMethod: KSMCreateHttpCommonRequestHttpMethod,
multiPartContent: [KsHttpMultiPart],
contentType: String,
userName: String,
password: String,
certificate: Data,
httpHeaders: [AnyHashable : Any],
cookieIdentifier: String,
accessTokenIdentifier: String
)
let event = KSMCreateHttpCommonRequestEvent(
followRedirect: Bool,
fullUrl: String,
httpMethod: KSMCreateHttpCommonRequestHttpMethod,
content: String,
contentType: String,
userName: String,
password: String,
certificate: Data,
timeout: UnsafeMutablePointer<UInt>,
isRetry: UnsafeMutablePointer<ObjCBool>,
httpHeaders: [AnyHashable : Any],
cookieIdentifier: String
)
let event = KSMCreateHttpCommonRequestEvent(
fullUrl: String,
httpMethod: KSMCreateHttpCommonRequestHttpMethod,
content: String,
contentType: String,
userName: String,
password: String,
certificate: Data,
timeout: UnsafeMutablePointer<UInt>,
isRetry: UnsafeMutablePointer<ObjCBool>,
httpHeaders: [AnyHashable : Any],
cookieIdentifier: String,
accessTokenIdentifier: String
)
```

```
enum KSMCreateHttpCommonRequestHttpMethod: Int {
case get
case post
case put
case delete
}
```

### **Properties**

| Property | Type | Description |
| --- | --- | --- |
| `fullUrl` | `String*` | Absolute URL of the request |
| `httpMethod` | `KSMCreateHttpCommonRequestHttpMethod` | HTTP method (GET, POST, etc.) |
| `content` | `String*` | Request body content |
| `contentType` | `String*` | MIME type of the content |
| `userName` | `String*` | Username for authentication |
| `password` | `String*` | Password for authentication |
| `certificate` | `Data*` | SSL certificate chain in PEM format |
| `httpHeaders` | `[AnyHashable : Any]*` | Additional HTTP headers |
| `cookieIdentifier` | `String*` | Cookie identifier |
| `followRedirect` | `Bool` | Whether the request follows redirects |
| `timeout` | `UnsafeMutablePointer<UInt>` | Timeout duration for the request in seconds |
| `isRetry` | `UnsafeMutablePointer<ObjCBool>` | Specifies if the request is a retry |

### **Response Handling**

The response is handled by `KSMCreateHttpCommonRequestResultEvent`:

```
- (instancetype _Nonnull) initWithStatus:(KSMCreateHttpCommonRequestStatus)status
httpStatus:(int)httpStatus
response:(NSData* _Nonnull)response
responseHeaders:(NSDictionary *_Nonnull)responseHeaders NS_DESIGNATED_INITIALIZER;
```

**Example Response Handling:**

```
if resultEvent.status == .success {
print("Response: " + (String(bytes: resultEvent.response, encoding: .utf8) ?? ""))
} else {
print("Error: \(resultEvent.status)")
}
```

---

### Android/Kotlin

The Kotlin implementation is encapsulated in the `CreateHttpCommonRequestEvent` class.

### **Initialization**

```
val httpCommonReqEvent = CreateHttpCommonRequestEvent(
String fullUrl,
HttpMethod method,
String content,
String contentType,
String userName,
String password,
byte[] certificateChain
)
val httpCommonReqEvent = CreateHttpCommonRequestEvent(
String fullUrl,
HttpMethod method,
String content,
String contentType,
String userName,
String password,
byte[] certificateChain,
Map<String, String> additionalHeaders
)
val httpCommonReqEvent = CreateHttpCommonRequestEvent(
String fullUrl,
HttpMethod method,
String content,
String contentType,
String userName,
String password,
byte[] certificateChain,
Map<String, String> additionalHeaders,
String cookieIdentifier
)
val httpCommonReqEvent = CreateHttpCommonRequestEvent(
String fullUrl,
HttpMethod method,
String content,
String contentType,
String userName,
String password,
byte[] certificateChain,
Map<String, String> additionalHeaders,
String cookieIdentifier,
boolean followRedirect
)
val httpCommonReqEvent = CreateHttpCommonRequestEvent(
String fullUrl,
HttpMethod method,
String content,
String contentType,
String userName,
String password,
byte[] certificateChain,
Map<String, String> additionalHeaders,
String cookieIdentifier,
boolean followRedirect,
String accessTokenIdentifier
)
val httpCommonReqEvent = CreateHttpCommonRequestEvent(
String fullUrl,
HttpMethod method,
String content,
String contentType,
String userName,
String password,
byte[] certificateChain,
Map<String, String> additionalHeaders,
String cookieIdentifier,
boolean followRedirect,
String accessTokenIdentifier,
int timeout,
boolean isRetry
)
val httpCommonReqEvent = CreateHttpCommonRequestEvent(
String fullUrl,
HttpMethod method,
List<HttpMultiPart> multiPartContent,
String contentType,
String userName,
String password,
byte[] certificateChain
)
val httpCommonReqEvent = CreateHttpCommonRequestEvent(
String fullUrl,
HttpMethod method,
List<HttpMultiPart> multiPartContent,
String contentType,
String userName,
String password,
byte[] certificateChain,
Map<String, String> additionalHeaders
)
val httpCommonReqEvent = CreateHttpCommonRequestEvent(
String fullUrl,
HttpMethod method,
List<HttpMultiPart> multiPartContent,
String contentType,
String userName,
String password,
byte[] certificateChain,
Map<String, String> additionalHeaders,
String cookieIdentifier
)
val httpCommonReqEvent = CreateHttpCommonRequestEvent(
String fullUrl,
HttpMethod method,
List<HttpMultiPart> multiPartContent,
String contentType,
String userName,
String password,
byte[] certificateChain,
Map<String, String> additionalHeaders,
String cookieIdentifier,
boolean followRedirect
)
val httpCommonReqEvent = CreateHttpCommonRequestEvent(
String fullUrl,
HttpMethod method,
List<HttpMultiPart> multiPartContent,
String contentType,
String userName,
String password,
byte[] certificateChain,
Map<String, String> additionalHeaders,
String cookieIdentifier,
boolean followRedirect,
String accessTokenIdentifier
)
val httpCommonReqEvent = CreateHttpCommonRequestEvent(
String fullUrl,
HttpMethod method,
List<HttpMultiPart> multiPartContent,
String contentType,
String userName,
String password,
byte[] certificateChain,
Map<String, String> additionalHeaders,
String cookieIdentifier,
boolean followRedirect,
String accessTokenIdentifier,
int timeout,
boolean isRetry
)
```

```
public enum HttpMethod {
GET, POST, PUT, DELETE
}
```

### **Properties**

| Property | Type | Description |
| --- | --- | --- |
| `fullUrl` | `String` | Absolute URL of the request |
| `method` | `HttpMethod` | HTTP method (GET, POST, etc.) |
| `content` | `String` | Request body content |
| `contentType` | `String` | MIME type of the content |
| `userName` | `String` | Username for authentication |
| `password` | `String` | Password for authentication |
| `certificateChain` | `byte[]` | SSL certificate chain in PEM format |
| `additionalHeaders` | `Map<String, String>` | Additional HTTP headers |
| `cookieIdentifier` | `String` | Cookie identifier |
| `followRedirect` | `boolean` | Whether the request follows redirects |
| `timeout` | `int` | Timeout duration for the request |
| `isRetry` | `boolean` | Specifies if the request is a retry |

### **Response Handling**

A corresponding response class `CreateHttpCommonRequestResultEvent` captures the HTTP response:

```
public CreateHttpCommonRequestResultEvent(int status, int httpStatus, byte[] response, Map<String, String> responseHeaders) {
this.status = status;
this.httpStatus = httpStatus;
this.response = response;
this.responseHeaders = responseHeaders;
}
```

**Example Response Handling:**

```
if (response.getHttpStatus == CreateHttpCommonRequestResultEvent.Status.success) {
System.out.println("Response: " + new String(response.getResponse()));
} else {
System.out.println("Error: " + response.getHttpStatus());
}
```

---
