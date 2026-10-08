// Source: Flutter app, McWrapperHandler (the class that owns the wrapper), trimmed (logging removed). One handler owns the
// wrapper: send() returns the reply of a request, pushed events go to every observer. Not compiled here.

class McWrapperHandler extends McWrapperApiEventReceiver {
  late McWrapperApi _mcWrapperApi;
  static final McWrapperHandler _instance = McWrapperHandler._internal();

  List<McWrapperApiEventReceiver> receivers = [];

  McWrapperApi get api => _mcWrapperApi;

  factory McWrapperHandler() {
    return _instance;
  }

  Future<void> initializerMethod() async {
    _mcWrapperApi = await McWrapperApi.init(CommunicationMode.byPort, "");
    _mcWrapperApi.receiver = this;
    _mcWrapperApi.start();
  }

  McWrapperHandler._internal();

  Future<Either<Error, Object>> send(EventT mcEvent) async =>
      await _mcWrapperApi.send(mcEvent);

  void addObserver(McWrapperApiEventReceiver observer) => receivers.add(observer);

  void removeObserver(McWrapperApiEventReceiver observer) => receivers.remove(observer);

  /// Events the SDK sends on its own arrive here and go to every observer.
  @override
  void onReceive(EventT event) {
    for (var element in receivers) {
      element.onReceive(event);
    }
  }
}
