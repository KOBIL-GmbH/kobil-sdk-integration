> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/bridging-header> on 2026-09-28. Converted to Markdown; wording unchanged.

# Bridging-Header (iOS/Swift)

Sometimes in swift, you are not able to access some of the files of master controller SDK, so you have to add a bridging-header file in your application and import some of the header files in this.

Bridging-Header

```
#import <KSMasterController/KSMasterController.h>
#import <KSMasterController/KsScpEvents.h>
#import <KSMasterController/KsMacroEvents.h>
#import <KSMasterController/KsHelpers.h>
#import <KSMasterController/KsEcoModulInterface.h>
#import <KSMasterController/KSEvent.h>
```
