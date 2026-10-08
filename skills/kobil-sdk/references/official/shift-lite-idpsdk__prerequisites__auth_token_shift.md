> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/auth_token_shift> on 2026-09-28. Converted to Markdown; wording unchanged.

# Getting Authorization Tokens

In the Shift environment, there are a lot of things that you can do by "manually" sending a request to one of the server, e.g. with the help of cURL. Using suitable cURL commands, you can e.g. add an app or register a new app version. Also for experimenting with functionality or for tests, you can use cURL requests.

However, in all those cases, you do need to add an authorization token to your cURL request to prove that this is a valid request coming from an authorized source. In the following, we will show how to obtain such an authorization token.

> **⚠️ Note**:
>
> * While the request to get an authorization token will use the subdomain **idp** all your App/App Version related requests should use the subdomain **asts**! Make sure that you are using the correct subdomains for your requests.
> * Avoid using (unescaped) line breaks in your cURL requests!
> * When using your authorization token, make sure that you do not have any whitespaces or linebreaks in it!
> * Make sure you do not add any redundant characters to your request's URL! For example an unneeded ‘/‘ at the end of the URL might cause a 404 response.
> * The token must belong to a user with the correct role. In our cases, a safe choice is to use a user with the ks-management Admin role.

There are two ways to get an Authorization Token, one is to use a cURL request which seems to be the natural choice if you plan to use the token in another cURL request, the other is to use the OpenID Connect debugger, which might be interesting to get some additional insight into the internal workings of the process of obtaining such a token.

### Via cURL CLI

Getting an authorization token can be accomplished by the following cURL command:

```
curl -L -X POST 'https://idp.your-environment.shift.company.com/auth/realms/$yourTenantName/protocol/openid-connect/token' \
-H 'Content-Type: application/x-www-form-urlencoded' --data-urlencode 'client_id=$yourClientId' \
--data-urlencode 'grant_type=password' --data-urlencode 'scope=openid' --data-urlencode 'username=$adminUser' \
--data-urlencode 'password=$adminPassword' --data-urlencode 'response_type=code token' \
--data-urlencode 'response_mode=form_post' --data-urlencode 'client_secret=$yourClientSecret'
```

> * **your-environment.shift.company.com** should be replaced by the suitable host name of your environment. While the request to get an authorization token will use the subdomain **idp** all your transaction related requests should use the subdomain **asts**.
> * **$yourTenantName** should the the tenant responsible for the recipient of the transaction.
> * **$yourClientId** is the ID of the a suitable "client" in your environment that has the needed capabilities for the task at hand. Typically, you need to ask your administrator for a suitable value to use here.
> * **$yourClientSecret** is the secret corresponding to the given clientID. This secret will only be needed for the clients with the configuration option "Authorization Enabled" set to "ON" and if the "access type" selected during client creation is "confidential". Otherwise, just ommit it, i.e. leave out the `--data-urlencode 'client_secret=$yourClientSecret'` at the end of the request.
> * **$adminUser** is the name of the user for which you want to request a token and **$adminPassword** is his password.

In case of success the reply will be a JSON structure similar to this one:

```
{"access_token":"eyJ...","expires_in":900,"refresh_expires_in":1800,"refresh_token":"eyJ...","token_type":"Bearer","id_token":"eyJ...","not-before-policy":0,"session_state":"...","scope":"..."}
```

The value that you need in subsequent cURL requests is the very long value that you get as "access\_token". Again, keep in mind that this value must not be "corrupted" by inserting spaces or line breaks.

### Via OpenID Connect Debugger

Another way to get a token is to use <https://oidcdebugger.com/>. This will require your IDP to allow redirects via mentioned URL and can be configured via KOBIL IDP (usually you want to do that only on non-productive environments).

---

oiddebugger: ![](https://developer.kobil.com/assets/images/oidcdebugger-79c50ce45a208fc0094475914123eb1a.png)

---

On this page make sure to check the option **token** as we want to get a token.

> To get the required Authorize URI for oidcdebugger you can open the openid-configuration page of your environment that might look like following:   
> <https://idp.your-environment.shift.company.com/auth/realms/$yourTenantName/.well-known/openid-configuration>   
> and extract the URL for the "authorization\_endpoint" displayed there - or contact your server team to provide you the Authorize URI.

After filling out the values for **Authorize URI** and **Client ID** scroll down and select **form\_post** as response mode.

---

![](https://developer.kobil.com/assets/images/oidcdebugger2-4c5bc51bed6be6c19c0296dd50d9dc10.png)

---

After sending the request you should see the login site of your IDP:

---

![](https://developer.kobil.com/assets/images/oidc_login1-0a5be7784efa2db90bbd3cc222ce2a26.png)

---

Upon entering the credentials of your ks-management Admin user you will be redirected to below site allowing you to copy the access token.

---

![](https://developer.kobil.com/assets/images/oidc_token-7b693f5a5d778c1706734f5801a681df.png)

---
