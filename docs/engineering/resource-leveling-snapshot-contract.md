# Resource-Leveling Snapshot Contract (Implementation Gate)

Status: **design contract; implementation and conformance tests remain blocked**  
Baseline inspected: `main` at `f64b8689a9327f53c9a2a5cbb1b1ffb3cc14450e`  
Related work: Issues #1462, #1468, #1447.

## Problem statement

The authoritative query provider evaluates a `ScheduleInputSnapshot` and `CalculationContext`, but does not supply `SchedulerLevelingInput`. The evaluator correctly rejects a leveling request with `SCHEDULE_LEVELING_INPUT_REQUIRED`. The persisted-input composer also rejects resource assignments that are not bound to the immutable schedule input. Do not bypass either guard by reading mutable repositories from inside the calculation.

## Required identity and data flow

1. Perform fresh, tenant/project/revision-scoped reads in the application composition boundary.
2. Normalize assignments, assignment-period demand, resource calendars, calendar versions and capacity slices into a deterministic canonical resource-leveling payload.
3. Bind that payload to the same tenant ID, project ID, project revision, schedule snapshot ID, schedule snapshot hash and calculation identity as the CPM input. The resource payload must have its own canonical SHA-256 hash and explicit schema/version.
4. Persist the companion payload immutably (or embed it in the canonical schedule snapshot). If stored separately, persist a reference containing the companion snapshot ID, schema version, content hash and source project revision in the schedule snapshot before evaluation.
5. On read, verify tenant/project/revision, schedule snapshot ID/hash, calculation identity, schema version, canonical hash and all referenced calendar ID/version/hash identities. Any mismatch must fail closed.
6. Materialize the companion payload into a typed `SchedulerLevelingInput` before calling `evaluate_schedule_snapshot(..., leveling_input=...)`. The evaluator must not query repositories or depend on mutable state.
7. Include the resource payload hash in the calculation-run identity so a change in resource demand/capacity cannot replay as the same calculation.

## Canonical payload minimum

- Contract/schema version.
- Tenant, project, project revision.
- Schedule snapshot ID, snapshot hash and calculation identity.
- Resource assignment IDs, activity IDs, resource IDs, units, units/cost metadata required by the leveling algorithm, and resource calendar ID + version.
- Assignment period values with ISO date, units, assignment ID, activity ID and resource ID.
- Calendar snapshot hashes and normalized capacity slices.
- Explicit leveling horizon start/end and the policy used to derive it from the authoritative CPM schedule.
- Deterministic ordering and duplicate/aggregation rules. Duplicate capacity slices must be rejected; demand aggregation must be specified by assignment/resource/period before implementation.
- Hash algorithm and canonical serialization rules.

## Fail-closed conditions

Use stable machine-readable error codes for missing or mismatched data. At minimum distinguish:
- missing companion snapshot/reference;
- schedule identity or scope mismatch;
- resource payload hash mismatch;
- missing assignment or period row;
- assignment/activity/resource mismatch;
- calendar version/hash mismatch;
- incomplete capacity coverage over the declared horizon;
- duplicate/ambiguous demand or capacity slice;
- unsupported priority field or unavailable authoritative priority value.

Do not silently substitute a calendar by ID when its version/hash differs. Do not infer capacity for unrepresented periods from a default unless the domain contract explicitly defines that behavior.

## Leveling horizon and coverage

The caller-provided `periods` list and dates appearing in demand rows are not, by themselves, proof of complete coverage. Derive a declared horizon from the authoritative CPM windows and leveling policy; validate every selected resource's capacity for every period in that horizon, using the exact versioned calendar snapshot. Document how nonworking days, partial periods, and manual future-period capacity values are represented. No calculation may proceed with unknown capacity in a period that can affect the result.

## Proposed finite-horizon policy for independent review (not yet approved)

P6 v26 documents the movement semantics, but it does **not** define a universal arbitrary date-range cap for the resource leveler. The finite bound below is therefore a CUBI execution-safety contract, not a claim that P6 itself exposes a matching option. Farmj / the independent scheduling reviewer must accept or amend it before production calculation changes.

The companion schema should carry an explicit `horizon_policy_version`, `horizon_mode`, `horizon_start`, `horizon_end`, and the source values needed to reproduce those boundaries. The bounds must be computed before the companion hash is finalized.

### Mode A — float-bounded forward leveling

- Allow only when the persisted options explicitly preserve scheduled early/late dates and limit leveling to activity Total Float. If the selected P6 option combination cannot be supported exactly, reject it rather than switching modes.
- Derive each activity's maximum allowed forward shift from the authoritative intermediate CPM output (the appropriate late-date boundary and configured minimum preserved float), using the exact activity calendar resolver. The resource input itself must not supply early/late dates or floats.
- Project every persisted period-demand slice for that activity through its maximum allowed shift using the same activity calendar semantics as the Shared Core leveler. The declared window must include the baseline scheduled windows and all original/projected demand dates; this matters because manually entered future-period values can extend beyond the activity's nominal finish.
- Require a resolved capacity value for every resource/date needed through the entire declared window. A nonworking date is a known zero only when established by the versioned calendar definition; an absent capacity slice is unknown data and must fail closed.

### Mode B — explicitly bounded movement

- When leveling may move work beyond the baseline float window or invoke the backward pass, require a positive, finite `max_shift_working_days` in the immutable request/companion. Do not quietly inherit the core's internal safety-loop limit as a product default.
- Use each activity's authoritative calendar to project its demand dates by the declared forward and/or backward movement bound. Set the companion window to cover the union of original demand dates, all projected candidate demand dates, and every date used by final resource-load validation.
- If an activity/calendar combination cannot be projected deterministically, a capacity date is uncovered, or a remaining overload reaches the declared movement bound, return a stable “horizon/movement bound exceeded” failure. Do not treat an absent capacity bucket as zero and do not report a completed leveling run.
- The run output/audit record must say which bound policy was applied and whether the final resource ledger passed. This operational bound is an explicit CUBI limitation/guard; it must not be represented as a Primavera setting.

### Acceptance questions for the independent reviewer

1. Do the two modes preserve the official V26 forward-only / backward-pass and Total-Float-limit semantics without silently changing the selected mode?
2. Does demand projection use the same authoritative activity-calendar arithmetic as the Shared Core leveling engine, including weekends, holidays, calendar exceptions, and user-entered future periods?
3. Is complete capacity coverage proven for every date that can affect proposal and final-load validation, and is missing data distinguished from calendar-derived zero capacity?
4. Are the movement bound, companion hash, calculation-run identity, and failure result deterministic and auditable?
5. Are the unbounded/unsupported option combinations explicitly rejected until an exact finite coverage proof exists?

No answer is pre-approved by this proposal. Keep `CUBI-RES-005` BLOCKED until the independent review outcome is recorded.

## Priority conformance gate

The P6 Professional v26 priority list has 13 fields: Activity ID, Activity Priority, Early Finish, Early Start, Free Float, Late Finish, Late Start, Original/Planned Duration, Planned Finish, Project Planned Start, Project Priority, Remaining Duration and Total Float. Current shared-core mapping/comparison supports only a subset. Do not allow-list missing fields until each is backed by a typed authoritative value and tests cover ascending/descending, blank values, numeric-vs-text ordering, precedence of priority rows, and deterministic fallback behavior.

Source: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_priority_definitions.htm  
Resource-leveling behavior and preserve-early/late-date semantics: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_resources.htm

## Required acceptance tests before marking complete

1. Persist assignment and period rows; commit; create schedule and resource snapshots; then read both through fresh scoped repositories and evaluate through the authoritative query provider.
2. Identical immutable inputs produce the same calculation-run identity and output.
3. Changing one demand, capacity slice, resource calendar version/hash or leveling option changes the relevant identity or is rejected.
4. Cross-tenant, cross-project, stale-revision, wrong-snapshot-ID and wrong-snapshot-hash inputs are rejected.
5. Missing capacity at the first, middle and final period of the horizon is rejected.
6. Duplicate capacity and ambiguous demand slices are rejected or aggregated only according to the explicit contract.
7. A leveling request without its companion payload fails closed; a non-leveling request remains behaviorally unchanged.
8. Forward/backward leveling respects relationship logic, constraints, calendar semantics and the configured preserve-early/late-date mode.
9. Priority conformance tests cover all 13 fields or prove unsupported fields are rejected at configuration validation.
10. Run focused tests, full Python suite, typecheck and CI on the exact PR head commit. Record command/run IDs and results; a green run on a different SHA is not evidence for this change.

## Completion rule

This document does not claim implementation or conformance. Close #1462/#1468 only after the complete persistence-to-authoritative-query path is implemented, acceptance tests pass on the same commit, and the documentation-first review gate in #1447 is satisfied.
