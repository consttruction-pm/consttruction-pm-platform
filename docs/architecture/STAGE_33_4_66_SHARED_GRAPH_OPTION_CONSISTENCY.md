# Stage 33.4.66 — Shared-Graph Schedule Option Consistency

## Finding

A shared multi-project graph is evaluated once through the authoritative Shared Core scheduler. If projects provide different calculation-affecting ScheduleOptions, using the first snapshot's options makes behavior dependent on input ordering.

## Contract

- Calculation-affecting options passed to a single shared graph must match across snapshots.
- Incompatible options fail before scheduler execution with the stable error prefix `MULTI_PROJECT_SCHEDULE_OPTIONS_MISMATCH:` followed by sorted option names.
- Explicitly orchestration-scoped/resource-selection fields remain excluded from this equality check only where the batch boundary already resolves them or validates their own semantics.
- Existing guards for float basis, relationship settings and resource-leveling compatibility remain in force.
- Do not silently select the first project's calculation options.
- Do not add a second scheduler or change CPM formulas.

## Regression evidence

`tests/scheduling/test_authoritative_schedule_batch.py` adds input-order reversal coverage for critical float threshold, open-ended criticality, multiple-float-path options, expected finish dates and data date. It also covers a project-routing option that is intentionally handled per project.

## Verification

Implementation and tests are committed to main. Exact-head ConstructionPM CI, Client Typecheck, PostgreSQL Integration and PostgreSQL Sync State Integration are pending; this stage is not considered verified until those checks finish successfully.

## Compatibility impact

- P6/Shared Scheduling: preserves a single authoritative scheduler; rejects ambiguous mixed calculation settings rather than inventing semantics.
- Web/Desktop/Mobile: no client calculation changes.
- Portability/replay: input order cannot silently choose different calculation options.
