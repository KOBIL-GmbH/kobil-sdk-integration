> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/prerequisites/app-lifecycle/register-app-version/register_app_version_overview> on 2026-09-28. Converted to Markdown; wording unchanged.

# Overview

The Security Server only accepts "registered" app versions when users want to activate/login with their user accounts, so each app version must be registered before using the app for the first time. You can freely give the version numbers within certain parameters, but you must use a 3 digit format for it.
This version number is not shown to the user, it must be handed over from app to MasterController. It can differ from the version number shown in app stores or on iOS/Android app detail screen, but best practice is to use same app version number for Security Server and app stores.

In this "registration" process we also store some App Integrity Check parameters, so manipulated apps are detected by the Security Server. This App Integrity Check parameter differs per platform (iOS or Android) and architecture (ARM v7 (32 Bit), ARM v8 (64 Bit), ...), so they must be stored multiple times.

The registration steps differ for each KOBIL solution, however you always need access to the corresponding server (SSMS or KOBIL portal), so you need to get the URL from your system administrator, who also must provide credentials so you can access the server.
