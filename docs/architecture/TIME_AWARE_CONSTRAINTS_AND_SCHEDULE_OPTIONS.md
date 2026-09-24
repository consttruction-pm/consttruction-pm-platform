# Stage 33.4.32 — Time-Aware Constraints + Schedule Options

Date: 2026-09-24

## P6-aligned constraint scope

The time-aware Shared Core now supports the six established activity constraints with datetime targets:

- Start No Earlier Than
- Start No Later Than
- Finish No Earlier Than
- Finish No Later Than
- Mandatory Start
- Mandatory Finish

The scope follows the existing P6 constraint matrix:

- No Earlier Than constraints affect the early schedule and reduce float; they do not move late dates.
- No Later Than constraints govern upper bounds on the late schedule and are validated on early dates.
- Mandatory Start/Finish constrain both early and late dates.

## Calendar semantics

Constraint targets are normalized through the activity's authoritative working-time calendar. A non-working target therefore resolves through Shared Core rather than a client-specific date/time rule.

Duration arithmetic uses the activity calendar. Constraint target conversion is never performed by Web/Desktop/Mobile.

## Schedule options

The current time-aware integration intentionally keeps schedule-mode selection outside the constraint primitives. The existing EARLIEST/ALAP schedule option remains an application-level choice, while constraints provide deterministic date bounds.

A future time-aware schedule-options contract must explicitly carry:
- selected schedule mode;
- project finish / data date;
- relationship-lag calendar option;
- critical/float threshold;
- time precision and rounding policy.

## Compatibility

Existing date-based constraints remain unchanged. Time-aware constraints are a separate explicit contract and do not silently reinterpret date-based inputs.

## Remaining gates

- formal time-aware schedule-options contract;
- complete portability schema for per-activity time quantities and constraint targets;
- cross-client API regression pack;
- final P6 time-based parity certification.

Runtime CI execution remains unverified.
