// Source: Flutter app, splash view (_triggerStartEvent / _handleStartResult), trimmed; the reply of send() is an
// showActivation, showLogin and handleStartErrorCase are the app's own screens (not SDK calls).
// Either: left = the call failed, right = the result event. Continue by sdkState. Not compiled here.
import 'package:source file';

Future<void> triggerStartEvent(McWrapperHandler handler, EventT startEvent) async {
  try {
    final responseEvent = await handler.api.send(startEvent);
    responseEvent.fold((error) {
      handleStartErrorCase('start failed: $error');
    }, (response) {
      handleStartResult(response);
    });
  } catch (e) {
    handleStartErrorCase(e.toString());
  }
}

void handleStartResult(EventT response) {
  if (response is StartResultEventT) {
    switch (response.sdkState) {
      case SdkState.activationRequired:
      case SdkState.unidentified:
      case SdkState.uninitialised:
        showActivation();
        break;
      case SdkState.loginRequired:
        if (response.userList?.isNotEmpty == true) {
          showLogin(response.userList!);
        } else {
          handleStartErrorCase('login required but the user list is empty');
        }
        break;
    }
  }
}
