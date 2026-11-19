# V30 — Remaining items and explicit boundaries

These items are **not** claimed as complete.

## 1. 73 `verify` topics remain

The V29 matrix contained 73 `verify` rows. V30 did not individually exercise all of them; the
count is unchanged. V30 closed 4 `partial` edit-command rows and 5 of the 7 `absent` Gantt
attachment rows. The remaining matrix is `pdf-topic-disposition.md`
(116 confirmed / 34 partial / 0 absent / 26 delegated / 15 out-of-scope / 73 verify).

The next increment must give each `verify` row its own browser action or an explicit
out-of-scope decision; flipping the label without that evidence is forbidden.

## 2. 34 `partial` topics

They are rows where a surface exists but the full reference workflow is not proven. Examples:

- “Hide all curtain attachments” / “Display all curtain attachments”: per-record Hide/Show works
  and is persisted; a single bulk toggle is not implemented.
- Predecessor/Successor tab column dialogs, relationship editing in the Gantt chart, renumbering
  activity IDs, and resource-assignment Replace remain partial.
- Several long-tail toolbar/menu items remain disabled with a stated reason.

## 3. Copy Activity Options / Renumber IDs

V30 Paste copies the source fields plus codes, notebook topics and steps. It does **not** present
the reference’s Copy Activity Options dialog (relationships, expenses, WPs & Docs, financial
period data, “only between copied activities”) or the Renumber Activity IDs dialog. New IDs use a
deterministic `-C1` suffix. Relationships are not copied.

## 4. Fill Down scope

Fill Down operates on the Activity Name, the only table field with a shared editable contract.
Other columns are edited in Activity Details. The reference applies to any table column.

## 5. Spell Check detection

Detection is delegated to the browser’s spellchecker (`spellcheck="true"`). CUBI does not ship
Oracle’s dictionary, so detection quality differs. The dialog is usable (review, edit, save), but
it is not a byte-for-byte parity claim.

## 6. Ctrl+W semantics

The reference labels Ctrl+W “Close All”; CUBI closes the current window. Closing every project
window would discard other unsaved layouts and needs an explicit owner decision.

## 7. EPPM-only surfaces

Activity owners, EPPM tasks, discussions, team messaging and reflection workflows are not
presented. They remain `out-of-scope` in the matrix.

## 8. Risks / Issues

The shared Issues/Risks windows and APIs remain read into Details; V30 did not add new
risk/issue write workflows inside Activities. The shared services own those writes.

## 9. Menu/dialog completeness

V30 audited the new commands and dialogs and the changed shortcut/menu states. It did not
re-audit every existing dialog’s tab order and error text. Rows still marked `verify`/`partial`
are the honest indicator of that gap.

## 10. Visual matrix breadth

The matrix covers the main Activities window, Edit menu, Attachments, Replace and Spell Check
dialogs in 6 themes × 3 sizes × 2 languages (84 screenshots). It does not capture every remaining
dialog (columns, filters, group/sort, bars, timescale, preferences) in every theme.
