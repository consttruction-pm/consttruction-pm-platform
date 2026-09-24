# Time-Aware Scheduling Portability Contract

Stage 33.4.33 — 2026-09-24

This contract defines the Backend transport boundary for time-aware scheduling data. It does not implement scheduling formulas.

## Contract

time-scheduling-portability.v1 carries project schema version, versioned activity and relationship-lag calendar assignments, activity durations, relationship lag/lead, and activity constraints with ISO-8601 targets.

Working-day/hour semantics remain authoritative in the Shared Scheduling Core. The backend contract only validates and transports the typed data needed to reproduce the calculation context.

Decimal-like duration and lag values are canonical decimal strings. Calendar references require an explicit positive version; a calendar identity without a version is not portable enough for deterministic reconstruction.

Web, Desktop and Mobile must consume this same contract and must not implement alternative scheduling formulas.

## Regression

Tests cover valid time-aware data, canonical decimal enforcement, explicit calendar-version enforcement, and stable contract fingerprinting. Full runtime CI verification remains pending.
