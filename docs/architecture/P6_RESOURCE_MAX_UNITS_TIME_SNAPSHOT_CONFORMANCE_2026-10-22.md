# Resource Max Units/Time — Immutable Schedule Snapshot Contract

Date: 2026-10-22  
Status: **Implemented domain contract and repository adapters; production wiring and full P6 shift coverage remain open.**

## Authoritative references

- [P6 Professional v26 — Units & Prices tab / Resource Details](https://docs.oracle.com/cd/G48902_01/client_help/en_US/20417.htm)
- [P6 Professional v26 — Leveling resources](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_resources.htm)
- [P6 Professional v26 — Calendar dialog and time-period factors](https://docs.oracle.com/cd/G48902_01/client_help/en_US/calendar_dialog_box.htm)
- [P6 Professional v26 — Leveling priority definitions](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_priority_definitions.htm)

## Required calculation inputs

The maximum work available from a resource is not derived from the resource calendar alone. The P6-compatible input contract therefore binds these values to the same immutable schedule snapshot:

- Resource ID and assignment ID, activity ID, assignment unit of measure, assigned units and remaining units.
- Resource calendar ID, exact calendar version and canonical calendar snapshot hash.
- Effective-dated Max Units/Time value, time-period unit, unit of measure and explicit hours-per-period conversion.
- Whether the conversion comes from the resource calendar or global time-period settings.
- For percentage-based limits, an explicit full-time units-per-period basis; the calculation must not invent a percentage base.
- Capacity horizon start/end, calculation timezone, per-period calendar work hours, derived capacity, and the exact resource-rate hash/effective date used to derive each capacity slice.

The canonical resource facts are schema version 2. Rate and capacity facts are validated again when an immutable snapshot is materialized; the evaluator must not query mutable repositories to fill gaps.

## Capacity calculation and fail-closed rules

For an absolute Max Units/Time limit, capacity is derived from the persisted limit and the explicit period conversion, scaled by the resource calendar's work hours for the date. Percentage-based limits additionally require the persisted full-time base. Decimal arithmetic is used throughout.

Publication/materialization rejects missing or ambiguous rate data, an ineffective rate, unit mismatches, a missing calendar-period conversion, mismatched rate/calendar hashes, duplicate period records, missing capacity slices, and a capacity horizon longer than 36,500 days. The horizon bound is a safety guard, not a scheduling limit in the product specification.

P6 documentation states that resource curves are not used by resource leveling, while manually entered future-period assignment values are considered. The snapshot therefore uses persisted period-demand values for the leveling input and does not treat a distribution curve as a capacity limit.

## Explicit current limitations

1. **Multiple resource shifts:** the current date-based capacity contract rejects multiple shift identities with `RESOURCE_RATE_SHIFT_LEVELING_UNSUPPORTED`. This is intentional fail-closed behavior; it is not a claim of full parity for installations whose leveling behavior depends on resource shifts.
2. **Percentage rates:** the contract supports percentages only when the authoritative full-time base is provided. It does not infer the base from a job title, resource type, calendar, or unit.
3. **Time-period settings:** calendar-sourced conversion factors must be present in the versioned calendar snapshot. Missing factors are rejected rather than replaced with a default.
4. **Deployment wiring:** the snapshot composer now accepts a version-scoped resource-rate repository, and the production publication path forwards the calculation timezone. The deployment that constructs `AuthoritativeScheduleInputComposer` / `P6ScheduleSnapshotPublicationAPI` must inject the concrete rate repository. The current repository does not by itself prove that every deployed runtime has done so.
5. **Resource-rate write surface:** SQLite and PostgreSQL persistence adapters exist, but the authenticated resource-rate CRUD/API and end-to-end deployment provisioning still require verification before this feature is marked production-complete.

## Acceptance gate

Do not mark resource leveling complete until all of the following are evidenced on the same commit:

- The deployment assembly injects the correct tenant/project/revision-scoped rate repository.
- The authenticated write/read surface persists effective dates, Max Units/Time, unit, time-period source/conversion and percentage base without lossy defaults.
- The snapshot publication route reads assignments, demand periods, rates and calendar versions in one transaction and commits their complete immutable payload/hash.
- The schedule query materializer reproduces the same facts from the saved snapshot and performs no mutable repository reads.
- Regression tests cover rate changes at an effective-date boundary, absolute and percentage limits, calendar/global time-period settings, zero/nonwork capacity, missing data, cross-tenant/revision isolation, concurrent conflicting writes, and the explicitly unsupported shift case.
- CI and PostgreSQL integration pass on the exact candidate commit, followed by independent review.

Until these gates are satisfied, this work remains a tested partial integration rather than a claim of complete P6 resource-leveling parity.
