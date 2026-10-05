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
| StandardWorkWeek / StandardDetailedWorkHours | Equivalent-Superset pending dedicated contract | Shared-Core calendar snapshots already carry canonical working-week data |
| DetailedWorkHours / TotalWorkHours | Equivalent-Superset pending dedicated contract | Working-time snapshot carries canonical intervals/factors |
| Calendar fields metadata | Outside this slice | Must be connected to canonical P6 field registry in a separate parity task |

The remaining dedicated work-hour contract/API work is intentionally not represented as complete by this slice.
