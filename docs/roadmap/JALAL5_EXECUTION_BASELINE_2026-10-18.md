# Jalal 5 execution baseline — 2026-10-18

**Status: proposed executable rebaseline; pending owner acknowledgement and P6-source acceptance gates.** This corrects the earlier pre-Mobile scope. Native Mobile is mandatory in V1 alongside Website and Desktop.

## Baseline numbers

| Measure | Current model |
|---|---:|
| Integrated activities | 144 (130 existing + 14 Native Mobile V1) |
| Total activity weight | 100.00 points (85.00 existing scope + 15.00 Mobile V1) |
| Provisional remaining effort | 635.24 person-days |
| Dependency edges | 360 |
| Relationship mix in current plan | 353 FS, 7 SS |
| Calculated finish | 2028-02-04 (week 68) |
| Management target, including separate 10-working-day reserve | 2028-02-18 (week 70) |
| Calendar days from snapshot 2026-10-18 to calculated finish | 474 |
| Calendar days from snapshot 2026-10-18 to management target | 488 |

**These are schedule-model outputs, not a guarantee or earned-progress claim.** The 85/15 weight split is the proposed control policy; owners must acknowledge estimates and weights. The 14 Mobile estimates total 94.5 PD and are first-pass estimates pending device/API/test-matrix review. Existing effort is re-estimated only where identified; B08 retains a provisional 12 PD pending Hasan's next triage and owner re-estimate. The live CI has since improved from the earlier 19-failure result to two remaining failures on head 84f0694a6bee54e1a228ba35b21c6d545cd7f1e2.

## Estimate and resource assumptions

- Planned work start: 2026-10-19.
- Planning calendar: Monday–Friday, five working days/week; no public holidays are separately modeled.
- Duration model: remaining person-days divided by 0.80 effective focus for the primary owner (four effective PD per owner-week).
- One primary owner does not execute two assigned tasks at the same time. Tasks assigned to different owners may overlap when predecessor constraints permit.
- Each task keeps the predecessor relations, lag unit, dates, owner, acceptance rule, evidence state, and schedule row ID in the attached execution workbook. All 360 edges passed the model's FS/SS/FF/SF relation-bound checks; the current modeled mix is 353 FS and 7 SS. Non-zero positive working-day lags are explicit on Native Mobile V1 items.
- This is a delivery-planning precedence/resource-lane model, not proof that CUBI's scheduling implementation is P6-conformant. Issue #1447 remains the mandatory documentation-first gate for product calculation semantics.

## Owner lanes and principal risk

| Primary owner | Activities | Provisional effort | Load against 68-week baseline capacity (272 PD) |
|---|---:|---:|---:|
| Jalal | 45 | 183.90 PD | 67.6% |
| Hasan | 41 | 193.64 PD | 71.2% |
| Farmj22002-droid | 58 | 257.70 PD | 94.7% |
| **Total** | **144** | **635.24 PD** | |

Farmj's lane is the bottleneck. Do not quietly assign more primary work to this lane; any estimate or ownership change must trigger a schedule/forecast recalculation and a recorded risk decision. The 10-working-day reserve is separate from weighted work and cannot be used to hide unresolved P0 blockers.

## Parallel work / CI wait-window rule

- **Hasan — implementation lane:** Own B08 / Issue #1476 / PR #1487. Diagnose the full current failure list, map fixes to the source-backed semantics, implement the root-cause correction, add regression tests, and run the targeted tests plus the full Python matrix and relevant client/database checks on the exact final SHA. While the next CI run is executing, inspect logs and prepare a minimal evidence-based correction plan; do not stack unexplained changes.
- **Farmj — independent conformance/review lane:** While Hasan is implementing/running CI, work on the independent P6 source-rule/edge-case/test acceptance matrix for backward SS feasibility, signed working-day displacement, shifted resource-demand periods, mixed/activity calendars, shared batch graph, priority/tie-break rules, and infeasible windows. Avoid concurrent edits to the same implementation branch/files. After a candidate SHA is available, inspect that exact diff and its fresh CI, then record independent pass/fail findings.
- **Jalal — programme/control lane:** Reconcile the J4→J5 crosswalk and task actuals; validate 85/15 weighting and Mobile V1 scope; keep this schedule/workbook consistent with live GitHub issues/PRs; update the forecast only from recorded owner actuals and accepted changes.

A CI wait period is not idle time: use a non-conflicting work item in the workbook's **CI Wait & Closure** sheet. Waiting alone, comments, documentation-only work, open PRs, mocks, or stale CI results earn zero product-progress credit.

## Mandatory defect-to-acceptance rule for every team member

Any error discovered in a person's assigned area must be owned and followed to full correction—do not merely report it, assign it away, or stop after a local test passes.

1. Link the defect to a Jalal 5 task row and GitHub issue/PR; preserve reproduction steps, inputs, logs, and the exact starting SHA.
2. For scheduling, relationships, calendar logic, constraints, resource leveling, numerical outputs, and AI scheduling claims, apply Issue #1447 first: cite the exact official/versioned source section; record the source-derived rule and edge cases; link regression tests before semantic code changes. Unclear rules remain **UNVERIFIED/BLOCKED**—do not guess.
3. Fix the root cause and include a regression that reproduces the failure before the fix and passes after it. Run targeted tests and all relevant CI/checks on the final exact SHA. Do not weaken tests/validators, swallow exceptions, fabricate a feasible result, or use an unrelated green check as acceptance.
4. A different reviewer records independent acceptance where the task requires it. For #1476, Hasan implements; Farmj independently verifies; Jalal records programme acceptance after evidence is complete.
5. Then report actual start and finish, actual effort, exact SHA, test commands and pass/fail/skip counts, reviewer/decision, and evidence URLs. Jalal updates the workbook with actuals and accepted status. If any criterion is outstanding, status remains **In progress** or **Blocked**, not Done.

### Required completion report

`Task ID | Issue/PR | Actual start (ISO local time) | Actual finish (ISO local time) | Actual effort PD | Final SHA | exact commands + results | reviewer + decision | evidence links | Accepted/In progress/Blocked | remaining action/owner`

## Current blocking evidence

PR #1487 remains Draft/unmerged. **Current exact head:** `84f0694a6bee54e1a228ba35b21c6d545cd7f1e2`. Client Typecheck and PostgreSQL Integration passed, but ConstructionPM CI failed on Python 3.11/3.12/3.13. Python 3.11 reports **2 failed, 2,525 passed, 90 skipped**: (1) `tests/scheduling/test_authoritative_schedule_batch.py::test_shared_resource_leveling_runs_once_for_the_batch_graph` — final resource demand R1=2 vs capacity 1 on 2026-10-02; (2) `tests/scheduling/test_public_forward_backward_leveling.py::test_public_backward_leveling_moves_linked_activities_without_breaking_ss` — start-no-later-than constraint violation for B. Exact run: https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/39104945732. The earlier 19-failure report on `075a6dbefa48fb35a3366e652dddfb4c2cdc03a7` is historical, not current. Do not merge or mark B08 complete until both failures and relevant regressions are resolved, exact-SHA gates pass, and independent review is recorded.

## Workbook authority

The accompanying `Jalal5_Weighted_Master_Schedule_2026-10-18_EXECUTION-BASELINE.xlsx` is the detailed task-level control artifact. It includes the 144-row master schedule, formulas and assumptions, workstream summary, 360-edge dependency/lag register, owner-lane overlap checks, CI wait-window/closure obligations, release milestones, and 70-week Gantt. The file is generated for this handoff but has **not** been merged into the repository; PR #1484 remains Draft. Reconfirm the workbook after each accepted owner estimate/actual change before calling the baseline final.
