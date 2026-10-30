# CUBI Workspace Layout Specification

Status: Phase 3 blueprint. Supplements `docs/design/CUBI_UI_LAYOUT_SYSTEM.md`; it does not replace that document's typography, colour or print rules.

## Desktop geometry (≥1280px)

```
┌──────────────────────────────────────────────────────────────────────┐
│ App status bar (28px): product · sync · language · calendar · user   │
├──────────────────────────────────────────────────────────────────────┤
│ Menu bar (32px): Workspace Edit View Project Organization Tools ...  │
├──────────────────────────────────────────────────────────────────────┤
│ Main toolbar (40px, wrap-free, overflow menu)                        │
├──────────────────────────────────────────────────────────────────────┤
│ Context bar (36px): Domain › Portfolio › Project · R12 · Data date  │
├──────────────────────────────────────────────────────────────────────┤
│ Window tabs (34px): [Activities ×] [WBS ×] [Resources ×] …          │
├──────────────┬───────────────────────────────────────┬───────────────┤
│ Navigation   │ Layout bar (32px): layout · filter · menu             │
│ tree         ├───────────────────────┬───────────────┤ Details rail  │
│ 200–280px    │ Activity table        │ Gantt         │ 220–340px     │
│ resizable    │ min 360px             │ min 320px     │ resizable     │
│              ├───────────────────────┴───────────────┤               │
│              │ Bottom layout: Activity Details (160–45%)            │
├──────────────┴───────────────────────────────────────────────────────┤
│ Status bar (26px): project · data date · baseline · layout · filter  │
└──────────────────────────────────────────────────────────────────────┘
```

Heights: app status 28, menu 32, main toolbar 40, context 36, tabs 34, layout bar 32, status 26. These are content-box heights at 100% zoom; text must not clip at 125% browser zoom.

Widths:
- Navigation tree default 220px, range 180–320px, collapsible to a 36px rail.
- Table/Gantt split default 55/45, each min 320px; splitter 6px hit area, 1px visual.
- Details rail default 260px, range 220–380px, collapsible.
- Bottom layout default 240px, range 140px–45% of working area, collapsible to 32px header.

The workspace uses the full viewport height (`100dvh`) with internal scrolling only. The page itself must not scroll. The 1920px centring rule from the visual system applies to the content column of public pages; the authenticated workspace is edge-to-edge to maximise table width.

## Regions and stacking

| Layer | z-index | Notes |
| --- | --- | --- |
| App status | 60 | Never overlapped |
| Menu bar / dropdowns | 50 | Dropdowns above toolbars, below modals |
| Modals | 80 | Focus trap |
| Toasts | 90 | Top-right in LTR, top-left in RTL |
| Splitters | 10 | Visible on hover/focus |
| Sticky table header | 5 | Stays inside table container |

No sticky element may cover the first data row or the tab strip.

## Table

- Sticky header; frozen columns optional; horizontal scroll inside the table container.
- Row height default 30px (compact 26, comfortable 34) persisted in layout.
- Header height 34px; uppercase labels at 11–12px with letter spacing only in Latin.
- Numeric cells right-aligned in LTR and left-aligned in RTL with tabular figures.
- Selection: single row, Ctrl/Cmd multi, Shift range; keyboard Up/Down/Home/End/Page.
- Editable cell enters edit on double-click, Enter or F2; Esc reverts; Tab commits and moves.
- WBS group rows are bold with an expand/collapse chevron and aggregate values.
- Empty state stays inside the table body and never replaces the toolbar.

## Gantt

- Left edge aligns with the table's right edge; both share one vertical scroll container so rows stay synchronised.
- Timescale header 48px (two tiers: month/quarter above, day/week below).
- Bar height 14px, row pitch matches table; milestone diamond 10px.
- Relationship lines orthogonal with arrowheads; critical path in the critical colour; baseline bar as a thin outline below the current bar.
- Data date line full height with a label at the top tier.
- Zoom keeps the selected activity in view.
- In RTL, the time axis still runs left→right (dates are not mirrored); only text alignment and panel order mirror.

## Splitter behaviour

- Pointer drag, keyboard (focus + arrow keys, Home/End), double-click to reset to default.
- Min/max clamping per region; the layout must never produce a zero-width table or Gantt.
- Sizes persist per user per window in `localStorage` (`cubi:workspace:split:{window}`) and are included in saved layouts where the layout format supports it.
- During drag, disable text selection and set `cursor: col-resize/row-resize`.

## Window tabs

- Height 34px; each tab shows icon, label, dirty dot and close `X`.
- Active tab uses surface colour + 2px accent underline; inactive tabs are muted.
- Overflow scrolls horizontally with edge fades; a chevron lists all tabs.
- Drag to reorder; Ctrl+Tab cycles; middle-click closes; `X` on hover only.
- Dirty tab close asks Discard / Save / Cancel.

## Default layout

1. Activities window open, WBS grouping, WBS sort ascending.
2. Top layout: table + Gantt. Bottom layout: Activity Details, General tab.
3. Table columns: ID, name, WBS, type, duration, start, finish, predecessors, total float, critical, % complete.
4. Gantt scale: week. Relationship lines on. Data date line on.
5. Navigation tree expanded to the current project.

The default must be restored on first login, after clearing preferences, and whenever no project layout exists. It must not silently revert after a refresh once the user has saved a layout.

## Responsive behaviour

| Width | Behaviour |
| --- | --- |
| ≥1440px | Full layout as above |
| 1280–1439px | Navigation collapsible; details rail 240px |
| 1024–1279px | Details rail becomes an overlay drawer; table/Gantt split 50/50 |
| 768–1023px | Menu bar condenses to "Menu" button; toolbars overflow; bottom layout tabbed |
| <768px | Single-column: table, then Gantt, then details as tabs; menu and toolbars in drawers; no horizontal page scroll |

Touch targets ≥40px on tablet/mobile. Splitter drag is replaced by preset panel sizes on touch.

## RTL

- Direction comes from the workspace locale (fa → rtl), independent of calendar system.
- Menu order, navigation side, details rail and tab order mirror; table columns keep domain order but cell text follows direction.
- Icons with direction (expand, next) mirror; play/zoom and time-axis icons do not.
- Scrollbars and sticky shadows mirror.
- Print mirrors the page margin order.

## Print

- Print uses the active layout: columns, grouping, filters, Gantt range and timescale.
- Page: A4/A3 landscape default, margins 12mm, header with project + data date, footer with page number and build.
- Sticky headers/footers and splitters are removed; tables may wrap the page width but never shrink below 8pt.
- RTL print uses right-to-left page order for columns.

## Accessibility

- Landmarks: `banner` (app status), `navigation` (menu + tree), `main` (working area), `contentinfo` (status).
- Menu bar uses `role=menubar` with arrow-key navigation and Esc to close.
- Window tabs use `role=tablist`/`tab` with correct `aria-selected` and panel linkage.
- Splitter uses `role=separator` with `aria-valuenow/min/max`.
- Focus ring visible on all surfaces; colour contrast ≥4.5:1 for text.

## Verification

- Unit tests for splitter clamping, tab state and layout defaults.
- Playwright/browser E2E: open Activities, verify WBS grouping, resize panels, switch window tabs, reload and confirm persistence, switch fa/en and rtl/ltr, verify no overlap at 1280/1024/768 widths.
- Screenshot evidence stored under `apps/web/e2e/artifacts/` and referenced by the execution log.
