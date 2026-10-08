# App design ideas: a complete KOBIL SDK app

Ideas for the screens of a whole app, for when the customer brings no design of their own.
Nothing here is required: use the customer's name, texts, colours, layout and artwork.
For tokens and components see [design-system.md](design-system.md).

## What the SDK needs (keep these whatever the design)

- Route the root view on `session.phase`: starting, activation needed, sign-in needed,
  signed in, error with a retry.
- Present the TMS approval from the root view, so it opens over any screen.
- Errors as one plain sentence (the variants' error text), never a status code.
- Chat is display-only: the iOS SDK cannot send messages, so offer no reply field.

## A possible flow

```
Splash ──SDK starts──▶ Welcome ──no user yet──▶ Activation ──▶ Tabs
                         └──user activated──▶ Sign-in (Face ID or password) ──▶ Tabs
Any screen ──TMS request──▶ Approval
```

## Screen ideas

| Screen | Idea |
|---|---|
| Splash | The brand mark and a short status line while the SDK starts |
| Welcome | Brand header, one line on what the app does, the entry points below |
| Activation | Title "Activation", one line of explanation, the fields the variant needs, one button |
| Sign-in | "Sign in with Face ID" first when a password is saved, the password form below it, a cancel while waiting |

## Tab ideas

| Tab | Idea |
|---|---|
| Home | Greeting, a banner while a request waits for approval, recent activity |
| Payments | Accepted and declined requests, newest first, an empty state that says what will appear; a Wallet row at the top when the app keeps cards ([wallet.md](wallet.md)) |
| Sign | Documents to sign and signed ones; import a PDF |
| Chats | Messages from the provider, grouped by sender, with unread counts |
| Profile | Photo and name, signature, device and security, sign out with a confirmation |

Fewer tabs are fine; add only what the product uses.

Before calling a tab done, check that it is reachable and wired, not only compiled:

| Tab | Done when |
|---|---|
| Home | a pending request shows the banner; an approved payment appears in recent activity |
| Payments | an accepted and a declined request both appear; with a wallet, "Pay with" shows on the next payment sheet |
| Sign | an accepted signature request appears as a document ([signing.md](signing.md), wiring step 6) |
| Chats | a display message appears; the screen does not offer to send (the iOS SDK cannot) |
| Profile | sign out asks first; Face ID and signature rows reflect the stored state |

## Style hints

- Check light and dark mode; make sure the primary colour stays readable in both.
- One accent colour for primary actions; green for success, red only for destructive actions.
- Native controls (`TabView`, `List`, `.sheet`), SF Symbols and system fonts.
- Short, plain sentences: what happened and what to do next.
