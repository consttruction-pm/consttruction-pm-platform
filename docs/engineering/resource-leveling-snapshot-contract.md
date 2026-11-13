# Resource-Leveling Snapshot Contract (Implementation Gate)

Status: **design contract; implementation and conformance tests remain blocked**  
Baseline inspected: `main` at `f64b8689a9327f53c9a2a5cbb1b1ffb3cc14450e`  
Related work: Issues #1462, #1468, #1447.

## Problem statement

The authoritative query provider evaluates a `ScheduleInputSnapshot` and `CalculationContext`, but does not supply `SchedulerLevelingInput`. The evaluator correctly rejects a leveling request with `SCHEDULE_LEVELING_INPUT_REQUIRED`. The persisted-input composer also rejects resource assignments that are not bound to the immutable schedule input. Do not bypass either guard by reading mutable repositories from inside the calculation.

## Required identity and data flow

1. Perform fresh, tenant/project/revision-scoped reads in the application composition boundary.
2. Normalize assignments, assignment-period demand, resource calendars, calendar versions and capacity slices into a deterministic canonical resource-leveling payload.
3. Bind that payload to the same tenant ID, project ID, project revision, schedule snapshot ID/hash and base CalculationContext identity as the CPM input. The resource payload must have its own canonical SHA-256 hash and explicit schema/version.
4. Prefer embedding the fully prepared facts in the canonical schedule snapshot when its capacity horizon can be derived before final serialization. If stored separately, preallocate an immutable companion ID and include only that ID, schema version and source project revision in the schedule-snapshot payload. Save/fresh-read the companion atomically with the base snapshot and CalculationContext.
5. Keep the content-hash graph acyclic: when a companion payload includes the parent schedule snapshot hash, do **not** put the companion's content hash back into the parent's canonical payload. The parent hash covers the companion reference ID; the companion binds to that final parent hash and has its own independently verified hash. The combined calculation-run identity must include both hashes. This prevents a self-referential hash contract.
6. On read, verify tenant/project/revision, schedule snapshot ID/hash, base calculation identity, schema version, canonical hash and all referenced calendar ID/version/hash identities. Any mismatch must fail closed.
7. Materialize the immutable payload into a typed `SchedulerLevelingInput` before calling `evaluate_schedule_snapshot(..., leveling_input=...)`. The evaluator must not query repositories or depend on mutable state.

## Hash dependency graph (mandatory contract invariant)

For an embedded input, one canonical schedule payload and one SHA-256 hash cover schedule data plus resource assignments, period demand, capacity, and the explicit horizon.

For a separate companion, use this one-way dependency graph:

```
preallocated companion_id
        ↓ included in base payload
schedule snapshot payload → schedule_snapshot_hash
        ↓                                   ↓
base CalculationContext identity           resource companion payload
                                            (includes schedule_snapshot_hash)
                                                     ↓
                                            resource_facts_hash
                                                     ↓
combined calculation_run_identity
```

The schedule snapshot must **not** also include `resource_facts_hash` when the companion includes `schedule_snapshot_hash`; that would create a hash cycle. The base snapshot's immutable companion ID/schema/source-revision reference plus one-to-one immutable repository key identifies the expected companion. Fresh-read verification recomputes its content hash and validates its parent bindings. Resource facts still affect replay identity because `resource_facts_hash` is an explicit input to `calculation_run_identity`. If the implementation cannot enforce this one-way graph and atomicity, keep the separate-companion architecture blocked; do not weaken hash validation to make it work.

## Canonical payload minimum

- Contract/schema version.
- Tenant, project, project revision.
- Schedule snapshot ID, snapshot hash and calculation identity.
- Resource assignment IDs, activity IDs, resource IDs, units, units/cost metadata required by the leveling algorithm, and resource calendar ID + version.
- Effective-dated Resource Max Units/Time records, their exact unit/time basis, source revision/hash, and the documented conversion into each period's capacity ceiling.
- Assignment period values with ISO date, units, assignment ID, activity ID and resource ID.
- Calendar snapshot hashes, normalized calendar working-time factors, resource Max Units/Time provenance, and normalized capacity slices.
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

## Capacity ceiling versus calendar working time (P6 v26 conformance blocker)

The official V26 resource-planning documentation distinguishes the resource's effective capacity limit from the resource calendar's working-time pattern. The resource's **Max Units/Time** is the maximum work units that resource can perform per time period; the calendar supplies the working hours for that period. The V26 resource planning reference describes a resource limit as Max Units/Time applied to the working hours available under its calendar. Consequently, the calendar definition alone is not a complete capacity source.

- Source: [P6 Professional Version 26 — Max Units/Time (Resources)](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/maxunits_timeresources-31188a.html)
- Source: [P6 Professional Version 26 — Resource assignments Spreadsheet View / Limit field](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/101011.html)
- Source: [P6 Professional User Guide Version 26 — Assign a Calendar to a Project Resource](https://docs.oracle.com/cd/E80480_01/help/en/user/96368.htm)

**Current code gap from source inspection:** `p6_resource_capacity_contract.py::build_resource_capacity_slices` reads capacity directly from `ResourceCalendar.capacity_on(period)`. The general `resources/models.py::Resource` model has no Max Units/Time or resource-calendar version field; `P6ResourceAssignment` stores a versioned assignment calendar reference but is not the resource-master capacity authority; and `p6_field_registry.py` has a Max Units/Time field definition while its registry status is still `seeded_not_certified`. The current capacity path therefore proves the assigned calendar ID/version/hash but does not provide a typed, versioned, effective-dated Resource Master Max Units/Time value. It cannot prove that the numeric capacity matches P6 for non-default or time-varying resource limits.

Before production wiring, the independent reviewer must define the units and normalization equation against project time-period preferences and the effective-dated Max Units/Time records. Do not simply multiply or replace values based on names: the representation must be derived from the official dimensional convention and tested at least for a single-person resource, a multi-person resource, a changed effective date, a nonworking date and a resource-calendar exception. If the repository cannot provide the required typed values/version history, resource leveling stays blocked; no calendar-only fallback may be described as full P6 capacity parity.

The immutable resource facts must therefore bind both:
- versioned calendar working-time/exception facts and the calendar hash; and
- the effective-dated Resource Max Units/Time values, their units/time basis and source revision/hash.

The normalized per-period capacity slice and the exact transformation/provenance must be part of the canonical resource-facts hash.

## Leveling horizon and coverage

The caller-provided `periods` list and dates appearing in demand rows are not, by themselves, proof of complete coverage. Derive a declared horizon from the authoritative CPM windows and leveling policy; validate every selected resource's capacity for every period in that horizon, using the exact versioned calendar snapshot. Document how nonworking days, partial periods, and manual future-period capacity values are represented. No calculation may proceed with unknown capacity in a period that can affect the result.

## Proposed finite-horizon policy for independent review (not yet approved)

P6 v26 documents the movement semantics, but it does **not** define a universal arbitrary date-range cap for the resource leveler. The finite bound below is therefore a CUBI execution-safety contract, not a claim that P6 itself exposes a matching option. Farmj / the independent scheduling reviewer must accept or amend it before production calculation changes.

The companion schema should carry an explicit `horizon_policy_version`, `horizon_mode`, `horizon_start`, `horizon_end`, and the source values needed to reproduce those boundaries. The bounds must be computed before the companion hash is finalized.

### Mode A — float-bounded leveling

- This mode is available only when the persisted options explicitly enable `level_within_float`; the baseline early/late dates and float must come from the authoritative Shared Core CPM pass. Never take those calculated values from request or resource-assignment data.
- The exact `preserve_scheduled_early_and_late_dates` option still selects the pass strategy and must be preserved: when selected, use the supported forward-only leveling behavior and preserve the scheduled late-date boundary; when cleared, use the documented forward-and-backward behavior and recalculate early/late dates. Do not silently flip the option to make the horizon easier.
- Derive each activity's permissible movement boundary from its baseline CPM early/late window, its float and configured minimum preserved float, applying the same exact activity-calendar resolver used by the Shared Core leveler. Any option combination for which that boundary cannot be proven remains unsupported and must fail closed.
- Project every persisted period-demand slice for each activity through all positions permitted by that movement boundary. The declared window must include the baseline scheduled windows and all original/projected demand dates; manually entered future-period assignment values can extend beyond an activity's nominal finish.
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
