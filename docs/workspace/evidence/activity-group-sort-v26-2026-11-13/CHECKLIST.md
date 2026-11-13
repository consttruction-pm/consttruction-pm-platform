# ACT-002 — Multi-level grouping, nested bands and independent collapse (2026-11-13)

- Contract: `cubi-activity-group-sort-v26.v2`
- Tested code: `5945c90723fe63d221d213588fbbfcfd2089475c` (code commit; evidence is committed separately)
- Environment: local full-stack preview, `PYTHONPATH=src python3 -m construction_pm.preview --web-root apps/web --host 127.0.0.1 --port 4198 --database /tmp/cubi-act002-evidence.sqlite --reset`, tenant `cubi-preview-tenant`, project `preview-rps-01` (14 activities, 7 WBS bands)
- Help topics:
  - [Group activities by field](https://docs.oracle.com/cd/G48902_01/client_help/en_US/group_activities_by_field.htm): group by an activity field and count the activities in each band.
  - [Grouping by hierarchy](https://docs.oracle.com/cd/G48902_01/client_help/en_US/grouping_by_hierarchy.htm): the WBS level walks the stored hierarchy and each band collapses on its own.
  - [Grouping activities by WBS path](https://docs.oracle.com/cd/G48902_01/client_help/en_US/grouping_activities_by_wbs_path.htm): grouping levels can be reordered, including WBS after another field.
  - [Sort activities](https://docs.oracle.com/cd/G48902_01/client_help/en_US/sort_activities.htm): the Activity Table sorts the rows inside a group.
- CUBI component: Activities → View → Group and Sort By (dialog and toolbar shortcut).
- Code path: `apps/web/src/workspace-grouping.ts` (six-field catalog, persisted value reads, typed band keys, band ordering) → `apps/web/src/workspace-wbs-display.ts` (`buildWorkspaceDisplayRows` emits WBS and field bands up to three levels deep with rollups and composite band keys) → `apps/web/src/workspace-filter-sort.ts` (grouped fields are removed from the in-band sort, so the innermost band keeps the configured order) → `apps/web/src/workspace-dialogs.ts` (three ordered field+direction rows) → `apps/web/src/workspace-view.ts` (table bands, Gantt band rows, per-band collapse handling) → `apps/web/src/main.ts` (hydrate/save/reset the plan with the layout).
- Persistence / API boundary: the plan is stored in the saved Activities layout as `metadata.groupSort.groupLevels` through `GET|POST /api/projects/{id}/p6/layouts/{scope}/activity`; the existing `wbsCollapse` metadata still carries top-level WBS ids. Band collapse uses the per-project `cubi:workspace-wbs-collapse` store. No activity row, date, duration, relationship or other schedule input is written; grouping is display-only and the expected bands are computed from `GET /api/v2/workspace/control-room/read`, not from fixture constants.
- Permissions: the same layout write path (`PROJECT_WRITE`) as every other presentation change; no new route is introduced.
- Slice delivered:
  - `activityGroupLevels` is the ordered source of truth (max three levels, unique valid fields); `activityGroupBy` still mirrors only whether the outer band is WBS, so tree actions, Collapse To and the existing WBS tests keep their meaning.
  - Catalog: `wbs`, `activity_status`, `activity_type`, `is_critical`, `activity_code`, `total_float`. Values are read from persisted `cells`; criticality falls back to the schedule fact and is never recalculated.
  - Typed band keys (`s:`, `n:`, `b:`, `e:`) keep text `"1"` apart from number `1`, are attribute-safe, and persist in the collapse store. Top-level WBS bands keep the node id; nested bands use `<parent>><field>:<key>` and `<parent>>wbs:<nodeId>`.
  - Sibling bands order naturally and numerically; "No value" is always last, in either direction. A WBS level with no loaded tree is skipped rather than grouping by raw ids. Field bands carry derived start/finish/duration/progress rollups and an activity count.
  - The Group and Sort dialog renders three ordered group rows from the shared catalog; the toolbar select remains the single-level shortcut. The layout selector's dirty state compares the full plan.
- Browser scenarios (`apps/web/e2e/activity-group-sort-v26.mjs`, 9/9 pass, 0 exceptions / 0 console errors / 0 5xx):
  1. The dialog exposes three group rows with the six fields and default WBS; Start desc + name asc renders a flat computed order and the Gantt follows.
  2. Save Layout stores `none` with no levels; a full reload restores the exact order.
  3. WBS grouping keeps name-ascending activities in every band, stores `[{wbs, asc}]` and reloads 7 bands / 14 rows.
  4. The Persian dialog and a flat plan render RTL at 1280×720 with 0 px overflow.
  5. 1920×1080 fits with 0 px overflow.
  6. Activity Status renders `Completed (3)`, `In Progress (1)`, `Not Started (10)`; the toolbar and Gantt agree; one band collapses to 11 visible rows while its siblings stay open; `[{activity_status, asc}]` saves and reloads.
  7. WBS + Activity Status nests status bands inside each WBS node with exact per-node labels and counts; a nested band and a WBS band collapse independently; `[{wbs, asc}, {activity_status, asc}]` survives reload.
  8. A field-first `is_critical` → WBS plan renders `Critical (7)` / `Non-critical (7)` outer bands with WBS bands nested inside and stores both levels.
  9. The nested plan stays readable in Persian RTL at 1280×720 with 0 px overflow.
- Screenshots: `01`…`09` in this folder (`01` flat sort, `03` WBS bands, `06` status bands after reload, `07` nested WBS+Status after reload, `08` critical-then-WBS, `09` RTL nested).
- Unit tests at the same code: 1016 `tsx` + 14 `node --test` pass; `npx tsc --noEmit`, `npx tsc -p tsconfig.test.json --noEmit` and `npm run build` pass.
- Remaining gaps: the toolbar select changes only the first level; field bands inherit the WBS band palette (no per-band font/colour editor); the WBS level is the persisted hierarchy, not a hand-typed path string; sorting by a grouped field is intentionally skipped; the grid is not virtualised for very large grouped projects.
