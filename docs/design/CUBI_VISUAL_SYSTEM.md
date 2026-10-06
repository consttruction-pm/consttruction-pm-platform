# CUBI Platform Visual System

Status: Registered baseline
Audit date: 2026-10-05
Scope: Web, Desktop, Mobile client presentation layers, exported visual/report surfaces, and future brand assets.

## Purpose

CUBI uses a restrained engineering-oriented visual language. Color must support project data hierarchy rather than compete with scheduling grids, Gantt charts, cost/EVM tables, reports, or control-room information.

## Registered brand palette

| Token | Hex | Role |
|---|---|---|
| Deep Navy | #0F2747 | Primary brand, navigation, authoritative UI chrome |
| Navy Dark | #081A2F | Dark hero/footer, high-contrast brand surfaces |
| Engineering Blue | #1976D2 | Primary interactive/data accent, links, focus, selected states |
| Copper Orange | #F28C28 | Primary commercial CTA, key highlight, limited emphasis |
| Brushed Titanium | #B8BDC5 | Metallic brand accent and restrained chrome |
| Titanium Light | #E8EBEF | Light metallic support surface and subtle separators |
| Titanium Dark | #707883 | Metallic detail/texture contrast |
| Titanium Mid | #E1E5E9 | Mid-tone metallic blend support |
| Neutral Border | #D9E0E7 | Standard UI border |
| Neutral Divider | #E6E9EE | Table/divider lines |
| Neutral Subtle | #F7FAFD | Low-contrast hover/support surface |

### Semantic status colors

Status/KPI semantics are separate from brand identity:
- Success: #2E8B57
- Warning: #D99A00
- Error: #D64545
- Informational: Engineering Blue

These colors may appear in schedules, alerts, KPI cards, validation states and audit outcomes because their meaning is semantic.

## Usage rules

### Homepage

The registered homepage direction is:
- Dark Navy hero.
- Copper Orange primary CTA.
- Engineering Blue for controlled highlights and technical accents.
- Light sections after the hero.
- Product/dashboard visuals stay primarily neutral/light so project data remains readable.
- Footer may use Navy Dark.

### Product workspace

The main application workspace remains calm and data-first:
- white/light neutral surfaces;
- Deep Navy for headings and authoritative labels;
- Engineering Blue for interaction/focus/selection;
- Copper reserved for important actions or high-value emphasis;
- semantic status colors for state/KPI meaning;
- no decorative gradients inside dense scheduling, cost, EVM or Gantt data areas unless they improve interpretation.

### Brushed-metal texture

The metallic treatment is intentionally subtle and restricted to brand chrome:
- logo frames/marks;
- selected header/navigation accents;
- limited premium brand details;
- future app/report title bars where appropriate.

Use the registered --cubi-brushed-metal CSS token rather than creating new metallic gradients.

Do not use brushed-metal texture as a background for dense tables, Gantt charts, forms, dashboards or control-room panels.

## Typography

- Latin: Inter.
- Persian/RTL: Vazirmatn.
- The font stack is shared by the Web CSS and should remain multilingual-safe.
- Typography changes must not introduce a separate visual system for Persian.

## Logo

The **uploaded CUBI Platform logo sheet supplied on 2026-10-06 is the final brand reference**. It is the single source of truth for the CUBI mark and lockups across Web, Desktop and Mobile.

Approved variants shown in that reference:
- Full logo / CUBI Platform lockup.
- Icon-only mark for favicon, app, dashboard and compact navigation.
- Light app icon.
- Dark app icon.
- Light/dark presentation variants.
- Brand lockup with the tagline: "Plan. Control. Build Smarter."

Implementation rules:
- Preserve the approved geometry, proportions, spacing and lockup.
- Do not redraw, simplify, recolor or create a competing CUBI mark.
- The logo's own approved blue/cyan/teal facets are **logo-specific identity colors** and may remain inside the logo asset. They are not a license to introduce cyan/teal as general UI accent colors.
- Outside the logo asset, application UI continues to use the registered CUBI palette and semantic status colors.
- Light/dark contexts must select the corresponding approved logo variant.
- All three clients must consume the same canonical logo asset family.

## Forbidden drift

Do not introduce:
- new cyan/teal brand accents;
- arbitrary saturated gradients;
- decorative construction imagery as a substitute for product identity;
- per-screen color systems;
- a second component/theme palette;
- decorative color that competes with project data.

New colors require a documented semantic purpose and should normally be a tint/shade of an existing registered token.

## Implementation anchors

Web source of truth:
- apps/web/styles.css
- apps/web/public/logo.svg
- apps/web/public/logo-dark.svg

The CSS variables beginning with --cubi- are the canonical palette and neutral tokens. Client applications should consume equivalent semantic tokens rather than inventing client-local brand colors.

## Audit result — 2026-10-05

The repository already had the correct broad direction (Deep Navy, Engineering Blue, Copper, calm neutral workspace), but the audit found three sources of visual drift:
1. Homepage hero and CTA did not match the registered dark-hero / copper-CTA direction.
2. Logo assets contained independent cyan/teal colors outside the registered palette.
3. Brushed Titanium and the brushed-metal treatment were not explicitly registered as reusable design tokens.

The current audit branch corrects these three points without changing Shared Core, scheduling, P6 or calculation behavior.