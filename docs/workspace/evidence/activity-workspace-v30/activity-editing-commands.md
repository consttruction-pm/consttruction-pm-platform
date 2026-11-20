# V30 — Activity editing commands

All eight commands requested by the mission are connected to real behaviour. None is a
browser-only simulation: every project change goes through an HTTP contract with authorization,
scope, persistence and a revision guard.

## Cut / Copy / Paste

- Reference: PDF pp. 14–15.
- Client: `workspace-activity-clipboard.ts` (clipboard shape, collision-free IDs, clone payload).
- Flow:
  1. Cut/Copy store the selected authoritative activity IDs and the project ID in memory.
  2. Paste re-reads each source from the Activity Master GET (so a stale snapshot is impossible).
  3. A new row is created through `POST /p6/activities` with a new ID (`source-C1`, `-C2`, …),
     the selected WBS (or the source's band), the source's duration/type/cost account/priority,
     and **Not Started/Planned** status/progress.
  4. Codes, notebook topics and steps are copied through their existing V29 contracts. Failures
     are reported as warnings, never hidden.
  5. Cut deletes each source **after** the copies exist, using the current record revision.
- Copy options are not a dialog in V30: supported children are copied, relationships are not.
  This is a documented limit in `remaining-items.md`; the reference's Copy Activity Options
  dialog and Renumber IDs dialog are not claimed as parity.

## Delete

- Reference: PDF p. 12.
- `DELETE /p6/activities/{id}` with `expected_revision`.
- Refuses a linked activity (`ACTIVITY_HAS_RELATIONSHIPS`) and any child record
  (`ACTIVITY_HAS_CHILD_RECORDS:CODES,NOTEBOOK,STEPS,RESOURCE_ASSIGNMENTS,DOCUMENTS`).
- Confirmation is required; success refreshes the grid and clears the selection.
- Stale revision → 409 `REVISION_CONFLICT`; the row remains.

## Dissolve

- Reference: PDF pp. 12–13.
- `POST /p6/activities/{id}/dissolve` with `expected_revision`.
- Requires ≥1 predecessor and ≥1 successor; otherwise
  `DISSOLVE_REQUIRES_PREDECESSOR_AND_SUCCESSOR`.
- For each predecessor × successor pair, the new type is
  `predecessor.type[0] + successor.type[1]` (e.g. SF + FF → SF), lag 0.
- Existing duplicate pairs are not created; old links are deleted with their record revisions;
  the activity is then deleted. Child records block the operation.
- Unit tests cover the single pair, many-to-many, the missing-link precondition and permissions.

## Fill Down

- Reference: PDF p. 9.
- Requires ≥2 selected activities; copies the first selected **Activity Name** to the rest.
- Each write is an Activity Master PATCH with its own revision; a confirm states the name and
  target count. Other columns keep their dedicated editors (documented limit).

## Replace

- Reference: toolbar/menu reference, printed pp. 58–59 of 93; Ctrl+R.
- `planActivityReplacements` implements case-sensitive/insensitive find, all occurrences,
  selection scope and a preview count.
- Applies name-only PATCHes with per-record revisions. Empty find never matches.

## Spell Check

- Reference: F7.
- Lists every displayed activity name in an input with `spellcheck="true"`; the browser marks
  misspellings. Saving sends only changed names with record revisions.
- No private dictionary and no fake underline; detection quality is the browser's, stated in the
  dialog.

## Evidence

- `activity-edit-v30.json` (real Chrome, dedicated port 4200, fresh DB): delete leaf, refuse linked
  activity, stale 409, dissolve SF+FF→SF with old links gone, copy/paste planned clone,
  cut/paste source removed, Replace preview+persist, Fill Down two rows, Spell Check correction.
- Python: `tests/test_p6_activity_edit_commands.py` (7 tests) and the repository tests.
- Web unit: `workspace-activity-clipboard.test.ts`, `workspace-activity-bulk.test.ts`,
  desktop-shell and toolbar-rail suites.
