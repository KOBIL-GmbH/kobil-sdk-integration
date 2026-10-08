> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/hardening/hardening_topics> on 2026-09-28. Converted to Markdown; wording unchanged.

# Hardening Topics

### Hardening Differences Between Debug and Release Builds

### Antidebugging In Release Builds

In our Hardening and App Security process, we make sure that our software is secure and resilient. However, there are differences in how the software behaves in release and debug modes. It is crucial to conduct early testing with a release build to ensure everything works as expected. In a release build, debug support is disabled, meaning you cannot debug your app. If you try to attach a debugger, it is seen as an attack. Additionally, a message box automatically pops up to identify debug builds.

### Device Binding in Debug and Release Builds Differs

Device binding works differently in release and debug builds. Therefore, it is recommended to test update tests only with release SDK builds. However, you can conduct update tests between debug builds since they all share the same device binding.

### Integrity Check

During development, it is advisable to disable the integrity check. This is because every rebuild alters the running application, and enabling the integrity check would prevent any code changes.

### Start Early Release Tests With Enabled Integrity Check

To avoid complications with full security features enabled, begin early testing with release builds and the integrity check enabled.
