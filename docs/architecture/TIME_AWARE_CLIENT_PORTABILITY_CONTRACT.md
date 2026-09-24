# Stage 33.4.33 — Time-Aware Client Integration & Portability Contract

Date: 2026-09-24

## Purpose

Web, Desktop and Mobile must reproduce the same time-aware scheduling result from the same portable calculation context. Clients consume the Shared Core/API contracts and do not implement scheduling semantics.

## Portable calculation context

The portability contract now carries:

- project/default/activity/relationship-lag calendar references with version;
- time scheduling mode;
- project start, project finish and optional data date;
- critical float threshold in working hours;
- time precision and rounding policy;
- time-aware activity constraint records.

Datetime values use explicit ISO 8601 date-time representation. Decimal-like thresholds remain strings in JSON to avoid binary floating-point ambiguity.

## Client parity

Each client must preserve the calculation context without changing:
- duration units;
- lag units/sign;
- calendar identity/version;
- constraint type/target;
- schedule mode;
- precision/rounding policy.

Desktop and approved Mobile offline scheduling use the same Shared Core semantics. Web execution uses the same API/Application contract. Recalculation results must be compared through deterministic regression fixtures.

## Contract boundary

The authoritative chain is:

Portable Project Package -> API/Application Contract -> Shared Scheduling Core -> typed result DTO -> Web/Desktop/Mobile presentation.

No client may introduce an alternative constraint, duration, calendar, lag, float or criticality formula.

## Remaining Stage 33.4 gates

- typed API DTOs for the time-aware contract;
- cross-client parity/regression fixtures;
- offline portability round-trip tests;
- final P6 time-aware parity review.

Runtime CI execution remains unverified.
