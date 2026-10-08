> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/app-lifecycle/add-app/add_app_overview> on 2026-09-28. Converted to Markdown; wording unchanged.

# Add App in Security Server Overview

### Tenants

An important concept used by the security server is the **tenant**. Tenants can manage their own users and their on specific apps, e.g. to seperate different companies in a cloud systems or to split your administration tasks between multiple independent administration teams by using a separate tenant for each team.
However, especially in the KOBIL Shift Lite case, each tenant also adds to administrative overhead, as you need to maintain separate configuration files and apps for each tenant. In the case of KOBIL Digitanium / Digitanium+, this is mitigated by the concept of the MASTER tenant which manages all the tenants, which provides the app configuration files that are valid for all tenants, and which is able to add apps that are made available to all tenants by using the "One App for All tenants" mode available in the dialog for adding a new app version. So, for KOBIL Digitanium / Digitanium+ environments it is up to you whether you use just the MASTER tenant and ignore the concept of the sub-tenants, while for KOBIL Shift Lite you always have to use your specific tenant which is completely independent of other possibly existing tenants.

### AstAppName

The Security Server and our Push Notification service supports multiple apps per tenant, so each app must be registered with one unique AstAppName. This AstAppName is not shown to the user, it must be handed over from app to MasterController. It can differ from the app name shown on app stores or on iOS/Android home screen.

### Push Notifications via Apple's APNs server

When sending Push Notifications via Apple's APNs server, remember to correctly choose the development mode. The "Development server" typically is only used when you are running your app directly via Xcode, e.g. when debugging, while everything that involves a signed package uses the "Production server", no matter whether that package is distributed locally via the Ad-hoc-mechanism, whether it is distributed via Testflight, or whether it is distributed via the App Store. Remember to upload the correct certificates corresponding to your use case.

### Credentials

The registration steps differ for different KOBIL solutions, however you always need access to the corresponding server (SSMS or KOBIL portal), so you need to get the URL from your system administrator, who also must provide credentials so you can access the server.
