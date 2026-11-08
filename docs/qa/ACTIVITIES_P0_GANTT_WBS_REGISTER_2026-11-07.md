# Activities P0 register — Gantt geometry, relationship attachment, WBS hierarchy color

Date: 2026-11-07
Branch: `codex/jalal/cubi-shell-v26-20261104`
Scope: Activities window (activity grid + Gantt chart + WBS hierarchy)
Status: **OPEN — implementation in progress**

This register records three P0 defects before any code change. Each defect was
confirmed against the current source, not against a screenshot impression. The
Activities window is not accepted until all three are closed with live browser
evidence across the viewport/interaction matrix below.

## P0-1 — Bars are not anchored to one shared timeline/row geometry

Evidence in the current code:

- `apps/web/src/workspace-view.ts` renders relationship paths with
  `viewBox="0 0 100 ${rows.length * 100}"` and `preserveAspectRatio="none"`,
  while every Gantt row is a fixed pixel height (`--cp-p6-row-height`). The
  vertical viewBox unit therefore does not equal a rendered pixel, so the path
  centre of row *i* drifts from the real row centre as the row count grows.
- `.cp-gantt-links` is positioned at `left: calc(var(--cp-gantt-label-width) + 16px); right: 8px`,
  but the bar track starts at exactly the label width. The SVG overlay and the
  tracks therefore use different horizontal origins.
- The axis (`.cp-gantt-axis`) is a sibling of the scrolling chart
  (`.cp-gantt-chart`). A vertical scrollbar appears inside the chart only and
  narrows its tracks, so axis ticks and bars no longer share a width.
- Table/Gantt scroll sync copies `scrollTop` one-to-one even though the table
  header and the Gantt axis have different heights.

Required result: one shared row pitch and timeline mapping drives the axis,
rows, bars and relationship endpoints. Resizing the panes, changing row height,
font size, column widths, zoom or timescale must recompute presentation
geometry without moving a bar off its date or its row.

## P0-2 — Relationship endpoints are not guaranteed to touch their bars

Evidence in the current code:

- Link geometry uses generic bar edges but ignores milestone point geometry and
  has no lane separation for multiple links between the same rows.
- The path Y coordinates come from the drifting viewBox described in P0-1, so
  the arrow can land between rows.
- Because the SVG overlay is offset by 16/8 px, a path that mathematically
  touches the bar edge is painted beside it.
- FS/SS/FF/SF routing is present in `relationshipPath`, but there is no test
  proving all four types plus lag persistence and RTL/scroll stability.

Required result: every path starts and ends on the real start/finish edge of
the persisted predecessor/successor bar, for all four relationship types,
after resize, zoom, scroll, collapse and reordering.

## P0-3 — WBS level colour is painted across the whole row instead of the hierarchy

Evidence in the current code:

- `.cp-p6 #cp-activity-grid tbody tr.cp-p6-wbs-band > td` sets
  `background-color: var(--cp-wbs-band)` for **every** cell, including the
  logic and action columns. The level colour therefore reads as a row status
  colour, competes with selection/critical colour and does not form a tree.
- Activity rows only receive a blank `cp-p6-indent` spacer. There are no
  vertical rails, no parent/child elbows, no branch end, and no per-level line
  colour or weight.
- WBS colours are a hard-coded module constant and cannot be changed or saved.

Required result: each WBS level has its own colour used for vertical guide
rails and elbows in the hierarchy area of both the table and the Gantt; the
colour follows the branch to its last child and stops there; selection,
critical path and activity status colours remain independent; the palette is
editable and persisted with the presentation model.

## Acceptance matrix (must pass before Activities is accepted)

Viewports: 1280×720, 1366×768, 1920×1080. Window resized horizontally and
vertically. Fullscreen enter/exit.

Interactions: row height change, table font-size change, WBS/Activity Name
column width change, Gantt pane width change, Zoom In/Out, Timescale change,
horizontal and vertical scroll, collapse/expand all WBS levels, reordered
activities, filter apply/clear, relationships of all four types in first,
middle and last visible rows.

Assertions for every state:

1. Each bar's left/right edges match its persisted start/finish date on the
   axis.
2. Each link endpoint coincides with the corresponding bar edge (tolerance
   ≤ 1 px after measurement).
3. Every visible WBS branch keeps continuous vertical rails to its last child,
   with no rail bleeding into the next branch and no level colour across the
   whole row.

## Honest limits recorded up front

- The project read model exposes no data date fact (`dataDate` is rendered as
  “—”), so the Data Date line and a Remaining bar split at the data date will
  stay disabled rather than fabricated. They are tracked as blocked on a
  service contract, not simulated.
- Fiscal-year, shift and day/hour timescale intervals need calendar facts the
  runtime does not expose yet; they stay disabled with an explicit reason in
  the Timescale dialog.
