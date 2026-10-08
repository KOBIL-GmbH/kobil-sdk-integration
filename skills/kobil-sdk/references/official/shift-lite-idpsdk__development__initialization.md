> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/initialization> on 2026-09-28. Converted to Markdown; wording unchanged.

# Initialization of the MasterController (iOS/Swift)

Always begin by calling the StartEventEx function from the MasterController SDK.

Develop an Adapter class to handle communication between your application and the MasterController SDK.

MasterControllerHandler

```
import Foundation
import KSMasterController
import ObjectiveC.runtime
/// main access to c++ master controller
class MasterControllerAdapter: KSAsyncEventReceiver {
static let sharedInstance: MasterControllerAdapter = {
var sharedInstance = MasterControllerAdapter()
return sharedInstance
}()
/// the master controller instance
var masterController: (KSAsyncEventReceiver & KSEcoModulInterface & KSEventSource)?
private init() {
if masterController == nil {
masterController = KSMasterControllerFactory.getMasterController(withParmeter: "", andConsumer: self)
}
}
}
```
