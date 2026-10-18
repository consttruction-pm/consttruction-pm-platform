# CUBI Project State Ledger

**Purpose:** concise, durable handoff point for every new chat, developer task and team review.  
**Status:** proposed on the Jalal 5 governance PR; do not treat this branch copy as merged `main` until PR acceptance.  
**Snapshot date:** 2026-10-18, based on the GitHub evidence linked below.  
**Continuity rules:** [Project Continuity Protocol](PROJECT_CONTINUITY_PROTOCOL.md) · [Mandatory governance issue #1486](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1486).

> This is a verified-at-snapshot index, not a substitute for live verification. At the next session, refresh `main` SHA, PR states, check runs and workbook state before acting. Replace stale facts only with fresh evidence; never infer progress from missing information.

## Binding product decisions

1. **V1 includes Website + Desktop + native Mobile.** Mobile is mandatory in V1 and is not deferred to V2. Product-owner instruction is recorded in [Issue #1486](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1486). This supersedes the conflicting mobile-V2 wording in the proposed J4→J5 crosswalk and plan. Historical [Issue #1133](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1133) describes native mobile host/planning scope but its old state/closure does not negate the latest decision.
2. **No duplicate calculation engine in a client.** Web/Desktop/Mobile must use the authoritative Shared Domain/Calculation Core and versioned contracts for scheduling, calendars, resources, progress, costs and EVM. Client UI can present/input facts and invoke authoritative services; it must not redefine calculation semantics.
3. **Calculation parity and source-before-coding are mandatory.** For behavior overlapping the mature scheduling/control baseline, verify relevant source-backed contracts before code; unresolved semantics remain open and need regression fixtures, not guesses.
4. **AI assistant:** Web uses authenticated server-hosted inference; Desktop must support declared local/offline inference with no hidden cloud fallback. Tool actions require permission boundaries, preview/approval, revision/idempotency safety, audit and fresh-read evidence.
5. **Website and every client are multilingual by design.** All declared supported languages, locale-aware user/project data, RTL/LTR, Jalali/Gregorian and localized help/SEO/navigation must be treated as full-scope concerns, not a late cosmetic pass.
6. **Every public website page must satisfy SEO and journey acceptance.** Validate route graph, previous/next/breadcrumb/CTA links, indexability, canonical, metadata, structured data, sitemap/robots and localized alternates; do not index private app/auth routes.
7. **Evidence-based progress only.** Open PRs, documents and planned activities are not product completion. Earned weighted points require applicable implementation merged to current `main`, fresh checks for the exact SHA, runtime/behavior acceptance and updated row-level traceability.
8. **GitHub is the canonical project record.** Material decisions must be stored in issues/decision docs, and every activity must be linked to a stable schedule row plus issue/PR. Conversation memory is secondary.

## Current Jalal 5 baseline and caveats

- [Jalal 5 schedule PR #1484](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1484) remains **open/draft and unmerged** at the last live inspection. Do not rely on a stored head SHA in this ledger; fetch the current PR head and base SHA directly at the start of the next session.
- The proposed plan currently describes 100 weight points, 130 activity rows, a 535.21 person-day proportional residual estimate, a conditional 60-week schedule ending 2027-12-08 (week 60 ending 2027-12-10), and 300 predecessor edges / 127 owner-lane checks. These are **proposed planning-model numbers, not an approved final forecast**.
- Mandatory Mobile V1 expands the scope relative to the old plan/crosswalk. The candidate workbook `/Schedules/Jalal5_Weighted_Master_Schedule_2026-10-18_MobileV1-Rebaseline.xlsx` now has a `Mobile V1 Rebaseline` sheet with 14 candidate activities; the companion [candidate backlog](../roadmap/MOBILE_V1_REBASELINE_BACKLOG_2026-10-18.md) contains their definitions of done and dependency points to validate. These candidate rows still have `TBD` estimates/weights/dates and are not integrated into the main schedule denominator. **The authoritative master schedule is not yet recalculated to include Mobile V1.** Until weights sum to 100.00 after task-level reallocation and owner/dependency/forecast checks pass, the old 130-row/535.21-PD forecast must not be reported as certified.
- The workbook's `Crosswalk جلال۴` fields were previously recorded as unpopulated. The 58-row markdown mapping exists in [crosswalk audit](../audits/JALAL4_TO_JALAL5_CROSSWALK_2026-10-18.md), but owner acceptance and workbook reconciliation remain pending at this snapshot. Confirm current workbook contents directly.
- **Jalal 5 earned progress: PENDING / NOT CERTIFIED.** Do not borrow Jalal 4's historical 48.13% or present it as a new Jalal 5 percentage.

## Active governance/verification items (refresh live)

| Item | Snapshot status | Required next action |
|---|---|---|
| [#1486 Mobile V1 + continuity gate](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1486) | Open; assigned to Jalal and Farmj | Size/accept 14 candidate Mobile V1 rows; integrate into master schedule; recalc weights/dependencies/owner lanes/forecast; verify read-first protocol. |
| [PR #1484 Jalal 5 master schedule](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1484) | Open/draft; unmerged at last inspection | Review updated plan; reconcile workbook and crosswalk; do not count docs as product implementation. |
| [PR #1477 resource-leveling CPM correction](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1477) | Open at the last audit; current-head checks had a green reported test/typecheck/PG run | Confirm live exact head and checks, complete independent review plus calendar/priority/infeasible-window parity matrix before certification. |
| [PR #1485 snapshot identity validation](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1485) | Open; latest validation checks were pending at the last audit | Refresh checks on exact head and inspect review result. |
| [#1462 persisted Activity Master write/read](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1462) | Release blocker in Jalal 5 plan | Prove write→commit→fresh-read into immutable authoritative schedule input; attach database/runtime evidence. |
| [#1423 AI end-to-end slice](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1423) and [#94 Desktop offline inference](https://github.com/consttruction-pm/consttruction-pm-platform/issues/94) | AI implementation/release acceptance not proven by the schedule document | Verify real end-to-end Web tools and a real no-network Desktop inference workflow. |
| [#1436 site route/SEO graph](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1436), [#1428 all-language acceptance](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1428) | Execution requirements, not implementation claims | Verify the actual built web artifact, route graph and supported language behavior. |
| [#1476 scheduling blockers](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1476) and [#1447 source-before-coding gate](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1447) | Explicit release gates in Jalal 5 plan | Refresh current-main test status; resolve backward SS/constraint handling and shared resource-load conflicts with authoritative source-backed tests. |

Repository enforcement aids added on the proposed branch: [root `AGENTS.md`](../../AGENTS.md), [PR checklist template](../../.github/pull_request_template.md), and [task/decision issue template](../../.github/ISSUE_TEMPLATE/jalal5_task.yml). They support the read-first protocol but do not prove it was read; reviewer and, if desired, repository-admin branch-protection settings remain necessary for actual enforcement. The PR branch is still a proposal until PR #1484 is reviewed and merged.

## Next task sequence

1. Finish and review the governance PR; ensure README and `AGENTS.md` route contributors to the read-first protocol and state ledger.
2. Size the 14 Mobile V1 candidate rows, integrate accepted tasks into the main weighted schedule, reallocate exactly 100.00 points, update release-gate cross-references, and recompute dependencies, owner lanes, formulas and forecast. Keep the Jalal 3 mobile 20-point figure as a reference only, not a predetermined weight.
3. Populate and review the complete J4→J5 workbook crosswalk; accept or reject mappings explicitly per row; grant no progress transfer by default.
4. Refresh active PRs/issues/checks and inspect current-main code before making implementation claims.
5. Start with the highest-impact implementation/release blocker after the schedule and current evidence are reconciled.

## Session handoff template

Copy and fill at every meaningful task boundary:

- **Snapshot date / current-main SHA:**
- **Task / Jalal 5 activity IDs / issue or PR:**
- **Sources read and any inaccessible files:**
- **Changed files and commit/branch SHA:**
- **Exact checks/tests/runtime evidence:**
- **Status:** DECIDED / PLANNED / IN PROGRESS / BLOCKED / IMPLEMENTED—UNVERIFIED / MERGED—VERIFYING / ACCEPTED / SUPERSEDED
- **Progress point change and workbook row(s), if any:**
- **Risks / decisions needed:**
- **Next action:**
