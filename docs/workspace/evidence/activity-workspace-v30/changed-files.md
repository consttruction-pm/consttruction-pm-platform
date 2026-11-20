# V30 — Changed files

Implementation commit: `48f2f0c1b7d2e83427b549af0803563fea100ccc`
(`feat/2047-activity-workspace-v26`, 29 files, +3950 / -54).

## Backend

| File | Change |
|---|---|
| `src/construction_pm/p6_gantt_attachment.py` | New: attachment model/serializer, SQLite repository, revision guard, `P6GanttAttachmentAPI` |
| `src/construction_pm/activity_master_repository.py` | `delete()` on the protocol and both SQLite/Postgres repositories |
| `src/construction_pm/p6_activity_master_api.py` | `delete`, `dissolve`, dependency checks, scope/permission guards |
| `src/construction_pm/http/project_lifecycle_routes.py` | Attachment routes, activity DELETE and dissolve POST, error mapping |
| `src/construction_pm/http/production_composition.py` | Wires relationship/assignment/children/step/document dependencies and attachment repos |
| `src/construction_pm/preview/runtime.py` | Wires the preview repositories into the lifecycle app |

## Frontend

| File | Change |
|---|---|
| `apps/web/src/workspace-gantt-attachments.ts` | New client contract for curtain/text/notebook |
| `apps/web/src/workspace-activity-edit.ts` | Delete/Dissolve client calls with record revisions |
| `apps/web/src/workspace-activity-clipboard.ts` | Clipboard shape, pasted ID allocation, clone payload |
| `apps/web/src/workspace-activity-bulk.ts` | Replace, Fill Down and Spell Check planning/dialog |
| `apps/web/src/workspace-view.ts` | Curtain/bar attachment layers, counts, Attachments dialog and handlers |
| `apps/web/src/main.ts` | Attachment/project state, paste flow, name edits, command dispatch |
| `apps/web/src/workspace-desktop-shell.ts` | Commands, menu/toolbar/shortcut enablement, Alt bindings |
| `apps/web/src/workspace-toolbar-registry.ts` | Real targets and preconditions for edit/standard commands |
| `apps/web/src/workspace-command-icons.ts` | Icons for Replace/Spell Check |
| `apps/web/styles.css`, `apps/web/public/styles.css` | Attachment, curtain, dialog and RTL-safe styles |

## Tests and tools

- `apps/web/src/workspace-gantt-attachments.test.ts`
- `apps/web/src/workspace-activity-clipboard.test.ts`
- `apps/web/src/workspace-activity-bulk.test.ts`
- `apps/web/src/workspace-view.test.ts`, `workspace-desktop-shell.test.ts`, `workspace-toolbar-rails.test.ts` (updated counts/preconditions)
- `tests/test_p6_gantt_attachment.py`
- `tests/test_gantt_attachment_http_routes.py`
- `tests/test_p6_activity_edit_commands.py`
- `apps/web/e2e/gantt-attachments-v30.mjs`
- `apps/web/e2e/activity-edit-v30.mjs`
- `apps/web/e2e/visual-matrix-v30.mjs`
- `scripts/v30_topic_disposition.py` (evidence generation)

## Evidence

- `docs/workspace/evidence/activity-workspace-v30/*.md` and JSON
- `docs/workspace/evidence/activity-workspace-v30/screenshots/` (14 functional screenshots)
- `docs/workspace/evidence/activity-workspace-v30/visual/` (84 matrix screenshots + JSON)
