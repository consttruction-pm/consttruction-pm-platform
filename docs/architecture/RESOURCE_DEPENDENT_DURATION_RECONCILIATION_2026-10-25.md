# Resource Dependent Duration — Reconciliation Record

Date: 2026-10-25
Base/source commit: `52483e55e19b927cc392b86808d6ff484cb26215`
Status: implementation merged on source commit; semantic scope remains partial and must not be called full schedule parity.

## What the source commit implements

- Adds deterministic derivation for a supported Resource Dependent activity subset in `src/construction_pm/scheduling/resource_dependent.py`.
- Uses persisted driving assignment facts, Planned Units for not-started activities, explicit daily Units/Time, one exact calendar ID/version, and the longest driving duration.
- Hashes the canonical tenant/project/revision/activity/assignment facts and carries the input hash into the activity snapshot.
- Re-derives the duration on the persisted resource resolver path and fails closed when the driving facts/hash/duration/calendar binding no longer match.
- Adds unit-level unsupported-contract tests and an authenticated write → commit → snapshot → query integration test for a 3-working-day activity, plus an unknown driving-flag publication rejection test.

## Important limitations retained

- This is deliberately a supported subset, not complete Resource Dependent semantics: in-progress/actual activities, nondriving placement, non-daily rates, incompatible units/calendars, and fractional working-day results are rejected rather than guessed.
- The current rule takes the maximum of each driving assignment's Planned Units / Units per Time. Confirm this interpretation against the exact source product behavior and activity/resource assignment contract before claiming semantic parity.
- The integration fixture proves the persisted API/query path for the covered case; it does not prove all resource calendars, period demand, capacity, leveling priority, or all relationship/constraint interactions.
- The prior resource-leveling regression note remains a separate open verification gate. Full P6 parity and full CUBISITE schedule completion are not certified by this feature.

## Required next verification

1. Run the focused Resource Dependent module tests and the new authenticated snapshot/query integration tests on this exact source SHA.
2. Run exact-head ConstructionPM CI, Client Typecheck, PostgreSQL Integration, and relevant web/e2e checks; record run IDs and results.
3. Independently review the derivation formula, calendar precedence, status/actual behavior, assignment period reconciliation, and stale-revision rejection against the authoritative reference contract.
4. If a test fails, fix implementation and add regression coverage; do not weaken assertions or mark this note complete.
5. Update the main project state ledger only after fresh evidence is available.

This record is additive. It does not remove existing project requirements or grant release-completion credit.
