> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/mcsdk-api/error-handling/error_handling> on 2026-09-28. Converted to Markdown; wording unchanged.

# Different Error Types

If something goes wrong, the result event will indicate that the operation was not successful. See [status information](shift-lite-idpsdk__mcsdk-api__error-handling__status_type.md) for details.

If the SDK is expecting an event X from the UI and another event Y is sent by the UI instead, then an `InvalidStateEvent` will be set as the result (if event Y has a result event) and it will be sent over the event bus.

In some cases, in addition to the result that indicates a failure, a `RuntimeErrorEvent` will be sent over the event bus and will contain additional information about the encountered error (error code/error description).

Please refer to the [error codes list](shift-lite-idpsdk__mcsdk-api__error-handling__mc_error_codes.md) for a more extensive overview of the error codes and their meaning.

## Automated Restart

In some cases, errors will lead to an automated restart by the SDK. For example, when receiving a `RuntimeErrorEvent`, the SDK will automatically trigger a restart.

> ⚠️ Handle the **`RuntimeErrorEvent`** directly as it arrives first in the event sequence. There's no need to wait for your original event result (e.g., **LoginResultEvent**) or the automated restart, since the **RuntimeErrorEvent** already contains the same **errorCode** and all necessary details about the failure.

For comprehensive details about when automated restarts occur and how to handle them, see [Automated Restart Scenarios](shift-lite-idpsdk__development__start.md#automated-restart-scenarios).
