# Stage 33.4.29 — Activity & Relationship-Lag Calendar Resolution

Date: 2026-09-24

## Resolution contract

Scheduling now has an explicit, versioned calendar reference:

- `calendar_id`
- `calendar_version`
- `kind`: `working-day` or `working-time`

`SchedulingCalendarContext` defines three scopes:

1. project calendar;
2. activity calendar;
3. relationship-lag calendar.

If an activity calendar is not specified, it inherits the project calendar. If a relationship-lag calendar is not specified, it inherits the activity calendar, then the project calendar.

## Why the inheritance is explicit

The inheritance chain is deterministic and portable. It prevents each client from deciding independently which calendar to use for duration or lag.

The registry refuses to silently substitute another calendar version. A missing requested version is an error.

## P6 compatibility direction

The architecture leaves room for a schedule option to select a relationship-lag calendar explicitly. This is necessary because P6 supports calendar-aware relationship lag behavior rather than a universal fixed-hour conversion.

This stage does not yet change the existing date-based Forward/Backward implementation. It establishes the authoritative calendar-selection contract required before time-aware CPM integration.

## Portability

`project-portability.schema.json` now carries activity-calendar and relationship-lag-calendar policy fields in calculation context so the same project calculation context can be reconstructed on another client/device.

## Client rule

Web/Desktop/Mobile may select or display the calendar reference, but the Shared Core owns resolution, validation and scheduling semantics.

Runtime CI execution remains unverified.
