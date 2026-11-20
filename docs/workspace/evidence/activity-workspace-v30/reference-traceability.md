# V30 — Reference traceability

- Product: Primavera P6 Professional, Version 26
- Help ID: G57535-02, October 2026
- HTML reference (mandated): `https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-help/index.html`
  - Checked 2026-11-19 with the default client: **HTTP 403**.
  - Retried with a desktop Chrome user agent: **HTTP 403**.
  - No HTML content was used. See `html-topic-disposition.md`.
- PDF reference: `D:\کنترل پروژه\p6-professional-help.pdf`, 815 pages. Re-extracted with
  `pdftotext -layout` on 2026-11-19; page 1 reads
  `Primavera P6 Professional / Help / G57535-02 October 2026`.
- Base disposition: `activity-workspace-v29/pdf-topic-disposition.md` (264 topics).
  V30 rewrote only the rows whose behaviour changed; the rest are carried forward.

## Changed topics and where each was proven

| Topic | Printed page | CUBI implementation | Proof |
|---|---:|---|---|
| Delete an activity | 12 | `P6ActivityMasterAPI.delete`, `SQLiteActivityMasterRepository.delete`, `POST/GET` command `edit.delete` | `activity-edit-v30` (leaf delete, linked refusal, stale 409), `test_p6_activity_edit_commands.py` |
| Dissolve an activity | 12–13 | `P6ActivityMasterAPI.dissolve`, command `edit.dissolve` | `activity-edit-v30` (SF+FF → SF), `test_p6_activity_edit_commands.py` |
| Copy and paste activities in the Activity Table | 14 | `workspace-activity-clipboard.ts`, `edit.copy`/`edit.paste`, Activity Master POST | `activity-edit-v30` (paste row, planned status, children copy) |
| Cut and paste activities in the Activity Table | 15 | Clipboard mode `cut`; paste creates first, then deletes with the record revision | `activity-edit-v30` (source gone, moved row present) |
| Fill Down | 9 | `planFillDown`, command `edit.fill-down` | `activity-edit-v30` (two selected rows share the first name), `workspace-activity-bulk.test.ts` |
| Replace (Ctrl+R) | 58–59 of 93 (toolbar/menu reference) | `mountActivityReplaceDialog`, `planActivityReplacements`, command `dialog.replace` | `activity-edit-v30` (preview count, persisted name, grid repaint) |
| Spell Check (F7) | 58–59 of 93 | `mountActivitySpellCheckDialog`, command `dialog.spell-check`; fields expose `spellcheck="true"` | `activity-edit-v30` (corrected name persisted, dialog closed) |
| Add a curtain attachment in a Gantt Chart | 16 | `p6_gantt_attachment.py`, `workspace-gantt-attachments.ts`, Gantt curtain layer and dialog | `gantt-attachments-v30`, `test_p6_gantt_attachment.py`, `test_gantt_attachment_http_routes.py` |
| Hide a curtain attachment in a Gantt Chart | 17 | `visible=false` through the revisioned PATCH; the curtain leaves the Gantt body but stays listed | `gantt-attachments-v30` (hide), survives reload |
| Add a text attachment to a Gantt Chart | 17 | `kind=text` anchored to the activity bar | `gantt-attachments-v30` (A130 mark) |
| Remove a text attachment from a Gantt Chart | 18 | Revisioned DELETE | `gantt-attachments-v30` (delete all created records) |
| Attach notebook items to bars in a Gantt Chart | 18 | `kind=notebook` stores `topic_id`; the body stays in the Notebook tab | `gantt-attachments-v30` (topic link and bar mark) |
| Hide all curtain attachments in the Gantt Chart | 18 | Toggle per curtain; hidden records are excluded from the drawn layer | `gantt-attachments-v30` |
| Delete a curtain attachment from a Gantt Chart | 19 | Revisioned DELETE with 409 on a stale revision | `gantt-attachments-v30` |
| Display all curtain attachments in the Gantt Chart | 19 | Every `visible` curtain in the timeline is drawn from its stored range | `gantt-attachments-v30` |

## V26 rules implemented exactly

- **Dissolve is not Delete.** It requires at least one predecessor and one successor. For every
  predecessor × successor pair it builds a new relationship whose first half comes from the
  predecessor link and second half from the successor link (`SF` + `FF` → `SF`). Lag is set to zero,
  as the reference states when “Retain lag” is not enabled. The old links and the activity are then
  removed. Child records block the operation.
- **Delete is guarded.** A delete is refused with `ACTIVITY_HAS_RELATIONSHIPS` or
  `ACTIVITY_HAS_CHILD_RECORDS` (codes, notebook, steps, resource assignments, document links) rather
  than silently orphaning them.
- **Attachments are presentation records.** They never change schedule dates, progress, float or the
  critical path; the Gantt uses only the authoritative activity/date values it already reads.
- **Notebook attachment ≠ notebook content.** The attachment stores a `topic_id` link and a bar
  label; the topic body remains in the Notebook tab through the existing service.
