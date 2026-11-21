# CUBI AI Workbench — Implementation Map

Status of this document: Phase 0 repository audit, 2026-11-21. It records what
exists in `main` (`593aa55ce`), what the Workbench may reuse, and what is
blocked. It is not proof that a studio works.

## 1. Governing inputs inspected

| Input | State at audit | Consequence |
|---|---|---|
| `main` | `593aa55ce` (PR #2089, #2091, #2092 merged) | Work starts from the current Workbench/Enterprise entry contract |
| Issue #2090 | OPEN, owner-approved P0 | Defines the five studios and the no-second-engine rule |
| Issue #1989 | OPEN, Phase 1 contract only | Scenario backend/UI not implemented |
| Issue #1706 | OPEN | Engineering intelligence engines not complete |
| Issue #2019 | OPEN | Assistant interaction matrix is not accepted as complete |
| Issue #1423 | OPEN | Shared scheduling core contract still the authority |
| Issue #1799 | OPEN | Project exchange/import gaps remain |
| Issue #2085 | MERGED | Personal Workbench is the signed-in entry |
| PR #1988 | MERGED (docs only) | Capability/menu ownership contract |

## 2. What already exists and must be reused

| Capability | Code | Usable as |
|---|---|---|
| Shared scheduling core + authoritative schedule read | `src/construction_pm/scheduling/`, `authoritative_schedule_input_composer.py`, `schedule_snapshot_*` | Read-only project schedule, Gantt/grid, CPM identity |
| Schedule/baseline HTTP routes | `http/project_lifecycle_routes.py`, `/api/projects/{id}/p6/*` | Authoritative read models |
| Register exchange | `exchange_api.py`, `exchange_application.py`, `/api/projects/{id}/exchange/*` | Preview/validate/apply of four register datasets, atomic, idempotent |
| P6 interchange codecs | `p6_xer_codec.py`, `p6_mpx_codec.py`, `p6_interchange_api.py` | Row-level mapping/export, **not** project ingestion |
| Risk register | `risk_api.py`, `risk_application.py`, `workspace-risks.ts` | Real risk read/write |
| Assistant chat backend | `ai_assistant_orchestration.py`, `ai_action_runtime.py` | Command intake provider, not a studio |
| Assistant UI chrome | `ai-assistant-chat.ts`, `ai-action-panel.ts`, `global-assistant-launcher.ts` | Chat entry that must route to studios |
| Scenario shell | `workspace-engineering-shells.ts` (`scenario-lab`) | Presentation placeholder, explicitly **not live** |

## 3. What does not exist

- No project-level import engine (EPS/projects/WBS/relationships/calendars/
  baselines). Exchange imports four register datasets only.
- No revision-bound scenario entity, run history, comparison or promotion
  service.
- No Engineering proposal store bound to a scenario revision and no execution
  contract with reauthorization, atomic apply, audit and read-back.
- No Workbench HTTP route or studio document. Only the chat backend exists.

## 4. Implementation map

| Phase | Component | Status | Owner path |
|---|---|---|---|
| 0 | Audit, path ownership, docs | DONE (this change) | `docs/ai-workbench/` |
| 1 | Command envelope, intent resolver, studio registry, permissions | LIVE: exposed over the Workbench HTTP boundary | `src/construction_pm/ai_workbench/` |
| 1 | Workbench shell, command panel, inspector, status bar | WIRED (preview browser journey) | `apps/web/src/workbench/`, `apps/web/ai-workbench.html` |
| 2 | Import staging (7 tabs) | PARTIAL: register exchange only; project ingestion still absent | `exchange_*` |
| 3 | Schedule Scenario Studio | BLOCKED by #1989 backend contract | none |
| 4 | Risk Analysis Studio | WIRED_WRITE: table, matrix, create/edit forms with `expected_revision`, audit history, read-back | `risk_*` |
| 5 | Project Analysis Studio | WIRED_READ: stored counts and control metrics | schedule read models |
| 6 | Decision & Approval | PARTIAL: Enterprise approvals exist, proposal execution absent | `enterprise` approvals |
| 7 | Enterprise reuse | PLANNED after shared contracts stabilise | Enterprise shell |

## 5. Ownership and collision rules

- Do not modify `scheduling/`, `schedule_evaluator.py`, resource leveling or the
  schedule composer while #1989/#1423 work is open.
- The Workbench shell is its own document and bundle; `apps/web/src/main.ts`
  only routes to it through a single localized menu command.
- Do not add a second import engine. #1799 owns project exchange.
- Do not add a second scenario persistence model. #1989 owns it.
- The Workbench may read the risk and schedule routes today; it may not write
  schedule facts.

## 6. Definition of done for the two P0 deliverables

`PROJECT_IMPORT_STAGING_SPEC.md` and `SCHEDULE_SCENARIO_STUDIO_SPEC.md` contain
the acceptance gates. Until the missing services exist, both remain BLOCKED and
their controls must stay disabled with an explicit reason.
