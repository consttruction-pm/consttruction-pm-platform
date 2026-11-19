# V30 — Dialog and field audit

## Gantt Attachments dialog

- Entry: Gantt toolbar **Attachments** button (`data-gantt-attachments-open`) with a live count.
- Title: “Gantt Attachments” / «پیوست‌های گانت».
- Layout: header + close button, status line, table (Kind, Label, Range / Activity, State,
  actions), form grid, hint and actions. Logical properties keep it RTL-safe.
- Table actions: Hide/Show, Edit, Delete. Delete carries `data-attachment-revision` and is
  disabled while the request is in flight.
- Form fields, in order: Kind (Curtain/Text/Notebook), Label (required), Start date, Finish date,
  Colour, Activity select (from the loaded workspace), Notebook topic ID, “Show on the chart”.
- Validation: label required; kind must be one of the three; the server enforces curtain range
  (`start <= end`) and text/notebook activity links; notebook requires a topic. Rejections show
  the stable error code in the form message.
- Save/Cancel: Save submits through the transport; Escape/× closes; a successful save reopens the
  dialog so the operator keeps context; a stale revision shows `REVISION_CONFLICT` and leaves the
  stored row unchanged.
- Keyboard/RTL: native `<dialog>` focus trap, labels wrap the inputs, logical `inset-inline` and
  `border-inline` properties, sized `min(720px, 100vw - 32px)`.

## Replace dialog

- Entry: Edit > Replace… or Ctrl+R.
- Title: “Replace in Activity Names” / «جایگزینی در نام فعالیت‌ها».
- Fields: Find what (required), Replace with, Match case, Scope (All displayed / Selected
  activities only).
- Behaviour: the status line previews the exact number of names that will change before Apply.
  Apply is disabled during writes; errors stay in the dialog; Cancel/Escape closes without a
  write. Every change is an Activity Master PATCH with `expected_revision`.
- Scope limit: the dialog replaces **Activity Name**, the one table field with a shared editable
  contract; other fields keep their dedicated editors.

## Spell Check dialog

- Entry: Edit > Spell Check… or F7.
- Title: “Spell Check Activity Names” / «غلط‌یابی نام فعالیت‌ها».
- Fields: one text input per activity with `spellcheck="true"` so the browser’s own dictionary
  marks misspellings. No private word list and no fake detection are shipped.
- Behaviour: Save corrected names sends only changed names, each with its record revision;
  Cancel closes without writes; the list scrolls inside a 50vh region.
- Limit: detection quality is the browser’s, not Oracle’s dictionary. The dialog states this in
  the hint.

## Delete / Dissolve confirmation

- Native confirmation dialogs state the activity ID and, for Dissolve, that predecessors will be
  joined to successors.
- Refusals are shown as alerts containing the stable server code
  (`ACTIVITY_HAS_RELATIONSHIPS`, `ACTIVITY_HAS_CHILD_RECORDS:…`, `REVISION_CONFLICT`), and the row
  remains selected.
- E2E `activity-edit-v30` accepts both dialog types through CDP and asserts the linked activity
  was not removed.

## Visual checks

`visual-matrix-v30` opened all four surfaces in every theme and both languages at 1366×768 and
asserted that each dialog rectangle is inside the viewport, the document has no horizontal
overflow, and the spell fields request browser spellcheck. Screenshots are under `visual/`.
