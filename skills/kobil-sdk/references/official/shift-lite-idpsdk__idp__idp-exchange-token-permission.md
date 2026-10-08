> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/idp-exchange-token-permission> on 2026-09-28. Converted to Markdown; wording unchanged.

# Configuration of Token Permissions

IDP 5 provides a high-level and effective solution to handle the exchange of your tokens between your external services.

Follow the recommended steps below to restrict or configure Exchange IAM Token features in your identity provider platform.

### Step1: Create Client Policy into your workspace

![](https://developer.kobil.com/assets/images/kc23_realm_managment-b9f9e7c0fb7e0a5998de3d4a83352ecc.png)

* Search for the realm-management in your client list, then select it.

---

#### Create Client Policy

![](https://developer.kobil.com/assets/images/kc23_create_client_Policy-f74ba401d7af56ed7db6601c9bf8ba47.png)

* Reach to the **Authorization** -> **Policies** section of your realm-management, and press Create policy button.

---

#### Choose Policy Type

![](https://developer.kobil.com/assets/images/kc23_choose_policy_type-56e4e4e7a40657d93d34be4e620e256c.png)

* While creating a policy, please select the policy type as **Client**. This will support you to define your Source Client.

---

#### Setup your Client Policy

![](https://developer.kobil.com/assets/images/kc23_set_client_policy-a51f76f9b2c67a4a7765788b6906c9fa.png)

* Once the policy type is slected as Client, please specify the name of your policy and Source Client.

> **⚠️NOTE**: Any client of your Workspace could be assigned as a Source Client, but clients used for the Authentication methods should not be selected.

---

### Step2: Apply Policy to your Target Client

![](https://developer.kobil.com/assets/images/kc23_target_client_permission_on-7fd978214fcb2216ddf420b1d14245e5.png)

* Let's assume that, Target Client(audience) is created in your workspace, and called as ExchangeToken.
* Navigate to Permissions section of your Target Client.
* Then turn ON the **Permission enabled** option to remove all current permissions that have been set up.

---

#### Allow Exchange Token Features

![](https://developer.kobil.com/assets/images/kc23_target_client_enable_token_permission-7fcd306b92f0d88cf8e9be6c90102ea1.png)

* Once the permission is enabled, select the token-exchange option to identify your policy, which allow to exchange token between the external services.

---

#### Apply your Client Policy

![](https://developer.kobil.com/assets/images/kc23_target_client_apply_policy-6779dcdf97dd16f32b58fd15bdc328be.png)

* In the final step, you could easily apply your created Client Policy, and save your changes.

---

### Step3: Configure the Token Permission

![](https://developer.kobil.com/assets/images/kc23_add_scope-471e21bf3ad252688490ac127bdfb05f.png)

> Since the **Exchange IAM Token** requires audience to be triggered via Rest API or MC SDK, it's permissions are recommended to be configured.

* Reach to the **Client scopes** -> **Setup** section of your Target Client, and press Add client scope button.

---

#### Add AST Token Mapper

![](https://developer.kobil.com/assets/images/kc23_add_ast_token_mapper-82edbeb078f6dcfe59ce45389fe0d0ce.png)

* To allow storing the user data in a secure way in the external services, you could assign **AST Token Mapper** as **Defult**.

---

#### Determine the Client's Dedicated

![](https://developer.kobil.com/assets/images/kc23_add_token_dedicated-b6490adce652695a7a7451f16216ac2f.png)

* Once the AST Token Mapper is assigned to your Target Client, press the TargetClientName-dedicated button, to start configuring your Client's Mappers & Scope.

---

#### Disable Full Scope

![](https://developer.kobil.com/assets/images/kc23_disable_full_scope-1fb07fe1768e90e88fcb6afc2ab67718.png)

* Navigate to Scope section, then turn OFF the **Full scope allowed** option to initiate Client & Realm Roles.

---

#### Assign Minimal Permissions

![](https://developer.kobil.com/assets/images/kc23_add_assign_role-65ac0df89f68a2cd118610ed3d3b3636.png)

* To manage account activities via created tokens in the external services(Exchange IAM Token) with the minimal permissions;
* Assign the Scope roles as **digitanium\_user**, and **query-users** to your Target Client(audience).

> After adding all the permissions, this token can be used in external service requests such as getting a user's information by name or uuid. In this way MC-Token is secured and not exposed outside of MC SDK but this exchanged token is used for such operations.
