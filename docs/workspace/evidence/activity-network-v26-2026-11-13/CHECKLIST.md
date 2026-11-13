# ACT-013 — Activity Network view, node/edge details and selection (2026-11-13)

Contract: `cubi-activity-network-v26.v1`
Tested code: `a9776bb9ed8d16a2f5752b5b0909f74f002a5c2a`
Suite: `apps/web/e2e/activity-network-v26.mjs`
Report: `activity-network-v26.json` (9/9 scenarios, 0 exceptions, 0 console errors, 0 failing API responses, 0 schedule writes, 0 relationship writes)
Screenshots: `01`–`07`

## Help topics

- [Activity Network](https://docs.oracle.com/cd/G48902_01/client_help/en_US/activity_network.htm) — a diagram of activities and relationships according to the WBS; a red border marks critical activities and a line is a relationship; hover shows an activity's ID and name; double-click a relationship line to edit or remove it; place the pointer on an activity to view its details.
- [Move around in the Activity Network](https://docs.oracle.com/cd/G48902_01/client_help/en_US/move_around_in_the_activity_network.htm) — click an activity to select it; Zoom In, Zoom Out and Zoom to Best Fit are the Display toolbar controls.
- [View Activity Network Activity Details](https://docs.oracle.com/cd/G48902_01/client_help/en_US/view_activity_network_activity_details.htm) — placing the pointer on an activity shows its ID and name.

## Environment

- `PYTHONPATH=src python3 -m construction_pm.preview --web-root apps/web --host 127.0.0.1 --port 4206 --database /tmp/network-postmerge.db --reset`
- Fixture: Riverside Pump Station Upgrade (`preview-rps-01`), 14 activities and 15 persisted relationships (14 FS plus the SS `REL-RPS-170` A140→A170 with +5 working days).
- Viewports: en/LTR 1366×768 and 1920×1080, fa/RTL 1280×720.

## Scenarios

| # | Proof | Result |
|---|---|---|
| 01 | Show on Top → Activity Network renders 14 nodes and 15 edges over 10 longest-path levels. Critical nodes carry `is-critical`, both stored types FS and SS appear, the SS edge shows `SS+5d`, its tooltip reads `SS A140 → A170 (5 working-day)`, and every node tooltip carries its ID. No schedule or activity request is issued. | pass |
| 02 | Clicking node A120 selects the A120 table row, marks the node selected/`aria-pressed` and updates the details pane; clicking the A145 table row moves the selection back to node A145. | pass |
| 03 | Focusing node A150 and pressing Enter selects A150 in both the network and the table. | pass |
| 04 | Double-clicking edge `REL-RPS-100` (A100→A110 FS) opens the existing relationship editor in the Tools drawer with the stored revision 1, takes focus and writes nothing. | pass |
| 05 | Right-clicking an edge opens the Relationship menu labelled `Relationship` with Edit, Delete, Go to Predecessor and Go to Successor; choosing Go to Successor moves the selection and details to the successor (A110). | pass |
| 06 | Right-clicking node A100 opens the activity menu labelled `Network Activity` with Details, Add, Link, Bars, Font, Filters, Group and Sort, Show Relationships and the WBS collapse commands. | pass |
| 07 | Zoom In twice moves 100 %→120 %, the SVG grows to 1.2× the base width, a full reload restores 120 %, Zoom Out reaches 110 %, and Zoom to Best Fit frames the whole 10-level diagram at 20 %. No schedule write occurs. | pass |
| 08 | fa RTL at 1280×720: the heading is `شبکهٔ فعالیتها`, the document is RTL while the diagram stays LTR, 14 nodes/15 edges draw, node A160 selects in both panes, and horizontal overflow is 0 px. | pass |
| 09 | en at 1920×1080 keeps 14 nodes/15 edges, the English heading, LTR, 0 px overflow, and node A210 selection stays synchronised with the table. | pass |

## What this slice changed

- `apps/web/src/workspace-network.ts` adds a wide transparent hit path and `data-network-relationship-id` / `data-link-*` identity to each edge, a `<title>` carrying type, endpoints and lag, keyboard focusability for edges, and Zoom In/Out/Best Fit controls backed by the clamped `clampNetworkZoom`, `readNetworkZoom` and `storeNetworkZoom` helpers. Zoom is presentation-only and stored per tenant/project/window.
- `apps/web/src/workspace-view.ts` classifies `network-activity` and `network-link` context targets and routes them to the existing activity and relationship menus, opens the relationship editor on edge double-click or Enter, and applies zoom to the rendered SVG without re-rendering the schedule.
- Both stylesheets add the edge hit band, edge hover/focus emphasis, zoom controls and header layout.
- No API, storage or layout change.

## Boundaries

- The network remains a pure projection: `buildActivityNetwork` reads only the loaded activities and relationships, assigns levels by longest path, and never recalculates dates, invents endpoints or drops a persisted edge silently.
- Selection uses the same `onGanttActivitySelect` / `onActivitySelect` callbacks as the table and Gantt; there is no second selection store.
- Edge editing reuses `P6RelationshipAPI` and the form's `expected_revision`; this suite only opens it, so zero relationship writes are observed.
- Zoom writes a local preference only. No non-GET `/p6/schedule/` or `/activities/` request is made in any scenario.

## Known limits

- The layout is deterministic longest path, not user-positioned. P6's Reorganize / Reorganize All, dragging boxes, and saved Activity Network layouts are not offered yet.
- The left pane is the shared Activity Table with its WBS bands, not a WBS-only hierarchy; selecting a WBS band does not filter the diagram.
- The node box shows ID, name and progress only; box templates and box-level field selection are not implemented.
- Zoom is a browser-local view preference, not part of the saved layout metadata.
