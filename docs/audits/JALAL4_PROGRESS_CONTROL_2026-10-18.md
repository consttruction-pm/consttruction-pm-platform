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


## Workbook control-flow fix — verified 2026-10-18

A refreshed working workbook was created from the detailed 58-activity Jalal 4 schedule: `Jalal4_Weighted_Master_Schedule_2026-10-18_ProgressControl.xlsx`.

The new **Progress Control** sheet fixes the operational gap between a static activity snapshot and a weighted roll-up:

- It keeps each previous completion fraction and evidence URL in an activity-by-activity review queue.
- Column G accepts a candidate new completion fraction; column K must be set to `Accepted` before it affects the calculation.
- Column H computes effective completion only when the candidate is nonblank and the status is `Accepted`; otherwise it retains the previous recorded completion.
- `Master Schedule` completion column H now reads from that effective control value; earned weight/remaining weight and Dashboard totals remain formula-driven.
- The Assumptions text that incorrectly reported 48.58% was corrected to distinguish the last detailed 48.13% snapshot from current certification status.
- Validation simulation passed: entering 95% for a 2-point activity while pending left overall completion at 48.13%; marking that row Accepted recalculated to 48.23%; clearing the candidate and returning to Pending restored 48.13%.
- Formula-error scan returned no `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?` or `#N/A` matches.

This is a **controlled, evidence-gated workbook workflow**, not a live GitHub API sync. The current number remains the last calculated snapshot, 48.13%, because no new row has yet been recertified and accepted. The current certified figure for 2026-10-18 remains pending; this workbook change does not create implementation credit.


## Dashboard category completeness check — 2026-10-18

A second workbook reconciliation found that the overall activity matrix correctly totaled 100 weighted points, but the Dashboard's workstream breakdown listed only 12 of the 13 distinct workstream labels. It omitted the 1-point `G · امنیت و چندمستاجری` workstream. The overall 48.13% did not change, but the workstream display summed to only 99 points and was incomplete.

The refreshed workbook adds this missing row with SUMIF-linked formulas. Verification now shows:
- Dashboard workstream weights: **100.00**
- Workstream earned points: **48.13**
- Workstream remaining points: **51.87**
- Formula-error scan: **0 matches**
- Evidence-gated input simulation remains green: pending input ignored; accepted input recalculates; clearing input restores the prior snapshot.

This is an additional reporting-integrity repair; it does not create product-code credit or change the last computed detailed progress snapshot.


## Source-to-model conformance blocker discovered — 2026-10-18

The current Jalal resource-leveling candidate has a new source-backed blocker, tracked in [Issue #1447](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1447), [PR #1457](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1457), and its matrix row **RL-P6-08**:
- Release 26 Project REST exposes `LevelPriorityList` / `LevelResourceList` as resource-leveling project settings; it describes the former as the ordered criteria used to level resources and the latter as the resources to level.
- The distinct ScheduleOptions REST object exposes `PriorityList` / `ResourceList` as scalar strings without the same resource-leveling description.
- Release 26.4 Integration API shapes differ too: Project `getLevelPriorityList()/getLevelResourceList()` return `String`, while ScheduleOptions `getPriorityList()/getResourceList()` return `String[]`.
- Candidate `scheduling/leveling_boundary.py` currently maps ScheduleOptions `priority_list/resource_list` into the Shared Core leveling boundary. The chosen object/profile, canonical storage, scalar-string encoding and lossless round-trip remain unverified. This is an established contract ambiguity, not yet a proven runtime defect. No mapping/encoding should be guessed; an independent semantic review and authoritative read/write/read fixture are required.

Official source links:
- [Project REST GET](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-project-get.html)
- [Update Project REST](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-syncservice-updateproject-put.html)
- [ScheduleOptions REST GET](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-get.html)
- [ScheduleOptions REST PUT](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-put.html)
- [P6 Integration API Project](https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/Project.html)
- [P6 Integration API ScheduleOptions](https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/ScheduleOptions.html)

Candidate evidence current as of 2026-10-18: matrix update commit `bdd1d6c8a30dde3c207f06987f33ba0bd044a18d`; ConstructionPM CI run `39083278773` passed on Python 3.11, 3.12 and 3.13; Client Typecheck run `39083278784` passed for web, mobile, desktop and client-sync; PostgreSQL Integration run `39083278778` passed. These are exact-head checks for the current candidate SHA. Keep #1457 Draft/unmerged because the source-to-model mapping, lossless field round-trip, independent semantic review, and production immutable input composition gates remain open. Do not increase weighted progress on this documentation/conformance finding.
