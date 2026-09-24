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

## Typed API contract v1

`shared/contracts/time-scheduling.schema.json` defines the cross-client payload for calculation context, activities, relationships, duration units, lag units, calendar references, and constraint-linked activity records. Decimal-like duration/lag/float values are represented as strings to preserve exactness across clients.

## Deterministic parity and offline round-trip

The Shared Core now provides a canonical JSON representation and SHA-256 fingerprint for the time-scheduling wire payload. This is a transport-level parity guard: Web, Desktop and Mobile can compare the same payload independently of property ordering. A JSON round-trip regression test verifies that offline serialization/deserialization preserves the payload exactly.

This fingerprint does not replace scheduling-result parity tests; it verifies that the calculation context and scheduling inputs are preserved without transport mutation.

## Remaining Stage 33.4 gates

- typed API DTOs for the time-aware contract — contract v1 is now defined in `shared/contracts/time-scheduling.schema.json`;
- scheduling-result parity fixtures executed against the same Shared Core;
- client adapter/API integration tests;
- final P6 time-aware parity review.

Runtime CI execution remains unverified.
