# ACT-016 — Trace Logic predecessor and successor levels (2026-11-13)

Contract: `cubi-activity-trace-logic-v26.v1`
Tested code: `446de0e970f304916adde1cfc7e03ed17db8f707`
Suite: `apps/web/e2e/activity-trace-logic-v26.mjs`
Report: `activity-trace-logic-v26.json` (9/9 scenarios, 0 exceptions, 0 console errors, 0 failing API responses, 0 schedule writes, 0 relationship writes)
Screenshots: `01`–`08`

## Help topics

- [Trace Logic](https://docs.oracle.com/cd/G48902_01/client_help/en_US/trace_logic.htm) — the lower layout represents the relationships of an activity selected in the upper layout; a red border marks a critical activity and a connecting line is a relationship; the number of levels is set through View, Bottom Layout Options.
- [Set Trace Logic preferences](https://docs.oracle.com/cd/G48902_01/client_help/en_US/set_trace_logic_preferences.htm) — the number of predecessors and the number of successors are specified separately.
- [Move around in Trace Logic](https://docs.oracle.com/cd/G48902_01/client_help/en_US/move_around_in_trace_logic.htm) — clicking an activity in the Activity Table, Gantt Chart, Activity Usage Spreadsheet, Activity Network or Trace Logic itself focuses its chain.
- [Display Trace Logic](https://docs.oracle.com/cd/G48902_01/client_help/en_US/display_trace_logic.htm) — View, Show on Bottom, Trace Logic.

## Environment

- `PYTHONPATH=src python3 -m construction_pm.preview --web-root apps/web --host 127.0.0.1 --port 4209 --database /tmp/trace-post.db --reset`
- Fixture: Riverside Pump Station Upgrade (`preview-rps-01`), 14 activities and 15 persisted relationships (14 FS plus the SS `REL-RPS-170` A140→A170 with +5 working days).
- Viewports: en/LTR 1366×768 and 1920×1080, fa/RTL 1280×720.

## Scenarios

| # | Proof | Result |
|---|---|---|
| 01 | View → Show on Bottom → Trace Logic for A130: the pane is the labelled bottom surface; predecessors A120 (level 1) and A110 (level 2); successors A140, A150, A145 (level 1), A155, A160, A170 (level 2); the stored SS edge reads `SS+5d`; defaults are 2/2 selected in two controls. | pass |
| 02 | Setting predecessor depth 1 and successor depth 3 gives A120 only as predecessor and adds A170/A180 to the successor chain; the values are stored in the two local keys and survive a full reload (selection restored, level 3 still present). | pass |
| 03 | Following the A120 chain row selects A120 in the table and details, redraws predecessors as A110 and successors around A130. | pass |
| 04 | With the Activity Network on top, clicking node A160 moves the trace selection to A160: predecessors A140, A150, A130; successors A180, A190. | pass |
| 05 | Clicking the A145 Gantt bar moves the trace selection to A145: predecessor A130; successors A155, A180, A190 at depth 3. | pass |
| 06 | A critical activity selected from its critical Gantt bar produces critical chain rows with the localized `Critical activity` title and the computed `rgb(192, 57, 43)` start border. | pass |
| 07 | A100 has no predecessor: the predecessor group shows the explicit `None within depth.` state while its successor chain A110, A120, A130 is still listed. | pass |
| 08 | fa RTL at 1280: heading `ردیابی منطق`, localized `پیش‌نیازها` / `پس‌نیازها` groups and depth labels, selecting A130 renders its chain, following A120 selects it in the table, horizontal overflow 0 px. | pass |
| 09 | en at 1920 with depths reset to 2/2: A160 predecessors A140, A150, A130; successors A180, A190; LTR, 0 px overflow. | pass |

## What this slice changed

- `apps/web/src/workspace-trace-logic.ts`:
  - `TraceLogicDepths` (predecessors/successors), `normalizeTraceDepth`, `normalizeTraceLogicDepths`.
  - `buildTraceLogic` walks each direction to its own limit; unchanged cycle, diamond and missing-reference handling.
  - `readTraceLogicDepths` / `storeTraceLogicDepths` persist the pair under two per-project keys, migrating the previous single-depth key to both sides.
  - `renderTraceLogic` emits two `data-trace-depth` selects, `data-trace-predecessor-depth` / `data-trace-successor-depth` and a localized critical-row title.
- `apps/web/src/workspace-view.ts` handles `data-trace-depth` per direction, stores the pair and re-renders only the bottom surface.
- Both stylesheets wrap the header and group the two depth fields.
- `apps/web/e2e/layout-trace-v26.mjs` updated to the two depth controls and per-direction change handling.

## Boundaries

- Trace Logic is a pure projection of `state.activities` and `state.relationships`, which come from the persisted workspace read. It does not call the scheduler, re-date an activity or add an edge that is not stored.
- Selection uses the existing `onActivitySelect` / `onGanttActivitySelect` callbacks; there is no second selection store.
- The browser suite observed no non-GET request to `/p6/schedule/`, `/activities/` or `/p6/relationships`; the only writes are the two `localStorage` depth keys.
- The read path requires `PROJECT_READ` like the rest of the workspace; no new API route, table or permission was added.

## Known limits

- The Activity Usage Spreadsheet/Profile is still disabled, so the "click in the usage spreadsheet" source named by Help cannot be exercised yet (ACT-015).
- There is no dedicated View → Bottom Layout Options dialog; the two level selects are in the Trace Logic header. The values are a browser-local preference, not saved layout metadata.
- The trace layout is a two-list chain, not the graphical activity-box diagram of the desktop client; box fonts, curves and saved Trace Logic layouts are not offered.
- A cycle stops at the repeated activity and is reported; the fixture has no cyclic relationship, so only the unit test covers that path.
