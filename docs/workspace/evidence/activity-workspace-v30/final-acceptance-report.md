# V30 — Final acceptance report

## Verdict

**Not fully accepted against the V30 closing criteria.** The mission requires all 264 topics
reviewed and all 73 `verify` rows resolved; V30 closes the mission’s highest-priority functional
gaps (Gantt attachments and all eight editing commands) but leaves 73 `verify`, 34 `partial`,
26 `delegated` and 15 `out-of-scope` rows. This report does not claim parity.

What is real and proven:

- Gantt **curtain, text and notebook attachments** are persisted per project, drawn in the real
  Gantt layers, revision-guarded, permission-checked, and exercised end to end.
- **Delete, Dissolve, Cut, Copy, Paste, Fill Down, Replace and Spell Check** are connected to
  authoritative contracts; none is a browser-only simulation.
- Six themes × three sizes × two languages and the new dialogs were captured and asserted
  (84 screenshots).
- All four GitHub Actions workflows passed at the tested SHA.

What remains is listed in `remaining-items.md` and counted in `pdf-topic-disposition.md`.

## Tested code

- Branch: `feat/2047-activity-workspace-v26`
- PR: #2048 (not merged, not deployed)
- Tested SHA: **`48f2f0c1b7d2e83427b549af0803563fea100ccc`**
- V29 baseline: `af1ec41e01a6b540e952ed0ada1577a9187d10a6`

## What was implemented in V30

### Gantt attachments (was absent in V29)

- New `p6-gantt-attachment-api.v1` with `curtain | text | notebook`, project scope, permissions,
  `record_revision`, 201/200/409/404 mapping and SQLite persistence.
- Curtains are projected from stored date ranges into the Gantt body layer and clipped to the view;
  text/notebook links sit on the activity bar; hidden records stay stored and are not drawn.
- Dialog with table, Hide/Show, Edit, Delete, validation and messages; label/range/colour/activity/
  topic fields; RTL-safe layout.
- E2E: create/draw/hide/reload/show/edit/delete, stale 409, viewer 403, notebook topic link.

### Edit commands (were disabled in V29)

- Delete: confirmation + revision-checked DELETE, refuses relationships/children/assignments/
  documents.
- Dissolve: requires predecessor and successor, joins each pair with combined type, removes old
  links and the activity.
- Cut/Copy/Paste: authoritative clipboard, collision-free IDs, planned clones, child records
  copied, Cut deletes only after the copy exists.
- Fill Down: first selected name to the rest.
- Replace: preview count, match case, scope; persisted PATCHes.
- Spell Check: browser-spellcheck review dialog with revision-checked saves.

### UI

- Edit menu, Edit toolbar and shortcut catalogue now expose the real commands and accurate
  enablement; Alt+E sequences dispatch them.
- Gantt toolbar Attachments button with live count.
- Styles for curtains, bar marks, dialog, Replace and Spell Check, both stylesheets and RTL.

## Evidence index

| File | Content |
|---|---|
| `reference-traceability.md` | PDF pages and implementation proof per changed topic |
| `html-topic-disposition.md` | Mandated HTML 403 attempts and consequence |
| `pdf-topic-disposition.md` | 264-topic matrix; 116 confirmed / 34 partial / 0 absent / 26 delegated / 15 out-of-scope / 73 verify |
| `menu-toolbar-audit.md` | Menus, toolbars, shortcuts and Alt sequences |
| `dialog-field-audit.md` | Attachment, Replace, Spell Check and confirmation dialogs |
| `gantt-attachments.md` | Contract, drawing, UI, evidence, limits |
| `activity-editing-commands.md` | Each of the eight commands and its proof |
| `visual-comparison.md` | 36 cells, 12 dialog cells, 84 screenshots |
| `test-matrix.md` | Unit/API/E2E/regression results and Windows-only failures |
| `remaining-items.md` | Every explicit boundary |
| `changed-files.md` | 29-file commit summary |
| `commit-and-ci-evidence.md` | SHAs, local runs, CI run URLs |
| `*.json`, `screenshots/`, `visual/` | Raw reports and images |

## Test results (summary)

- TypeScript: pass. Build: pass.
- Web unit: 1200 pass, 0 fail.
- Python: 4707 pass, 224 skipped, 4 failures — all pre-existing Windows environment issues
  (`resource` module absent; `/tmp` path assertion), not caused by this branch. Eight additional
  Unix-only modules cannot be collected on Windows.
- Browser (port 4200, fresh DB): attachments 11/11 pass (26 s), edit commands 10/10 pass (47 s),
  visual matrix 36+12 cells pass (74 s). Exit code 0 for each.
- CI: ConstructionPM CI, Web CI, PostgreSQL Integration and Client Typecheck all success at
  `48f2f0c1b…`.

## What is not done

- 73 `verify` topics were not individually exercised; statuses were not flipped.
- 34 `partial` topics, including bulk hide-all curtains, copy options/renumber dialog, relationship
  editing in Gantt, renumber activity IDs, resource Replace, predecessor/successor column dialogs.
- Fill Down covers Activity Name only.
- Spell Check detection uses the browser’s dictionary.
- Risks/Issues writes inside Activities were not added; shared services keep ownership.
- Ctrl+W still closes one window, not “Close All”.
- The visual matrix does not capture every legacy dialog in every theme.

These are dependencies on product decisions or further increments, not silent omissions.

## Prohibitions

No merge, no deploy, no Vercel, no production database, no force push, no history rewrite, no
removal of another author’s work.
