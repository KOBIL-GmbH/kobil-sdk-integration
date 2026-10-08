> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/postman_usage/postman_token_rest_api> on 2026-09-28. Converted to Markdown; wording unchanged.

# Token Handling API

## Handling Exchange IAM Token by using API requests

This part of the documentation provides a detailed walkthrough for managing source and target clients within the IDP server. It encompasses the creation of clients, exchange of tokens, and various additional steps to establish a secure and efficient communication flow between clients and endpoints.

### **Create Source Client**

![](https://developer.kobil.com/assets/images/createSourceClient-1e959081cbafc45e676ccdf22e5fa6e7.png)

* **General Info:**

  + This client is the source client that will provide MC-TOKEN to the target client in order to be exchanged, and used later for other operations.
  + The *`{{source_client}}`* parameter specifies the name of the client to be created.
  + To create a source client, you could use the following **API endpoint:**

```
POST https://idp.{{base_url}}/auth/admin/realms/{{tenant}}/clients
```

* **Sample Request Body:**

Configure the request body parameters as follows:

```
{
"clientId": "{{source_client}}",
"name": "",
"description": "Source client in purpose of testing the API",
// ... (other parameters)
}
```

* **Response:**
  + Upon successful execution, you will get **HTTP 201** as a response, and the API will create the specified source client within the IDP realm.

---

### **Create Target Client**

![](https://developer.kobil.com/assets/images/createTargetClient-67df9f72caadc44a0f3bed9bf337db60.png)

* **General Info:**
  + Follow the same steps as above, replacing *`{{target_client}}`* with the desired target client name.
  + To exchange a token between the source and target clients, please use the following **API endpoint:**

```
POST https://idp.{{base_url}}/auth/admin/realms/{{tenant}}/clients
```

* **Sample Request Body:**

Configure the request body parameters as follows:

```
{
"clientId": "{{target_client}}",
"name": "",
"description": "Target client in purpose of testing the API",
"rootUrl": "",
// ... (other parameters)
}
```

* **Response:**
  + Upon successful execution, you will get **HTTP 201** as a response and the API will create the specified target client within the IDP realm.

---

### **Get Client UUID for any Client**

![](https://developer.kobil.com/assets/images/getClientUUID-656cf264b727908a08e2f2310408e973.png)

* **General Info:**

  + This API call retrieves the client UUID for a specific client within the IDP realm.
  + The client UUID is essential for various configuration and management tasks.
  + To get a client UUID use the following **API endpoint:**

  ```
  GET https://idp.{{base_url}}/auth/admin/realms/{{tenant}}/clients?clientId={{source_client}}
  ```

  > Client name can be any clientID that exists in IDP server e.g `{{source_client}}` or `{{target_client}}` or any other `{{client_name}}`.
* **Sample Response:**

  + Upon successful execution, you will receive an **HTTP 200** response with details about the specified client, including its UUID. For example:

```
{
"id": "02434b30-ad16-4be0-81b4-f072c6cbf242",
"clientId": "clientSource",
"name": "",
"description": "Test Client from postman",
"rootUrl": "",
"adminUrl": "",
"baseUrl": "",
}
```

---

### **Create Token Exchange Policy for Source Client**

![](https://developer.kobil.com/assets/images/createTokenExchangePolicy-403b8fbd2f2106b40e003ca0f3427624.png)

* **General Info:**
  + This API call is used to create a token exchange policy for a source client within the IDP realm.
  + The token exchange policy defines specific configurations for secure token exchanges. **API Endpoint:**

```
POST https://idp.{{base_url}}/auth/admin/realms/{{tenant}}/clients/{{realm_mgmt_uuid}}/authz/resource-server/policy
```

* **Sample Request Body:**

Configure the request body parameters as follows:

```
{
"name": "{{token_exchange_policy_name}}",
"type": "client",
"logic": "POSITIVE",
"decisionStrategy": "UNANIMOUS",
"config": {
"clients": ["{{source_uuid}}"]
}
}
```

* **Sample Response:**

Upon successful execution, you will receive an **HTTP 200** response with details about the created token exchange policy:

```
{
"id": "f4959e35-6e2a-4abe-87f6-138092f79ec9",
"name": "PolicyClient",
"type": "client",
"logic": "POSITIVE",
"decisionStrategy": "UNANIMOUS",
"config": {
"clients": ["02434b30-ad16-4be0-81b4-f072c6cbf242"]
}
}
```

---

### **Enable Permissions for Target Client**

![](https://developer.kobil.com/assets/images/enableClientTargetPermission-0dff65dd6f1c709535c9d213ac0bf0e2.png)

* **General Info:**
  + This API call enables permissions for a target client within the Keycloak realm.
  + The endpoint for enabling permissions for the target client is:

```
POST https://idp.{{base_url}}/auth/admin/realms/{{tenant}}/clients/{{target_uuid}}/management/permissions
```

* **Sample Request Body:**

Configure the request body parameters as follows:

```
{
"enabled": true
}
```

* **Sample Response:**

  + Upon successful execution, you will receive an **HTTP 200** response with details about the enabled permissions for the target client:

```
{
"enabled": true,
"resource": "0f50d641-38ce-4589-a390-b76bf19d4beb",
"scopePermissions": {
"view": "88a4a2ae-d26b-4d6d-9378-d4b37b6f214d",
"manage": "0b379f99-107e-424a-8834-3d9ef673fe5f",
"configure": "17012f74-0680-49d5-82b3-cbef77a4d0d6",
"map-roles": "120a5cd9-6fc2-42b7-9f3d-14c07cf0535a",
"map-roles-client-scope": "a2c0d423-5723-46f7-91e5-eb142b60b499",
"map-roles-composite": "e2c3c1ca-7bef-43ab-9a00-aa8e5a7e685a",
"token-exchange": "3521e745-d14a-4f36-a66b-84a492f50a35"
}
}
```

> This API call facilitates enabling permissions for the target client within the IDP realm. Customize the parameters according to your specific requirements for enhanced security and access control.

---

### **Get Token Exchange Scope ID**

![](https://developer.kobil.com/assets/images/getClientScopeId-f1e201d24b8fcd3bee6ad964784fc5bc.png)

* **General Info:**
  + This API call retrieves the ID for token exchange scopes within the Keycloak realm.
  + The endpoint for getting token exchange scope IDs is:

```
GET https://idp.{{base_url}}/auth/admin/realms/{{tenant}}/clients/{{realm_mgmt_uuid}}/authz/resource-server/scope
```

* **Sample Response:**

  + Upon successful execution, you will receive an **HTTP 200** response with details about the token exchange scope IDs:

```
{
"id": "a2ef25ae-0714-48aa-b991-afaed5047fe6",
"name": "configure"
},
{
"id": "e20e72f9-c085-4aa8-92e0-a6b16e840f91",
"name": "manage"
},
{
"id": "f1a7e471-e756-49da-9a29-4b4dc404d06a",
"name": "map-roles"
},
{
"id": "82466ebf-4951-4c3d-829c-cb7870f9180f",
"name": "map-roles-client-scope"
},
{
"id": "5e532229-4655-4093-867e-20b80f80f28d",
"name": "map-roles-composite"
},
{
"id": "01179eef-f019-41ea-8508-5ef0630cb52a",
"name": "token-exchange"
},
{
"id": "d5de278e-f433-437d-a1d1-5a268e83ae1f",
"name": "view"
}
```

---

### **Update Token Exchange Permission Policy with Source TEP Policy**

![](https://developer.kobil.com/assets/images/updatePermissionPolicy-e47a3e4a5af7b0047ffc48df05c24241.png)

* **General Info:**
  + This API call updates the token exchange permission policy with the source Token Exchange Policy (TEP) within the Keycloak realm.
  + The endpoint for updating the token exchange permission policy is:

```
PUT https://idp.{{base_url}}/auth/admin/realms/{{tenant}}/clients/{{realm_mgmt_uuid}}/authz/resource-server/permission/scope/{{token_exchange_permission_policy_id}}
```

* **Sample Request Body:**

Configure the request body parameters as follows:

```
{
"id": "{{token_exchange_permission_policy_id}}",
"name": "token-exchange.permission.client.{{target_uuid}}",
"type": "scope",
"logic": "POSITIVE",
"decisionStrategy": "UNANIMOUS",
"resources": ["{{target_client_resource_id}}"],
"policies": ["{{token_exchange_policy_id}}"],
"scopes": ["{{token_exchange_scope_id}}"]
}
```

* **Response:**

* Upon successful execution, you will receive an **HTTP 201** response, indicating that the permission has been updated.

---

### **Token Exchange between Source and Target Clients**

![](https://developer.kobil.com/assets/images/tokenExchangeSourceClient-6067362c2398c7e2b60868537f73416f.png)

* **General Info:**
  + This API call initiates a token exchange between the source and target clients within the Keycloak realm.
  + The endpoint for the token exchange is:

```
POST https://idp.{{base_url}}/auth/realms/{{tenant}}/protocol/openid-connect/token
```

* **Sample Request Body:**

Configure the request body parameters as follows:

```
{
"grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
"client_id": "{{source_client}}",
"subject_token": "{{source_token}}",
"audience": "{{target_client}}",
"subject_token_type": "urn:ietf:params:oauth:token-type:access_token"
}
```

* **Sample Response:**

  + Upon successful execution, you will receive an **HTTP 200** response with the exchanged tokens:

```
{
"access_token": "{{token}}",
"expires_in": 300,
"refresh_expires_in": 1800,
"refresh_token": "{{refresh_token}}",
"token_type": "Bearer",
"not-before-policy": 1702992349,
"session_state": "1e8e00e7-478c-4873-858e-93492007c6d9",
"scope": "profile email"
}
```

---

## Handling Exchange IAM Token via IDP console

![](https://developer.kobil.com/assets/images/exchangeToken-0be90e399607560539703f987d87994f.png)

1. Create a client - ID which is called as **ExchangeToken** in your Workspace, and give [**token\_exchange**](https://developer.kobil.com/docs/idp-docs/utilities/exchange_token/#enable-permissions) permission.
2. Set the created client - ID as **audience** of your rest call.
3. In next step, navigate to your IDP server, and add [**Client Policy**](https://developer.kobil.com/docs/idp-docs/utilities/exchange_token/#client-policy-creation) to any existing client to send exchange token request.
4. Please configure the **client\_id** of your rest call, as the Client Policy value on the KOBIL - IDP server side.

---

![](https://developer.kobil.com/assets/images/exchangeToken_Auth-366ab2780e88ea6ccb4562a208557d10.png)

* Every exchange token request can be handled by the **Authorization Token**.
* In this step, **client\_id** of your rest call needs to be set as the Client Policy value on the KOBIL - IDP server side.

---

Example of Exchange Token setup.

![](https://developer.kobil.com/assets/images/eg_exchangeToken-9210e84cc256c5c8e0f9ea38b387fd0d.png)

---

Example of Authorization Token setup.

![](https://developer.kobil.com/assets/images/eg_exchangeToken_Auth-146978ee82a5d1f54a5a99b9c7fae569.png)

---

* **General Info:**

  + Exchange token requests can only be sent to the selected Client Policies.
  + Token requests are valid for every 300 seconds, to see the details of your exchange token requests, you could check the [jwt.io](https://jwt.io)
* **Performing the API Request and Response:**

  + To get more information about the request body configurations and responses, you could check the [Token API](https://developer.kobil.com/api/idp#tag/Authorization/paths/~1realms~1%7BtenantId%7D~1protocol~1openid-connect~1token/post) methods.

---
