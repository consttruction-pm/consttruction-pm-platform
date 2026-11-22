# Project Import Review & Staging — Specification

Status: **PARTIAL**. The source stage now exists:
`src/construction_pm/importing/` implements contract
`cubi-reference-import-source.v1`, which reads the whole workbook, validates the
engineering referential integrity (project/EPS/OBS/WBS/activity/relationship/
calendar/resource/assignment/baseline/progress) and returns deterministic counts
and issues without touching a database. See
[`docs/engineering/CUBI_REFERENCE_PROJECTS_IMPORT_MAPPING.md`](../engineering/CUBI_REFERENCE_PROJECTS_IMPORT_MAPPING.md).
Staging/apply stays **BLOCKED** until the canonical project exchange/import
engine from issue #1799 is mounted — the repository today has register-level
exchange only (`exchange_application.py`): resources, WBS, activities,
assignments and cost/expense rows. It has no EPS/project, relationship,
calendar, baseline or document ingestion.

## Non-negotiable rule

An imported project never appears in the live Engineering workspace first. The
staging surface is isolated: preview, mapping, validation and plan generation
must not mutate the target project. Only an explicit, bound confirmation may
run the import contract.

## Page contract

One studio, seven tabs, shared header and status bar. Tabs are not separate
apps.

| Tab | Required data | Server contract | Status |
|---|---|---|---|
| 1 Source | file name/type/size/format/version, received at, origin, checksum, security scan, parse state | staging intake | BLOCKED |
| 2 Inventory | EPS, projects, WBS, activities, relationships, calendars, codes, UDFs, resources, roles, assignments, expenses, costs, baselines, constraints, documents; total/valid/invalid/duplicate/orphan/unsupported | staging inventory | BLOCKED |
| 3 Mapping | source field/value, target, rule, confidence, status; auto/manual; date/duration/unit/currency/calendar/code/resource/ID mapping; ambiguous values need a user choice | staging mapping | BLOCKED |
| 4 Validation | duplicate IDs, missing parent, WBS cycle, dangling/cyclic logic, invalid lag/date/duration, missing calendar/resource, orphan assignment, constraint, baseline inconsistency, unsupported field, cross-project reference, data loss; four severities; row drill-through | staging validation | BLOCKED |
| 5 Schedule Preview | WBS tree, Gantt, synchronized grid, activity details, float/critical, baseline overlay, milestones, error highlights; source-reported vs CUBI-recalculated values | staging snapshot + shared core | BLOCKED |
| 6 Options | create/update/merge, preserve/remap IDs, datasets, conflict policy, project calendar, timezone, planned create/update/skip counts | staging plan | BLOCKED |
| 7 Final Review | counts, remaining errors/warnings, data loss, target, permissions, target revision, source digest, exact confirmation, apply and verify | staging apply + audit | BLOCKED |

## Apply sequence

1. Re-authorize the actor for the target scope.
2. Re-read the target revision and compare it with the plan.
3. Recompute the source digest and compare it.
4. Execute through the canonical import contract inside one transaction.
5. Write an audit/import-run record.
6. Fresh-read the created/updated project and verify counts, hierarchy,
   relationships, dates and calculation identity.
7. Only then enable **Open Imported Project in Engineering**.

On failure: rollback or expose an explicit recoverable state. Never hide a
partial write.

## Blocking gaps

- No project-level parse/inventory/relationship/calendar/baseline contract.
- Exchange preview returns register rows and errors, not a project graph.
- No staging snapshot handoff to the scheduling core.
- No import-run audit identity for a project graph.

## Acceptance

A real project file can be staged, reviewed, mapped, validated, previewed in a
real Gantt and imported only after exact confirmation, with counts and the
schedule verified from the database afterwards. Until the gaps above close,
this page must render a blocked entry, not a demo.
