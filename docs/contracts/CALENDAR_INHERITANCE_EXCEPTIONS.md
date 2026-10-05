# Calendar inheritance and exception persistence contract

## Scope
This bounded issue #1207 slice establishes persistence-ready semantics for P6 calendar inheritance and per-date exceptions without changing CPM arithmetic.

## Implemented
- CalendarMaster has an optional versioned base-calendar reference.
- The reference is an all-or-nothing pair; self-inheritance is rejected.
- CalendarException is a first-class record supporting nonwork, total-work-hours, detailed non-contiguous work-hours, and reset-to-standard.
- Gregorian dates and JalaliDate inputs canonicalize to Gregorian; the declared calendar system is retained.
- SQLite and PostgreSQL enforce tenant/project scope and project revision checks.
- Identical exception replay is idempotent; changing an existing exception within the same calendar version is rejected.
- Exception identity includes calendar version and exception date, enabling deterministic replay.

## Precedence contract
This slice stores the data required to express inheritance and overrides. It does not alter the scheduling resolver. The intended materialization precedence is:
1. child/project/resource override;
2. inherited base-calendar exception;
3. standard/base rule.

Scheduling arithmetic remains exclusively in Shared Core.

## P6 evidence classification
| Capability | Classification | Evidence boundary |
| --- | --- | --- |
| Versioned base/global calendar reference | Equivalent-Superset | Persisted and round-tripped; resolver inheritance is a follow-up |
| Nonwork exception | Implemented | SQLite/PostgreSQL round-trip tests |
| Total work-hours override | Implemented | SQLite domain/persistence regression |
| Detailed non-contiguous work-hours | Implemented | SQLite/PostgreSQL round-trip tests |
| Reset-to-standard | Implemented | SQLite persistence regression |
| Full Calendar CRUD / Copy / Replace / REST API parity | Outside-Scope | Tracked by issue #1209 |

No P6 parity claim is made beyond the executable evidence above.
