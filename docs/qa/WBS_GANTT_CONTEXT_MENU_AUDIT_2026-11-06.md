# WBS bands, synchronized collapse, Gantt and activity context menu — audit

**Date:** 2026-11-06
**Branch:** `codex/jalal/cubi-shell-v26-20261104`
**Code head audited:** `3857d7a1` (ledger commit follows on the same branch)
**Environment:** managed preview runtime, SQLite, project `preview-rps-01`, Chrome at 1280×720 (DPR 1), plus 1440×900 and 1920×1080 for layout checks
**Surface:** authenticated live workspace (`workspace-view.ts`, `workspace-wbs-display.ts`, `workspace-gantt.ts`) — not the visual-demo route

The reference activity window, Gantt and right-click menu were compared against the supplied screenshot. Only behavior and structure were reimplemented; no product branding, proprietary icons or downloaded assets were used. The brand-guard test rejects `P6`, `Primavera`, `Oracle` and external URLs in the rendered workspace markup.

## Audit matrix

| Requested capability | Status | Evidence | Remaining gap |
| --- | --- | --- | --- |
| Per-level WBS colors | Implemented | Level 1 `#3B3BBF` with white text; level 2 `#FFFF00`; the fill covers all 12 cells of each band row, including the final Predecessors (`cp-logic-column`) and Edit (`cp-actions-column`) cells, as well as pinned/frozen columns; Gantt group row and summary bar share the level color | The preview dataset has only two real levels. Levels 3–6 (`#C6FFC6`, `#CCF2FF`, `#FFD9EC`, `#EEE0FF`) and deeper indentation are unit-tested but not visually demonstrated |
| Expand/collapse with `+/−`, synchronized with the Gantt | Implemented | One display-row model feeds both views; collapsing `WBS-RPS-PM` removed `A100`, `A110`, `A210` from the table and the Gantt (14 → 11 activities), kept 7 bands and 7 summary bars, and left unrelated activities visible | No branch deeper than level 2 exists in the preview data |
| Gantt shape and bar refinement | Implemented in scope | Task, summary, milestone and critical bars from persisted schedule values; FS/SS paths retain their stored semantics; day/week/month/quarter/year ticks; group rows aligned with the table | Baseline/actual/remaining bar editing was not part of this increment and is not claimed by this audit |
| Activity right-click menu with the reference command set | Implemented with honest disabled states | 20 commands in reference order; 11 enabled through the shared command registry; 9 disabled with a specific reason; menu clamped inside the workspace; Escape closes and restores focus; RTL/Persian variant mirrored and fully visible | Cut, Copy, Paste, Fill Down, Delete, Dissolve, Renumber, XLSX export and Assign need real service routes before they may be enabled |

## Live measurements

- Workspace surface: 1280×609 at top 97.
- Expanded table: 7 WBS bands, 14 activities, 14 Gantt activity rows, 7 summary bars.
- WBS toggles: 14×14 px; depth-2 activity indentation 24 px.
- Band colors read from computed styles: `rgb(59, 59, 191)` (level 1) and `rgb(255, 255, 0)` (level 2); every band row reports 12 of 12 cells with the row background, including `cp-logic-column` (Predecessors) and `cp-actions-column` (Edit); the first cell carries a matching 3 px inset marker.
- After scrolling the table to its end, both final cells remain inside the table viewport and compute to the band color (`lastColumns.last[*].visibleInsideTable: true`).
- Collapse state: `WBS-RPS-PM` became `+`; table children and Gantt children removed together; `unrelatedActivitiesStillVisible: true`; state stored under `cubi:workspace-wbs-collapse` per project.
- Context menu: 244×474 at (267, 228); workspace bounds 97–706; `fullyVisible: true`; last item bottom 699.
- Escape closed the LTR menu (`closedByEscape: true`).
- RTL menu: 244×474 at left 677, fully visible, Persian labels, mirrored layout.

## Context menu commands

| Command | Shortcut | State | Reason / route |
| --- | --- | --- | --- |
| Activity Details |  | Enabled | Opens the activity Details pane |
| Cut | Ctrl+X | Disabled | Cut needs the activity delete route, which this runtime does not expose. |
| Copy | Ctrl+C | Disabled | Activity duplication is not implemented by the project service. |
| Paste | Ctrl+V | Disabled | There is no activity clipboard or bulk-create route. |
| Fill Down | Ctrl+E | Disabled | Bulk cell updates are not exposed by the activity API. |
| Add | Ins | Enabled | Uses the real activity-create route |
| Delete | Del | Disabled | The activity delete route is not exposed by this runtime. |
| Dissolve |  | Disabled | Dissolving a group has no server-side contract. |
| Renumber Activity IDs |  | Disabled | Activity ID renumbering is not implemented. |
| Export to Excel |  | Disabled | Only XML interchange is available; no XLSX export route exists. |
| Assign | › | Disabled | Resource assignment write is not available; capacity is read-only. |
| Link Activities |  | Enabled | Uses the real relationship route |
| Columns… |  | Enabled | Opens the column chooser |
| Line Numbers |  | Enabled | Toggles the line-number column |
| Table Font and Row… |  | Enabled | Opens the persisted font/row dialog |
| Filters… |  | Enabled | Opens the filter manager |
| Group and Sort… |  | Enabled | Opens the group/sort dialog |
| Expand All | Ctrl+Num + | Enabled | Expands every WBS branch |
| Collapse All | Ctrl+Num - | Enabled | Collapses every WBS branch |
| Collapse To… |  | Enabled | Opens the level picker |

## Verification

- `npx tsc --noEmit` — passed.
- Web unit tests — 615 passed, 0 failed (includes the new CSS contract test for the full-row band fill).
- Preview resolver tests — 14 passed, 0 failed.
- `npm run build` — passed.
- Managed browser E2E — 98 checks, 53 screenshots. The evidence file records `git_head` `2ccfd942`, the base commit; the tested working-tree content is committed as `3857d7a1`.
- Regression coverage added for Gantt links anchored to display rows and for the WBS display-row view model.

## Evidence files

- `docs/workspace/evidence/wbs-context-menu-2026-11-06.json` — full computed-style and geometry capture.
- `docs/workspace/screenshots/visual/44-wbs-bands-en-1280.png`
- `docs/workspace/screenshots/visual/45-wbs-collapsed-en-1280.png`
- `docs/workspace/screenshots/visual/46-context-menu-en-1280.png`
- `docs/workspace/screenshots/visual/47-context-menu-fa-1280.png`
- `docs/workspace/screenshots/visual/48-wbs-bands-last-columns-en-1280.png` — table scrolled to the end, proving the Predecessors and Edit cells keep the band fill
- Capture tool: `apps/web/e2e/capture-wbs-menu.mjs`.

## Not claimed

- No visual proof of WBS levels 3–6; only unit tests exist for the deeper palette and indentation.
- Disabled commands remain disabled until the corresponding server routes are implemented; the UI does not simulate success.
- Exact-head CI for `3857d7a1` had not completed at the time of this audit.
- No merge to `main`, no Production deployment and no repository-setting change.
- PR #1716 and the visual-demo PR #1728 are separate surfaces; this increment is in the authenticated live workspace and does not adopt the demo surface.
