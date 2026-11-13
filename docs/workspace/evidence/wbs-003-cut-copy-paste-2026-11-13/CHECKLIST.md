# WBS-003 — Copy, Cut/Paste and Delete Guidance (2026-11-13)

Contract: `cubi-wbs-003-cut-copy-paste.v1`
Tested code: `888512ca` (branch `feat/wbs-003-cut-copy-paste`)
Result: 24/24 checks passed, 7 scenarios, 7 screenshots.

## Official V26 HTML Help

- [Copy and paste a work breakdown structure element](https://docs.oracle.com/cd/G48902_01/client_help/en_US/copy_and_paste_a_work_breakdown_structure_element.htm) — Project > WBS; Edit > Copy; select the target; Edit > Paste; the Copy WBS Options dialog chooses what to include.
- [Cut and paste a work breakdown structure element](https://docs.oracle.com/cd/G48902_01/client_help/en_US/cut_and_paste_a_work_breakdown_structure_element.htm) — Edit > Cut, then Edit > Paste at the target; “the element's activity assignments are also pasted”.
- [Delete a work breakdown structure element](https://docs.oracle.com/cd/G48902_01/client_help/en_US/delete_a_work_breakdown_structure_element.htm) — deleting an element assigned to activities prompts to delete those activities or reassign them to the parent; deleting a parent deletes everything it contains.

## CUBI component

WBS window (navigation key `wbs`), toolbar commands Cut, Copy, Paste and Delete, plus the page-local clipboard indicator.

## Code path

- `PostgresWBSMasterRepository.copy_subtree` and `SQLiteWBSMasterRepository.copy_subtree` (`src/construction_pm/wbs_master_repository.py`) duplicate a depth-first subtree under a target parent. The root takes the requested sibling-unique code; descendants keep their local code, name, sequence, status and percent-complete technique. Every copied record starts at revision 1 and its weighted milestones are copied with it. Activity assignments are never copied.
- `P6WBSMasterAPI.copy` (`src/construction_pm/p6_wbs_master_api.py`) requires `PROJECT_WRITE`, a current `expected_revision` on the source and a same-scope target, and returns `kind: p6_wbs_copy` with the new root ID and every copied node DTO.
- `POST /api/projects/{id}/p6/wbs/{wbs_id}/copy` (`src/construction_pm/http/project_lifecycle_routes.py`) accepts `target_parent_wbs_id`, `code` and `expected_revision`. A stale source returns 409 `REVISION_CONFLICT`, a duplicate sibling code or a foreign/missing target returns 400 with its stable persistence code (the pre-existing WBS write contract).
- Cut/Paste reuses `PATCH /p6/wbs/{wbs_id}` with a new `parent_kind`/`parent_wbs_id`; the record ID is unchanged, so its activity assignments stay attached. An attempt to paste a node under its own descendant is rejected by the repository with `WBS_HIERARCHY_CYCLE` and leaves the record untouched.
- The browser clipboard (`apps/web/src/workspace-wbs-clipboard.ts`) is page-local, one entry per WBS container. `nextWbsCopyCode` derives a sibling-unique copy code; the server remains the authority.
- Delete (`DELETE /p6/wbs/{wbs_id}`) still refuses a node with children or activity assignments with 409 `WBS_IN_USE`; the window now shows the V26 precondition as localized guidance instead of the raw code (`main.ts` `onWbsDelete`).

## Permissions

Reads use the existing `PROJECT_READ` path. Copy, cut/move (PATCH) and delete require `PROJECT_WRITE`; a viewer receives 403 `AUTHORIZATION_PERMISSION_DENIED` and the hierarchy is unchanged.

## Tests

- `tests/test_wbs_master_repository.py`: subtree copy records/codes/parents/revisions, milestone copy (75%), stale source revision, sibling-code collision with no write, unknown source/target, argument validation.
- `tests/test_p6_activity_master_http_routes.py`: copy round trip (`201`, DTO shape, 75% roll-up, source revision unchanged, six nodes), stale 409, sibling conflict 400, missing source 404, missing target 400, viewer 403 with no write.
- `tests/integration/test_wbs_master_postgres_live.py`: live PostgreSQL copy with milestone copy, source untouched, stale conflict and sibling conflict.
- `apps/web/src/workspace-wbs-clipboard.test.ts`: copy-code derivation, clipboard text and localized delete guidance.
- `apps/web/src/workspace-view.test.ts`: WBS toolbar renders Cut/Copy/Paste with the correct disabled state, Copy then Paste calls the copy handler with the derived code, Cut then Paste calls the update handler with the new parent.

## Browser scenarios

1. Copy `WBS-RPS-CIVIL` (with a new `2.1 Site survey` child and weighted milestones) beneath `WBS-RPS-PM`: POST `/copy`, new revision-1 root with code `2`, child `2.1`, copied milestones at 75%, source unchanged, no activity assignments on the copy.
2. Cut `WBS-RPS-PROC` and paste on `WBS-RPS-ENV`: the same record moves (PATCH, revision advance) and its single activity assignment stays attached; the clipboard clears.
3. Cut `WBS-RPS-PM` and paste on its own descendant: `WBS_HIERARCHY_CYCLE` is stated in the window and the parent is unchanged.
4. A copy onto an existing sibling code is rejected with `WBS_SIBLING_CODE_CONFLICT` and no record is added.
5. Delete of `WBS-RPS-CIVIL` (children and activities) shows the localized precondition guidance and keeps the record.
6. Persian RTL at 1280×720: Cut/کپی/Paste labels localized, no horizontal overflow.
7. A full reload keeps the copied subtree and the moved element and shows an empty clipboard.

One console error is recorded: the deliberate hierarchy-cycle rejection is logged by the shared WBS mutation reporter (`WBS mutation failed … WBS_HIERARCHY_CYCLE`). No 5xx responses or uncaught exceptions occurred.

## Evidence files

`contract.json` (24 checks), `01-wbs-copy-clipboard.png`, `02-wbs-copy-pasted.png`, `03-wbs-cut-pasted.png`, `04-wbs-cycle-rejected.png`, `05-wbs-delete-guidance.png`, `06-wbs-clipboard-fa-rtl.png`, `07-wbs-reloaded.png`.

## Remaining gaps

- The V26 Copy WBS Options / Copy Activity Options / Renumber Activity IDs dialogs are not implemented; CUBI never copies activities (the API documents this).
- The V26 delete prompt offers “delete the element and its activities” or “reassign activity assignments to the parent”. CUBI refuses the delete and explains the precondition instead of performing either destructive choice.
- Cut/copy/paste are exposed on the WBS window toolbar, not in the Edit menu or a WBS context menu.
