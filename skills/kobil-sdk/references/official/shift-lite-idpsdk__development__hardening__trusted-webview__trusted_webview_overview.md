> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/hardening/trusted-webview/trusted_webview_overview> on 2026-09-28. Converted to Markdown; wording unchanged.

# Trusted WebView

Trusted WebView adds an additional security layer for apps that display web content inside a WebView or WebKit-based view. It helps ensure that only approved destinations are loaded, connections are protected with strong certificate validation, and the app does not blindly rely on potentially compromised, outdated, or incomplete platform certificate stores.

---

## Features

### URL Whitelist

Restricts WebView navigation to explicitly allowed domains or URLs. This helps prevent redirects, injected links, deep-link abuse, and unintended access to untrusted web content.

### Certificate Pinning on Android and iOS

Enforces certificate pinning across supported Android and iOS versions. This reduces the risk of man-in-the-middle attacks, rogue certificate authorities, intercepted HTTPS traffic, and malicious network inspection.

### Cookie Encryption (Android)")

On Android, WebView cookies can be encrypted at rest using the Android Keystore. This reduces the impact of local data extraction, backups, forensic access, or compromised app storage.

### Cookie Sharing (iOS)")

On iOS, Trusted WebView provides a cookie synchronization channel between the WebView and other SDK components such as the AST SDK. This keeps session cookies consistent across components without exposing them to unrelated parts of the app.

### Custom Trust Store

Allows the app to use a dedicated trust store instead of relying only on the Android or iOS system certificate store. This protects against maliciously installed or compromised certificates and helps maintain compatibility on devices with outdated, incomplete, or missing root certificates.

---

Together, Trusted WebView helps harden WebView-based flows such as login pages, payment flows, account portals, dashboards, and embedded web features against common network, certificate, navigation, and local storage attacks on both Android and iOS.
