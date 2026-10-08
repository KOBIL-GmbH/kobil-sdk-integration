> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/postman_usage/postman_tms> on 2026-09-28. Converted to Markdown; wording unchanged.

# TMS APIs

### Display Message

![](https://developer.kobil.com/assets/images/DisplayMessage-9201e02f14c263dbb152b32d7c34fa81.png)

* **General Info:**

  + To send a Display Message to the specified users, the user ID or client ID needs to be included in the request body.
  + After the request call is sent, the unique ID of the Display Message will be displayed in response for further tracking.
* **Performing the API Request and Response:**

  + For more information about the request body configurations and responses, please follow the [Send a Display Message API](https://developer.kobil.com/api/ast/#tag/Message-Sign/operation/sendDisplayMessage) methods.

---

### Trigger Transaction

![](https://developer.kobil.com/assets/images/triggerTransaction-cf40ae4eca4a031b216bb00a8dfe39a0.png)

* **General Info:**

  + Specify the user's ID in the request call to trigger the transaction.
  + The information presented to the user during the transaction is encapsulated in the **tmsData** parameter.
  + Set the transaction's validity period using the **retrievalTimeout** and **tmsTimeOut** parameters.
  + Upon sending the request call, obtain the unique transaction ID and its status for further tracking.
* **Performing the Transaction with Push Notification:**

> 1. Set the push notification provider API key, during the [App Creation](#create-app-name) process.
> 2. On the app side, trigger the [SetPushTokenEvent](shift-lite-idpsdk__development__push-notification__push-token.md) via MCSDK.
> 3. Add the **"push"** method from the **Trigger Transaction API** to your Postman request body.

To get more information about the request body configurations and responses, please follow the [Trigger Transaction API](https://developer.kobil.com/api/ast/#tag/Message-Sign/operation/startTms) methods.

---

### Get Transaction Result

![](https://developer.kobil.com/assets/images/getTransactionInfo-be60e4591deda6fa22cd8ae8894931f9.png)

* **General Info:**

  + To retrieve the transaction result, the transaction ID needs to be included in the request call.
  + The transaction result, such as **ACCEPTED**, **REJECTED**, and **TIMEOUT**, will be displayed in the response, if it is available. If no transaction result is known yet, you will get an error message.
* **Performing the API Request and Response:**

  + To get more information about the request body configurations and responses, you could check the [Get Transaction Result API](https://developer.kobil.com/api/ast/#tag/Message-Sign/operation/getTmsResult) methods.

---

### Cancel Transaction

![](https://developer.kobil.com/assets/images/cancelTMS-7d3a24a72c7996a6e6c13b3fb522dafe.png)

* **General Info:**
  + With an simple click, you can cancel an ongoing transaction in your workspace.
  + To execute the request call, the unique ID of the transaction needs to be defined.
* **Performing the API Request and Response:**
  + For more information about the request body configurations and responses, you could check the [Cancel an Ongoing TMS API](https://developer.kobil.com/api/ast/#tag/Message-Sign/operation/cancelTms) methods.
