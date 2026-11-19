# V31 — Remaining items

This file is deliberately **not empty**. V31 implemented and proved four Help areas, but the 264-topic matrix still contains open review and partial rows. Recording them is required so the next increment does not relabel them without execution.

## Matrix position

| Status | V30 | V31 |
|---|---:|---:|
| confirmed | 116 | 119 |
| partial | 34 | 32 |
| verify | 73 | 72 |
| delegated | 26 | 26 |
| out-of-scope | 15 | 15 |

## 72 `verify` rows

These are mapped surfaces that have never been individually exercised in a browser. They are concentrated in:

- Chapter 5 activity creation, dates, percent complete, milestones and summaries (rows 1–3, 14–15, 21–23).
- Relationships: add/change/remove predecessor and successor, Gantt/Network relationship views (rows 29–39, 44–50).
- Future-period bucket planning and FAQ rows (66–68 and adjacent).
- Long-tail Chapter 5–8 topics listed in `../activity-workspace-v30/pdf-topic-disposition.md` with `VERIFY`.

Closing a row requires its own browser action and persisted evidence, not a status edit.

## 32 `partial` rows

Known examples after V31:

- **Predecessor/Successor tab column dialogs** — the tabs render authoritative relationships, but the P6 column chooser/order/reset workflow is not complete.
- **Relationship editing in the Gantt chart** — create/delete link surfaces exist and write through the relationship API; the full P6 edit path (type/lag change from the chart) and duplicate/cycle messaging are not individually proven in this increment.
- **Replace resources assigned to activities** — the dialog surface exists, but the shared assignment service does not yet expose a replace contract.
- **Several long-tail menus/toolbars** remain explicitly disabled with a stated reason.
- **Spell Check** still delegates detection to the browser dictionary; no Oracle word list is shipped.

## Explicit boundaries left by this increment

1. **Cut with assignments or period actuals.** Paste/cut creates the new row and copies children, but the server refuses to delete an activity while assignment or period-actual rows still reference it. Moving those rows needs a shared-service contract. The refusal is named; no data is dropped.
2. **PostgreSQL renumber execution.** The repository method is implemented for both dialects, and the PR `postgres` CI job passes, but no dedicated PostgreSQL renumber scenario was added there. The executable renumber proof remains SQLite (unit, HTTP and browser).
3. **Full visual matrix.** The three new dialogs are captured at 1366×768 English. Six themes × three sizes × Persian RTL are not captured for these dialogs yet.
4. **Risks/Issues write workflows.** V30 decision carried forward: shared services own those writes; Activities reads them.
5. **EPPM-only surfaces.** Owners, EPPM tasks, discussions, team messaging and reflection remain out-of-scope.

## Next increments (in order)

1. Add a PostgreSQL renumber integration scenario (the code path exists; CI currently proves the wider integration only).
2. Complete Gantt relationship editing as a dialog with type/lag, duplicate and cycle guards, plus predecessor/successor column chooser.
3. Give each remaining `verify` row a browser action or an explicit owner decision.
4. Move cut semantics for assignments/period actuals into the shared assignment service.
5. Extend the visual matrix to the new dialogs in six themes, three sizes and both languages.
