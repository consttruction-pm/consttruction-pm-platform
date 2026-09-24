# Stage 33.4.29 — Activity Calendar & Relationship-Lag Calendar Resolution

Date: 2026-09-24

## Authoritative rule

Calendar selection is an explicit Shared Core concern. It must never be inferred differently by Web, Desktop or Mobile.

`SchedulingCalendarContext` carries three references:
- project calendar
- activity calendar (optional; falls back to project calendar)
- relationship-lag calendar (optional; falls back to the effective activity calendar)

Each reference contains `calendar_id`, `calendar_version`, and `kind` (`working-day` or `working-time`).

## Resolution

`CalendarResolverRegistry` resolves the exact versioned reference. A missing calendar/version raises an error; it never silently falls back to another version.

This is required for deterministic project portability and reproducible calculations across devices.

## Relationship lag

The lag calendar is independently addressable. This prevents the product from hard-coding predecessor, successor or project calendar semantics when the schedule option requires a dedicated lag calendar.

## Portability

`shared/contracts/project-portability.schema.json` now carries versioned calendar assignment references in `calculation_context.calendar_assignments`.

The calculation context must travel with the project so Desktop offline, Web and Mobile can reproduce the same Shared Core semantics.

## Integration boundary

This stage establishes calendar identity and resolution. Existing date-based CPM APIs remain unchanged. Time-aware Forward/Backward/Float integration must consume this context rather than creating local calendar rules.
