# Look and feel in words

For apps where the customer brings no design of their own; a customer design always wins. This page describes the
impression in plain words so that any agent on any platform builds the same app. Measurements and colours are in
[design-system.md](design-system.md). Build the screens with the native controls of the platform.

## The impression

Calm, flat and soft. It should feel like a good banking app that stays out of the way: plenty of white space, round
shapes, one strong colour, almost no decoration. Nothing shouts, nothing bounces.

## Colour

A very light grey-blue screen with white panels on top of it. One strong brand blue for links, focus and the active
tab. A very dark navy for the main button. Text is a near-black blue with a mid grey for secondary lines. Green means
done or incoming, red means a problem, and no other colours are used. Panels are separated by thin hairlines, not
by shadows. In dark mode the layout stays the same: deep navy screen, slightly lighter panels, near-white text.

## Shape and space

Everything is rounded: panels, cards and buttons share one large radius, text fields a slightly smaller one. Buttons
are tall and as wide as the content, with the main button at the bottom of the screen. The side margins are generous
and the same on every screen. Lists breathe: rows are tall, with a clear gap between the icon, the title and the
detail line.

## Type

One font family, the system font unless the customer supplies brand fonts. Screen titles are large and semibold,
body text regular, captions small and grey. Bold is kept for money amounts only.

## Movement

Short and gentle: sheets slide up, pages fade or slide over a fraction of a second. No springs, no bouncing, no
decorative animation while the user waits; a calm progress indicator is enough.

## One focus per screen

Each screen has one thing that is brand-coloured: the main button, or the card the screen is about. Everything else
stays neutral. Do not repeat on the home screen what the tab bar already offers. When a screen feels busy, remove
parts before restyling anything.

## The screens, in words

- **Start:** the brand mark and one short status line while the SDK starts.
- **Welcome:** a brand-coloured header, one sentence about what the app does, the entry buttons below.
- **Activation:** a title, one sentence saying what to do, the fields stacked under it, the main button at the
  bottom. A code is entered in separate boxes, digits only, with the keyboard already open.
- **Login:** the same layout as activation, so the user feels at home; biometric sign-in is offered first when
  available, the password stays as a fallback.
- **Home:** a greeting with the user's picture or initials; a banner only while something waits for approval; then
  the tiles. When there is nothing, one centred friendly line.
- **Approval of a transaction:** a full-screen sheet over whatever is open that cannot be swiped away. At the top a
  countdown, then a card with the transaction as label and value rows, at the bottom the accept control and a
  plain decline button. After the answer, a short confirmation and back to where the user was.
- **History:** a plain list grouped by day; a small coloured circle for the status, one title, one detail line such
  as "Approved, 12 minutes ago", the amount on the right.
- **Settings:** tall rows with an icon on the left and a chevron on the right; switches for yes or no choices.
- **Errors:** one plain sentence in the user's words, never a status code, and a retry button.

## What to avoid

Gradients, drop shadows, mixed corner radii, more than one accent colour, illustrations that carry no meaning,
technical words in messages, and any screen that needs an explanation.

## Check before calling it done

Look at every screen on a real device or simulator, in light and in dark, with the largest text size. Fix what looks
crowded by removing, not by shrinking.
