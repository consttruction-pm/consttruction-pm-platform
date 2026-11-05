# CUBI Platform Visual System

Status: Registered baseline
Audit date: 2026-10-05
Scope: Web, Desktop, Mobile client presentation layers, exported visual/report surfaces, and future brand assets.

## Purpose

CUBI uses a professional engineering-oriented visual language. The brand palette defines CUBI identity, not a mandatory limit on workspace presentation. Workspace themes, window backgrounds, panel surfaces, WBS level treatments, Gantt backgrounds and user-selected colors may use broader coordinated palettes when they improve readability, hierarchy, accessibility or user preference.

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
- provide complete, usable light and dark workspace themes;
- allow configurable workspace, window, panel, grid and Gantt background colors;
- allow coordinated theme palettes and distinct but consistent window-level color treatments;
- retain sufficient text contrast, visible selection/focus states and distinguishable semantic status colors;
- preserve activity/status/criticality/selection meaning independently of WBS grouping colors;
- permit user-selected colors and custom theme palettes without requiring every color to be a tint of a brand token;
- keep branded logo colors and commercial brand surfaces governed by the registered brand palette, while treating workspace presentation as a separately configurable product capability.

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
- All contexts and clients resolve to the single canonical logo asset; do not introduce separate light/dark logo files.
- All three clients must consume the exact same canonical logo file path.

## Forbidden drift

The following restrictions apply only to brand identity assets and must not be used to block workspace customization:
- do not recolor or redraw the approved logo;
- do not present workspace theme colors as a replacement for the registered CUBI brand identity;
- do not use decorative imagery as a substitute for product identity.

Workspace color restrictions that previously prohibited per-screen/window color treatments, a second workspace theme palette, broader background choices or custom user palettes are withdrawn. New workspace colors may be selected for usability, accessibility, semantic meaning or user preference. Dense data views must remain legible, but they are not required to use only neutral/brand-tinted backgrounds.

## Implementation anchors

Web source of truth:
- apps/web/styles.css
- apps/web/public/cubi-platform-logo-primary.svg (the sole canonical logo asset)

The CSS variables beginning with --cubi- are the canonical palette and neutral tokens. Client applications should consume equivalent semantic tokens rather than inventing client-local brand colors.

## Audit result — 2026-10-05

The repository already had the correct broad direction (Deep Navy, Engineering Blue, Copper, calm neutral workspace), but the audit found three sources of visual drift:
1. Homepage hero and CTA did not match the registered dark-hero / copper-CTA direction.
2. Logo assets contained independent cyan/teal colors outside the registered palette.
3. Brushed Titanium and the brushed-metal treatment were not explicitly registered as reusable design tokens.

The current audit branch corrects these three points without changing Shared Core, scheduling, P6 or calculation behavior.