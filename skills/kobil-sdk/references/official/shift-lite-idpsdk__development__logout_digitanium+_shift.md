> Official KOBIL MCSDK documentation, copied from <https://developer.kobil.com/docs/mcsdk-docs/shift-lite-idpsdk/development/logout_digitanium+_shift> on 2026-09-28. Converted to Markdown; wording unchanged.

# Logout

Sometimes, you might want to explicitly log out of your session, e.g. if you want to re-connect as a different user or just to be sure that nobody can abuse your device while you leave it alone for some time.

If you are working with either a KOBIL Digitanium+ or a KOBIL Shift Lite environment, your locally cached IAM tokens will be used to (automatically) log you in again.
So, in those environments you need to clear the IAM tokens from the local cache if you want to completely logout a user. To clear the IAM tokens from the cache, you should use the **ClearIamTokenCacheEvent**.

This event comes with two signatures:
The default signature **ClearIamTokenCacheEvent(UserIdentifier userIdentifier)** will delete all the stored tokens.
The second signature **ClearIamTokenCacheEvent(UserIdentifier userIdentifier, ClearIamTokenCacheEvent.ClearBehavior clearBehavior)**
takes an enum value of **ClearIamTokenCacheEvent.ClearBehavior** allowing you to choose which tokens should be cleared.

These are the available clear-behavior options:

```
enum ClearBehavior {
CLEAR_ALL, CLEAR_ACCESS_AND_REFRESH, CLEAR_OFFLINE;
}
```

#### Effects of deleting tokens

| **ClearBehavior** | **Effect of using the option** |
| --- | --- |
| CLEAR\_ACCESS\_AND\_REFRESH | Clears the locally stored Access Token and Refresh Token. If AuthenticationMode.BIOMETRIC is enabled the next time the app calls OfflineLoginEvent the user will be asked for for biometric authentication. |
| CLEAR\_ALL | Clear all tokens that are locally stored in MC (Access Token, Refresh Token and Offline Token). The next OfflineLoginEvent will fail because all tokens are gone, so the App has to ask user to enter his IDP online credentials in WebView. |
| CLEAR\_OFFLINE | Clears the locally stored Offline Token. Depending on your IDP setup, you should prefer one of the other options for logout purposes to avoid the creation of too many new Offline Tokens in your IDP. |

See the chapter on [**Tokens**](shift-lite-idpsdk__development__tokens__token-handling__token_handling_intro.md) for more details on the mentioned tokens.

#### iOS/Swift

For Swift, the following snippet can be used to trigger the ClearIamTokenCacheEvent

Triggering ClearIamTokenCache Event (Swift)

```
func triggerClearIAMTokenCache(useridentifier: KsUserIdentifier, completion:@escaping(KsEvent?) -> Void){
let clearIamToken = KSMClearIamTokenCacheEvent(userIdentifier: useridentifier)
masterControllerAdapter.sendEvent2MasterController(clearIamToken) { event in
completion(event)
}
}
```

#### Android/Kotlin

Example usage of the **ClearIamTokenCacheEvent** with chosen **ClearBehavior**:

ClearIamTokenCacheEvent

```
fun triggerClearIAMTokenCache(userIdentifier: UserIdentifier, clearBehavior: ClearIamTokenCacheEvent.ClearBehavior) {
val clearIamToken = ClearIamTokenCacheEvent(userIdentifier, clearBehavior)
synchronousEventHandler.postEvent(clearIamToken)?.then {
logDebug("received ClearIamTokenCacheResultEvent with result: $it", "triggerClearIAMTokenCache")
}
}
```

### **ClearIamTokenCacheEvent sequence diagram**

> We suggest triggering a [**RestartEvent**](shift-lite-idpsdk__development__start.md#restartevent) upon receiving your **ClearIamTokenCacheResultEvent**.

![](https://www.plantuml.com/plantuml/png/hP51JiD034NtSmfVW0jqWOf2X28L405M5A5fvYiPTUA9R4yhRe_QicWAx5ZR__bzsItLl5WPatCtqvHYvorcfgjhklTga2gpIKu9ig3p1PFOzn2bAi5BuyUNl0LNlXjGxy3cBkC7v1bWyODF0fqo1wLzjE4NRWijoKxqcUkSJ7-8jZXM_H-xRzX9oRbUSfbey1mIvhFZENhJi7qsRw2ej7gyQnu-slhfjMdhspLlqFcYeCpfa-nGLsaF0GKa6CAQDyMeAEIGLeifaUyixhmXl5--RTQYHOY2pX38Cgro7vcq4u0TE3Yt18SofYy0)
