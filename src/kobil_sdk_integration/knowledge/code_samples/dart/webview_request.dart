// Source: Flutter superapp, AstRepo (header and PKCE keys, getAstClientDataAsMap), trimmed. A bare URL is refused (blank page):
// the SDK delivers the AST client data and the PKCE challenge (GetAstClientData); the URL carries code_challenge and the
// request carries the headers X-KOBIL-ASTCLIENTDATA and X-KOBIL-ASTCLIENTID. clientData is a LIST of strings in the wrapper:
// join it for the header. Not compiled here.

class AstWebRequest {
  static const clientIdKey = 'X-KOBIL-ASTCLIENTID';
  static const clientDataKey = 'X-KOBIL-ASTCLIENTDATA';

  final Map<String, String> headers;
  final String codeChallenge;
  final String codeChallengeMethod;
  AstWebRequest(this.headers, this.codeChallenge, this.codeChallengeMethod);

  /// Ask the SDK for the AST client data of the tenant; null when the call failed.
  static Future<AstWebRequest?> fetch(McWrapperApi api, String tenantId) async {
    final response = await api.send(GetAstClientDataEventT(tenantId: tenantId));
    return response.fold((error) => null, (event) {
      if (event is! GetAstClientDataResultEventT || event.status != StatusType.ok) return null;
      final headers = <String, String>{clientDataKey: event.clientData?.join() ?? ''};
      // only when a valid value exists (all zeros before the first activation)
      final id = event.astClientId ?? '';
      if (id.isNotEmpty && int.tryParse(id) != 0) headers[clientIdKey] = id;
      return AstWebRequest(headers, event.codeChallange ?? '', event.codeChallangeMethod ?? '');
    });
  }

  /// authorizationEndpoint comes from sdk_idp_flow_overview / sdk_native_preflight (<host>/auth/realms/<realm>/protocol/openid-connect/auth).
  /// The redirect URI must be one the client has registered. Load the URL WITH [headers] (URLRequest(url:, headers:)).
  Uri authorizationUrl(String authorizationEndpoint, String clientId, String redirectUri) =>
      Uri.parse(authorizationEndpoint).replace(queryParameters: {
        'client_id': clientId,
        'redirect_uri': redirectUri,
        'scope': 'openid',
        'response_type': 'code',
        'code_challenge': codeChallenge,
        'code_challenge_method': codeChallengeMethod,
      });
}
