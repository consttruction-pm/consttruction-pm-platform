# Jalal 4 Progress Control — 2026-10-18

**Status: reconciled as a control finding; full current-main activity-by-activity recertification remains open.**

## Authoritative baseline and what the percentage means

- Repository/default branch: `consttruction-pm/consttruction-pm-platform`, `main`.
- Main HEAD inspected on 2026-10-18: `350c230064ff0052bb2f34bc2c16775c332d4ba9`.
- The last detailed 58-activity Jalal 4 workbook snapshot is dated 2026-10-13. Its Dashboard/weighted-contribution arithmetic is **48.13 / 100 complete; 51.87 / 100 remaining**. This is the last computed detailed Jalal 4 schedule snapshot, **not a newly certified percentage for 2026-10-18**.
- The workbook's Assumptions sheet also contains a conflicting 48.58% statement. The prior reconciliation recorded that its detailed contribution column sums to 48.13%; until the source workbook is corrected and revalidated, 48.58% must not be reported.
- The earlier 56.50/100 in PR #1425 came from a coarse 16-package, carry-forward proposal and was explicitly provisional. It is not a substitute for the detailed 58-activity workbook figure. The differing numbers arise from different granularity and completion estimates, not from a verified earned-progress increase.
- Jalal 3's 59.50% is historical and must not be presented as Jalal 4 or as today's current progress.

## Root cause: why the reported percentage appears stuck

1. **The tracker is a dated snapshot, not a live progress calculation.** The workbook was last reconciled on 2026-10-13; GitHub merges, exact-head CI and acceptance evidence are not automatically mapped back into its 58 weighted activities.
2. **The in-repository live pointer remained on Jalal 3.** `docs/audits/CURRENT_MAIN_AUDIT_POINTER_2026-10-12.md` still points to the older Jalal 3 matrix and an earlier main SHA. Issue #680 requires one reconciled, in-repository baseline; that requirement was not fully closed.
3. **The Jalal 4 proposal was not made authoritative.** PR #1425 remains open/unmerged and its 56.50 figure is provisional. Open PRs cannot earn weighted completion.
4. **The most visible scheduling lane is not release-accepted.** Current-main ConstructionPM CI run [38966482644](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/38966482644) is red across Python 3.11, 3.12 and 3.13 with the same two failures:
   - `test_shared_resource_leveling_runs_once_for_the_batch_graph`: final resource over-allocation (R1, demand 2 vs capacity 1.0).
   - `test_public_backward_leveling_moves_linked_activities_without_breaking_ss`: START_NO_LATER_THAN violation for activity B.
   The final-resource-load and explicit-constraint validations must remain fail-closed; the failing tests cannot be hidden to create a higher score.
5. **The production resource-leveling write/read path is not yet demonstrated end-to-end.** Issues [#1462](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1462) and [#1468](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1468) remain the relevant gates. PRs #1457/#1469/#1470 and related scheduling branches are open or Draft; their code, tests and PostgreSQL passes must not be treated as merged production acceptance.

## Correct reporting rule from this point

- Report **48.13%** only as “last computed Jalal 4 detailed snapshot — 2026-10-13”; remaining **51.87%**. Do not label it newly verified on 2026-10-18.
- Current certified progress on 2026-10-18: **not yet freshly recertified**. Do not invent a replacement number.
- On each main merge, compare the changed capability with the specific Jalal 4 activity acceptance criteria. Update only that activity when its relevant implementation is merged and its exact-head checks/required runtime evidence pass; prevent duplicate credit for shared work.
- Every refreshed report must record: cut-off date; main SHA; workbook/matrix version; activity ID, owner, weight, prior completion, new completion, evidence URL and exact tested SHA; weighted arithmetic; owner subtotals; remaining blockers. The total must be recalculated from the activity rows, not edited by hand.
- Keep separate indicators for overall Jalal 4 delivery, Web Beta, Shared Core/P6 semantic conformance and release readiness. They have different denominators and must not be blended.

## Action owners / next acceptance

- **Jalal:** maintain the approved weighted scope and P6 semantic acceptance criteria; reconcile the 58-activity matrix against current main and reject duplicate credit.
- **Hasan:** reproduce and fix both main CI scheduling failures with minimal semantic changes; demonstrate Activity Master → committed persisted state → fresh read → immutable, revision/hash-bound schedule and resource-leveling inputs.
- **Farmj22002 (Farmj):** independently review backward constraint/calendar/resource-demand semantics against issue #1447 and verify the immutable-input/wire mapping gates in #1468.
- **Team acceptance gate:** do not increase the score for resource leveling until the final resource-demand ledger and constraints pass the full Python matrix on the exact tested SHA and the authoritative production composition is demonstrated.

This control update fixes the **reporting-governance gap**; it does not claim a scheduling-code fix, a PR merge, or a new implementation-progress increase.
