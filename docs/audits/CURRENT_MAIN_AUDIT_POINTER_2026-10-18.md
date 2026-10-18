# Current-main Audit Pointer — 2026-10-18

## Authoritative reporting status

- Repository: `consttruction-pm/consttruction-pm-platform`
- Default branch: `main`
- Product-code SHA audited for this report: `350c230064ff0052bb2f34bc2c16775c332d4ba9`
- Audit-only documentation updates are recorded in the main commit history. They refresh reporting/governance only and do not count as product capability; use the explicit product-code baseline above for implementation-progress comparison.
- Detailed progress control: [Jalal 4 Progress Control — 2026-10-18](JALAL4_PROGRESS_CONTROL_2026-10-18.md)
- Governing reconciliation issue: [#680](https://github.com/consttruction-pm/consttruction-pm-platform/issues/680)

## Jalal 4 — progress status

**Current certified percentage as of 2026-10-18: not freshly recertified.**

The most recent detailed Jalal 4 58-activity workbook arithmetic is dated 2026-10-13:
- Last computed completion: **48.13 / 100**
- Last computed remaining: **51.87 / 100**
- Workbook Assumptions also contains a conflicting 48.58% statement; do not use it until corrected and independently recomputed.
- The earlier 56.50 / 100 value in PR #1425 is a coarser, explicitly provisional 16-package proposal. It is not a verified earned-progress increase over the 58-activity schedule and is not the official current score.
- Jalal 3's 59.50% is a different historical scope and is not comparable to Jalal 4.

Thus the current report must preserve **48.13% as the last computed detailed snapshot** while explicitly labeling today's certification state as **pending current-main, activity-by-activity reconciliation**. Do not silently stamp the old number as freshly verified or fabricate a new one.

## Why the number did not change

1. The workbook is a dated snapshot; GitHub merges, exact-head checks and runtime acceptance are not automatically mapped to activity weights.
2. The 2026-10-12 audit pointer and reconciliation matrix still referenced Jalal 3. The old pointer has now been marked historical; this file is the new current pointer.
3. PR #1425 remains open/unmerged and its provisional 56.50 score must not replace the detailed weighted master schedule without reconciling the differing denominators/granularity and activity-level completion estimates.
4. Main's latest inspected ConstructionPM CI run [38966482644](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/38966482644) fails on Python 3.11, 3.12 and 3.13 with:
   - `test_shared_resource_leveling_runs_once_for_the_batch_graph`: final resource over-allocation (R1, demand 2 versus capacity 1.0).
   - `test_public_backward_leveling_moves_linked_activities_without_breaking_ss`: START_NO_LATER_THAN constraint violation for B.
5. The production path from persisted Activity Master data to fresh-read, immutable schedule/resource-leveling inputs is still a release gate tracked by [#1462](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1462) and [#1468](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1468). Open or Draft PRs receive zero incremental completion until their relevant changes are merged and validated.

## Reporting rules

- Every percentage must state the metric/scope, weighting version, cut-off date, product-code SHA, matrix version and evidence URLs.
- Recalculate `sum(activity_weight × accepted_completion_fraction)` from activity rows; never edit the aggregate value directly.
- Credit only distinct accepted work mapped to an activity. Count shared implementation once, prevent overlap, and do not use commit counts, open PRs, review comments or isolated component CI as completion.
- Keep separate figures for overall Jalal 4 delivery, Web Beta, Shared Core/P6 semantic conformance and release readiness; never blend their denominators.
- Every refresh records the previous and new completion fraction, weight, acceptance evidence, exact tested SHA, owner and remaining blocker.
- The next valid percentage refresh is due after the 58-activity matrix is reconciled with current main and each adjusted activity is supported by merged, exact-head-verified evidence.

## Owner actions

- **Jalal:** reconcile the 58 activity weights/evidence with current main, preserve P6 calculation-conformance gates, verify no duplicate credit, and publish the weighted arithmetic.
- **Hasan:** correct both scheduling CI failures without weakening final resource-load or explicit-constraint validation; demonstrate transactional persistence → fresh read → immutable revision/hash-bound schedule/leveling inputs.
- **Farmj22002:** independently review the backward movement, constraint/calendar/resource-demand semantics and versioned wire/input-mapping gates.
- **All owners:** keep the report uncertified until the detailed evidence matrix and required checks support the new score.

## Historical pointer

[2026-10-12 audit pointer](CURRENT_MAIN_AUDIT_POINTER_2026-10-12.md) is retained for traceability only. It is a Jalal 3 historical snapshot and no longer governs current reporting.


## Resource-calendar version pinning — follow-up audit (2026-10-18)

This is an audit-only finding, not a product fix or a test result.

### Confirmed source-to-wire gap

The resource assignment currently carries `calendar_id` but no `calendar_version`:

- `src/construction_pm/p6_resource_assignment_repository.py` (blob `6da967f98985549301921be7a5cf79a1578ebe57`): `P6ResourceAssignment`, `_payload`, SQLite schema/queries and Postgres schema/queries omit `calendar_version`. Both persistence implementations therefore cannot round-trip an exact calendar version from the assignment.
- `src/construction_pm/p6_resource_read_api.py` (blob `098d87a04b9f0a2e49c679badcb6f85d84103d7d`): assignment DTO serializes `calendar_id` only, so the read contract also drops version identity.
- `src/construction_pm/p6_resource_capacity_contract.py` (blob `6f3ce2a0d267fb592ac2e287dad7693b26fbc707`): capacity slices identify only `calendar_id`; the resolver receives `Mapping[str, ResourceCalendar]` and derives capacity through the legacy calendar model.
- `src/construction_pm/p6_resource_leveling_read_adapter.py` (blob `fae40d90bb8413158011b1e3e97e2e05f2a7ec6e`): the adapter maps the DTO into an assignment and resolves calendars by ID, without a version-pinned canonical calendar snapshot.

In contrast, `src/construction_pm/calendar_master_repository.py` (blob `61a954c49e0a13b8141ef02ec6f358a370197481`) already models `CalendarMaster.calendar_version` and version-specific repository keys. The missing link is therefore specifically the resource-assignment → read DTO → capacity/leveling input path, not a lack of versioned calendar identity everywhere.

### Safe implementation boundary

Do not infer “latest calendar” for legacy assignments and do not silently substitute the legacy `ResourceCalendar` model in production. A coordinated fix needs to:

1. Add an optional, validated `calendar_version` to resource assignments without shifting existing positional constructor arguments (append the field or update all callers explicitly).
2. Persist/read it consistently in SQLite and Postgres, including migration behavior for existing tables.
3. Include it in the resource read DTO and adapter mapping; reject missing versions on the authoritative production leveling path where exact version binding is required.
4. Resolve the exact versioned CalendarMaster/canonical calendar snapshot using existing inheritance and exception semantics; include calendar ID/version and canonical snapshot hash in immutable leveling input bound to schedule snapshot scope/revision/calculation identity.
5. Add round-trip, migration, DTO, stale-version, SQLite/Postgres parity, and production-composition tests. Verify persisted Activity Master + assignments/periods/calendar → commit → fresh reads → immutable version-bound inputs → leveling and final capacity validation.

### Compatibility and release status

Existing assignment tests instantiate `P6ResourceAssignment` positionally, so inserting a new field before `note` would silently reinterpret callers. Existing adapter tests supply ID-keyed legacy `ResourceCalendar` objects and do not prove version-pinned production composition. No product code or tests were changed by this audit entry; no new test execution is claimed. Issue #1468 remains open and PR #1457 remains Draft until the production path and exact-head evidence meet the acceptance criteria.
