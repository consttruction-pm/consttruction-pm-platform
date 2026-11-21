# Schedule Scenario Studio — Specification

Status: **BLOCKED**. The shared scheduling core and authoritative schedule
read routes exist; the revision-bound scenario entity, run history, comparison
and promotion contracts do not (issue #1989 remains Phase 1). The existing
`scenario-lab` entry in `workspace-engineering-shells.ts` is a presentation
shell and is explicitly not live.

## Composition

Eight regions in one studio:

1. **Command Brief** — original request, project, source revision, data date,
   objective, constraints, assumptions, missing inputs, analysis progress,
   last calculation identity.
2. **Scenario Selector** — baseline, current/as-of, A/B/C, user scenarios;
   create, duplicate, rename, archive, delete draft, pin, mark recommended,
   compare, switch; each row shows scenario id, parent/source revision, created,
   objective, assumptions, changes, calculation version, validation state,
   author, run status. Runs are immutable; re-running creates a new version.
3. **Gantt Workspace** — day/week/month/quarter, zoom/fit/scroll, WBS
   expand/collapse, row height, baseline/current/scenario bars, actual progress,
   remaining work, milestones, summaries, constraints, critical/near-critical,
   total float, data date line, FS/SS/FF/SF with signed lags. Four bar styles:
   classic, capsule, slim, progress overlay. Shape/pattern/indicator accompany
   color.
4. **Activity Grid** — the 22 columns in #2090, frozen columns, sort, filter,
   group, multi-select, context menu, keyboard, export; selection is shared with
   Gantt and inspector.
5. **Comparison** — side-by-side, overlay and variance table; added/removed/
   modified, duration/date/logic/resource/cost/constraint/milestone/critical
   changes; old and new values; navigating a delta selects the same activity.
6. **Activity Inspector** — general, dates, durations, relationships, resources,
   costs, constraints, calendars, progress, scenario changes, evidence,
   validation; dock/resize/hide.
7. **Impact Dashboard** — project/baseline/current/scenario finish, days
   recovered/lost, critical/near-critical counts, float exposure, resource peak
   and overallocations, cost delta, milestone variance, risk exposure. Every
   number links to the run and calculation identity.
8. **Controls** — run, recalculate, validate, compare, save draft, export,
   request approval, discard. Running never mutates the source project.

## Interaction

- Commands such as "revise the schedule considering current delays" open the
  studio with a brief; the assistant must not change the project.
- Missing facts produce one focused question with valid choices and "not known".
- Refinements ("two extra crews", "do not change the calendar") create a new
  immutable scenario version and show the delta from the previous version.
- Switching scenario updates Gantt, grid, inspector, comparison and impact
  together; selection and visible date range are preserved where possible.
- Four candidate objectives (lowest cost, earliest finish, least additional
  resources, balanced) are profiles to evaluate, not pre-written results.

## Required services

| Contract | State |
|---|---|
| authoritative schedule snapshot + calculation identity | present |
| scenario entity, pinned inputs, immutable runs | absent (#1989) |
| scenario edit change set | absent |
| comparison/difference report | absent |
| promotion/approval request | absent |
| permission recheck + stale revision refusal | absent |

## Acceptance

Create, run, compare, refine, discard scenarios against a pinned revision; all
views synchronized; source unchanged until an exact approved promotion; results
reproducible and audited. No browser CPM. No second scheduler.
