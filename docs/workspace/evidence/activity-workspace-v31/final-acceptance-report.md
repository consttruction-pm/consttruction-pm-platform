# V31 — Activities workspace increment report

- Repository: `consttruction-pm/consttruction-pm-platform`
- Branch: `feat/2047-activity-workspace-v26`
- PR: #2048 (open, not merged)
- Tested code SHA: `894d435678796b00113d0a79855c2d4fd3314183`
- Reference: Primavera P6 Professional Help **G57535-02, October 2026**, physical PDF (815 pages). The PDF footer reads “October 9, 2026”. The Oracle HTML help for the 26 release returned HTTP 403 in the V30 audit, so the physical PDF remains the readable authority for this increment.
- Preview: local `construction_pm.preview` runtime on `127.0.0.1:4300` with a reset demo SQLite database. No Vercel deploy, no production write, no merge.

## What this increment implements

1. **Copy Activity Options** (Help: “Copy Activity Options dialog box”, “Copy and paste activities in the Activity Table”)
   - A real Paste dialog with Resource & Role Assignments, Relationships, “Only between copied activities”, Expenses, Activity Codes, WPs & Docs, Notebook, Steps, Financial Period Data and “Do not show this dialog again”.
   - Paste replays each selected child through its owning service; relationships are created through the relationship API after all pasted rows exist.
   - Selecting “Only between copied activities” drops links to activities outside the copied set; clearing it keeps the pasted activity’s links to unchanged activities.
2. **Renumber Activity IDs** (Help: “Renumber Activity IDs dialog box”, “Renumber activity IDs in the Activity Table”)
   - Edit menu and activity context menu open a real dialog with Increment, Auto-Number and Replace Beginning Characters methods, a live preview, duplicate resolution, the “Renumber selected activities in baselines” checkbox, and an explicit count of affected activities.
   - The server performs a two-phase, single-transaction rename (staged temporary identity), so mappings may reuse another selected activity’s old ID (including swaps) without breaking foreign keys.
   - Activity rows, WBS links, relationships, codes, notebook, steps, expenses, period actuals, resource/role assignments, issues and document JSON references follow the new ID. Baselines follow only while their checkbox is marked; clearing it leaves them disconnected, as the reference describes.
3. **Fill Down across editable columns** (Help: “Quickly enter the same text in multiple table rows”)
   - The command now targets the last clicked table column, not only Activity Name.
   - Supported visible P6 columns: Original Duration (`activity.planned_duration`), Remaining Duration, Schedule % Complete, Activity Type, Status, Status Code, Leveling Priority, plus the generic aliases.
   - The source value is re-read from the Activity Master GET contract, validated for the column type, previewed, then PATCHed to every target with its record revision. Invalid or empty source values are refused before any write.
   - Activity Name keeps the existing V30 behavior (no dialog) so the documented Ctrl+E flow is unchanged.
4. **Bulk curtain visibility** (Help: “Hide all curtain attachments in the Gantt Chart”, “Display all curtain attachments in the Gantt Chart”)
   - The Attachments dialog now has **Hide all curtains** and **Show all curtains**, enabled only when that action applies.
   - Every curtain is persisted with its own record revision; reload preserves the state.

## Acceptance for this increment

| Area | Evidence | Result |
|---|---|---|
| Copy options and child replay | `activity-v31-renumber-copy.mjs` step `copy-options`; `apps/web/src/workspace-activity-copy.test.ts` | pass |
| Renumber IDs and reference integrity | `activity-v31-renumber-copy.mjs` step `renumber`; `test_activity_master_repository.py`, `test_p6_activity_master_http_routes.py` | pass |
| Fill Down column scope | `activity-v31-renumber-copy.mjs` steps `fill-down`; `workspace-activity-fill.test.ts` | pass |
| Hide/Show all curtains | `activity-v31-renumber-copy.mjs` steps `curtain`; rerun of `gantt-attachments-v30.mjs` | pass |
| Regression of V30 edit commands | `activity-edit-v30.mjs` | pass (10 steps) |
| Regression of V30 attachments | `gantt-attachments-v30.mjs` (fresh database) | pass (11 steps) |

Full parity is **not** claimed. The matrix moved from 116/34/73 to **119 confirmed, 32 partial, 72 verify** (26 delegated and 15 out-of-scope unchanged). The remaining review and partial rows are listed in `remaining-items.md`; they were not relabelled without execution.

## Deliberate boundaries

- Cut still uses copy-then-delete. The server refuses deletion while unhandled assignment or period-actual rows remain, so Cut on such an activity fails with a named error instead of silently dropping data. Moving those records belongs to the shared assignment/period services and is not claimed here.
- Costs, resource levelling, CPM and EVM remain untouched.
- The preview uses fixture data; the renumber implementation for PostgreSQL follows the same staging logic but this increment’s executable proof is SQLite (unit, HTTP and browser).
