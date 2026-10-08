> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/testing/test_properties_shift> on 2026-09-28. Converted to Markdown; wording unchanged.

# Test Set and Get Properties

In addition to using properties on the client side, it is also possible to get (and set) properties for a user or for a specific device on the server side. This is helpful, when you want to use a property like e.g. the "device name" on pages that the server displays to the client.

### Prerequisites

You have to use an app version that is already registered at Security Server, see [**Add App in Security Server**](shift-lite-idpsdk__prerequisites__app-lifecycle__add-app__add_app.md) and [**Register App Version**](shift-lite-idpsdk__prerequisites__app-lifecycle__register-app-version__register_app_version.md).  
You need an activated user account in your app on your device, see [**Test User Registration, Activation and Login in KOBIL Digitanium+ / KOBIL Shift Lite**](shift-lite-idpsdk__testing__enrollment__test_user_registration_activation_login_digitanium+_shift.md). Note that you need to know the used internal userId, i.e. the UUID-style ID that uniquely identifies the user, not just the user name. This UUID is not normally displayed to the users, but it can be seen in the IAM system where you manage the users (KOBIL IDP).

### KOBIL Shift Lite

You have to use the AST properties service interface to get or set a property e.g. with the following cURL command you can get all the properties of a given user that are visible to the portal backend:

```
curl https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/portal/properties/user/$userID \
-H 'Authorization: Bearer $token'
```

If you additionally specify a client, you can restrict the result to all the client specific properties for that specific client belonging to the user:

```
curl https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/portal/properties/user/$userID/client/$clientID \
-H 'Authorization: Bearer $token'
```

**your-environment.shift.company.com** should be replaced by the suitable host name of your environment. While the request to get an authorization token will use the subdomain **idp** all your transaction related requests should use the subdomain **asts**.  
**$yourTenantName** should the the tenant responsible for the recipient of the transaction.  
**$userID** should be the userID of the user whose properties you want to get. Note that this must me the UUID-style ID of the user, see above.  
**$clientID** - if used - should be the clientID of the specific client for which you want to get the properties.  
**$token** should be an authorization token of a user with the correct permissions / roles to send a transaction.
Please refer to [this section](shift-lite-idpsdk__prerequisites__app-lifecycle__add-app__add_app.md#add-app-via-curl-cli) to see how to get a token.

For setting properties, there are two different cases with different APIs, one for adding a new property and one for modifying an existing property.
If you want to add a new property, this is generally done by sending a POST request with the desired property data, e.g.

```
curl -X POST https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/portal/properties \
-H 'Authorization: Bearer $token' \
-H 'Content-Type: application/json' \
-d '{
"userId": "$userID",
"astClientId":"$clientID"
"name": "$propertyName",
"type": "$propertyType",
"value": "$propertyValue",
"encryption": "NONE",
"readOnly": false,
"notify": false,
"inKeystorage": false,
"cpFlags": 0,
"visibility": []
}'
```

If you want to modify an existing property, you need to first find the internal ID of the property that you want to modify, e.g. by getting all the properties and looking for the property that you are interested in and finding its **id** field. Then you can send a PUT request for that specific property with the new value:

```
curl -X PUT https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/portal/properties/$propertyID \
-H 'Authorization: Bearer $token' \
-H 'Content-Type: application/json' \
-d '{
"userId": "$userID",
"astClientId":"$clientID"
"name": "$propertyName",
"type": "$propertyType",
"value": "$propertyValue",
"encryption": "NONE",
"readOnly": false,
"notify": false,
"inKeystorage": false,
"cpFlags": 0,
"visibility": []
}'
```

Basically, most variables are the same as in the request for getting the properties above, i.e.  
**your-environment.shift.company.com** should be replaced by the suitable host name of your environment. While the request to get an authorization token will use the subdomain **idp** all your requests relating to properties should use the subdomain **asts**.  
**$yourTenantName** should be the tenant responsible for the recipient of the transaction.  
**$propertyID** (only in the PUT request that changes a property) should be the **id** of the property that you want to change.  
**$token** should be an authorization token of a user with the correct permissions / roles to send a transaction.
Please refer to [this section](shift-lite-idpsdk__prerequisites__auth_token_shift.md) to see how to get a token.  
**$userID** should be the userID of the user whose properties you want to get. Note that this must me the UUID-style ID of the user, see above.  
**$clientID** - if used - should be the clientID of the specific client for which you want to set the properties. If you omit the "astClientId", the property is associated with the user and visible on all his clients.  
**$propertyName** is the name of the property that you want to set.  
**$propertyType** is the type of the property, see [Property Type](shift-lite-idpsdk__mcsdk-api__set-property__property_type.md). The values that you can use in this curl request are OCTETSTRING, INTEGER, BOOLEAN, UTF8STRING, or DATE.  
**$propertyValue** is of course the value that you want to store for this property.  
The fields **encryption**, **readOnly**, **notify**, **inKeystorage**, **cpFlags** and **visibility** are advanced usage that we do no want to get into the details in this guide for testing basic functionality, but they need to be present for the request to be accepted, so we just listed them with default values.

> Note, that while almost all attributes of a property can be changed by such a PUT request (even the **propertyName** and **propertyType**), it is not allowed to actually change the **userID** or **clientID**. Especially, adding or removing a value for **astClientId** is not allowed. While such forbidden changes will appear to work, getting the property after such a change will show that the changes that were not allowed just have been silently discarded, while other changes will have been applied successfully.

Finally, if you want to cleanup after testing, you can also delete a property. This is done via a delete request like this one:

```
curl -X DELETE https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/portal/properties/$propertyID \
-H 'Authorization: Bearer $token'
```

The variable values are as above, i.e.  
**your-environment.shift.company.com** should be replaced by the suitable host name of your environment. While the request to get an authorization token will use the subdomain **idp** all your transaction related requests should use the subdomain **asts**.  
**$yourTenantName** should be the tenant responsible for the recipient of the transaction.  
**$propertyID** (only in the PUT request that changes a property) should be the **id** of the property that you want to change.
