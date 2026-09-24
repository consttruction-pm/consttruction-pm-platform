# Stage 33.4.28 — Time-Based Duration & Lag Contract

Date: 2026-09-24

## Contract

The Shared Core now has an explicit quantity model:

- WORKING_DAY
- WORKING_HOUR

`TimeQuantity` represents non-negative activity duration quantities.
`LagQuantity` represents signed relationship lag/lead quantities.
Both store Decimal values so hour-based calculations do not silently lose precision through binary floating point.

## Important separation

The quantity contract does not perform calendar conversion. Conversion requires the authoritative WorkingTimeResolver/TimeAwareWorkingTimeResolver and the selected project/activity/relationship-lag calendar.

This prevents an incorrect assumption such as `1 working day = 8 hours` from becoming a global business rule. A project calendar defines its actual working intervals.

## Current compatibility boundary

Existing `Activity.duration: int`, `Relationship.lag: int`, Forward Pass and Backward Pass remain date-granularity working-day APIs for backward compatibility.

The new quantity types are an explicit foundation for the next integration stage. They are not yet wired into the existing CPM passes.

## P6 compatibility direction

P6 supports time-based relationship lag and calendar-aware scheduling options. Therefore the final integration must make the lag calendar explicit rather than assuming the predecessor, successor, or project calendar without a documented schedule option.

Required before integration:
1. activity duration unit/version in project data;
2. activity calendar identity/version;
3. relationship-lag calendar identity/version or explicit schedule option;
4. deterministic conversion through the Shared Core resolver;
5. time-aware Forward/Backward/Float regression coverage;
6. Web/Desktop/Mobile contract compatibility;
7. project portability/reproducibility across devices.

## No client duplication

Web, Desktop and Mobile may display units and edit quantities, but conversion, rounding, calendar application, lag semantics and scheduling results remain Shared Core responsibilities.

Runtime CI execution remains unverified.
