# V27 Icon, Colour and State Matrix — Activities Workspace

- Tested head: `b71cd61f46ebe358d1b15eee21068977b03493cf`
- Icon system: inline CUBI SVG icons, 53 distinct names across 57 toolbar buttons.
- No vendor icon artwork is used. Product name "CUBI" is shown, not the reference
  vendor's branding.

Statuses: **مطابق و تأییدشده** · **پیاده‌سازی‌شده ولی آزمون‌نشده** · **ناقص** · **غایب**

## 1. Toolbar icon set (53 distinct)

`activity, assignment, bars, baseline, calendar, check, clock, close, collapse,
collapseTo, columns, copy, cut, delete, dissolve, documents, edit, expand, fill,
filter, find, fit, folder, fullscreen, gantt, group, help, issues, language,
lineNumbers, link, money, network, open, panels, paste, plus, project, redo,
refresh, risks, rowHeight, save, saveAs, settings, sort, thresholds, tree, undo,
unlink, wbs, zoomIn, zoomOut`

Every icon appears with a visible label or an accessible title; no icon-only
control lacks a name.

## 2. Command states

| State | Visual treatment | Behaviour | Status |
|---|---|---|---|
| Enabled | Normal foreground | Executes command | **مطابق و تأییدشده** |
| Disabled | Muted foreground, `disabled` attribute | Not focusable; `title` states the reason | **مطابق و تأییدشده** |
| Pressed / active (Gantt, Full Screen, Details toggle) | Inset or accent background, `aria-pressed="true"` | Toggles the surface | **مطابق و تأییدشده** |
| Checked (menus: line numbers, WBS, Gantt, themes, toolbar families) | Check mark | Reflects current presentation | **مطابق و تأییدشده** |
| Hover / focus | Background and focus ring | Keyboard visible | **مطابق و تأییدشده** |
| Overflow | Horizontal scroller with overflow control | All 57 buttons reachable at 1280 | **مطابق و تأییدشده** |

Reference run: 10 toolbar buttons are disabled (Cut, Copy, Paste, Delete,
Fill Down, Dissolve, Expand All, Collapse All, Collapse To, Baselines); each
carries a localized reason. Expand/Collapse become enabled when grouped by WBS.

## 3. Table row and bar states

| Element | Colour / state rule | Evidence | Status |
|---|---|---|---|
| Normal activity row | Surface background, alternating selection only | visual acceptance | **مطابق و تأییدشده** |
| Selected row | Selection token across table and Gantt | `activity-multi-select-v26` | **مطابق و تأییدشده** |
| Critical activity | Critical token for row flag and Gantt bar | `activity-gantt-overlays-v26` | **مطابق و تأییدشده** |
| Completed | 100% progress state; bar fully filled | `activities-v26-scenarios` | **مطابق و تأییدشده** |
| In progress | Partial progress fill from stored percent | same | **مطابق و تأییدشده** |
| Milestone | Diamond marker (start/finish) | fixtures A155, gantt overlays | **مطابق و تأییدشده** |
| Summary / WBS band | Summary bar and band row style | `activity-wbs-band-v26` | **مطابق و تأییدشده** |
| Baseline bar | Baseline token, only when baseline facts exist | `activity-baseline-v26` | **مطابق و تأییدشده** |
| Dependency link | Arrow + relationship label; red when critical/driving per presentation rule | `activity-relationships-v26` | **مطابق و تأییدشده** |
| Data date | Distinct vertical line with label | gantt overlays | **مطابق و تأییدشده** |
| Non-working time | Weekend and holiday shading; Jalali exception honoured | visual acceptance (11 columns, 1 holiday) | **مطابق و تأییدشده** |
| Progress line | Optional line following the data date | `activity-gantt-overlays-v26` | **مطابق و تأییدشده** |
| WBS collapse control | Expand/collapse affordance on band rows | `activity-wbs-collapse-v26` | **مطابق و تأییدشده** |
| Dirty window tab | Dot marker on the tab | `workspace-window-tabs-v26` scenario 07 | **مطابق و تأییدشده** |
| Locked / read-only viewer | Write controls disabled with reason | `activity-columns-v26` scenario 10 | **مطابق و تأییدشده** |

## 4. Themes

Six presentation themes are selectable from View: CUBI Classic — Version 26
Reference, Modern 3D, Graphite, Arctic, Copper, Midnight. Each theme supplies
surface, text, muted, accent, critical, selection and band tokens. Theme choice
persists with the workspace presentation.

Status: **پیاده‌سازی‌شده ولی آزمون‌نشده** for a complete per-theme screenshot
grid. Contrast and fit are covered only for the Classic theme in the visual
acceptance run.

## 5. Colour integrity rules

- Critical colour is used only for critical facts from the read model, never
  inferred in the browser.
- Progress length and percent labels come from stored values; no browser-side
  date arithmetic exists for bars (the scheduling core owns dates).
- Holiday shading uses stored calendar exceptions, including the recorded Jalali
  holiday (2027-02-08 → Gregorian conversion through the Shared Core).

## 6. Gaps

- Per-theme visual regression screenshots are not part of this run.
- Vendor reference colours cannot be compared pixel-for-pixel because the
  official figures are not held and Help returns 403. See `deviation-register.md`.
