> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/idp-anonymous-enrollment-config> on 2026-09-28. Converted to Markdown; wording unchanged.

# Requirements for Anonymous Activation

Follow the recommended steps below to restrict or configure Anonymous Enrollment in your identity provider platform.

### Step1: Create Client ID into your workspace

![](https://developer.kobil.com/assets/images/kc23_anonymous_step1-2891b50a9c5af9298328196819d45781.png)

* Click on Create client button to proceed.

---

#### Add Client Name

![](https://developer.kobil.com/assets/images/kc23_anonymous_create-client-603791aa1b05d06a98a8b9ba682c09a5.png)

* Enter your unique client IDs name to begin with Anonymous Activation progress.

---

#### Secure your Clients End Points

![](https://developer.kobil.com/assets/images/kc23_anonymous_set_redirect_uri-8be2fea25e54061138dc59b3491d47c4.png)

* Enter the valid redirect URIs as `https://kobil/OpenIdRedirectUri` to complete client creation.

---

### Step2: Complete AST Client Scope

![](https://developer.kobil.com/assets/images/kc23_anonymous_step2-87d5089f8d19add43fb7a0415760e36a.png)

* Navigate to **Client Scope** page to acquire token data between your app to IDP.

---

#### Client Scope

![](https://developer.kobil.com/assets/images/kc23_anonymous_scope-cad49df08f16956e9b9a192a87b7e213.png)

* Click on Add client scope button.

---

#### Set AST Token Mapper

![](https://developer.kobil.com/assets/images/kc23_anonymous_add_token_mapper-3e5b69c6902490180aa82ca1fe8642d4.png)

* To complete the client scope, you could assign **AST Token Mapper** as **Defult** type.

---

### Step3: Set Anonymous Browser Flow

![](https://developer.kobil.com/assets/images/kc23_anonymous_step3-c1dc3badde7dc5cfb7f732b44f837c73.png)

* Navigate to the Advance option of your Client, and redirect to the end of the page.

---

#### Change Client's Browser Flow

![](https://developer.kobil.com/assets/images/kc23_anonymous_browser_flow-49f3912da94303386e046d7967bc52ea.png)

* Set Browser flow as Anonymous Device Enrollment.

---

### Final Step: Add AST Claim to Browser Flow

![](https://developer.kobil.com/assets/images/kc23_anonymous_auth_config-32aba35bfe47a767633963910b1c769f.png)

* Navigate to Authentication section of the IDP to add Step into your Browser Flow.

---

#### Create Step for Browser Flow

![](https://developer.kobil.com/assets/images/kc23_anonymous_add_step-00f60c190806fb833f00bf8b4592dc4b.png)

* Click on Add Step button.

---

#### Select AST Claim

![](https://developer.kobil.com/assets/images/kc23_anonymous_ast_claims-33b28dc8c8cfaa82d6833956d4a946df.png)

---
