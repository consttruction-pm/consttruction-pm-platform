# Stage 33.4.53 — Cross-Client Conflict Presentation Adapters

Web, Desktop and Mobile now share one framework-neutral conflict presentation adapter.

## Contract

The adapter preserves:

- stable error code
- localized message-key identity
- available action semantics
- expected revision
- actual revision
- opaque server details

## Client responsibilities

Each client may choose its own UI controls, layout and localization. It must not:

- change action identity or ordering;
- invent a new business resolution;
- alter revisions;
- merge domain values locally;
- recalculate Scheduling/P6, Calendar, Progress/EVM, Resource/Cost or financial semantics.

## Architectural boundary

The adapter is presentation infrastructure only. It does not perform synchronization, persistence, scheduling, conflict merging or business calculations.

## Acceptance

A parity test exercises Web, Desktop and Mobile through the same adapter and verifies identical conflict semantics.
