> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/mc-config-files/mc_configuration_files_overview> on 2026-09-28. Converted to Markdown; wording unchanged.

# MC Configuration Files Overview

A KOBIL Secured app is always tied to a KOBIL Security Server installation; therefore, such an app must provide some configuration files to the MasterController. The required files depend on the KOBIL solution used.

## Configuration Requirements by Solution

* KOBIL Digitanium
* KOBIL Digitanium+
* KOBIL Shift Lite TWV
* KOBIL Shift Lite KSSIDP

For **KOBIL Digitanium**, the Security Server is an **SSMS**, and the required configuration files are:

* **`sdk_config.xml`** - Signed by the SSMS server
* **`mc_config.json`** - Contains Master Controller configuration

**Detailed Configuration Guides:**

* [SDK Config XML](https://developer.kobil.com/docs/mcsdk-docs/digitanium/prerequisites/mc-config-files/sdk_config_xml)
* [MC Config JSON for Digitanium](https://developer.kobil.com/docs/mcsdk-docs/digitanium/prerequisites/mc-config-files/mc_config_json_digitanium)

For **KOBIL Digitanium+**, the Security Server is an **SSMS** in combination with a KOBIL IDP server, and the required configuration files are:

* **`sdk_config.xml`** - Signed by the SSMS server
* **`mc_config.json`** - Contains Master Controller configuration

**Detailed Configuration Guides:**

* [SDK Config XML](https://developer.kobil.com/docs/mcsdk-docs/digitanium-plus/prerequisites/mc-config-files/sdk_config_xml)
* [MC Config JSON for Digitanium+](https://developer.kobil.com/docs/mcsdk-docs/digitanium-plus/prerequisites/mc-config-files/mc_config_json_digitanium+)

For **KOBIL Shift Lite TWV (Trusted Web View)**, the Security Server consists of AST Services in combination with a KOBIL IDP server. The required configuration files are:

* **`sdk_config.jwt`** - Signed by AST Services
* **`mc_config.json`** - Contains Master Controller configuration

**Detailed Configuration Guides:**

* [SDK Config JWT](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-twv/prerequisites/mc-config-files/sdk_config_jwt)
* [MC Config JSON for Shift](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-twv/prerequisites/mc-config-files/mc_config_json_shift)

For **KOBIL Shift Lite KSSIDP (KOBIL Secure Sign-In with Identity Provider)**, the Security Server consists of AST Services in combination with a KOBIL IDP server. The required configuration files are:

* **`sdk_config.jwt`** - Signed by AST Services
* **`mc_config.json`** - Contains Master Controller configuration

**Detailed Configuration Guides:**

* [SDK Config JWT](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-kssidp/prerequisites/mc-config-files/sdk_config_jwt)
* [MC Config JSON for Shift](https://developer.kobil.com/docs/mcsdk-docs/shift-lite-kssidp/prerequisites/mc-config-files/mc_config_json_shift)

## Project File Structure Examples

### Android/Kotlin Projects

Structure of the Kotlin projects.

```
├── artifacts
│
├── app
│   └── src
│       ├── main
│       │   ├── AndroidManifest.xml
│       │   ├── java
│       │   │   └── com
│       │   │       └── yourCompany
│       │   │               └── yourApp
│       │   │                       ├── ...
│       │   │
│       │   └── assets
│       │       └── yourEnvironment
│       │                  ├── sdk_config.xml/.jwt
│       │                  ├── mc_config.json
│       │                  └── SSL_certificate.pem
│       │
```

### iOS/Swift Projects

Structure of the Swift projects.

```
├── artifacts
│
├── yourApp
│   ├── Extensions
│   ├── Models
│   ├── Views
│   └── Resources
│         └── assets
│              └── yourEnvironment
│                         ├── sdk_config.xml/.jwt
│                         ├── mc_config.json
│                         └── SSL_certificate.pem
```

## Trust Store Management

These configuration files (and some other places) require you to manage a "trust store." We recommend first reading and understanding the documentation on [which certificates to put into that trust store](shift-lite-idpsdk__prerequisites__mc-config-files__trust_store.md) before creating configuration files.

The trust store contains certificates that your application trusts for secure communication with KOBIL servers. Proper trust store configuration is critical for security and successful connection establishment.
