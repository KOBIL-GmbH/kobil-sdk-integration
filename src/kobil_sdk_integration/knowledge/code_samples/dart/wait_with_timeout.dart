// ADDITION (not from the apps): never wait for a reply without a limit. send() is a Future, so Future.timeout does it.
// Not compiled here.
import 'dart:async';

Future<EventT?> sendWithTimeout(McWrapperHandler handler, EventT event, {Duration limit = const Duration(seconds: 30)}) async {
  try {
    final reply = await handler.send(event).timeout(limit);
    return reply.fold((error) => null, (result) => result as EventT);
  } on TimeoutException {
    return null; // null = no reply in time
  }
}
