# Stage 33.4.36 — Time-Aware P6 Parity Certification Gate

Date: 2026-09-24

## Certification scope

This pack is a compatibility gate for the Shared Scheduling Core. It is not an Oracle certification.

The time-aware certification scope covers:

1. Working-time calendar intervals, breaks, weekends and holidays.
2. Working-hour activity duration without an implicit fixed hours/day conversion.
3. FS, SS, FF and SF relationships.
4. Signed working-hour lag/lead.
5. Successor-side relationship-lag calendar resolution.
6. Forward and backward schedule consistency.
7. Time-aware Start/Finish No Earlier/Later and Mandatory constraints.
8. EARLIEST/ALAP separation.
9. Total and Free Float in working hours.
10. Deterministic cross-client scheduling-result parity.
11. Portable calculation-context round-trip integrity.
12. Exact Decimal-like wire representations.

## Cross-client parity rule

Web, Desktop and Mobile are considered parity-compatible only when the same versioned calculation context and project inputs, executed through the same Shared Core semantics, produce the same typed scheduling result.

The client UI is not permitted to recalculate scheduling values independently.

## Current evidence

- shared/contracts/time-scheduling.schema.json defines the wire contract.
- src/construction_pm/scheduling/time_portability.py provides deterministic payload canonicalization and fingerprinting.
- Integration tests cover payload-order invariance and offline JSON round-trip.
- Integration fixtures execute the same Shared Core time scheduler repeatedly and compare the typed result projection.
- Stage 33.4.32 provides P6-aligned time-aware constraint semantics.
- Stage 33.4.31 provides time-aware Backward Pass and Float analysis.

## Gate status

The engineering gate is **implemented but not certified as passed** until the repository's CI environment executes the full regression suite successfully.

This distinction is intentional: source-level fixtures and committed tests establish the required evidence structure, while CI execution is the authoritative runtime confirmation.

## Remaining work after this stage

- Run and verify full CI.
- Resolve any runtime regressions discovered by CI.
- Perform final review of richer P6 time/calendar options and documented differences.
- Close Stage 33.4 only after the above evidence is available.
