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

The date-based Shared Scheduling Core now implements these P6-aligned options:
- schedule mode (EARLIEST / ALAP);
- total-float calculation type (Start Float / Finish Float / Smaller Float);
- critical activity float threshold;
- Make Open-Ended Activities Critical;
- Critical Activity Path Type = Longest Path.

Longest Path criticality is calculated from activities whose early finish equals the latest calculated early finish, then traces only driving incoming relationships in deterministic order. When a successor date is driven by a constraint rather than a relationship, the relationship chain is not treated as part of the longest path. The implementation does not claim multi-project/resource-leveling parity.

The time-aware integration still keeps schedule-mode selection outside the constraint primitives. Its future schedule-options contract must explicitly carry:
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
- remaining P6 ScheduleOptions semantics (multiple float paths, out-of-sequence scheduling, lag-calendar variants, expected-finish handling, multi-project/resource-leveling options, etc.);
- formal time-aware schedule-options contract;
- complete portability schema for per-activity time quantities and constraint targets;
- cross-client API regression pack;
- final P6 time-based parity certification.

PR #427 (P6 Longest Path) has fresh green CI on Python 3.11/3.12/3.13 and Web/Desktop/Mobile/Client-Sync typechecks.
