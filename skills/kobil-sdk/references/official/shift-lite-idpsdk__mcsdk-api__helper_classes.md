> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/helper_classes> on 2026-09-28. Converted to Markdown; wording unchanged.

# Helper Classes

| class Name | Infos | Parameter | Remark |
| --- | --- | --- | --- |
| UserIdentifier | identifies a user |

| Variable | Description |
| --- | --- |
| Username | is the given username |
| TenantId | The specified tenant for a multi tenant environment |

The username is an uuid when using the KOBIL IDP and JWT Token received by the ExchangeIamToken Event contains the UUID and the human readable name entered via webview or kssidp. One can have same usernames on different tenants.
