> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/idp/idp-realm-management> on 2026-09-28. Converted to Markdown; wording unchanged.

# Realm Management

Realm is a container for users, applications, and clients. It oversees the creation, configuration, and deletion of realm entities. The IDP has a default **master** realm for creating and managing new realms. Each realm is isolated and contains entities unique to that realm.

Here are some key points regarding the Realm:

* Realm can be created by following the certain steps mentioned [here](https://developer.kobil.com/docs/idp-docs/administration/realm-management/#realm-creation)
* Within the realm, you can control specific configurations such as [Email settings](https://developer.kobil.com/docs/idp-docs/administration/realm-management/#email-settings) and [SMS settings](https://developer.kobil.com/docs/idp-docs/administration/realm-management/#sms-settings).
* [Copy Features](https://developer.kobil.com/docs/idp-docs/administration/realm-management/#copy-features) enables the transfer of entities and configuration patterns from the Master realm to subordinate realms.
* By enabling **Risk Bits** over Realm Settings section you can restrict risky devices (device with higher risk score) from performing certain actions. You can check the complete detail regarding Risk Bits [here](https://developer.kobil.com/docs/idp-docs/administration/realm-management/#riskbits).

You can explore additional features within the Realm to gain greater control over IDP services. For comprehensive details, refer this [link](https://developer.kobil.com/docs/idp-docs/administration/realm-management).
