> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/postman_usage/postman_general> on 2026-09-28. Converted to Markdown; wording unchanged.

# General Structure

To integrate Postman we offer a comprehensive walkthrough of utilizing Postman API requests to seamlessly interact with KOBIL IDP services. Covering backend operations, each section dives into specific functionalities, providing detailed explanations and visual representations. From generating authorization tokens to triggering transactions, this guide ensures a robust understanding of integrating Postman effectively into your workflow.

### **WorkSpace Setup**

![](https://developer.kobil.com/assets/images/envDetails-bb55d8e0f4491d12347c1b505fecced3.png)

| Variable | Description | Mandatory |
| --- | --- | --- |
| **baseUrl** | Host url value of your KOBIL IDP console | Yes |
| **tenant** | Workspace name of your IDP Server | Yes |
| **access\_token** | Unique Token value to securely operate your workspace | Yes |
| **username\_with\_admin\_role** | The username, which used to access your KOBIL IDP console | Yes |
| **password** | The Password value of the user, which is in administrator role | Yes |
| **platform\_name** | Defines the desired Operating System to be used in your platform | No |
| **app\_name** | Represents the app's name, which registered on your platform | No |
| **app\_user\_name** | Name of users who'll use your KOBIL IDP secured product | No |
| **app\_user\_uuid** | Identity of users created in your workspace | No |
| **tmsId** | The unique ID value, when users perform a transaction | No |

---

### **Collection Specific**

![](https://developer.kobil.com/assets/images/generalStructure-1935e26f9788190b2b8f56488e4f92af.png)

> The KSSIDP Auth Collections are divided into 4 different file structures, while receiving the access token in the IDP Admission section, you could control your workspace in the platform / user activities sections. Further, you can easily perform and secure your transactions to your app users via TMS APIs.

## **IDP Admission**

### Generate Authorization Token

![](https://developer.kobil.com/assets/images/authorizationToken-5374280b8dafb653a5c32e6d81ed6857.png)

* **General Info:**

  + All the Postman API requests are processed with **access\_token** values, and tokens are valid for every 300 seconds.
  + To get the access\_token in your Workspace, please configure the body part of the **Authorization Token** request.
* **Performing the API Request and Response:**

  + To get more information about the request body configurations and responses, please follow the [Authorization Token API](https://developer.kobil.com/api/idp#tag/Authorization/paths/~1realms~1%7BtenantId%7D~1protocol~1openid-connect~1token/post) methods.

> KOBIL - IDP services will provide you **username** and **password** values, and these credentials will allow you access to the IDP console, and Smartdashboard of your workspace.
