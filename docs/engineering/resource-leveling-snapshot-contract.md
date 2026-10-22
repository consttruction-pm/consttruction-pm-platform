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
