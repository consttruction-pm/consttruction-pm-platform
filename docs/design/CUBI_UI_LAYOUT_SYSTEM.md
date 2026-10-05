# CUBI UI Layout, Typography and Print System

Status: Approved implementation baseline for the current V1 client layer.

## Purpose

This document defines the visual geometry rules that keep CUBI readable, stable and professional across Web, Desktop and Mobile. It complements `docs/design/CUBI_VISUAL_SYSTEM.md`.

## Typography

Primary Latin UI font: Inter.
Primary Persian/RTL UI font: Vazirmatn.
Fallback: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif.

The Web workspace uses a 14px base UI size. Dense activity/resource/cost tables use approximately 12.5px body text and 12px headers. Small metadata uses 11–12px. Major headings may scale independently.

Numeric project-control values should use tabular numeric figures where supported so columns stay visually aligned.

Client UI must not shrink dense data below a readable size merely to fit more columns. Prefer horizontal scrolling, column visibility controls and persisted field widths over illegible text.

## Web geometry

Preferred desktop workspace range: 1280–1920px viewport width.
The workspace is centered and capped at 1920px so very wide displays do not create excessive line length or stretched panels.

At desktop width the workspace uses:
- WBS/navigation column: about 200–240px.
- Main Activity Grid/Gantt column: flexible.
- Details/control column: about 220–280px.
- Standard inter-panel gap: 12px.
- Standard panel radius: 8px.

At 1024–1279px the side columns contract. At 760–1023px the layout changes to two columns with details spanning the full row. Below 760px the workspace becomes one column.

## Navigation and controls

The primary workspace menu must not wrap into multiple uncontrolled rows. It remains a single horizontal row with overflow scrolling when necessary.

Standard desktop control height: about 36px.
Touch-oriented/mobile control height: at least 40px.
Menu labels stay on one line.

Sticky navigation must remain below the application status bar and must never cover the first project row.

## Activity Grid and tables

Tables are allowed to scroll horizontally inside their own bounded container. They must not increase page width indefinitely.

The Activity Grid uses:
- sticky header;
- optional pinned/frozen columns;
- persisted field width and visibility;
- compact but readable cell padding;
- tabular numeric alignment;
- RTL-aware pinned-column shadows.

Print output removes sticky behavior and lets tables use the printable page width.

## Gantt

Gantt remains a separate bounded visual surface below the Activity Grid.
The label area is fixed/flexible within a minimum usable width while the time axis can scroll horizontally.

On narrow screens Gantt scrolling is preferred to compressing the time axis or task labels until they become unreadable.

Critical-path emphasis remains semantic and must not be implemented through decorative color overload.

## Charts

Cost, EVM, progress and other analytical charts must live inside bounded chart surfaces. The chart container uses a minimum readable height of about 220px on desktop and about 180px on mobile, with responsive height up to roughly 420px. The plotting surface must never create body-level horizontal overflow.

When a chart has more horizontal data than the viewport can show, use an explicitly scrollable chart surface rather than shrinking labels or axes below readability. Charts should keep a stable aspect and let legends/wrapped labels occupy reserved space.

Print charts use a controlled A4-safe height of about 55mm and must not split across pages when practical.

## Cards, dashboards and control surfaces

Control summaries, Smart Guide, field assurance, site logs, procurement, change/claim and similar auxiliary panels span the complete workspace width rather than occupying arbitrary cells of the three-column shell.

Inside those sections, metric cards use a compact grid:
- 4 columns on wide desktop;
- 2 columns on tablet;
- 1 column on mobile.

This keeps KPI cards, findings and operational records aligned and prevents the WBS/Activity/Gantt shell from being displaced by unrelated control cards.

## Marketing homepage

Marketing text uses a larger base size than dense workspace UI.
Hero heading scales responsively and uses balanced wrapping.
Cards are fluid and do not force horizontal overflow.
Header navigation may scroll on intermediate widths; on mobile it collapses rather than stacking into uncontrolled rows.

## Print

Project-control print output is A4 landscape with 10mm margins.

Print-specific behavior:
- hides interactive navigation and field-chooser controls;
- removes sticky positioning;
- disables decorative shadows;
- expands tables and Gantt surfaces to printable width;
- reduces table typography only enough to fit professional reports;
- prevents cards and Gantt rows from being split where practical;
- keeps semantic structure and readable headings.

No print rule may alter Shared Core calculations or project data; print is presentation-only.

## Cross-client handoff

Desktop and Mobile currently expose executable runtime/contract foundations rather than a finished native visual shell. Their UI implementations must adopt these same geometry and typography rules when the native shells are introduced, while preserving their product-specific interaction density.

Mobile remains field-first: fast entry, limited typing, large touch targets, clear sync state and camera/voice affordances.

Desktop remains data-dense: keyboard-friendly navigation, multi-pane project controls, large tables and Gantt surfaces.

## Forbidden layout drift

Do not:
- introduce arbitrary global font sizes for individual screens;
- let dense tables create body-level horizontal overflow;
- wrap primary menus into unpredictable multi-row stacks;
- use decorative metallic textures on dense data panels;
- squeeze Gantt time axes below readable dimensions;
- change calculation semantics to make presentation fit;
- duplicate scheduling or control formulas inside clients for visual convenience.
