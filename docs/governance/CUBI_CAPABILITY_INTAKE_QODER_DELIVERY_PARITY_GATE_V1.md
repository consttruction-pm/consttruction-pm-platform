# CUBI Capability Intake → Qoder Delivery & Parity Gate V1

**Recorded:** 2026-11-16  
**Canonical coordination:** #2009  
**Current Engineering contributor slice:** #2010 (ENG-11 / ENG-12)  
**Status:** governance contract; no application code, runtime, UI or schema changes.

## 1. Binding objective

A capability must not be considered "added" merely because it appears in a menu, shell, roadmap, issue, register, Help crosswalk or design. From the moment a capability is accepted into the product scope, it must enter the same traceable delivery path and remain synchronized with Qoder until implementation and parity evidence are complete.

The canonical chain is:

`Capability Register → Source/Help Crosswalk → Domain & Ownership Contract → Menu/Access Contract → Qoder Implementation Issue → Exact-Path Handoff → Implementation PR → Tests & Visual/Behavioral Parity → Release Evidence → Register/Help/Navigation Reconciliation`

No stage may be silently skipped. A new capability must not sit in a documentation-only queue indefinitely while the UI implies it is operational.

## 2. Capability lifecycle states

Every capability record and its visible UI must use one of these evidence-backed states:

| State | Meaning | UI rule |
|---|---|---|
| `PROPOSED` | Product request exists; owner/source not yet approved | No operational menu item or enabled action |
| `SOURCE_MAPPED` | EPPM V26 + relevant Team Member/Cloud source crosswalk recorded | May appear in Help/roadmap only |
| `CONTRACTED` | Owner, typed data, API, persistence, calculations, permissions, menu and failure states defined | No enabled operational controls |
| `READY_FOR_QODER` | Issue, exact scope, source evidence, dependencies, tests and non-interference handoff are complete | UI remains planned/disabled |
| `IN_PROGRESS` | Qoder has accepted a scoped task and implementation PR/branch exists | Only verified partial functionality may be exposed, clearly labelled |
| `IMPLEMENTED_UNVERIFIED` | Code exists, but required CI, persistence, security, browser or Help parity evidence is incomplete | Do not mark complete; keep incomplete actions disabled |
| `VERIFIED` | Exact-head acceptance evidence passes, including source parity and security | Feature may be enabled for authorized users |
| `RELEASED` | Approved release/deployment evidence and post-release smoke checks recorded | Normal operational availability |
| `BLOCKED` | Dependency, source ambiguity, path collision, Qoder availability or failed acceptance blocks progress | Record blocker, owner, next unblock action; never imply completion |

A label, route, screenshot or API file by itself cannot advance a capability to `VERIFIED`.

## 3. Mandatory intake record for every new capability

Before adding a capability to the canonical product register or presenting it as part of the product, record:

1. Stable capability ID and exact product/module name; legacy IDs are never renumbered.
2. Parent capability and explicit distinction from adjacent concepts (for example, generic Enterprise Task ≠ Team Member Activity Status Update ≠ Timesheet ≠ Field Work Plan commitment).
3. Normative source: exact P6 EPPM V26 Help topic(s); Team Member V26 for contributor behavior; Cloud Help only for additive behavior absent from EPPM. Record Professional V26 as supplementary, not normative, unless the product mandate explicitly says otherwise.
4. Topic-level source status: `VERIFIED`, `NOT PRESENT`, `NOT APPLICABLE`, or `MISSING / VERIFY`. A TOC title is not proof of detailed behavior.
5. Engineering / Enterprise / Shared owner and non-owning consumers.
6. Typed aggregate/record boundaries, authoritative calculation owner, versioned API, persistence and migration requirements, revision/idempotency/audit model.
7. Server-enforced tenant, actor, project, assignment and object scope; separate view/create/update/execute/submit/review/approve/configure grants.
8. Exact navigation placement: menu → section → tab/window → command; identify reuse of an existing surface and explicitly reject duplicate top-level menus.
9. Existing implementation evidence classified as `MISSING`, `SHELL_ONLY`, `WIRED_READ`, `WIRED_WRITE`, `VERIFIED` per operation, not per file.
10. Exact allowed and forbidden paths, active PR owners, base SHA, branch strategy and stop conditions.
11. Qoder execution issue, task packet, expected PR, test matrix, source/visual evidence and release gates.
12. Dependency ordering and a named next action if Qoder cannot start immediately.

## 4. Qoder synchronization rules

- Every `CONTRACTED` capability must have a linked Qoder implementation issue or an explicit `BLOCKED` record with owner and next unblock action.
- Every new capability accepted after this policy must be attached to the Qoder queue in the same change that registers it; it must not wait for a later backlog sweep.
- Qoder task packets must be implementation-ready: stable ID, branch/base SHA, exact allowed/forbidden paths, upstream contract versions, menu/access placement, source crosswalk, migration/transaction rules, tests, expected artifacts and stop conditions.
- Keep one active writer per path set. If an open PR touches a target path, Qoder must not edit it without an explicit handoff from that PR owner. A task may continue on disjoint paths only after verifying imports/contracts and integration boundaries.
- If Qoder has no tokens or cannot accept the task, mark it `BLOCKED`; continue only source verification, contract refinement, test design and non-conflicting docs. Do not claim implementation progress.
- Once Qoder begins, record branch, PR, current head SHA, touched paths, test outcomes and remaining Help/UI parity gaps in the capability issue and register.
- Qoder must not independently invent menu locations, capability IDs, domain owners, source semantics or duplicate engines. Those are contract inputs.
- New feature requests discovered during implementation must be recorded as child capability intake items, not silently folded into an unrelated PR.
- A capability must not be marked complete until its register, Help crosswalk, menu/access map, implementation issue and release evidence agree.

## 5. Source and UI parity acceptance

For each capability, acceptance is operation-level and topic-level. Compare the exact normative source with CUBI for:

- pages, tabs, dialogs, fields, labels, defaults and selectable options;
- filters, sort, grouping, tables, columns, icons, commands and command availability;
- validation, calculations, rounding, calendars, time zones and date/period semantics;
- lifecycle transitions, approval/rejection/withdrawal/resubmission and audit history;
- permissions, delegation, locked/closed states and negative access;
- reports, exports, charts, notifications, responsive states and accessibility;
- offline/online behavior where applicable;
- migration, persistence, retry, idempotency and recovery behavior.

Evidence must include source topic references, test names/results, screenshots or browser captures for material UI journeys, and exact commit/PR head. If source behavior is unknown, mark it `MISSING / VERIFY` and keep the affected operation blocked.

## 6. Menu and shell integrity

- A shell is not a feature. Planned shells must keep all nonfunctional actions disabled and be explicitly identified as `SHELL_ONLY`.
- Do not add a second route, menu, data store, API, workflow or calculation engine for an existing capability.
- Do not enable a button just because its visual design exists.
- Every visible command must map to a permission, API operation, persisted outcome and test.
- Existing contextual placement remains binding unless the product owner approves a documented change:
  - Schedule → Scenarios / Compare / Health.
  - Risk → Register / Assessment / Response / Quantitative Analysis / History.
  - Resources → Usage / Histogram / Assignments / Leveling.
  - Field Operations → Work Plan / Lookahead / Constraints / Daily Huddle / Commitments / PPC / Production & Productivity.
  - Activity Details → Team Update.
  - Workbench → My Work → Timesheets.
  - Project Control → Decisions; Project Reference → Standards & Methods; Project Scope → Scope & Work Packages.
  - Data Reconciliation and Smart Guide reuse existing Tools/Workbench surfaces.

## 7. Current application of this gate

| Capability | Current evidence | Qoder/delivery action |
|---|---|---|
| ENG-11 Activity Status Update | Contract packet exists in #2010; Team Member source partially verified; some child topics remain MISSING / VERIFY | Keep documentation-only until actuals/activity/authorization/UI path owners hand off; then create a separate implementation PR |
| ENG-12 Timesheets | Contract packet exists in #2010; Team Member submit/withdraw/opening topics verified; EPPM project-side approval/privilege details remain MISSING / VERIFY | Separate implementation PR from ENG-11; do not overload activity-period actual API |
| ENG-10 Field Work Plan / Last Planner | Capability is in the master scope; connected workflow remains MISSING / VERIFY | Next source/contract candidate after ENG-11/12 source closure; keep distinct from Enterprise generic Task |
| ENG-04 Scenarios / Compare / Promotion | Issue #1989 and schedule/shell collisions exist | Wait for schedule path owner handoff; reuse authoritative scheduler |
| ENG-05 Schedule Health / Quality | Quality-audit implementation evidence and #1711 overlap exist; generic shell is not proof of full parity | Reconcile implementation and source acceptance against #1711 before enabling new controls |
| ENG-09 Monte Carlo / Quantitative Risk | Separate model/run/result contract not yet verified | Contract separately; consume Engineering schedule/risk facts; no second CPM |
| Resources / Risk foundations | Existing read/write foundations exist by operation, not full parity | Continue operation-by-operation parity verification after #1974/#1983 handoff |

## 8. Current non-interference snapshot

Main was confirmed at `0fc0d80ece1d3f495564fa20e32d6f2f21f10a1b` during this audit. The following PRs were re-fetched as open:

- #2008 (draft, docs-only architecture).
- #1974 (draft; broad identity, project lifecycle, P6 APIs, Risk, schema, production composition and `apps/web/src/main.ts`).
- #1983 and #1980 (OBS/WBS authorization, workspace model/view/contracts, Risk/activity APIs and schema).
- #1711 (schedule quality audit, authoritative schedule query, Engineering shells, `main.ts`, CSS and interchange).
- #1971 (identity/invitations and authoritative schedule query/evaluator/checks).
- #2006 (ENT-13 claim-party membership and schema).
- #2001 (draft; canonical capability register and ENT-13 source/architecture records).
- #1929 (draft; Enterprise Task domain/contracts).

Changed-file lists were refreshed for these PRs. Treat the following as occupied/protected until explicit handoff: `apps/web/src/main.ts`, workspace model/view/contracts/styles and Engineering shells, authorization, identity/session, production composition, deployment schema/migrations, P6 activity/actuals/baseline/resource/risk APIs, authoritative schedule query/evaluator/checks, interchange and canonical capability register.

This is a snapshot, not a permanent ownership assignment. Refresh PR heads and changed-file lists immediately before any code write. The documentation-only branch is not a substitute for the canonical checkout's root/nested `AGENTS.md`, continuity protocol or state ledger; those must be read locally before Qoder starts.

## 9. Stop / go decision

**GO** only when:
- Qoder is available and accepts the task;
- the contract and source crosswalk are complete enough for the targeted operations;
- exact target paths are disjoint from active PRs or a named owner has handed them off;
- root/nested repository instructions and state ledger are read;
- acceptance tests and expected evidence are named.

**STOP** if:
- a target path is occupied or ownership is ambiguous;
- an API/data/calculation owner is unclear;
- a required source topic is unresolved for the behavior being implemented;
- a task would duplicate an existing owner/engine/menu/store;
- Qoder is unavailable;
- a proposed change would alter Jalal 5 weights/progress, merge/deploy, or protected shared core without explicit approval.

## 10. Required status update template

Every capability issue must maintain this compact status:

- **Capability / register ID:**
- **Lifecycle state:**
- **Normative Help topics + unresolved gaps:**
- **Current implementation evidence (per operation):**
- **Menu/access placement:**
- **Qoder issue / task owner / branch / PR:**
- **Base SHA / current head SHA:**
- **Allowed paths / forbidden paths / handoff owner:**
- **Tests and exact-head results:**
- **Visual/behavior parity evidence:**
- **Blockers and next unblock action:**
- **Release evidence:**

This gate is additive to the existing architecture, Qoder resumption and capability-register policies. It does not authorize application code changes, PR merges, deployments or schedule-weight changes.
