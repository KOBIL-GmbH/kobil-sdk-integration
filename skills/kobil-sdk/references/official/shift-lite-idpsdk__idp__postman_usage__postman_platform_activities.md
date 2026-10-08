> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/postman_usage/postman_platform_activities> on 2026-09-28. Converted to Markdown; wording unchanged.

# Platform Activities

### KSSIDP Supported Platforms

![](https://developer.kobil.com/assets/images/getAvaliablePlatforms-5a4ee5d5a9e420c94f32df92816d2c5c.png)

* **General Info:**

  + Indicates the operating system that KSSIDP supports
* **Performing the API Request and Response:**

  + For more information about the request body configurations and responses, please follow the [List All Platforms API](https://developer.kobil.com/api/ast#tag/Version/operation/listPlatforms) methods.

---

### Create App Name

![](https://developer.kobil.com/assets/images/createApp-f8f6b4b6cbfa182b0c4fbb945831a26a.png)

* **General Info:**

  + The primary objective is to create an app by specifying its name, and the newly created app will be promptly displayed on the Smartdashboard in real-time.
  + In Postman request calls, you can configure your categories of the app, choosing between **CHAT** and **TMS**.
* **Performing the Request:**

  + To create an app by utilizing the Create App API use following request:

  ```
  POST https://asts.{{baseUrl}}/v1/tenants/{{tenant}}/apps/{{app_name}}
  ```
* **Request Body:**

  + Configure the request body parameters as outlined below and ensure that the specified parameters in the request body are set up according to the provided guidelines.

  ```
  {
  "categories": ["chat"]
  }
  ```

> ***NOTE***: If push notification features are required for the created app, customers must define their **Android API key**, **iOS Bundle ID**, or **HPK Client ID** values in the [body](https://developer.kobil.com/api/ast#tag/Version/operation/saveApp) of the request call, see section [Add App in Security Server in KOBIL Shift Lite](shift-lite-idpsdk__prerequisites__app-lifecycle__add-app__add_app.md) for the details of how to obtain the needed values.

---

### Create App Version

![](https://developer.kobil.com/assets/images/createAppVersion-e23597c827fc8e87b893630480edad4a.png)

* **General Info:**

  + The app version registration is performed with the ID of the created users.
  + Based on the operating system where the app will be executed, platform can be selected as **Android** / **iOS**.
  + The version number setup represents the *major*, *minor*, *build* numbers of your app, and it is defined in the **versionStr** parameter.
* **Performing the API Request and Response:**

  + To get more information about the request body configurations and responses, you check the [Create App Version API](https://developer.kobil.com/api/ast/#tag/Version/operation/createVersions) methods.
* **Sample of Request Body:**

  + Configure the request body parameters as outlined below and ensure that the specified parameters in the request body are set up according to the provided guidelines.

  ```
  {
  "appName": "TestApp",
  "platform": "Android",
  "versionStr": "1.0.0",
  "registerUserId": "a13c2c21-6dc7-4d1f-96e3-2aa560f84bda",
  "versionLock": false,
  "isCheckIntegrity": false
  }
  ```

> ***NOTE***: A user can register as many app versions as desired, but app names must be different from the others.

---

### Get App Details by Version ID

![](https://developer.kobil.com/assets/images/getVersionId-f6f81fc33887329ff3b9707eac282e93.png)

* **General Info:**

  + This API call facilitates the retrieval of app version details based on Tenant/Workspace name.
* **Performing the API Request and Response:**

  + For more information about the request body configurations and responses, please follow the [Get Version ID API](https://developer.kobil.com/api/ast/#tag/Version/operation/listVersions) methods.

---

### Update App Version

![](https://developer.kobil.com/assets/images/updateAppVersion-15134145b2f0d73a48dbd92ad5798096.png)

* **General Info:**

  + Application upgrade is performed with the ID of created app version.
  + Please note that, the version of your application defined in the **versionStr** parameter of your request body.
* **Performing the API Request and Response:**

  + For more information about the request body configurations and responses, you check the [Update App Version](https://developer.kobil.com/api/ast#tag/Version/operation/updateVersions) methods.

> ***NOTE***: A user can update the same app as many times as want, however the **appName**, **platform**, and **registerUserId** parameters must be equal to, when the app was first created.

---

### Delete App Version

![](https://developer.kobil.com/assets/images/deleteAppVersion-14d265ac748fda574c3b77e275866730.png)

* **General Info:**

  + To delete an existing app version, an ID of the version is required.
  + The deleted versions will not be displayed on your Workspace anymore.
* **Performing the API Request and Response:**

  + To get more information about the request body configurations and responses, please follow the [Delete App Version API](https://developer.kobil.com/api/ast#tag/Version/operation/deleteVersionById) methods.

---

### Delete App's Integrity Check Value

Method of obtaining Architecture Integrity Values.

![](https://developer.kobil.com/assets/images/getVersionIdIntegrety-effca06ade69587dce4a5244551fd51d.png)

#### **General Info:**

* To delete integrity registered App Versions, it's necessary to receive **architecture** name.

Example of the Query Parameter setup.

![](https://developer.kobil.com/assets/images/deleteAppIntegrety-ab83fd071a1aeb5c3a8fcb9cadffdfab.png)

#### **General Info:**

* Remember that to delete an existing app version or to delete an integrity check value from the app, an ID of the version is required.
* Use the **architecture** name as a Query parameter of your API call.
* For more information about the request body configurations and responses, you could check the [Delete App Registration](https://developer.kobil.com/api/ast#tag/Version/operation/deleteAppRegister) method.
