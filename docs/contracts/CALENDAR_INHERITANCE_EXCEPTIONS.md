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
The Shared Core resolver now accepts an explicit, version-pinned `base_calendar_references` map keyed by the child's exact `calendar_id@calendar_version`. It resolves parent chains before handing the resulting layers to the existing day/time resolver. No CPM arithmetic is reimplemented.

For one date, the effective rule follows these precedence rules:
1. local exception on the current Project/Resource calendar;
2. an explicitly supplied inherited exception for that calendar;
3. the nearest parent calendar's local exception;
4. more distant inherited parent exception;
5. the current calendar's standard rule when no exception applies.

Within one inherited source layer, duplicate exception dates are rejected. When two ancestor levels define the same date, the closest ancestor wins. A local `RESET_TO_STANDARD` is retained as an explicit override; it is not treated as an absent record. Missing parent registrations, calendar-kind/system mismatches, and inheritance cycles fail before scheduling. Parent references include exact versions so updating a base calendar does not rewrite earlier child resolution.

The resolver only composes effective date rules. `WorkingTimeResolver` and `TimeAwareWorkingTimeResolver` remain the only arithmetic authorities.

## P6 evidence classification
| Capability | Classification | Evidence boundary |
| --- | --- | --- |
| Versioned base/global calendar reference | Implemented at Shared Core boundary | Explicit parent id/version map; version-pinned regression cases in `tests/scheduling/test_calendar_resolution.py` |
| Global nonwork + Project reset-to-standard | Implemented | Resolver inheritance/precedence regression |
| Global detailed hours + Project total-hours override | Implemented | Time-aware resolver regression |
| Resource local override > Project override > Global base | Implemented | Three-level resolver regression |
| Parent/child version changes preserve historical resolution | Implemented | Exact-version isolation regression |
| Missing parent, kind/system mismatch, inheritance cycles | Implemented | Fail-fast resolution contract; cycle regression |
| Nonwork/total/detailed/reset exception persistence | Implemented | SQLite/PostgreSQL domain and round-trip tests |
| Full Calendar CRUD / Copy / Replace / REST API parity | Outside-Scope | Tracked by issue #1209 |

No claim is made that a running production persistence adapter automatically builds this map; persistence-to-Shared-Core composition remains a separate integration boundary. No P6 parity claim is made beyond the executable evidence above.
