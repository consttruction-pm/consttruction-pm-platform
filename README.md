# P0 Field Resource Persistence

Field Operations resources share one versioned persistence boundary for:
daily logs, issues, observations, inspections, quality, safety, punch items,
field photos, timecards and equipment status.

The boundary provides tenant/project scope, project revision control,
idempotency replay/reuse protection and append-only audit creation.

This layer stores field-resource payloads only. It does not redefine Shared Core
P6 scheduling, calendar, duration, Progress/EVM, Resource/Cost or financial formulas.
