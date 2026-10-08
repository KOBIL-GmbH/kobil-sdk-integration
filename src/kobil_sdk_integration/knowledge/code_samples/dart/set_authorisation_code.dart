// Source: Flutter WLA app, SdkHandlerRepo.setAuthCode, and Flutter superapp, setAuthCodeEvent, trimmed. The WebView ends the
// login by navigating to the redirect URI with ?code=...: stop that navigation, take the code and hand it to the SDK. The reply
// SetAuthorisationCodeResultEventT is the result of send(). Reading the code with Uri is an ADDITION. The code is never logged.
// Not compiled here.

/// The code of the redirect URL, or null when it is not the redirect with a code.
String? authorisationCode(Uri url, String redirectUri) {
  if (!url.toString().startsWith(redirectUri)) return null;
  final code = url.queryParameters['code'];
  return (code == null || code.isEmpty) ? null : code;
}

/// True when the SDK accepted the code. mode: AuthenticationMode.password or AuthenticationMode.biometric.
Future<bool> setAuthCode(McWrapperApi api, String authCode, String clientId, String tenantId,
    {AuthenticationMode mode = AuthenticationMode.password}) async {
  final request = SetAuthorisationCodeEventT(
    authorisationCode: authCode,
    clientId: clientId,
    tenantId: tenantId,
    authenticationMode: mode,
  );
  final response = await api.send(request).timeout(const Duration(seconds: 30));
  return response.fold((error) {
    print('[kobil-debug] SetAuthorisationCode failed: $error'); // never the code
    return false;
  }, (event) {
    print('[kobil-debug] SetAuthorisationCodeResult status=${event is SetAuthorisationCodeResultEventT ? event.status : "unexpected"}');
    return event is SetAuthorisationCodeResultEventT && event.status == StatusType.ok;
  });
}
