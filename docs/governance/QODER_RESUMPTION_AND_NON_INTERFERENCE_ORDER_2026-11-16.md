# Qoder Resumption, Engineering Contract & Non-Interference Order

**Recorded:** 2026-11-16  
**Canonical coordination issue:** #2009  
**Architecture contract:** `docs/architecture/CUBI_ENGINEERING_CAPABILITY_MENU_ACCESS_AND_PATH_OWNERSHIP_V1.md`  
**Repository snapshot used for the initial collision audit:** `main` = `0fc0d80ece1d3f495564fa20e32d6f2f21f10a1b`  
**Status:** coordination/documentation only; no application code changes in this record.

## Executive order

The prior performance optimization work remains registered in #1992 and is not reopened by this queue. The next continuation is **Engineering capability contracts, exact menu/access placement, path ownership and implementation readiness**, without writes to the Shared Scheduling Core or any path owned by an open PR.

1. Refresh repository instructions, main SHA, all open PR heads/files/CI and exact path ownership.
2. Use the Engineering menu/access contract to finalize domain ownership, versioned APIs, data boundaries, authorization and exact contextual placement.
3. Choose the first Engineering vertical slice only from paths proven disjoint from open PRs and protected core paths. If no safe path set exists, continue Help/source inventory and contract work only.
4. Resume #1989 Scenarios only after schedule/shell path collisions are dispositioned; reuse the canonical scheduler.
5. Continue Field Operations, Team Member/Timesheets, Productivity, Risk/Monte Carlo, technical Delay Analysis, Decisions and Standards as separately contracted slices.
6. Continue Enterprise P2 through its existing canonical issues/PRs after required Engineering read contracts are stable. Do not create duplicate Organization & Access, OBS, claims, task or workflow subsystems.

## Superseded instruction

Earlier text in this queue prioritized Windows Desktop installer/runtime supervision and Mobile portable-runtime feasibility as the next P0 gate. That was not the requested next work and is **superseded for this continuation**. Those items may remain separately tracked, but they are not the current Engineering capability queue. Do not reopen performance optimization phases already recorded in #1992 absent new evidence.

## Capability/menu contract

The canonical placement and access rules are in the architecture contract above. In brief:
- Schedule → Scenarios / Compare / Health.
- Risk → Register / Assessment / Response / Quantitative Analysis / History.
- Resources → Usage / Histogram / Assignments / Leveling.
- Field Operations → Work Plan / Lookahead / Constraints / Daily Huddle / Commitments / PPC / Production & Productivity.
- Activity Details → Team Update.
- Workbench My Work → Timesheets.
- Project Control → Decisions; Project Reference → Standards & Methods; Project Scope → Scope & Work Packages.
- Data Reconciliation and contextual smart guidance reuse existing Tools/Workbench surfaces.
- No top-level menu per Cloud feature; no duplicate route, store, API, owner or calculation engine.
- Each action requires server-derived tenant/actor/project/object scope and distinct read/write/execute/approve privileges. Client hiding is not authorization.

## Current open-PR collision warning (2026-11-16 snapshot)

- PR #2008: documentation only; safe for the new architecture contract on its branch.
- PR #1974: broad Organization & Access, identity, project lifecycle, P6 APIs, Risk, schema, production composition and `apps/web/src/main.ts`.
- PR #1983/#1980: OBS/WBS authorization, workspace model/view/contract, `main.ts`, Risk UI/API, activity/WBS/baseline and schema.
- PR #1711: schedule quality audit, schedule query, Engineering shells, `main.ts`, CSS and interchange.
- PR #1971: identity/invitations and authoritative schedule query/evaluator/checks.
- PR #2006: ENT-13 claim-party membership and schema.
- PR #2001: canonical capability register and ENT-13 architecture/source manifests.
- PR #1929: Enterprise Task domain/contracts.
- #1989: Schedule Scenarios implementation issue; no separate implementation PR confirmed in this snapshot.

This list is not a permanent assignment. Fetch fresh PR file lists before every implementation task. Treat `apps/web/src/main.ts`, shared workspace shells/model/view/contracts, authorization/identity/production composition, deployment schema, authoritative scheduler/snapshot/query/resource-leveling paths and the canonical register as protected until explicit owner handoff.

## Mandatory handoff packet

Every Qoder slice must specify:
- issue and capability/register IDs;
- branch and exact base SHA;
- exact allowed and forbidden file paths;
- owner of every read/write contract and upstream version;
- menu/window/tab/command placement and permission matrix;
- migrations, transaction/revision/idempotency/audit rules;
- focused, integration, negative-authorization and browser tests;
- expected artifacts/evidence and stop conditions.

Only one active task may write any given path set. No overlapping edits, force-pushes, rebases or cherry-picks without owner review. Preserve user changes, existing PR work, P6 behavior, Cloud additions and Jalal 5 weights/progress.

## Execution availability and evidence

Qoder had no available tokens at the last coordination check. Recheck at actual handoff. No code execution is claimed. Documentation, menu proposals and shell labels do not prove implementation. Every implementation claim requires exact-head CI, persistence/security tests, browser/runtime evidence and source traceability. No merge/deployment is authorized here.


## 2026-11-16 — next Engineering P1 slice registered: ENG-11 / ENG-12

The next documentation-first contributor slice is registered as [#2010](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2010), with contract packet `docs/engineering/ENG11_ENG12_TEAM_MEMBER_CONTRACT_AND_HELP_CROSSWALK_V1.md` on this branch.

Scope is deliberately split into two distinct domain aggregates:
- ENG-11 assigned Activity Status Updates and Step Progress → Activity Details → Team Update.
- ENG-12 designated-user Timesheets → Workbench → My Work → Timesheets.

Enterprise generic Task and ENG-10 Field Work Plan commitments remain separate. Existing `p6-activity-period-actual-api.v1` is only the downstream activity-period actual posting boundary, not a timesheet aggregate or approval workflow.

Exact Team Member V26 topics were checked for Updating Activities, Updating Progress on Steps, Working with Timesheets, Opening, Submitting and Withdrawing Timesheets. TOC child pages that could not be retrieved remain explicitly MISSING / VERIFY; they are a pre-code source gate.

No implementation is authorized yet: PR #1974 owns current actuals API/persistence, schema, production composition, identity and main.ts paths; #1929 owns Enterprise Task contracts; #1711/#1971/#1983 overlap activity, workspace, authorization and production paths. Refresh exact path lists and obtain handoff before any write. Qoder token availability remains unverified/unavailable at last check.


## 13. Separate Qoder implementation packets registered (2026-11-16)

The source/contract stage now has three independent implementation packets. They are intentionally **BLOCKED**, not marked ready-to-run, because exact path handoff and Qoder availability are not verified.

- ENG-10 Field Work Plan / Last Planner: [#2012](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2012). Contract: `docs/engineering/ENG10_FIELD_WORK_PLAN_LAST_PLANNER_SOURCE_CROSSWALK_AND_CONTRACT_V1.md`. Core FieldTask/TaskPlan/hand-off/constraint/commitment/completion only; Daily Huddle, PPC and Production & Productivity remain separately gated sub-slices.
- ENG-11 Team Member Activity Status Update: [#2013](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2013). Contract: `docs/engineering/ENG11_ENG12_TEAM_MEMBER_CONTRACT_AND_HELP_CROSSWALK_V1.md`. Assignment-scoped activity/step progress only.
- ENG-12 designated-user Timesheets: [#2014](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2014). Same contract packet, but separate aggregate, approval lifecycle and implementation PR.

All three packets use the refreshed main base SHA `0fc0d80ece1d3f495564fa20e32d6f2f21f10a1b` as the coordination snapshot, require a fresh SHA/PR-path refresh before execution, and explicitly state **allowed write paths = NONE until named owner handoff**. The PR collision audit refreshed open PRs #1974, #1983, #1980, #1711, #1971, #1929, #2001, #2006 and #2008. Shared protected paths remain unavailable without explicit handoff.

No Qoder connector/tool is exposed in the current ChatGPT tool session. Token availability and task acceptance are unverified. Do not claim Qoder has started. If Qoder becomes available, start only after the named owner grants the exact path set and repository instructions/state ledger are read.
