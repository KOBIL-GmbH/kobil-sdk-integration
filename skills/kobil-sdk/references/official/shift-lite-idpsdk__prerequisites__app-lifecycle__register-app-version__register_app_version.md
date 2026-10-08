> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/app-lifecycle/register-app-version/register_app_version> on 2026-09-28. Converted to Markdown; wording unchanged.

# Details

Keep in mind that on the first login with the freshly registered app version you need to do a login with the 'app registrar user'. By default, this is the same user that you used for registration at the server. So either make sure to use an appropriate user during registration or do the extra steps required to set a different 'app registrar user'. For example, if your login/activation process relies on having a valid Email address as the user name and getting an automatic confirmation Email, then you need to either use that same Email address as login name for the KOBIL Portal when accessing it to register a new app version or you need to determine the UUID-style userId of the user with that Email address and set that as the 'app registrar user'.

### Register App Version via KOBIL Portal

1. Register new app version in AST Services by using the KOBIL Portal.  
   1.1 Go to App Management \ Apps Versions and press 'Add App Version' button:
   ![](https://developer.kobil.com/assets/images/add_app_version_Shift1-d22394c6e512b9bcbf52480c2fb9e3a6.png)  
   1.2 Enter 'App Version' number of your build app:
   ![](https://developer.kobil.com/assets/images/add_app_version_Shift2-7044a64df6e8bbfd2e00623868012a9f.png)

> **Note**: Be sure that you enabled 'Integrity' for productive apps.

2. Define the registration user for this app version (**only** needed when current user of KOBIL Portal will not be the later registration user)  
   2.1 Go to App Management \ Apps Versions, select an app and press 'Edit Version':
   ![](https://developer.kobil.com/assets/images/add_app_version_Shift3-0d3776b4afabcb1bca12f500e595514f.png)  
   2.2 Set the correct 'App Registrar' user
   ![](https://developer.kobil.com/assets/images/add_app_version_Shift4a-9a9f2247fb046d1f4bb621e52b80576b.png)

> **Note**: You need use the user id, not the user name for the 'app registrar user'!  
> **Note**: Be sure that you enabled 'Integrity' for productive apps.

3. Do a normal login / activation with the registration user inside the app.

> **Note**: For additional details see KOBIL Portal documentation.

### Register App Version via cURL CLI

> **Note**: All of the described API requests require an authorization token, see [**Getting Authorization Tokens**](shift-lite-idpsdk__prerequisites__auth_token_shift.md).
> While the request to get an authorization token will use the subdomain **idp** all your App/App Version related requests should use the subdomain **asts**

##### Create a New App Version

```
curl -v -X POST https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/versions -H 'Content-Type: application/json' -H 'Content-Type: application/json' -d '{
"appName": "",
"platform": "",
"versionStr": "",
"registerUserId": "",
"versionLock": false,
"isCheckIntegrity": true
}' -H 'Authorization: Bearer $token'
```

> **your-environment.shift.company.com** should be replaced by the suitable host name of your environment. While the request to get an authorization token will use the subdomain **idp** all your other requests should use the subdomain **asts**.  
> **$yourTenantName** must be the tenant managing the app and its version. For a short discussion of tenants see the corresponding section of the [overview](shift-lite-idpsdk__prerequisites__app-lifecycle__add-app__add_app_overview.md#tenants).  
> For **appName**, **platform**, **versionStr** and **registerUserId** you need to provide the appropriate values for the app version you want to register.  
> **versionLock** is a boolean (i.e. either `true` or `false`) that decides whether or not the version is locked.  
> **isCheckIntegrity** is a boolean (i.e. either `true` or `false`) that decides whether or not app integrity is enforced by comparing a hash over the app against the value that is stored on the server when the registerUser connects to the server for the first time. This, of course, increases security and is strongly recommended for productive apps, but it can be troublesome when some new OS version automatically tries to "optimize" the app in some creative way.  
> **$token** should be an authorization token of a user with the correct permissions / roles to add apps.

Here, -v option is to run the command in verbose mode.
On successful creation of an App Version, it returns created version location URL with `version-id` in the response header as shown in the below screenshot, when you run the create new version cURL command with -v option.

![](data:image/png;base64,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)

The returned **location** URL containing the version-id is required for updating or deleting an existing App Version as shown in following cURL commands.

##### Update existing App Version

For updating a version you need to know the versionId of the version you want to update.
You will get the versionId upon successfully creating a new app version with the verbose option as described in [**Create New App Version**](#create-a-new-app-version).
Alternatively if you created the app version without verbose flag or forgot the versionId you can find the ID of your version by using the request to [**Get a list of App Versions**](#get-a-list-of-app-versions).
Note that for deleting the registration values for the app, so you get back to the state just after app registration but before logging in for the first time, you cannot use this update request. Instead you need the request decribed in [**Delete App Version Registration Value**](#delete-app-version-registration-value) below.

```
curl -X PUT https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/versions/$versionId -H 'Content-Type: application/json' -H 'Content-Type: application/json' -d '{
"appName": "",
"platform": "",
"versionStr": "",
"registerUserId": "",
"versionLock": false,
"isCheckIntegrity": true
}' -H 'Authorization: Bearer $token'
```

##### Get a list of App Versions

Here is a request that gives you a list with all the versions of all the apps registered for a specific tenant.

```
curl https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/versions -H 'Content-Type: application/json' -H 'Authorization: Bearer $token'
```

You can add pagination parameters like page and pagesize to just get part of that list, e.g. to select entries 21 to 40 a request like the following can be used:

```
curl https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/versions?page=2&pageSize=20 -H 'Content-Type: application/json' -H 'Authorization: Bearer $token'
```

##### Get information for an existing App Version

Here is a request for just getting all the information the server has stored about a specific app version:

```
curl https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/versions/$versionId -H 'Content-Type: application/json' -H 'Authorization: Bearer $token'
```

##### Get all available platforms

```
curl https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/platforms -H 'Content-Type: application/json' -H 'Authorization: Bearer $token'
```

##### Get all available architectures for a platform

Some platforms (like e.g. Android) might support multiple hardware architectures. Got get a list of all the architectures that are supported by a specific platform, you can use the following request

```
curl https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/platforms/$platformName/architectures -H 'Content-Type: application/json' -H 'Authorization: Bearer $token'
```

> **$platformName** should be the name of one of the platfomrs obtained from the [**previous request**](#get-all-available-platforms).

##### Delete App Version Registration Value

```
curl -X DELETE https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/versions/$versionId/register?architectureName=$architecture -H 'Content-Type: application/json' -H 'Authorization: Bearer $token'
```

> **$architecture** should be the name of the architecture for which you want to delete the registration value. This should be one of the architectures obtained from the [**previous request**](#get-all-available-architectures-for-a-platform).

##### Delete existing App Version

```
curl -X DELETE https://asts.your-environment.shift.company.com/v1/tenants/$yourTenantName/versions/$versionId -H 'Content-Type: application/json' -H 'Authorization: Bearer $token'
```
