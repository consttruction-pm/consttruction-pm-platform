# ACT-012 — Relationship arrows and editing in the Gantt chart (2026-11-13)

Contract: `cubi-activity-relationships-v26.v1`
Tested code: `04fba0298652cd6e29d9e436b665dd615f691314`
Suite: `apps/web/e2e/activity-relationships-v26.mjs`
Report: `activity-relationships-v26.json` (11/11 scenarios, 0 exceptions, 0 console errors, 0 failing API responses, 0 schedule/activity writes)
Screenshots: `01`–`08`

## Help topics

- [Create relationships in the Gantt Chart](https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_relationships_in_the_gantt_chart.htm) — move the pointer to an edge of the predecessor bar until it becomes a vertical single-ended arrow, drag to the successor and release. Right→left is finish to start, right→right is finish to finish, left→right is start to finish, left→left is start to start. A hint window names the relationship that will be created while dragging.
- [Edit relationships in the Gantt Chart](https://docs.oracle.com/cd/G48902_01/client_help/en_US/edit_relationships_in_the_gantt_chart.htm) — double-click the line, choose a different type, enter lag days and confirm.
- [Show or hide relationship lines in the Gantt Chart](https://docs.oracle.com/cd/G48902_01/client_help/en_US/show_or_hide_relationship_lines_in_the_gantt_chart.htm) — View, Barchart Options, Options, General tab, Show Relationships; the same toggle is on the Top Layout toolbar.

## Environment

- `PYTHONPATH=src python3 -m construction_pm.preview --web-root apps/web --host 127.0.0.1 --port 4204 --database /tmp/rel-postmerge.db --reset`
- Fixture: Riverside Pump Station Upgrade (`preview-rps-01`), 14 activities `A100`–`A210` and 15 persisted relationships (14 FS plus one SS `REL-RPS-170` A140→A170, lag +5 working days).
- Viewports: en/LTR 1366×768 and 1920×1080, fa/RTL 1280×720.

## Scenarios

| # | Proof | Result |
|---|---|---|
| 01 | Without browser-local setup the chart draws all 15 stored arrows, the type mix is FS+SS, 28 edge handles are exposed (2 per 14 primary bars), the SS relationship keeps its `+5d` lag badge, and the arrow layer is visible. | pass |
| 02 | A pointer press on a bar edge enters the drag with a dashed `cp-gantt-link-preview` path and a live hint `FS — Finish to Start`; dragging A100 finish→A120 start resolves target row A120, and Escape during a separate drag aborts it with no POST. Releasing persists `POST /api/projects/preview-rps-01/p6/relationships` with `{relationship_type:"FS", lag_value:"0", lag_unit:"working-day"}`. | pass |
| 03 | Drawing A110 finish→A140 finish shows `FF — Finish to Finish`, resolves target A140 and POSTs `FF`. | pass |
| 04 | Drawing A120 start→A145 start shows `SS — Start to Start` and POSTs `SS`. | pass |
| 05 | Drawing A140 start→A150 finish shows `SF — Start to Finish` and POSTs `SF`. | pass |
| 06 | A full page reload keeps all four new arrows with their stored type and endpoints (A100→A120 FS, A110→A140 FF, A120→A145 SS, A140→A150 SF) and 19 links in total. | pass |
| 07 | The arrow context menu edits A100→A120 to SS with lag 2: the `PATCH` body carries `expected_revision: 1` (the revision the form read), the badge becomes `+2d`, and the edit survives reload. | pass |
| 08 | The arrow context menu's Delete asks for confirmation; cancelling leaves 19 links and sends no DELETE, confirming removes exactly one (18 left) and the removal survives reload. | pass |
| 09 | Hiding relationship lines removes the SVG and every edge handle, drawing on a bar starts no drag and writes nothing, and switching the lines back on restores all 18 persisted arrows. | pass |
| 10 | fa RTL at 1280×720: regardless of the RTL mirroring, the physical bar edges keep their documented meaning — A150 finish→A190 start shows `FS — پایان به شروع`, `dir=rtl`, 0 px horizontal overflow. | pass |
| 11 | en at 1920×1080: A190 finish→A210 start yields `SS — Start to Start`, 20 links, 0 px horizontal overflow. | pass |

## What this slice changed

- `apps/web/src/workspace-gantt.ts` adds `relationshipTypeFromEdges(from, to)`: finish→start FS, finish→finish FF, start→finish SF, start→start SS — the Help table as one pure function, unit-tested.
- `apps/web/src/workspace-view.ts` renders two `data-gantt-link-edge` handles on each primary bar when relationship lines are shown, and adds a drag system: it resolves the pressed row by pointer Y and the bar edge by the bar's box (the default task bar is a clipped triangle, so element hit-testing cannot be used), draws a dashed elbow preview plus a localized hint, resolves the successor geometrically, and on release calls the existing `onRelationshipCreate` callback. Escape (document-level capture listener) or an invalid drop cancels and writes nothing.
- `apps/web/styles.css` and `apps/web/public/styles.css` add the handles, preview layer, hint and target highlight.
- No storage or API change: POST/PATCH/DELETE keep using `P6RelationshipAPI`, `PROJECT_WRITE`, duplicate/cycle checks and `expected_revision`.

## Boundaries

- Drawing only proposes a relationship; the existing relationship API performs the write. There is no optimistic-lock bypass: the edit form reads the current revision (scenario 07 asserts `expected_revision: 1`).
- Presentation never enters schedule input: the drag draws an overlay and calls the same create callback as the dialog; scenarios assert zero non-GET requests to `/p6/schedule/` or `/activities/`.
- Relationship type is derived only from the two physical edges the user connects; no type is inferred from dates.

## Known limits

- Lag is entered afterwards through the arrow context menu (default 0 working days at draw time), matching the Help flow of drawing first and editing later.
- Dragging creates a predecessor→successor proposal at the release bar; the existing server-side duplicate and cycle rejection still applies and its message is surfaced by the shared write path.
- The hint is a lightweight positioned label, not the Oracle hint window chrome.
