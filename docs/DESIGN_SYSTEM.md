# FORGE Talent Connections Design System

The one visual system behind the application and the public landing page.
Every value here is the value in code: the application reads them from
`lib/theme/tokens.dart` (generated from the design token file, version
`v4-dark-2026-08-28`), and the landing page carries the same values as CSS
custom properties in `index.html`. If this document and the code disagree,
the code wins and this document is stale.

## Identity marks

| Mark | Asset | Where it appears |
|---|---|---|
| Phoenix medallion | `assets/brand/forge_phoenix_medallion.png` (376 by 454, transparent) | Splash, sign-in, mission, pending states, empty states, app and home-screen icons, the landing page hero |
| Gold flame | `assets/brand/forge_flame.png` (578 by 780, transparent) | The compact brand mark: the browser tab icon and the landing page navigation |
| Wordmark lockup | `BrandLockup` widget | Beneath the medallion on the door pages |
| FORGE LINK LLC | `assets/brand/forge_link_llc.png` | Operator footers and the landing page footer |

Medallion rules: never stretch it, never recolor it, never place it on a
light background, and never animate it beyond a breath (a scale of 1.022)
or a fade. The landing page fire is the one exception, and even there the
flames stay off the bird.

## Color tokens

| Token | Value | Use |
|---|---|---|
| `bgGradientTop` | `#0F1A33` | Top of every screen background |
| `bgGradientBottom` / `navyDeep` | `#060B16` | Bottom of every screen; the darkest surface |
| `heroGradientTop` / `heroGradientBottom` | `#1A2647` / `#0D142B` | Page header band on form screens |
| `surface` | `#141E35` | Cards |
| `surface2` | `#1C2945` | Raised cards, the gold-bordered statement card |
| `gold` | `#E3B341` | Accent, titles inside cards, focus rings |
| `goldGradient` | `#F2C759` to `#C79929` | Primary call to action, rules, numbered steps |
| `goldDeep` | `#9E7821` | Gradient end for the flame and depth |
| `text` | `#F5F7FC` | Body text |
| `textSub` | `#93A0BC` | Secondary text, labels, captions |
| `stroke` / `strokeSoft` | `#4D5C80` / `#334059` | Borders and dividers |
| `violet` | `#9466FF` | The demo badge and the AI-generated label |
| `cyan` | `#40D9FF` | Preview chips and tags |
| `green` | `#38D9A9` | Verified |
| `red` | `#F04F6E` | Failed or locked |
| `usmcScarlet` | `#B3141F` | Service flags only |

Semantic assignments: verified is green, pending is `textSub`, failed or
locked is red, the primary call to action is the gold gradient with white
text. The vibe gradient is library-private to the social action widgets and
is never painted on forms or governance surfaces.

Measured contrast on the landing page (WCAG 2.2 AA requires 4.5:1 for
text): `textSub` on `surface` 6.3:1, `textSub` on `navyDeep` 7.5:1, `text`
on `surface` 15.5:1, `gold` on `surface` 8.5:1, `cyan` on `surface` 9.9:1,
`violet` on `navyDeep` 5.3:1.

## Typography

Arial for both display and body, so the same face renders identically in
the application and on the page.

| Role | Size | Landing page equivalent |
|---|---|---|
| `metric` | 48 | none |
| `wordmark` | 44 | hero title, fluid 30 to 44 |
| `heroTitle` | 30 | none |
| `screenTitle` | 26 | section headings, 26 |
| `lockupDescriptor` | 18 | none |
| `name` | 17 | card titles, 16 |
| `input` | 16 | inputs, the floor that stops mobile browsers auto-zooming |
| `cardTitle` | 15 | body, 15 |
| `body` | 13 | card copy, 14 |
| `caption` | 11 | captions, 12.5 |
| `chip` | 9 | chips, 10.5 |

Capitalization: every title is Title Case ("The Road Ahead"). Section
labels render in capitals with 1.1 to 1.6 letter spacing. Body copy is
sentence case. A guard test (`test/copy/title_case_test.dart`) enforces the
title rule in the application.

## Spacing, shape, and grid

| Token | Value |
|---|---|
| `screenPadX` | 20 |
| `cardPad` | 16 |
| `gapSection` | 16 |
| `gapCard` | 10 |
| `screenRadius` | 28 |
| `cardRadius` | 18 (16 on the landing page) |
| `ctaRadius` | 16 |
| `pillRadius` | 999 |

Borders are one pixel of `strokeSoft`; a gold border at 55 percent alpha
marks the statement card. Elevation is expressed by surface step, not by
shadow; the only shadows are the medallion's gold halo.

The application is a single column at the phone width (390 by 844 is the
baseline) and `ForgeDeviceFrame` centres a 480 point column on tablets. The
landing page uses a fluid grid with 272 pixel minimum columns, which yields
three columns on desktop, two on tablets, and one on phones, with card
counts chosen so no row is left with a gap (nine feature cards, six
audience cards).

## Components

| Component | Widget | States |
|---|---|---|
| Primary and secondary buttons | `GoldButton`, `OutlineGoldButton` | enabled, disabled (null callback), pressed |
| Inputs | `FieldBox` | empty, filled, with help |
| Status | `StatusChip` | verified, pending, failed or locked, dense |
| Cards | `ForgeCard` | default, gold-bordered, custom background |
| Section headings | `SectionLabel`, `HeroBand` | |
| Navigation | `BottomNav` (Home, Discover, Create, Projects, Me) | selected |
| Pending | `MedallionPending` | animated, reduced motion |
| Empty | `EmptyState` | with or without one action |
| Error | `AsyncView` error branch | with or without retry |
| Disclosure and notes | `BannerNote`, `demoNote` | |
| Media | `PitchVideoPlayer` | pending, failed, empty, playing, paused |
| Marks | `PhoenixMedallion`, `BrandLockup`, `BurningFlame` | animated, reduced motion |

Every shared widget renders in every state in the Widget Gallery
(`/gallery`), which is a development surface, not a product screen.

## States, by rule

Every asynchronous value renders fail-closed through `AsyncView`: pending
shows the medallion and names what is being checked; error says so plainly
with the reason and never shows empty content that could pass for "nothing
to report"; empty is a true, calm answer with at most one way forward.
Denied outcomes never look like success. Three fixture scenarios (verified,
pending, denied) render every screen in each outcome.

## Motion

Motion communicates state or brand, never decoration. The medallion
breathes at 2.4 seconds; the pending pulse runs at 1.1 seconds; the
landing page fire is real-time and pauses off screen. Every animation is
disabled when the platform asks for reduced motion (`disableAnimations` in
the application, `prefers-reduced-motion` on the page), and every animated
widget renders a complete still frame in that case.

## Accessibility baseline

WCAG 2.2 AA. Touch targets are at least 44 points. The landing page has a
skip link, a main landmark, one `h1`, and a two pixel gold focus ring on
every focusable element. Layouts hold at 1.3 and 2.0 times text scale and
at 320 pixels wide with no horizontal scrolling. Images carry alternative
text; decorative images are excluded from the accessibility tree.
