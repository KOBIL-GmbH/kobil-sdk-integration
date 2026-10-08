# KOBIL default theme

This is the look of a KOBIL SDK app when the owner has no design of their own. It is written in words and tables so
that an agent can build it on any platform (iOS, Android, Flutter) with the native controls. The owner can replace
the whole text with their own theme (`sdk_theme_set`); a theme that is set always wins over this one.

## How to use this theme

1. Build every screen from the roles below, never from loose values: name each colour, size and style by its role
   and keep all values in one place of the app (one theme file), so a re-skin is one edit.
2. Use the native controls of the platform; do not recreate another platform's widgets.
3. Support dark mode from the first screen.
4. Check each screen on a device or simulator, light and dark, with the largest text size, before calling it done.

## The impression

Calm, flat and soft, like a good banking app that stays out of the way. Plenty of white space, round shapes, one strong
colour, almost no decoration. Nothing shouts and nothing bounces. Each screen has one brand-coloured thing: the main
button, or the card the screen is about. Everything else is neutral.

## Colour

| Role | Light | Dark (suggested) | Use |
|---|---|---|---|
| Brand | `#1D19FF` | `#1D19FF` | links, focus ring, active tab, outgoing chat bubble, secondary button outline |
| Brand dark | `#04004C` | `#04004C` | main button fill, badges |
| Screen | `#F2F4F9` | `#0E111A` | background behind panels |
| Surface | `#FFFFFF` | `#1A1F2B` | panels, cards, sheets, tab bar |
| Text primary | `#232935` | `#F2F4F9` | titles, body |
| Text secondary | `#747B86` | `#ADB7CA` | captions, subtitles, timestamps |
| Hairline | `#E7EAF0` | `#2B3242` | 1 pt borders and dividers instead of shadows |
| Field fill | `#FAFBFD` | `#151A25` | text field background |
| Disabled fill | `#E7EAF0` | `#2B3242` | disabled button background |
| Disabled text | `#ADB7CA` | `#ADB7CA` | disabled button text, placeholders |
| Error | `#EB5757` | `#EB5757` | error text, error badge, destructive button |
| Success | `#27AE60` | `#27AE60` | success badge, incoming amounts |

Button text on the main button is white. The dark values are a suggestion that keeps the same roles; the brand guide
itself only says that dark mode is almost the same. No other accent colours.

## Shape and space

| Measure | Value |
|---|---|
| Side margin of every screen | 24 (chat 16) |
| Corner radius of panels, cards, buttons, sheets (top corners) | 16 |
| Corner radius of text fields | 12 |
| Height of buttons and text fields | 48 |
| Gap between related items | 12; between groups 24 |
| Border | 1 thin line, never a shadow |
| List row height | 48, 72 with a subtitle |
| Avatar in lists / in the profile | 48 / 84 |

Units are points on iOS, dp on Android and logical pixels in Flutter: the same numbers.

## Type

One font family: the system font, unless the owner supplies brand fonts (the KOBIL brand uses Barlow for text and Inter
for headers). Bold is kept for money amounts only.

| Style | Size | Weight | Use |
|---|---|---|---|
| Screen title | 24 | semibold | the title of a screen, left aligned at the margin |
| Sheet title | 18 | semibold | sheets, status titles |
| Row title | 16 | medium | buttons, list rows |
| Body | 16 | regular | text, inputs |
| Caption | 14 | regular, secondary colour | subtitles, timestamps |
| Amount | 32 to 36 | semibold to bold | money |

## Movement

Short and gentle, about 400 ms ease: sheets slide up, pages slide or fade, the welcome panel rises in about 700 ms. No
springs, no bouncing, no decorative animation while the user waits; a calm progress indicator is enough.

## Components in words

- **Main button:** full width, 48 high, radius 16, brand dark fill, white row-title text. Disabled: disabled fill and
  disabled text. One main button per screen, at the bottom.
- **Second button:** the same size, transparent, 1 pt brand outline and brand text. For the second choice only.
- **Text field:** 48 high, radius 12, field fill, 1 pt hairline that turns brand colour while focused; hint in the
  secondary colour; error text in the error colour under the field.
- **Code entry:** six separate boxes spread over the width, digits only, keyboard already open.
- **Card:** surface colour, radius 16, 1 pt hairline, padding 16, no shadow.
- **Status badge:** a small pill with a 12 percent tint of its colour and the text in that colour: green success, red
  error, grey neutral.
- **List row:** an icon or a coloured status circle on the left, a row title, a caption below, the amount or a
  chevron on the right; thin inset divider; no heavy separators.
- **Sheet:** surface colour, 16 radius on the top corners, a dimmed screen behind it.
- **Tab bar:** surface colour with a thin top line; the active tab in brand colour on a light brand pill.
- **Header:** brand coloured band, 56 high, with the title left aligned at the margin.

## The screens in words

- **Start:** the brand mark and one short status line while the SDK starts.
- **Welcome:** a brand header, one sentence about what the app does, the entry buttons below.
- **Activation:** a title, one sentence saying what to do, the fields stacked under it, the main button at the bottom.
- **Login:** the same layout as activation; biometric sign-in first when available, the password as fallback.
- **Home:** a greeting with picture or initials; a banner only while something waits for approval; then the tiles; when
  there is nothing, one centred friendly line.
- **Approval of a transaction:** a full-screen sheet over whatever is open that cannot be swiped away. At the top a
  countdown, then a card with the transaction as label and value rows, at the bottom the accept control and a plain
  decline button. After the answer a short confirmation, then back to where the user was.
- **History:** a plain list grouped by day; a coloured circle for the status, one title, one detail line such as
  "Approved, 12 minutes ago", the amount on the right.
- **Settings:** tall rows with an icon on the left and a chevron on the right; switches for yes or no choices.
- **Errors:** one plain sentence in the user's words, never a status code, and a retry button.

## Accessibility

Text scales with the system setting and rows grow with it. Every icon-only control has a spoken label. Contrast of text
on surface and of white on brand dark is high; do not lower it for style. Dark mode follows the system.

## What to avoid

Gradients, drop shadows, mixed corner radii, more than one accent colour, illustrations without meaning, technical
words in messages, repeating on the home screen what the tab bar already offers, and any screen that needs an
explanation. When a screen feels busy, remove parts before restyling anything.
