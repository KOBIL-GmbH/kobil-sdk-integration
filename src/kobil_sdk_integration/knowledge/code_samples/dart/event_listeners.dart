// Source: Flutter WLA app sdk_handler event listeners (source file, source file,
// source file), trimmed. A listener says which events it wants (isSubscribed) and gets them in onEventReceived.
// Rules from the official error-handling page: a RuntimeErrorEvent is pushed and the SDK restarts itself afterwards, so handle it
// right away and do not wait for the result of the request that was running. Not compiled here.
import 'dart:async';
import 'package:source file';

abstract class EventListener {
  bool isSubscribed(EventT event);
  void onEventReceived(EventT event);
}

class RuntimeErrorEventListener implements EventListener {
  final _runTimeErrorStreamCtrl = StreamController<int>.broadcast();
  final List<Type> _eventsToSubscribe = [RuntimeErrorEventT];

  Stream<int> get runTimeErrorStream => _runTimeErrorStreamCtrl.stream;

  @override
  bool isSubscribed(EventT event) => _eventsToSubscribe.contains(event.runtimeType);

  @override
  void onEventReceived(EventT event) {
    if (event is RuntimeErrorEventT) {
      _runTimeErrorStreamCtrl.add(event.errorCode);
    }
  }
}

class AuthEventListener implements EventListener {
  final _startLoginStreamCtrl = StreamController<List<dynamic>>.broadcast();
  final _loginResultStreamCtrl = StreamController<void>.broadcast();
  final List<Type> _eventsToSubscribe = [StartLoginEventT, LoginResultEventT];

  Stream<List<dynamic>> get loginRequestStream => _startLoginStreamCtrl.stream;
  Stream<void> get loginResultStream => _loginResultStreamCtrl.stream;

  @override
  bool isSubscribed(EventT event) => _eventsToSubscribe.contains(event.runtimeType);

  @override
  void onEventReceived(EventT event) {
    if (event is StartLoginEventT) {
      _startLoginStreamCtrl.add(event.userIdentifiers ?? []);
    } else if (event is LoginResultEventT) {
      _loginResultStreamCtrl.add(null);
    }
  }
}
