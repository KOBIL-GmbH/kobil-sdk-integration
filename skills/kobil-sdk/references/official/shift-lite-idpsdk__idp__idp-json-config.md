> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/idp-json-config> on 2026-09-28. Converted to Markdown; wording unchanged.

# Configuration of Partial Import Json

Follow the steps below to integrate json file to your IDP service.

#### Epoch Timestamp Conversion and Password Setup in JSON

```
{
"users": [
{
"username": "idp_external_admin",
"createdTimestamp": "1708349829", //Add Up to date Epoch Converter value
"credentials": [
{
"type": "password",
"value": "</YourPassword>", //Set your password to the same as AST_ADMIN_PASSWORD
"temporary": false
}
],
...
}
],
"settings": {
"AST_ADMIN_USER": "idp_external_admin",
"AST_ADMIN_PASSWORD": "</YourPassword>",
...
}
}
```

* To set the users → "**createdTimestamp**" value, please check [Epoch Timestamp Conversion](https://www.epochconverter.com) web page.
* During the configuration, set the "**AST\_ADMIN\_PASSWORD**" and, user's → credentials "**value**" the same.

---

Sample of KSSIDP ClientId SetUp

```
{
"clientId": "KssIdpEnrollment",
"enabled": true,
"clientAuthenticatorType": "client-secret",
"login_theme": "kobil-lite",
"redirectUris": [
"*"
],
"protocol": "openid-connect"
...
}
```

> **NOTE**: To receive the full resource of the .json file, please contact with the KOBIL IDP services.

## Importing Json Configurations to the IDP

![](https://developer.kobil.com/assets/images/kc_import_json-f2160a2afec5bad3f759af2ec540da49.png)

* Navigate to your IDP service, then select your realm to import Json file.
* Click on **Select file** to upload your local Json.

---

![](https://developer.kobil.com/assets/images/kc_partial_import_config-ef0adb3c632fe702bcf2937f923b70a1.png)

* Before importing the Json file, please change the **If a resource exists** section to Skip to avoid duplication of client - ID values.

---

![](https://developer.kobil.com/assets/images/kc_added_clients-24efa8aa2882f5f2ef606ba1e86988c4.png)

* Once the Json file is successfully imported, you could see the client - ID values in your IDP service.

> In order to implement the secured authentication methods by **Shift Lite - KSSIDP**. You could check the client - ID values and their usage from the table below

| Client - ID | Description |
| --- | --- |
| `KssIdpEnrollment` | Client -ID value to complete the Shift Lite - IdpSdk [Activation](shift-lite-idpsdk__development__idpsdk__idpsdk-activation.md) / [Add User](shift-lite-idpsdk__development__idpsdk__idpsdk-add-user.md) method. |
| `KssIdpLogin` | Client -ID value to complete the Shift Lite - IdpSdk [Login](shift-lite-idpsdk__development__idpsdk__idpsdk-login.md) method. |
| `KssIdpChangePassword` | Client -ID value to complete the Shift Lite - IdpSdk Change Password method. |
| `KssIdpForgotPassword` | Client -ID value to complete the Shift Lite - IdpSdk Forgot Password method. |
