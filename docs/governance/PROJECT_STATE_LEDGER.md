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

## Current Jalal 5 execution baseline and caveats

- [Jalal 5 schedule/governance PR #1484](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1484) remains **open/draft and unmerged**. This ledger and the detailed execution baseline are still proposals until reviewed/merged. Verify live SHA and CI at every new session.
- **Latest proposed integrated baseline:** [Jalal 5 execution baseline](../roadmap/JALAL5_EXECUTION_BASELINE_2026-10-18.md) plus workbook `/Schedules/Jalal5_Weighted_Master_Schedule_2026-10-18_EXECUTION-BASELINE.xlsx` in the user Library (19 sheets; not yet committed as a binary to this PR). Workbook covers 144 tasks, dependency/lag register, Mobile V1, owner lanes, CI wait-window tasks, release gates, and 70-week Gantt.
- Baseline inputs: 144 tasks = 130 existing-scope rows + 14 required Native Mobile V1 rows; total weight = 100.00 points, provisionally 85 points to existing scope and 15 to Mobile V1; provisional remaining effort = 635.24 person-days; 360 dependency edges (353 FS / 7 SS). The model has primary-owner no-overlap checks and cross-owner parallel work where predecessors permit. The proposed calendar is Monday–Friday with no separate public-holiday calendar, 80% effective focus, and planned start 2026-10-19.
- **Forecast (not commitment):** modeled finish 2028-02-04 (week 68; 474 calendar days from 2026-10-18); management target 2028-02-18 (week 70; 488 calendar days) includes a separate 10-working-day reserve. Owner loads are Jalal 183.90 PD / 45 rows; Hasan 193.64 PD / 41 rows; Farmj 257.70 PD / 58 rows. Farmj is the bottleneck at about 94.7% of the modeled capacity, so any reassignment or new work requires recalculation.
- **Approval caveat:** 85/15 weight split and initial Mobile effort (94.5 PD) are proposed pending owner acknowledgement; assumptions do not prove a committed date. The detailed J4→J5 workbook crosswalk still requires explicit owner acceptance/reconciliation. No schedule progress transfers by default.
- **Current earned progress: PENDING / NOT CERTIFIED.** No new percentage should be announced from documentation, modelled tasks, open PRs or green unrelated checks. Product credit requires merged current-main implementation, fresh exact-SHA checks, runtime/behavior acceptance and row-level traceability.
- **Critical fresh CI finding:** current PR #1487 head is `84f0694a6bee54e1a228ba35b21c6d545cd7f1e2`. Client Typecheck and PostgreSQL Integration pass, but ConstructionPM CI fails on Python 3.11/3.12/3.13. Python 3.11 reports **2 failed, 2,525 passed, 90 skipped**:
  1. `tests/scheduling/test_authoritative_schedule_batch.py::test_shared_resource_leveling_runs_once_for_the_batch_graph` — final R1 demand 2 vs capacity 1 on 2026-10-02.
  2. `tests/scheduling/test_public_forward_backward_leveling.py::test_public_backward_leveling_moves_linked_activities_without_breaking_ss` — start-no-later-than constraint violation for B.
  This is the active blocker; do not merge or mark it done. Previous SHA `075a6dbefa48fb35a3366e652dddfb4c2cdc03a7` had 19 failures and is stale for current reporting.
- [P6 documentation-first gate #1447](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1447) is mandatory for scheduling, relationships, calendars, constraints, leveling, formulas and numerical AI: exact official/versioned source section → source-derived rule/edge cases → regression test → independent review before semantic code changes. Unknown semantics remain UNVERIFIED/BLOCKED; do not guess or weaken validators.
- Team instruction is recorded in [#1486](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1486) and repeated against the current blocker in [#1476](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1476) and [PR #1487](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1487): Hasan owns the fix; Farmj performs independent conformance/review without conflicting implementation edits; Jalal maintains schedule/actuals. Explicit team acknowledgement is **not yet evidenced** by an acknowledgement from each assignee.

## Active governance/verification items (refresh live)

| Item | Current verified status | Required next action |
|---|---|---|
| [#1486 Mobile V1 + continuity gate](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1486) | Open; assigned to Jalal, Hasan and Farmj; directive posted; individual acknowledgement not yet evidenced | Confirm each owner's activity lane/estimate/next action; accept Mobile V1 estimates/weights; reconcile workbook and J4→J5 crosswalk; update forecast on actuals. |
| [PR #1484 Jalal 5 master schedule](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1484) | Open/draft; contains the proposed execution-baseline document; unmerged | Review/accept the 144-row model, workbook consistency, assumptions, exact 100.00 weights and crosswalk; keep progress pending until accepted. |
| [#1476 / PR #1487 scheduler blocker](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1476) | Open; latest PR head `84f0694a6bee54e1a228ba35b21c6d545cd7f1e2`; two exact-head CI failures remain | Hasan fixes resource overload and backward SS feasibility at root cause; add regressions; targeted + full relevant CI across Python 3.11–3.13; Farmj independently reviews same SHA. |
| [#1483 P6 parity matrix](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1483) | Open; shared with Hasan/Farmj | Complete independent relationship FS/SS/FF/SF, lag/lead, calendars, priority/tie-break, infeasible-window and aggregate resource-ledger coverage. |
| [PR #1477 leveling CPM candidate](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1477) | Open; green CI claim is not complete parity acceptance; latest stored body has stale older SHA reference | Refresh latest SHA and checks; finish independent review, calendar/priority/infeasible-window matrix; do not infer full parity from green CI. |
| [PR #1485 snapshot identity validation](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1485) | Open; exact-head state not refreshed in this pass | Refresh current head/checks and review result before relying on it. |
| [#1462 persisted Activity Master write/read](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1462) | Release blocker in J5 plan | Prove write→commit→fresh-read into immutable authoritative schedule input; attach database/runtime evidence. |
| [#1423 AI end-to-end slice](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1423) and [#94 Desktop offline inference](https://github.com/consttruction-pm/consttruction-pm-platform/issues/94) | Not accepted by schedule documentation alone | Verify real end-to-end Web tools and real no-network Desktop inference. |
| [#1436 site route/SEO graph](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1436), [#1428 all-language acceptance](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1428) | Execution requirements; implementation acceptance not proven here | Verify actual built web artifact, route graph and supported-language behavior. |

Repository enforcement aids proposed on PR #1484: [root `AGENTS.md`](../../AGENTS.md), [PR checklist](../../.github/pull_request_template.md), and [task/decision issue template](../../.github/ISSUE_TEMPLATE/jalal5_task.yml). They improve consistency but do not prove that contributors read them; reviewer verification is still required.

## Next task sequence

1. **Close the two active #1476/#1487 CI failures.** Hasan implements one root-cause fix at a time and posts candidate SHA; Farmj prepares a source-backed matrix in parallel without editing the implementation branch, then independently reviews the exact tested SHA.
2. **Use CI wait time for non-conflicting work.** Every owner takes the next available workbook task in `CI Wait & Closure`; waiting itself is not progress and the same implementation files must not be edited concurrently without an explicit coordination decision.
3. **Obtain explicit acknowledgement from each owner in #1486.** Each person states task/activity IDs, estimate, predecessor/dependency, current action, and the expected evidence they will report. Do not infer acknowledgement from assignment or a comment mentioning their username.
4. **Review and accept the detailed schedule.** Verify workbook formulas, integrated 144-row denominator, exact 100.00 weights, 360 dependency edges/lag units, no within-owner overlap, owner capacity, schedule dates, Mobile V1 work, and row-level J4→J5 crosswalk. Any changed estimate/assignment must trigger forecast recalculation.
5. **Refresh other release gates (#1462, #1423, #94, #1436, #1428 and #1485) from live exact-SHA/runtime evidence** once the scheduler blocker is under control; prioritize tasks that can safely proceed in parallel with the blocker.
6. **Earned progress only after acceptance.** Record actual start/finish, actual person-days, final 40-character SHA, commands/counts, reviewer decision and evidence links. Update the workbook after the owner submits those facts; no progress credit for comments, drafts, planned tasks or stale CI.
7. **Merge governance PR #1484 only after** its documentation/workbook/weighting/crosswalk contradictions have been reviewed and resolved. Until merged, this ledger remains a proposed-branch handoff, not main's authoritative file.

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


## Resource-leveling / P6 conformance handoff — 2026-10-19

Preflight:
- Current `main` SHA verified by GitHub: `9945856c8f2c40453cc0b0414c1f89600228348a`.
- Read `README.md`, `AGENTS.md`, the proposed continuity protocol and this proposed ledger, Jalal 5 execution baseline, and the authoritative 19-sheet workbook in the user Library. These governance files are still on the unmerged Jalal 5 PR branch, not accepted `main`.
- Oracle P6 Professional Help Version 26 confirms that resource leveling must fit demand within availability, priority rows are considered in configured order, selected-resource scope is supported, and clearing “Preserve scheduled early and late dates” invokes a backward leveling pass (official source: https://docs.oracle.com/cd/G48897_01/p6help/en/91573.htm; https://docs.oracle.com/cd/G48897_01/p6help/en/91739.htm; https://docs.oracle.com/cd/G48897_01/p6help/en/91740.htm).

Fresh scheduler code/test evidence:
- PR #1477 remains open and unmerged. Source/test head `b350156fa8d1ffbe651478feb97a24f2f6658f2a` passes ConstructionPM CI (run https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/39189550470; Python 3.11/3.12/3.13), Client Typecheck (https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/39189550298; web/desktop/mobile/client-sync), and PostgreSQL Integration (https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/39189550280).
- Additional source/test commits on #1477: `10dbb1b96e9f40829568f626c1ceffcce5f80f7b` passes the activity-calendar resolver map into backward candidate load validation; `c0a29da3e9d4b38ab3a6a986fa48cc036afd65ef` adds the resolver propagation regression; `0e5b656b109df6849d22377850b662b3e7188e48` preserves proposal/priority order for equal-advance candidates; `b350156fa8d1ffbe651478feb97a24f2f6658f2a` adds the stable-order regression.
- The latest live #1477 head is now `15a4ec5d4f0bcea049997830fed5c7ed091d715c`, a documentation-only refresh after the passing code/test SHA. At the time of this ledger update, no workflow run/status was returned for this docs-only head; the green runs above are attributed to `b350156...`, not to `15a4ec5...`.
- The older calendar-only PR #1487 remains open/Draft at `84f0694a6bee54e1a228ba35b21c6d545cd7f1e2`, whose recorded ConstructionPM CI failed on shared-resource overload and backward SS feasibility. Do not claim that #1487 is fixed by its own head; use #1477 as the current scheduler-candidate branch and reconcile/close the duplicate only after review.
- PR #1457 remains open/Draft on `bdd1d6c8a30dde3c207f06987f33ba0bd044a18d`; ConstructionPM CI (run 39083278773), Client Typecheck (run 39083278784) and PostgreSQL Integration (run 39083278778) passed on that exact SHA. It contains the broader P6 priority-value/provenance/persistence path, but has not been reconciled with the activity-calendar resolver work in #1477.

Current acceptance status: **IMPLEMENTED — UNVERIFIED for product release; full P6 parity OPEN / NOT CERTIFIED.** Passing tests on an open branch do not equal merged current-main acceptance. No Jalal 5 product-progress points are earned from this work yet.

Remaining integration gates:
1. Reconcile #1477 calendar-aware CPM/resource validation with #1457's distinct Project Leveling Priority, Activity Leveling Priority, duration criteria, Project Planned Start and Planned Finish provenance. Avoid merging parallel/conflicting scheduler implementations.
2. Run final ConstructionPM CI on Python 3.11/3.12/3.13, client typecheck, PostgreSQL integration and focused resource-leveling tests on one identical final SHA after that integration.
3. Complete independent Farmj semantic review of priority order/ties, selected-resource scope, project-level multi-project priority, FS/SS/FF/SF × negative/zero/positive lag, activity/resource/lag calendars, infeasible windows, final floats/dates and aggregate period-by-period resource demand.
4. Verify the merged current-main SHA after acceptance and update the master workbook/state ledger with exact evidence. Do not increase weighted progress before this gate passes.
