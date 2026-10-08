> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/testing/tms/test_tms> on 2026-09-28. Converted to Markdown; wording unchanged.

# Details

You have to use the AST TMS service interface to trigger a transaction.

Note that you need to know the used internal userId, i.e. the UUID-style ID that uniquely identifies the user, not just the user name. This UUID is not normally displayed to the users, but it can be seen in the IAM system where you manage the users (KOBIL IDP).

Then a transaction can be triggered with the following cURL command:

Trigger a transaction via CURL

```
curl -X POST https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/tms \
-H 'Authorization: Bearer $token' \
-H 'Content-Type: application/json' \
-d '{
"userId": "$userID",
"tmsData": {"text": "Test", "external": false, "data": {} },
"retrievalTimeout": 3000,
"tmsTimeout": 6000,
"requireExplicitAuthentication": false,
"requireFreshnessOfAuthentication": -1,
"auditMessage": "Test audit message"
}'
```

**your-environment.shift.company.com** should be replaced by the suitable host name of your environment. While the request to get an authorization token will use the subdomain **idp** all your transaction related requests should use the subdomain **asts**.  
**$yourTenantName** should the the tenant responsible for the recipient of the transaction.  
**$userID** should be the userID of the recipient of the transaction. Note that this must me the UUID-style ID of the user, see above.  
**$token** should be an authorization token of a user with the correct permissions / roles to send a transaction.
Please refer to [this section](shift-lite-idpsdk__prerequisites__auth_token_shift.md) to see how to get a token.
