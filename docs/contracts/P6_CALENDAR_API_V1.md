# P6 Calendar API v1

This document records the bounded API/persistence slice for Issue #1209.

## Implemented in this slice

- Explicit global, resource, and project calendar type semantics on the authoritative CalendarMaster.
- Versioned calendar create/read/update/delete lifecycle with optimistic record-revision checks.
- Copy of a calendar master, authoritative Shared-Core snapshot, and persisted exceptions.
- Replace of an existing target record using an authoritative source snapshot.
- First-class API access to persisted Holiday/exception records.
- SQLite and PostgreSQL schema support for the explicit calendar type.
- Authorization and tenant/project scope enforcement.
- First-class typed contracts now exist for standard work week, standard detailed work hours, detailed work hours, and calendar-level total work hours.
- SQLite/PostgreSQL persistence and API-level regression coverage are included for the work-hour contract.
- No CPM/scheduling arithmetic was added or duplicated.

## Boundary

CalendarMaster, CalendarSnapshotRepository, and CalendarExceptionRepository remain the persistence authorities. The API only orchestrates those contracts. Shared Scheduling Core remains authoritative for calendar interpretation and scheduling arithmetic.

## P6 evidence classification

| Operation | Classification | Evidence |
|---|---|---|
| Global / Resource / Project calendar type | Implemented | CalendarMaster.calendar_type validation + SQLite/PostgreSQL persistence + API regression |
| Calendar create/read/update/delete | Implemented | versioned API boundary + optimistic revision regression |
| Copy Calendar | Implemented | master/snapshot/exception replay regression |
| Replace Calendar | Implemented (bounded) | target revision + authoritative snapshot replay regression |
| Holiday/exception persistence | Implemented | existing immutable exception repository exposed through API |
| StandardWorkWeek / StandardDetailedWorkHours | Implemented | Typed CalendarWorkHourRule contract + API + SQLite/PostgreSQL persistence and regression coverage |
| DetailedWorkHours / TotalWorkHours | Implemented | Typed CalendarWorkHourRule contract + API + SQLite/PostgreSQL persistence and regression coverage |
| Calendar fields metadata | Outside this slice | Must be connected to canonical P6 field registry in a separate parity task |

Calendar fields metadata remains outside this slice and must be connected to the canonical P6 field registry in a separate parity task. The work-hour contract is intentionally persistence/API-only; Shared Scheduling Core remains authoritative for interpreting these records.
