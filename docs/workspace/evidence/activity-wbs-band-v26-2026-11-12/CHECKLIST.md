# ACT-004 — WBS band fonts, colours and hierarchy formatting

Contract: `cubi-activity-wbs-band-v26.v1`
Browser suite: `apps/web/e2e/activity-wbs-band-v26.mjs`
Evidence captured at code SHA: `138208c805ec2ee52bc3a85cb16e949868a103d4` (pre-merge tested commit of this slice)
Environment: local CUBI preview (`python3 -m construction_pm.preview`), Chromium via the repository
CDP harness, database `/tmp/wbs-band-e2e.sqlite3` reset for the run.

## Reference

- [Change group row fonts and colors](https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_group_row_fonts_and_colors.htm) —
  View, Group and Sort; each band owns a Font & Color cell with independent font and colour.
- [Format grouping bands](https://docs.oracle.com/cd/G48902_01/client_help/en_US/format_grouping_bands.htm) —
  Font box, Color box, and the Show Title / Show ID-Code / Show Name-Description band text options.

CUBI maps the documented per-band Font & Color cell to the WBS band presentation in
`WorkspacePresentation.wbs`, edited in User Preferences (`WBS band format`). It is a
presentation value stored with the saved layout; it never reaches the schedule model.

## Scenarios

| # | Scenario | Viewport / language | Result | Screenshot |
|---|----------|---------------------|--------|------------|
| 01 | Seven WBS bands render code + name with the shipped defaults (Tahoma 11 px, level contrast ink, 22 px band); no band overlaps the next; every band has its Gantt summary row at the same depth and vertical offset | 1366×768 / en LTR | PASS | `01-wbs-band-defaults-en-1366.png` |
| 02 | The dialog writes Cairo 14 px, custom ink `#102030`, 30 px band, Show Title on, Show ID/Code off, Show Name on; cell computed font/size/colour/height match; the activity table keeps its own 11 px Tahoma; the layout publishes `presentation.wbs` with the same values; bands stay aligned with Gantt rows | 1366×768 / en LTR | PASS | `02-wbs-band-cairo-30px-en-1366.png` |
| 03 | A full reload restores the band font, ink, height and label selection, and keeps the table/Gantt alignment | 1366×768 / en LTR | PASS | `03-wbs-band-after-reload-en-1366.png` |
| 04 | `Reset band format` restores Tahoma 11 px, automatic ink, 22 px and the default labels, publishes a new layout revision, leaves the activity table presentation untouched, and survives a reload | 1366×768 / en LTR | PASS | `04-wbs-band-reset-en-1366.png` |
| 05 | The Persian dialog exposes `ترجیحات کاربر`, `قالب باند WBS` and `بازنشانی قالب باند`; dialog and 7-band RTL table render with 0 px page overflow | 1280×720 / fa RTL | PASS | `05-wbs-band-dialog-fa-rtl-1280.png` |
| 06 | The band format and Gantt agreement hold with 0 px page overflow | 1920×1080 / en LTR | PASS | `06-wbs-band-en-1920.png` |

## Diagnostics

- Runtime exceptions: 0
- Console errors: 0
- API responses ≥ 500: 0

## Defect found and fixed during this slice

The Gantt advanced every row by the table's activity row height only. WBS bands are taller
than activity rows, so each band moved the table one row ahead of its Gantt summary row;
with the new configurable band height the drift became large. The chart now builds cumulative
row metrics (`ganttDisplayMetrics`) from the band height and routes bars, relationship links,
sight lines and the progress line from those metrics, and the group row publishes its own
pitch. The suite asserts the vertical offset of every band against its Gantt row in all
viewports.

## Known limits

- Band font & colour are a per-level background palette plus one band typeface/ink, not a
  separate font dialog per level; the reference exposes a Font & Color cell for each band.
- Show Title renders the field title `WBS`; the reference also allows an empty title band,
  which CUBI does not emit because a band without a label would be indistinguishable.
- Band height is a single value for all levels; per-level heights are not offered.
