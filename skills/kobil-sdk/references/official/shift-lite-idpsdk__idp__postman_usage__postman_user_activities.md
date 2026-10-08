> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/postman_usage/postman_user_activities> on 2026-09-28. Converted to Markdown; wording unchanged.

# User Activities

### Create User

![](https://developer.kobil.com/assets/images/createUser-e52c097fe437aa7f0d5276b281375b31.png)

* **General Info:**

  + To create a new user, the username and email values should be unique and did not been used.
  + The created users will be displayed on your IDP service in real-time, and can be configured as desired.
* **Performing the API Request and Response:**

  + To get more information about the request body configurations and responses, you could check the [Create User API](https://developer.kobil.com/api/idp#tag/path/to/~1realms~1%7BtenantId%7D~1%7Bversion%7D_user/post) methods.
* **Sample of Request Body:**

  + Configure the request body parameters as outlined below and ensure that the specified parameters in the request body are set up according to the provided guidelines.

  ```
  {
  "username": "testUser",
  "email": "admin@example.com",
  "enabled": true,
  "emailVerified": false,
  "firstName": "test",
  "lastName": "adminBank"
  }
  ```

---

### Update User

![](https://developer.kobil.com/assets/images/updateUser-e4cfc0c4479f6f5b17af62c52421db00.png)

* **General Info:**

  + To change user's password and so on, the user name needs to be included in the request call.
  + In Postman request body, you are able to configure the newly created password as desired with the **value** parameter.
* **Performing the API Request and Response:**

  + For more information about the request body configurations and responses, you could check the [Update User API](https://developer.kobil.com/api/idp/#tag/path/to/updateUser) methods.

> **⚠️NOTE**: Since the format of the created passwords will be clear-text. The method should not be used for users created under the BDDK regulations.

---

### Get User by Name

![](https://developer.kobil.com/assets/images/getInfoByName-6cc816dad503491cdd626450eb3e8a48.png)

* **General Info:**

  + The API call allows you to access real-time user data, providing flexibility for further configuration within your IDP service.
* **Performing the API Request and Response:**

  + To get more information about the request body configurations and responses, you could check the [Get User by Name API](https://developer.kobil.com/api/idp#tag/path/to/~1realms~1%7BtenantId%7D~1v3_user~1%7BUserID%7D/get) methods.

---

### Get User by UUID

![](https://developer.kobil.com/assets/images/getInfoByUUID-2604df09280e80fbcdfc55384f529621.png)

* **General Info:**

  + This API call facilitates the retrieval of user details based on their unique UUID, offering real-time insights for further configuration within your IDP service.
* **Performing the API Request and Response:**

  + For more information about the request body configurations and responses, please follow the [Get User by UUID API](https://developer.kobil.com/api/idp#tag/path/to/~1admin~1realms~1%7BtenantId%7D~1users~1%7Bid%7D/get) methods.

---

### Create Activation Code

![](https://developer.kobil.com/assets/images/ActivationCode-c56035c87cb377c14fd030f6503be840.png)

* **General Info:**

  + In Postman request call, you can configure the activation code values by using the **secretData** parameter.
  + The validity period of the generated activation code is determined by **credentialData**. e.g. 60 days(**60d**), 60 minutes(**60m**), 60 seconds(**60s**).
* **Performing the Request:**

  + To create an activation code by utilizing the Activation Code API use following request:

  ```
  PUT https://idp.{{baseUrl}}/auth/admin/realms/{{tenant}}/users/{{app_user_uuid}}
  ```
* **Request Body:**

  + Configure the request body parameters as outlined below and ensure that the specified parameters in the request body are set up according to the provided guidelines.

  ```
  {
  "credentials" : [
  {
  "type" : "ACTIVATION_CODE",
  "credentialData" : "{\"period\" : \"60d\"}",
  "secretData" : "{\"code\" : \"68493536\"}"
  }
  ]
  }
  ```
* **Sample Response:**

  + Familiarize yourself with the expected response structure by referring to the [Sample Response Documentation](https://developer.kobil.com/docs/legacy-idp-docs/api/activationcodes/createactivationcode#sample-response).

---

### Get Client Device with UUID

![](https://developer.kobil.com/assets/images/getClientDevice-63f03c85a47d68cf9e69e5af279f4000.png)

* **General Info:**

  + To execute the request call, please filled in the app user IDs.
  + The API call allows you to access real-time client device details, and it's unique ID.
* **Performing the API Request and Response:**

  + For more information about the request body configurations and responses, please follow the [Get Linked Clients API](https://developer.kobil.com/api/ast/#tag/Client-Management/operation/getLinkedClientsByUserId) methods.

---

### Unlink User from Client Device

![](https://developer.kobil.com/assets/images/unlinkClientDevice-a612a82cb6b7b08f84dde4937cd33752.png)

* **General Info:**

  + The Client Device ID needs to be included in the request body, to unlink the specified users.
* **Performing the API Request and Response:**

  + To get more information about the request body configurations and responses, please follow the [Unlink User API](https://developer.kobil.com/api/ast/#tag/Client-Management/operation/unlinkUser) methods.

> **⚠️NOTE**: Since the same user can perform activation on multiple devices, the ID of the app user and Client Device must be presented in the request body.

---

### Delete User

![](https://developer.kobil.com/assets/images/deleteUser-c26acfe6a9c5ba2dc94d793b74c5446a.png)

* **General Info:**

  + To delete an existing user, an UUID of the user is required.
  + The deleted users will not be displayed on your IDP service anymore.
* **Performing the API Request and Response:**

  + For more information about the request body configurations and responses, please follow the [Delete User API](https://developer.kobil.com/api/idp#tag/path/to/~1realms~1%7BtenantId%7D~1v3_user~1%7BUsername%7D/delete) methods.

---
