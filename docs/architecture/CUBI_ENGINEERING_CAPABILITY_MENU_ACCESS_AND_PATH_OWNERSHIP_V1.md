# CUBI Engineering Capability Contracts, Menu Placement & Path Ownership V1

**Recorded:** 2026-11-16  
**Parent:** #1990  
**Architecture/parity tracker:** #2007 / PR #2008  
**Engineering scenario slice:** #1989  
**Canonical capability IDs:** `docs/architecture/CUBI_MASTER_CAPABILITY_REGISTER_EPPM_V26_CLOUD_V1.md`  
**Navigation baseline:** `docs/architecture/CUBI_PRIMAVERA_CLOUD_P6_V26_IMPLEMENTATION_FEASIBILITY_AND_NAVIGATION_V1.md` §§4–6  
**Repository snapshot inspected:** `main` = `0fc0d80ece1d3f495564fa20e32d6f2f21f10a1b`  
**Status:** contract and navigation decision record; no application implementation or full Help parity is claimed.

## 1. Decision and non-goals

This document turns the existing capability consolidation into implementation contracts, exact host-menu placement, access rules and path ownership. It does not reopen the already-recorded performance optimization work, create another scheduler, or authorize broad shell refactoring.

Binding decisions:
1. Engineering remains the authoritative owner of project execution records and calculations. Enterprise owns organization, portfolio, cross-project capacity policy, workflow definitions and commercial/claims records. Shared owns technical primitives. Workbench is a non-owning projection.
2. New Engineering capabilities are inserted into the existing project/module contexts below. No new global top-level item is added for Scenarios, Compare, Health, Monte Carlo, PPC, Last Planner, histograms or other sub-capabilities.
3. A single record has one owner, one canonical write API/service and one persistence authority. Other environments consume permission-filtered, revision-pinned read models or deep links.
4. A capability is not “present” because a shell, menu label, route, mock, schema or API exists. Record status at the behavior level: `VERIFIED`, `WIRED_WRITE`, `WIRED_READ`, `SHELL_ONLY`, `MISSING`, `NOT_AUDITED`, `BLOCKED_EXTERNAL`, `NOT_APPLICABLE`.
5. Do not infer undocumented source behavior or visual dimensions. Exact source/topic/step and each option remain traceable; unresolved material is `MISSING / VERIFY`.
6. Do not change approved Jalal 5 weights or earned progress.

## 2. Capability contracts and exact Engineering menu placement

The following are the approved insertion points. Labels are proposed CUBI-native names; localization and exact icon/visual tokens must follow the existing workspace catalog and source-ledger evidence.

| Capability / canonical owner | Exact host placement | Entry/action | Data and calculation authority | Access boundary | Current evidence / next contract gate |
|---|---|---|---|---|---|
| ENG-04 Schedule Scenarios / What-if | Project → Activities / Schedule → tab **Scenarios** beside Schedule/Baselines; Schedule toolbar action | Create, duplicate, open, compare, archive; explicit validated **Apply to live schedule** only as a separately guarded command | Engineering scenario aggregate with immutable source schedule snapshot; run through the existing authoritative scheduler | Project membership + schedule/object privileges; reauthorize at every write/apply; optimistic revision and idempotency | #1989 says shell exists but is not a verified live service; Phase 1 contract remains DRAFT/IN REVIEW. Next: typed scenario/change-set/run contracts and isolated persistence/API/UI slice. |
| ENG-04 Schedule Comparison | Project → Activities / Schedule → **Compare** tab or analysis panel; launch from scenario/baseline version selector | Compare two pinned schedule versions; filter differences; drill through to activity/WBS | Read-only comparison projection over immutable schedule versions; no calculation authority of its own | Same project scope as both versions; deny cross-project or unauthorized baseline references | Feature is mapped in architecture; full entity/difference coverage and lifecycle remain unverified. Do not create a second Schedule window. |
| ENG-05 Schedule Health / Quality Audit | Project → Activities / Schedule → **Health** tab/right analysis panel; finding drill-through opens Activity row | Run/view rule results, severity, counts, exclusions, trend and remediation links | Engineering quality-audit rules consume authoritative schedule run/snapshot; no parallel CPM or duplicate formula service | Project/schedule view plus separate privilege for rule administration if applicable; findings inherit source-object visibility | Quality-audit code and PR #1711 exist, but exact current-main/head, full V26 rule catalog and UI parity must be rechecked. Health Score ≠ complete EPPM parity without source trace. |
| ENG-08 Project Risk Register | Project → **Risk** → Register, Assessment, Response, History tabs | Create/update risk, assign owner, assess probability/impact, response, link to WBS/activity/cost/resource | Engineering project-risk domain and source-owned records | Project + risk privileges; object-level links validated server-side; tenant isolation | Risk workspace/API foundations exist; lifecycle and UI completeness need exact-head audit. PR #1983 overlaps Risk paths. |
| ENG-09 Quantitative Risk / Monte Carlo | Project → Risk → **Quantitative Analysis**; launch from Risk Register and Schedule Health | Configure uncertainty, start run, inspect immutable results and sensitivity charts | One Engineering simulation service; consumes pinned schedule run, data date, calendars, cost model and risk inputs; async job; never a second CPM | Project + risk-analysis execute/view privileges; run/result access inherits tenant/project scope | Do not relabel deterministic risk score as Monte Carlo. Full simulation/run/result contract and UI are not verified; treat as missing until proven. |
| ENG-06 Project Resources / Resource-loaded plan | Project → **Resources** → Usage, Histogram, Assignments, Leveling views; Activity Details → Assignments | Inspect time-phased demand/capacity/cost, assign resources, run controlled leveling and inspect log | Engineering project assignments and canonical Shared Scheduling Core; no Enterprise recalculation | Project/resource/WBS assignment privileges; validate resource scope and project revision | Resource dictionary/assignment and leveling foundations exist. Verify UI views, spread semantics, role loading, units/rates, leveling controls and log against exact Help. |
| ENG-10 Field Work Plan / Last Planner | Project → **Field Operations** → Work Plan, Lookahead, Constraints, Daily Huddle, Commitments, PPC | Plan/release weekly work, handoffs, constraints, commitments, huddle, completion and missed reasons | Engineering field-execution records typed and linked to project/WBS/activity; no shadow activities; no generic Enterprise task substitute | Project + field/commitment privileges; crew/subcontractor filters are visibility-scoped, not authorization | Shell/roadmap is not proof of connected records. Build lifecycle and APIs as an Engineering vertical slice after path audit. |
| ENG-10 Activity-centric Team Updates | Activity Details → **Team Update** panel; contributor **My Activities** view in Engineering/Workbench | Update permitted status/steps, submit/withdraw, review; scheduler receives validated source mutation | Engineering activity/status service; distinct from generic task records | Assignment-to-actor check, project grant, field-level privileges, review/approval scope | P6 Team Member V26 Help is normative. Never route this through Enterprise Task Center. |
| ENG-07 Time entry / timesheets | Contributor Workbench → **My Work → Timesheets**; manager read/review in Project → Progress/Cost | Enter, save draft, submit/withdraw, approve/reject, post actuals through one controlled path | Engineering owns activity/resource actual-unit and cost effects; timesheet workflow may use shared runtime | Assigned resource + project/time-period privilege; approver scope; prevent duplicate posting via idempotency | Dedicated workflow and period semantics need exact Team Member/Cloud Help trace. Do not create duplicate entry forms in Resources and Progress. |
| ENG-10 Production & Productivity Intelligence | Project → Field Operations → **Production & Productivity** panel; link from activity/resource details | Quantities, rates, earned hours, production curves, crew/equipment productivity, bottlenecks | Engineering production facts and analytics; schedule/resource facts consumed with revision provenance | Project/WBS/activity/resource scope; quantity and rate write privileges distinct from analytics view | Capability is a registered child requirement, not an independently authorized top-level engine. Register owner must confirm canonical child row. |
| Engineering technical Delay Analysis | Project → Schedule → **Analysis → Delay Analysis** (contextual action from baseline/current schedule) | TIA/windows/fragnets/as-planned vs as-built and critical-path impact | Engineering owns technical schedule evidence and calculations; claim/commercial case remains Enterprise ENT-13 | Project schedule privilege; source snapshots pinned; external claim links permission-filtered | Technical delay evidence must not become an Engineering-owned commercial claim record. |
| Engineering Decision Register | Project → **Control → Decisions**; context links from Schedule, Risk, Resources and Field Operations | Record technical alternatives, evidence, assumptions, decision owner and outcome | Engineering project decision records; Shared audit/history primitive | Project/object scope and decision privileges | Do not merge with Enterprise portfolio/funding/contract decision authority. |
| Engineering Standards & Methods Library | Project → **Reference → Standards & Methods**; contextual links from activity/work-method templates | Browse/apply controlled technical methods and standards | Engineering-owned technical content; shared document/version infrastructure only | Project membership plus standard classification/permission | Register explicit Engineering child capability if no canonical row exists; no duplicate document store. |
| Project Scope & Work Packages | Project → **Scope & Work Packages**; Enterprise Portfolio shows read-only Scope Summary | Define project scope/work packages and links to WBS/activity/docs | Engineering owns project scope execution records; Enterprise owns portfolio intake/roll-up only | Project scope/WBS privileges | Keep one project scope record; no Enterprise duplicate editor. |
| Data Reconciliation / Data Quality | Existing Tools → **Data Reconciliation**; results deep-link to owning Project/Enterprise record; Engineering rule pack within project import/quality context | Match/diff/lineage, profile quality, propose conflicts; source owner executes writes | Shared matching/lineage framework; Engineering owns engineering rule packs and final mutations | Tenant and source-object permissions; samples redact unauthorized fields | Do not create a cross-domain mutable master record. Reuse import/export and audit infrastructure after contract review. |
| Engineering templates / work methods | Contextual **Templates** action in Project creation, WBS and Field Operations; no new global app | Create/use versioned project, WBS, activity and work-method templates | Engineering owns project execution templates; shared Form Builder/rendering may be reused | Template author/publisher privileges; use-time project scope | Enterprise owns organization/portfolio/workflow templates; no shared template business owner. |
| Recovery / Undo / Decision History | Existing File/Project History & Recovery tools; per-record history panel in owning module | Inspect revisions and invoke safe compensating commands | Shared audit/revision/idempotency/recovery primitives; source domain validates compensation | Same read/write permission as source command plus audit privilege where applicable | Never arbitrary DB rewind or last-write-wins. |
| Engineering command vocabulary / Smart Guide | Existing global command/search/help entry + contextual Help/Guide inside active module | Resolve owner-registered commands, synonyms, help and deep links | Shared command registry and Workbench presentation; domain owners register/execute typed commands | Search results and command execution are permission-filtered; server rechecks before mutation | No separate Engineering parser or duplicate help workspace. |

### Enterprise and Shared placement exclusions

- Portfolio resource planning, capacity envelopes, cross-project allocation and portfolio optimization: Enterprise → Portfolio & Executive → Resource Plans / Capacity Planning (ENT-03/04). Engineering Resources only shows authorized read-only envelopes and owns project assignments/leveling.
- Contract lifecycle, commercial obligations, notices, claims/disputes, entitlement and settlement: Enterprise → Project Portal / Contract & Commercial (ENT-13). Engineering contributes immutable technical schedule evidence only.
- Workflow definitions, delegation and approval policy: Enterprise → Workflow Studio / Approvals (ENT-08). Shared executes durable events/jobs; source domain commits business changes.
- Organization, people, teams, skills, memberships and grants: Enterprise → Organization & Access (ENT-01).
- Shared identity, tenant isolation, audit, jobs, notifications and idempotency have no duplicate user-facing business menu. Workbench exposes permission-filtered entry points only.

## 3. Common domain/API contract required for every slice

Every new or extended capability must publish a versioned contract packet before implementation:

1. **Identity and scope:** tenant ID, actor ID, environment grant, project ID and object/WBS scope are server-derived. Never trust client-supplied actor/tenant identity.
2. **Owner and authority:** one canonical domain owner, repository/write service, read projection and explicit cross-domain consumer list.
3. **Resource identity:** stable IDs; no display-name joins. Every external/cross-domain reference is typed, tenant-scoped and permission-checked.
4. **Revision safety:** expected revision / ETag for writes; immutable source revision/hash for calculations; stable conflict/error taxonomy.
5. **Idempotency and audit:** idempotency key, request hash, correlation ID, append-only actor/time/action audit, safe retry semantics.
6. **Calculation provenance:** engine/version, input snapshot hash, calendar/data-date/model versions, deterministic output hash and immutable run/result identity.
7. **Async lifecycle:** queued/running/succeeded/failed/cancelled state, progress, retry/dead-letter policy, lease/heartbeat where needed; do not make long calculations browser-owned.
8. **Authorization:** read/list/create/update/delete/execute/approve/export/admin are distinct actions. Filter before serialization; reauthorize at command execution; test cross-tenant, cross-project, unauthorized WBS/object and revoked grants.
9. **Persistence:** migration/backfill/rollback plan, SQLite/PostgreSQL behavior where applicable, transaction boundary, unique constraints, indexes and concurrency strategy.
10. **UI contract:** exact host window/tab/action, deep-link, permission-driven enabled/disabled state with reason, empty/loading/error/conflict states, keyboard/RTL/responsive behavior and traceable screenshots.
11. **Evidence:** contract tests, domain tests, persistence/integration tests, negative authorization tests, browser journey and source Help crosswalk on the exact tested SHA.

No API/schema presence alone marks a capability implemented.

## 4. Path ownership and collision register (snapshot only)

Open PR file lists were inspected on 2026-11-16. This is a collision warning, not a permanent assignment; refresh all heads/files immediately before any write.

| Open PR / issue | Observed path ownership or collision surface | Required handling |
|---|---|---|
| PR #2008 | Documentation only: this architecture, consolidation doc and governance queue | Safe documentation branch; no app source ownership. |
| PR #1974 | Broad identity, Organization & Access, project lifecycle, P6 APIs, risk, schema, production composition and `apps/web/src/main.ts` | Do not touch these paths while open without explicit owner handoff. |
| PR #1983 / #1980 | OBS/WBS access, workspace model/view/contract, `main.ts`, Risk UI/API, activity/WBS/baseline and schema | Do not overlap with risk, access, WBS, project-read or workspace-shell work. #1980 appears to be an overlapping predecessor/duplicate surface; verify status/relationship before action. |
| PR #1711 | Schedule quality audit, quality history/policy, schedule query, `workspace-engineering-shells.ts`, `main.ts`, CSS and interchange | Health/quality UI and shared workspace paths are occupied until exact-head review. |
| PR #1971 | Identity/invitation and organization access plus authoritative schedule query/evaluator/checks | Do not overlap identity, schedule evaluator/checks or production composition. |
| PR #2006 | ENT-13 claim-party membership, schema and PostgreSQL integration | Do not overlap claims membership or schema. |
| PR #2001 | Canonical capability register and ENT-13 architecture/source manifests | Coordinate register changes with this owner; do not independently edit the same register. |
| PR #1929 | Enterprise task domain/contracts and architecture/state ledger | Do not duplicate generic task contracts or edit those paths. |
| Issue #1989 | Schedule Scenario implementation; draft contract; no dedicated PR confirmed in this snapshot | Before starting, recheck all open PRs for scenario/schedule snapshot/scheduler/API/UI paths. |

### Protected shared paths

Until a fresh path-owner matrix explicitly grants a slice, treat these as protected:
- `apps/web/src/main.ts`, `apps/web/src/workspace-model.ts`, `apps/web/src/workspace-view.ts`, `apps/web/src/workspace-contract.ts`, `apps/web/src/workspace-engineering-shells.ts`, `apps/web/styles.css`, `apps/web/public/styles.css`;
- `src/construction_pm/scheduling/**`, `src/construction_pm/schedule_evaluator.py`, authoritative schedule snapshot/query/composer and resource-leveling modules;
- `src/construction_pm/application/authorization.py`, identity/session, production composition, project lifecycle routes;
- deployment schema/migrations, shared contracts and canonical capability register.

No concurrent Qoder task may write overlapping paths. A branch name or issue assignment alone does not confer file ownership.

## 5. Safe Engineering continuation sequence

1. **Preflight and contracts:** refresh main SHA, root/nested `AGENTS.md`, continuity protocol, all open PR heads/files/CI and current main. Reconcile owner IDs and Help source trace before choosing the first slice.
2. **Non-core, disjoint Engineering work first:** select a capability whose source contracts and owner are clear and whose complete allowed paths do not intersect the protected/open-PR paths. If no such slice exists, do documentation/source inventory only; do not force parallel code changes.
3. **Scenario / schedule-adjacent work:** #1989 only after PR #1711, #1971, #1974, #1983/#1980 and any newer schedule PRs have a fresh path disposition. Use the canonical scheduler and immutable snapshots. No second engine.
4. **Field Operations / Team Member / Timesheets / Production Intelligence:** each receives its own typed records and contracts; never reuse Enterprise generic task as a substitute. Confirm no collision with project lifecycle, activity master, Team Member or timesheet work.
5. **Risk / Monte Carlo / Decision / Delay Analysis:** Risk UI/API is currently collision-sensitive under #1974/#1983; wait for owner handoff. Monte Carlo requires independent model and async-run contract; it must consume authoritative schedule facts, not calculate CPM.
6. **Enterprise P2:** continue existing #2001/#2006/#1974/#1983 work after Engineering read contracts stabilize. No duplicate organization/access/claims/task subsystem.

Each Qoder handoff must name: issue, branch, base SHA, exact allowed paths, forbidden paths, upstream contract versions, dependencies, tests, expected artifacts and stop conditions. Qoder currently has no available tokens according to the last coordination snapshot; recheck availability at handoff. Do not claim execution has started until a real commit/test artifact exists.

## 6. Acceptance gates and status reporting

- One capability row per user-visible behavior, with exact EPPM V26 and/or Team Member topic, Cloud topic where it is an extension, or documented `NOT PRESENT` / `NOT APPLICABLE`.
- Exact route/menu placement, command ID, target component, role/privilege and deep-link are registered before UI implementation.
- No duplicate menu, route, data owner, API, workflow, store or calculation authority.
- Exact-head automated tests plus SQLite/PostgreSQL persistence where supported, negative authorization and cross-tenant tests, browser/runtime evidence and visual-diff evidence.
- Every capability status is reported separately. Do not upgrade a whole module based on one passing control.
- No merge/deploy or Jalal 5 progress change is authorized by this document.

## 7. Immediate registered follow-up

- Keep #2009 as the single Qoder resumption/non-interference queue, but replace the obsolete Desktop/Mobile runtime-first sequence with the Engineering contract/menu/path-ownership sequence above.
- Keep #1992 as the historical canonical performance optimization tracker; this continuation does not reopen that completed discussion.
- Update #1989 to point to the exact menu/access contract and require a fresh path matrix before implementation.
- #2007/#1990 remain the source-traceability, consolidation and overall capability program records.


## 8. Exact current-main navigation and implementation audit

This is a code-level snapshot check, separate from the target placement matrix above. The menu placements in §2 are **approved target insertion points**, not a claim that every tab/route is already mounted.

At inspected main SHA `0fc0d80ece1d3f495564fa20e32d6f2f21f10a1b`:

- `apps/web/src/workspace-model.ts` defines `WorkspaceMenuKey` entries for Project, WBS, Schedule, Progress, Resources, Assignments, Roles, Calendars, Cost, Expenses, Documents, Reports, Tracking, Issues, Risks, Thresholds, Control, Settings, Administration, Exchange and Backup. It does **not** define first-class menu keys for Scenario Lab, Field Operations, Timesheets, Team Update, Monte Carlo, Daily Huddle, PPC, Production Intelligence, Decisions or Standards & Methods.
- `apps/web/src/workspace-engineering-shells.ts` contains visual definitions such as `scenario-lab`, `optimization-studio`, `project-quality`, `construction-productivity` and `data-reconciliation`. Its renderer explicitly marks these as “Planned · shell only”; Add/Edit/Delete/Run/Export controls are disabled; no live records or data contracts are connected. These definitions are not operational capabilities and must not be presented as such.
- `apps/web/src/workspace-resources.ts` is a real project Resources client with versioned resource/capacity/rate API contracts and time-phased usage helpers. This is a wired foundation, not proof that every proposed histogram/leveling view and P6 option is complete.
- `apps/web/src/workspace-risks.ts` is a real project Risk Register client using `p6-risk-api.v1`, with risk lifecycle fields and a deterministic probability × impact exposure. This is not Monte Carlo and does not prove full Risk Help parity.
- The existing Schedule surface is the host for future Scenarios/Compare/Health. PR #1711 currently overlaps quality audit, shell and main workspace paths; do not add the Health UI until its exact head and owner disposition are refreshed.

### Status disposition from this audit

| Capability | Main-snapshot disposition | What is still missing before “implemented” |
|---|---|---|
| Schedule Scenarios / Scenario Lab | `SHELL_ONLY`; #1989 remains draft/in review | Scenario persistence/API, immutable fork/run lifecycle, comparison, conflict-safe promotion, real project-scoped UI and tests |
| Optimization Studio | `SHELL_ONLY` | Approved owner and scope split: project optimization in Engineering; portfolio optimization in Enterprise; typed solver contracts and evidence |
| Schedule & Project Quality visual shell | `SHELL_ONLY` for the generic shell; separate quality-audit code/PR evidence exists | Reconcile PR #1711 exact head, source rule catalog, Schedule → Health placement and full browser/evidence matrix |
| Construction Productivity | `SHELL_ONLY` | Canonical child capability ID, production quantity/rate records, calculation ownership, persistence/API and Field Operations placement |
| Data Reconciliation | `SHELL_ONLY` | Shared matching/lineage contract, Engineering-owned rule packs, permission-filtered review and source-domain mutation |
| Project Resources | `WIRED` foundation | Prove each usage/assignment/spread/role/leveling control and exact source semantics; do not infer complete parity |
| Project Risk Register | `WIRED` foundation | Finish lifecycle, history/response permissions and UI/source audit; deterministic exposure is not Monte Carlo |
| Monte Carlo / Quantitative Risk | `MISSING / VERIFY` as an operational simulation capability | Independent model/run/result contracts, async execution, reproducibility and analysis UI |
| Field Work Plan / Last Planner / Huddle / PPC | `MISSING / VERIFY` as an operational connected workflow; shell/roadmap labels are not evidence | Typed field commitments/constraints/huddles, activity links, workflow/API and acceptance evidence |
| Team Update / Timesheets | `MISSING / VERIFY` for full Team Member behavior | Normative Team Member Help crosswalk, assignment-scoped writes, submit/withdraw/review/approval and actual posting |
| Decision Register / Standards & Methods / Scope & Work Packages | `MISSING / VERIFY` as complete Engineering capabilities | Owner-approved child register rows, domain contracts, UI and source traceability |

The generic visual-shell renderer is intentionally honest about being unconnected. Preserve that honesty; do not enable its controls or route users to it as if the feature were live before the required backend, permission, data and test contracts exist.
