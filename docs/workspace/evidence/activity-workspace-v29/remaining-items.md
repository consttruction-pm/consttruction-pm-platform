# V29 — Remaining items and explicit boundaries

These items are **not** claimed as complete. They are recorded with the technical
reason so the next increment can pick them up without guessing.

## 1. Gantt Curtain and Text Attachments

- Reference: View > Attachments (PDF Activities chapter, “Attachments”).
- Status: **absent**. No overlay, dialog or sample data was added.
- Reason: this is a new project-level presentation contract (curtain range/colour/label
  plus activity-linked text). It requires a repository, revisioned HTTP contract,
  Gantt drawing and a management dialog. Shipping only the visual band would violate
  the “no appearance without function” rule.
- Recommended next step: add `p6_gantt_attachment` with `kind=curtain|text`, CRUD under
  `/p6/gantt/attachments`, draw curtains in the existing non-working band layer, and
  add a View > Attachments dialog with the same revision guard as the Notebook.
- Files that will be touched: `workspace-view.ts` (Gantt layer and dialog),
  `main.ts` (state load), `project_lifecycle_routes.py`, `preview/runtime.py`, both
  stylesheets. These are shared with PRs #1716/#1711/#1983; changes must stay additive.

## 2. Clipboard/editing commands

Cut, Copy, Paste, Fill Down, Delete Activity, Dissolve and Replace are visible but
disabled with a stated reason. There is no clipboard or deletion contract in the
project service; wiring a browser-only clipboard and presenting it as project editing
was rejected.

## 3. Ctrl+W semantics

The reference labels Ctrl+W “Close All”; CUBI closes the current window. The current
behaviour is preserved; changing it to close every project window would discard other
unsaved layouts and needs an explicit owner decision.

## 4. Enterprise dictionaries

Activity Codes *assignments* are implemented. Creating/editing code **types** belongs to
Enterprise > Activity Codes, Resource Codes, Project Codes, OBS, cost accounts and step
templates; those remain outside the Activities workspace and are disabled with reasons.

## 5. 73 `verify` topics

`pdf-topic-disposition.md` contains 73 rows mapped to an existing surface but not
individually exercised with a dedicated browser test. They are open review items, not
acceptance. The matrix shows each topic, page, mapped surface and reason.

## 6. EPPM-only topics

Activity owners, EPPM tasks, discussions and reflection workflows are P6 EPPM surfaces.
The CUBI desktop Activities workspace does not present them; the matrix marks them
`out-of-scope` rather than empty.

## 7. Issue/risk individual topics

The shared Issues and Risks windows and APIs already exist and are read into the
Details tabs. Individual topics such as “Assign a tracking layout to an issue” or
“Send email about an issue” depend on surfaces outside Activities; they are recorded
individually in the disposition matrix and were not all exercised this round.

## 8. Server-side production composition

The new child APIs are wired in the local full-stack preview, which is the mandated
test environment. Production composition accepts the optional APIs but no production
database migration was added: schema/migrations are protected and must be reviewed
separately before activation. Until then production simply reports the route as
unavailable; it does not fake success.
