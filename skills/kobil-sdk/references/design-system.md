# KOBIL design reference (iOS, Android and Flutter)

KOBIL brand values. Ideas, not rules: the customer's own design wins. Translate the design, don't
port it: keep the hierarchy, measurements, flows and brand, and build with the native controls of the platform (SwiftUI, Jetpack Compose, Flutter Material 3).
Measurements are points on iOS, dp on Android and logical pixels in Flutter; they are the same numbers.

## 1. Tokens

### Colour (KOBIL brand, light; dark is almost the same)

| Role | Token name | Value |
|---|---|---|
| Brand primary (links, focus, active tab, outgoing bubble) | `primaryColor` | `#1D19FF` |
| Brand secondary (primary buttons, badges, send button, FAB) | `secondaryColor` = `primaryButtonColor` | `#04004C` |
| Button text | `buttonTextColor` | `#FFFFFF` |
| Disabled button bg / text | `disableButtonColor` / `hintTextColor` | `#E7EAF0` / `#ADB7CA` |
| Header area behind panels | `scaffoldPrimaryBackgroundColor` | `#1D19FF` |
| Screen background | `scaffoldBackgroundColor` | `#F2F4F9` |
| Page background (alt) | `pageBackground` | `#F9FBFF` |
| Panel / card / sheet surface | `scaffoldPanelChildColor`, `bottomSheetColor` | `#FFFFFF` |
| Grouped container in sheets | `bottomSheetContainerColor` | `#F2F4F9` |
| Text primary | `textColor`, `grey100` | `#232935` |
| Text secondary | `whiteGrey60Color` | `#747B86` |
| Text regular (64 %) | `regularTextColor` | `#232935` @ 64 % |
| Placeholder / hint | `hintTextColor` | `#ADB7CA` |
| Disabled text, inactive tab | `disabledTextColor`, `tabbarInactiveTextColor` | `#ADB6BE` |
| Active tab pill | `tabbarActiveColor` | `#5C3BFF` @ 20 % |
| Error | `errorTextColor` | `#EB5757` |
| Success / incoming money | `transactionGreenColor` | `#27AE60` |
| Accent CTA (amount keypad Next) | `teal` | `#1D28ED` |
| Divider | `dividerColor` | black @ 8 % |
| Hairline border | `systemLine`, `textFieldBorderColor` | `#E7EAF0` |
| Text-field fill | `textFieldBackgroundColor` | `#FAFBFD` |
| Settings icon / chevron | `settingsTileIconColor` | `#777B83` |
| Icon default | `iconColor` | `#3E3E3E` |
| Tab bar bg / top shadow line | `bottomNavigationbarBackgroundColor` / `bottomBarShadow` | `#FFFFFF` / `#E3E9F5` |
| Sheet barrier | `barrierColor` | `#232935` @ 24 % |
| Dark chat bubble (alt) | `myChatBubbleColor` | `#19223C` |
| Signature ink | `signaturePrimaryColor` / `signatureSecondaryColor` | `#000000` / `#1D19FF` |

Colours are configured per tenant, not hard-coded. Put them in one `Theme` enum or an
asset catalog so a tenant can be re-skinned in one place.

### Typography

The body font is **Barlow** and headers use **Inter**. Tenants can override
both. On every platform use the system font unless the brand fonts are bundled.

| Style | Size / line height | Weight | Use |
|---|---|---|---|
| `largeScreenTitle` | 24 / 32 | 600 | screen titles, welcome, onboarding |
| `smallScreenTitle` | 18 / 28 | 600 | sheet titles, status titles |
| `bodyScreenTitle` | 18 / 24 | 500 | section headers, profile name |
| `textMedium` | 16 / 24 | 500 | buttons, row titles |
| `textRegular` | 16 / 24 | 400 | body, inputs |
| `messageText` | 16 / 22 | 400 | chat bubbles |
| `labelMedium` | 14 / 20 | 500 | small emphasis |
| `labelRegular` | 14 / 20 | 400, 64 % alpha | captions, timestamps, email |
| amount | 36 (entry) / 32 (card) | 600–700 | money |
| card number | 22, tracking 3 | OCR-A (monospaced) | card PAN |

### Shape, spacing and motion

| Token | Value |
|---|---|
| Screen horizontal margin | **24** (lists 23–24, chat 16) |
| Panel / sheet top corner radius | 16 (tenant `panelBorderRadius`, fallback 32) |
| Card radius (`cardBorder`) | 16 |
| Button: height / radius | **48** / 16 |
| Text field: radius / border | 12 / 1 pt `#E7EAF0`, focused 1 pt primary |
| Primary / secondary radius | 24 / 16 |
| Avatar (list) / avatar (profile) | 48 / 84 |
| Switch | 42 × 24 |
| Header height | 56 |
| Default transition | 400 ms ease; page carousel 500 ms; welcome panel 700 ms easeOut |

Visual language: flat, soft and rounded. It uses solid surfaces, 1 pt hairlines and almost no shadow.
White content panels sit on a brand-blue or light-grey scaffold, with generous 24 pt margins and
400/500 weights (never heavy bold except money).

## 2. Core components

- **Primary button:** full width, 48 high, radius 16, fill `secondaryColor`, white `textMedium`.
  Disabled: `#E7EAF0` fill with `#ADB7CA` text. It has an optional 26 pt leading icon with an 8 pt gap.
  Secondary variant: transparent fill with a 1 pt border.
- **Text field:** fill `#FAFBFD`, radius 12, padding 12, 1 pt border that turns primary on focus. Hint
  colour `#ADB6BE`. Error text in `#EB5757` below the field. Password fields get an eye toggle
  (`#ADB7CA`).
- **OTP:** 6 digit cells 42 pt wide, spread evenly across the width. Digits only, autofocused, and
  disabled while loading or expired. A countdown sits below.
- **Bottom sheet:** white, top corners 16–32, dimmed barrier. Header padding 12/23/12/4 with a centred
  18/28 title and a close ✕ at the trailing edge. Content has 24 side and 40 bottom padding.
- **Settings row:** 48 high (72 with a subtitle). 24 pt leading icon `#777B83`, then a 14 gap, then the
  title in `textMedium`, then the subtitle in `#747B86`, then an 18 pt chevron. There is a bottom
  divider and the whole row is tappable. Sections have a `bodyScreenTitle` header.
- **Page scaffold:** brand header (56) with a title that is left-aligned at 24 pt in `largeScreenTitle`.
  Below it a white rounded content panel. Loading shows shimmer blocks (radius 16) rather than
  spinners. Empty states show an illustration and `textRegular` copy, with pull-to-refresh.
- **Tab bar:** Home, Chat, Pay (wallet), Profile, plus optional QR. White background with a
  `#E3E9F5` top line. Active tab: primary tint on a 20 % pill. Inactive: `#ADB6BE`.

## 3. Screens

### Splash → onboarding → welcome
- **Onboarding:** paged carousel with 3–4 pages. Logo at the top, then an illustration (≈37 % of
  screen height), then a 59 gap, a centred title (`largeScreenTitle`), 8, and a subtitle
  (`textRegular`). Page dots: active black, inactive 8 % black. The bottom row has **Skip** (text) on
  the left and **Next/Start** (primary button) on the right, with 40 bottom spacing.
- **Welcome:** full-bleed brand illustration. A white bottom panel animates up (700 ms) with 16–32 top
  corners and 24/27 padding. It holds a centred "Welcome" title and a legal paragraph whose privacy,
  terms and contract links are in primary colour, followed by the Login/Activate buttons and 42 bottom
  spacing.

### Login / activation (AST)
- Fields and pages are driven by the flow configuration: a title and optional description at the top,
  then stacked fields (text, password with eye, date, dropdown, checklist, OTP), then the primary
  button at the bottom.
- **Email code:** "We sent a code to" then the email in semibold, with a **Change email** link in
  primary. After a 29 gap come the 6 OTP cells, then the countdown, then the Confirm button.
- **Password creation:** the password rules list sits above the field.
- **Loading:** a shimmer copy of the form layout, never a blank screen.
- **App lock:** biometric login with password fallback. The lock timeout sheet offers Immediately,
  1 min, 15 min and 1 h.

### Home
- Tab shell with configurable pages. Tiles use radius 16 with 64 × 64 icons. Empty state as in
  the scaffold above.
- Home is a launcher, like the iPhone home screen: the greeting and avatar, a banner only while a
  payment waits for approval, then the tile grid. With no tiles it shows one centred
  "Nothing here yet" message. Cards belong in Wallet and approval history in Payments, not on Home.

### Chat
- **Conversation list:** each row has 24 horizontal and 16 vertical padding. A 48 circular avatar
  (initials on a teal circle when there is no image), then a 14 gap. The title sits above a one-line
  preview in `labelRegular` `#747B86`; non-text previews show an 18 pt type icon with a label (Photo,
  Document, Signature, Choice…). On the right: the time, and below it an unread badge (min 20 × 20,
  pill, `secondaryColor`, white 12 pt). Dividers are inset after the avatar. Search sits in the header.
  Loading shows 3 shimmer rows. The empty state is an illustration with pull-to-refresh.
- **Conversation:** incoming bubbles are white (`scaffoldPanelChildColor`) on the left. Outgoing bubbles
  are primary-coloured with white text on the right. Max bubble width is screen width − 105, padding
  10, radius 12 with one pointed corner (2) on the sender side. Text is 16/22. The time and a
  delivered/read/failed icon sit inside the bubble at the bottom-right.
  - A sticky date chip slides in while scrolling and hides after 1.5 s.
  - A scroll-to-bottom FAB (`secondaryColor`) sits 16 from the trailing edge and 15 from the bottom.
  - Composer: white bar with a 1 pt top divider, 6 padding and 48 high. It has a ➕ (primary), a growing
    multiline field, and a send button that fades in (150 ms) only when there is text.
  - The attachment sheet slides up above the composer.
- **Message types:** text (with links, bold and italic), image, file (icon, name, size, download
  state), video, **choice request** (optional image, text, then 1 pt-bordered option buttons laid out
  vertically or horizontally), **signature request** (PDF thumbnail, file size and one row per
  signer), URL preview card, and app action.

### Signing
1. Tap the signature request bubble. If the PDF is password-protected, show an alert.
2. **Sign document screen:** full-screen PDF on the scaffold background. The nav bar has a
   **Decline** action. An embedded **Sign here** chip (108 × 44, radius 8, 1 pt primary border, primary
   at 8 % fill, 16 pt text) sits over the signature field. The footer is 48 plus the safe area, with a
   top divider and a right-aligned **Send** that is disabled until signed.
3. **Signature pad:** nav bar with the title and **Save**. A canvas with a centred guide line. The
   footer (padding 24/16) offers two ink colour swatches (black and primary) with a 14 gap, a spacer,
   then **Clear**. Saving shows a blocking spinner.
4. A stored signature is reused next time. A sheet offers Change or Delete (48 rows, radius 18,
   dividers) and an outlined Cancel.
5. An answered request opens a read-only PDF preview with a Share button.

### TMS transaction approval overlay (the production look)
- **Presentation:** when a TMS transaction arrives, a full-height modal sheet appears over whatever
  screen is open. It can't be dismissed by swiping or tapping outside, it has no barrier dimming, and
  its surface is white (`smartScreenContainer`). Present it at the root of the app: iOS `.fullScreenCover` (or a sheet with
  `.interactiveDismissDisabled()`), Android a full-screen `Dialog` with `dismissOnBackPress = false`, Flutter a
  full-screen route with `PopScope(canPop: false)`.
- **Layout** (padding 24 sides, 68 top, 44 bottom), top to bottom:
  1. **Countdown pill:** full width, 40 high, 1 pt `#D5DBE5` border, radius 8. It holds an 18 pt clock
     icon, an 8 gap and `mm:ss` in `textRegular`. It starts from the server timeout (default 60 s). At
     0 the app sends a *timeout* confirmation.
  2. 16 gap, then a scrollable **transaction card**: radius 8, 1 pt `#D5DBE5` border, no fill.
     - Header (padding 19/12/19/14, bottom border `#D5DBE5`, centred): the authorisation header in
       16/24 medium `#232935`, 4 gap, then the introduction in `labelRegular` at 64 %.
     - Body: one row per authorisation-data item, then per data-summary item. Each row has padding
       11 top, 13 bottom, 13 left, and a 1 pt `#D5DBE5` divider (none after the last). The key is on
       top in `labelRegular` `#747B86`, the value below in `textRegular` `#232935`. Dates are formatted.
  3. 16 gap, then the actions pinned at the bottom:
     - **Slide to accept:** a 52 high capsule with a 2 pt `#0DC5AB` (teal-green `sliderButton`)
       border and a centred uppercase "ACCEPT" (16 pt, same colour). A 46 pt circular thumb (fill
       `#0DC5AB`, 24 pt white arrow) sits on a 46 pt track circle at 8 % tint. Dragging to the end
       (width − 101) confirms; releasing early springs back (500 ms). Accept is never a plain tap. Keep
       an accessibility action for VoiceOver.
     - 8 gap, then a **Decline** text button in uppercase `textMedium` `#EB5757`.
- **Result** (same sheet, replaces the content): top padding min(216, 27 % of height), 40 bottom.
  Accepted, declined or timed-out illustration (timeout art ≈ 20 % of height), then a 15 gap, the title
  in 18/28 medium, an 8 gap, and the body centred in `textRegular` `#747B86` at about 73 % width. A
  spacer, then **Done**: 52 high, radius 26 (pill), transparent with a 1 pt black 8 % border and
  `#04004C` text. Done closes the overlay; `transactionComplete` also closes it automatically.
- **States:** received → (accept | decline | timeout) → result → closed. There is no separate loading
  UI while the answer is sent, so show a spinner in the thumb.

### Payment, cards and wallet
- **Pay tab:** header, then the **digital wallet card**, then a "Latest transactions" header with
  "See all", then the list. Pull-to-refresh; loading uses shimmer.
- **Card visual:** full width, **200 pt high**, radius 16, with the card image as background and a 1 pt
  white border at 66 %. The number is centred in white, OCR-A 22 pt with tracking 3, masked as
  `**** **** **** 1234`. The expiry is in the bottom-left (22, 23) in white `labelRegular`. The wallet
  card shows a balance label, the amount at 32 bold with the currency at 16 bold, bottom-left in white.
- **Transaction row:** 23 horizontal padding, a 48 circular avatar with a hairline border, a 13 gap,
  then the title above the date (`labelRegular` `#747B86`). The trailing amount is shown as +/−, with
  incoming amounts in `#27AE60`. The divider is inset 86 → 24. Tapping opens the details (hero
  transition).
- **My cards (wallet):** header titled "My cards" with an **Add card** action. Padding 24/23, cards
  stacked with 16 spacing. The empty state is an illustration about 40 pt below the header. Tapping a
  card opens the card-details sheet. Hitting the maximum card count shows an alert.
- **Amount entry sheet:** almost full height and white with rounded top corners. An optional mini card
  (98 × 60). The amount is centred at 36 semibold, with the currency symbol at 20; zero shows in
  `#ADB7CA`. A validation line below is in `labelRegular`. A 3-column circular keypad (1 pt `#E7EAF0`
  rings, 67 side padding, 18 row spacing, a backspace key and no decimal). A **Next** button in
  `teal`, disabled at 0.
- **Payment confirmation sheet:** cannot be dismissed. A header with the title and **Cancel**, then a
  "Transfer to" recipient section, the details, a selected-card row that opens the card picker (with
  Add card; unsupported cards are shown but disabled), and an expandable amount breakdown. A spacer,
  then **Confirm payment**, which is disabled with no or unsupported cards. It triggers biometric
  confirmation, then 3-D Secure if needed, then the status screen.
- **Status screen:** a dark background with a white rounded panel, a success or failure illustration
  200 high, a `smallScreenTitle`, and an explanation in `#747B86`. It can show a detail table
  (Recipient, Date & time, Transaction ID, Invoice ID; 14 pt, 10 row padding, dividers). **Done** has
  24/40 padding. Back is blocked until Done is tapped.

### Profile and account
- **Header:** "Profile" in `largeScreenTitle` at 24 left. A circular **84 pt** avatar (initials fallback,
  camera edit badge). The name in `bodyScreenTitle` 18 above the email in `labelRegular` `#747B86`.
- **Settings:** grouped sections of the settings row above, covering Account, Privacy & security
  (biometrics, app lock timeout), Language, Legal and so on. **Log out** is a separate button at the
  bottom.
- **Account:** Devices (the subtitle shows the active count), Remove account from this device (with a
  confirmation sheet), and **Delete my account** (destructive; it re-authenticates first).
- **Devices:** list rows with the status title ("Active" or the last-active date) above the model
  subtitle, with dividers. After the list, **Log out all devices** in primary.
- **Delete account:** warning text, username and password fields (password with eye), a destructive
  button that stays disabled until both are filled, and a final confirmation sheet.

## 4. Translation rules per platform
Keep the measurements and colours above and use the platform's own controls; don't recreate another platform's widgets.
- **iOS (SwiftUI):** `NavigationStack`, `TabView`, `.sheet` with `presentationDetents`, `List`/`Form` for settings,
  `.refreshable`, `.redacted(reason: .placeholder)` for shimmer, `PhotosPicker`/`Canvas`/PencilKit for the signature
  pad. iOS 26: allow system Liquid Glass on the tab bar and nav bar; keep content panels as solid white rounded
  surfaces so the brand look survives. Dynamic Type, dark mode through the theme, VoiceOver labels.
- **Android (Jetpack Compose, Material 3):** `Scaffold`, `NavigationBar`, `ModalBottomSheet`, `LazyColumn` for lists,
  `PullToRefresh`, shimmer with a placeholder modifier. Turn dynamic colour off so the brand colours stay; apply
  the template's `KobilTheme`. Font scaling, dark theme, TalkBack content descriptions.
- **Flutter (Material 3):** `Scaffold`, `NavigationBar`, `showModalBottomSheet`, `ListView`, `RefreshIndicator`.
  Use `KobilTheme.light()`/`dark()` and read colours from the `KobilColors` extension, not hard-coded values. Text scale,
  dark theme, `Semantics` labels.
- **All platforms:** badges, status icons and the amount keypad carry accessibility labels; support dark mode from the
  first screen, not at the end.

## 5. Rules for AI coding assistants
Short rules, learned on devices, for any agent building these screens:
- One brand-coloured surface per screen (usually the payment card or the primary button). Everything
  else stays neutral.
- Don't repeat on Home what the tab bar already offers: no quick-action tiles for tabs, no stat tiles.
- History and inbox screens: a plain list grouped by day, a status or initials circle, one subtitle
  line ("Approved · 12 min ago"), the amount on the right, no chevrons. Filters and "Clear" go in a
  toolbar menu; empty screens use the platform's empty-state view (iOS `ContentUnavailableView`).
- iOS: in dark mode a plain `List` paints black rows; set `.listRowBackground` to the screen colour.
- Remove before you add. When the user calls a screen busy, delete sections; don't restyle them.
- Look at the screen before calling it done, in light and dark. iOS simulator: `xcrun simctl io booted screenshot
  light.png` (then `xcrun simctl ui booted appearance dark` and again for `dark.png`); iOS device:
  `xcrun devicectl device capture screenshot --device <id> --destination shot.png`. Android: `adb exec-out screencap -p >
  shot.png`. Flutter: the screenshot command of the target platform.
