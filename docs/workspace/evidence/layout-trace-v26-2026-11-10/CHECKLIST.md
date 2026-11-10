# Layout and Trace Logic — browser evidence (2026-11-10)

Contract: `cubi-layout-trace-v26.v1` in `layout-trace-v26.json`.

Environment: real local full-stack preview (`construction_pm.preview`), SQLite database
`.preview/cubi-preview.sqlite3`, seed `cubi-preview-seed.v2`, project `preview-rps-01`
(Riverside Pump Station Upgrade, 14 activities, 15 persisted relationships), Planner persona,
English UI at 1440×900. Run at git head `e3ce8ef8`.

Re-run:

```bash
npm run build
CUBI_PREVIEW_URL=http://127.0.0.1:4174 node e2e/layout-trace-v26.mjs
```

| # | Scenario | Result | Screenshot |
| --- | --- | --- | --- |
| 01 | Default Activities layout is table + Gantt with the Details bottom surface | pass | `01-default-table-gantt-details.png` |
| 02 | View menu exposes the six Show on Top / Show on Bottom commands with real checked state | pass | `02-view-menu-layout-and-trace.png` |
| 03 | Show on Top: Activity Table hides the Gantt and splitter | pass | `03-top-table-only.png` |
| 04 | Show on Top: Activity Network draws 14 nodes and all 15 persisted relationships | pass | `04-top-activity-network.png` |
| 05 | Table + Gantt restored; A130 selected | pass | `05-activity-a130-selected.png` |
| 06 | Show on Bottom: Trace Logic shows the real predecessor/successor chain | pass | `06-bottom-trace-logic-a130.png` |
| 07 | Depth 1 narrows the chain to level 1 and is persisted | pass | `07-trace-depth-1.png` |
| 08 | Trace navigation selects A120 in the table and keeps Trace Logic open | pass | `08-trace-goto-a120.png` |
| 09 | Show on Bottom: None closes the pane and keeps the selection | pass | `09-bottom-none.png` |
| 10 | Table-only + None survive a full reload through the stored preferences | pass | `10-layout-persisted-after-reload.png` |
| 11 | Default table + Gantt / Details restored; no page exceptions, console errors or API 5xx | pass | `11-restored-default-layout.png` |

Scenario 06 chain for A130 at depth 2: predecessors A120 (level 1), A110 (level 2); successors
A140, A145, A150 (level 1), A155, A160, A170 (level 2), including the persisted `SS+5d` link from
A140 to A170. Diamond convergence (A160 reached from A140 and A150) is listed once and does not
produce a circular-dependency notice.
