# Portfolio Query Boundary

Version 1 defines a tenant-scoped read-model boundary for portfolio project snapshots.

The adapter returns authoritative/precomputed read-model metrics as opaque structured data. It does not calculate scheduling, calendar, duration, Progress/EVM, Resource/Cost, or financial semantics.

Production query stores and portfolio aggregation infrastructure remain behind the adapter.