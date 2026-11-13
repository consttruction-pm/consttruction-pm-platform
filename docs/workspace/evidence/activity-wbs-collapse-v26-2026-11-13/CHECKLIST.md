# ACT-006 / ACT-007 — WBS expand/collapse acceptance (2026-11-13)

Contract: `cubi-activity-wbs-collapse-v26.v1`
Tested code: `98e309c02604a956de37ef504b319c6dcd6e0c85`
Suite: `apps/web/e2e/activity-wbs-collapse-v26.mjs`
Report: `activity-wbs-collapse-v26.json` (9/9 scenarios, 0 exceptions, 0 console errors, 0 failing API responses)
Screenshots: `01`–`09`

## Help topics

- [Collapse or expand grouped data](https://docs.oracle.com/cd/G48902_01/client_help/en_US/collapse_or_expand_grouped_data.htm) — a minus sign beside a grouping band summarizes it and a plus sign expands it.
- [Collapse or expand all groups in a layout](https://docs.oracle.com/cd/G48902_01/client_help/en_US/collapse_or_expand_all_groups_in_a_layout.htm) — View > Collapse All / Expand All, also available from the layout shortcut menu.
- [Grouping by hierarchy](https://docs.oracle.com/cd/G48902_01/client_help/en_US/grouping_by_hierarchy.htm) — the WBS tree that supplies the bands.

## Environment

- `python3 -m construction_pm.preview --web-root apps/web --host 127.0.0.1 --port 4200 --database /tmp/collapse-e2e.db --reset`
- Fixture: Riverside Pump Station Upgrade (`preview-rps-01`), 7 WBS bands (root + six children) and 14 activities; Civil works holds 5 of them.
- Viewports: en/LTR 1366×768 and 1920×1080, fa/RTL 1280×720.

## Scenarios

| # | Proof | Result |
|---|---|---|
| 01 | Baseline shows 7 bands and 14 activities in both panes with every table row matching its Gantt row id, kind, height and vertical offset (≤2 px). The Civil works `−` control collapses it: `data-wbs-collapsed=true`, `aria-expanded=false`, the control turns to `+` with an Expand title, exactly 9 activities remain in table and Gantt, all 7 bands stay, the local view store records the id and no non-GET API request is issued. | pass |
| 02 | The root `−` control leaves exactly one band, zero activity rows and one Gantt group row; expanding restores 7 bands, 14 rows and alignment. | pass |
| 03 | Collapsing Civil works, double-clicking the root to collapse it and double-clicking the root again restores 7 bands but only 9 activities: the nested child keeps its own collapsed state. | pass |
| 04 | Toolbar Collapse All collapses only the depth-1 bands (7 bands, 0 activities); Expand All restores 14. Right-clicking a band opens a `table-wbs` context menu whose enabled **Collapse This Branch** command collapses the root to one band and zero activities; Expand All then restores the tree. | pass |
| 05 | With Civil works collapsed, Save Layout publishes `metadata.wbsCollapse = ["WBS-RPS-CIVIL"]` at revision 2 and keeps `metadata.groupSort.groupBy = "wbs"`. The browser-local collapse store is emptied and a full reload still shows the branch collapsed (9 activities) and repopulates the store; table and Gantt stay aligned. | pass |
| 06 | Expand All, Save Layout publishes `wbsCollapse: []` at revision 3; emptying the local store and reloading restores all 7 bands and 14 activities, proving the empty list is an explicit expanded state rather than an absent preference. | pass |
| 07 | Enter on a focused band row collapses it; Space expands it; Enter on the focused `+`/`−` button collapses it exactly once (no double toggle) with no schedule write. | pass |
| 08 | Persian RTL at 1280×720: `dir=rtl`, the collapsed branch survives the locale switch, the toggle title is `بازکردن…`, all seven bands and nine activities keep their Gantt partners aligned and the document has 0 px horizontal overflow. | pass |
| 09 | English at 1920×1080 keeps the same collapsed tree with 0 px overflow and exact table/Gantt row identity. | pass |

## Defects found and fixed in this slice

1. **Collapse state did not travel with the saved layout.** `cubi:workspace-wbs-collapse` in localStorage was the only store, so Save Layout, a layout switch or another browser lost the tree state. `apps/web/src/workspace-layout-settings.ts` now validates and writes `metadata.wbsCollapse` (deduplicated, trimmed, capped at 500 ids, absent key = no opinion, empty array = all expanded); `withCollapsedWbsMetadata` merges it into every layout commit and Save As, and `hydrateCollapseFromLayout` in `apps/web/src/main.ts` applies it once per `tenant:project:scope:revision` before the grid and Gantt read display rows.
2. **The band row was focusable but inert.** A WBS band carries `tabindex="0"` and `aria-expanded`, yet Enter/Space did nothing unless the pointer hit the inner button. The key handler in `apps/web/src/workspace-view.ts` now toggles the focused branch and leaves the native button activation alone so a focused `+`/`−` never toggles twice.

## Boundaries

- Collapse is a view preference: it never writes an activity, relationship, date, duration or layout revision until the user chooses Save Layout; scenario 01 asserts zero non-GET `/api/` requests during toggles.
- Table and Gantt read the same `WorkspaceDisplayRow[]`; a collapsed branch removes only descendant rows and the derived summary band keeps its display-only rollup bar.
- An active filter reveals matching descendants and ignores collapse, so hits cannot be hidden (documented in `workspace-view.ts`).

## Known limits

- Collapse state is stored per project id inside the browser and per saved layout; there is no server-side per-user tree preference outside a layout revision.
- The Gantt group row is not itself a toggle target; collapsing is done from the table band, toolbar, context menu or keyboard on the band row.
- Collapse All keeps top-level bands open (desktop convention); there is no separate "collapse to level" control beyond Collapse To.
