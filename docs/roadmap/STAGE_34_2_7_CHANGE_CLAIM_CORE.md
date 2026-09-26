# Stage 34.2.7 — Change / Variation / Notice / Claim Core

Status: implementation in progress.

## Scope

Backend P0 foundations that turn the existing Change Notice and Change/Claim Impact links into persistent Change Case and Claim records.

## Acceptance criteria

- Change Case supports potential change, instruction, variation and delay-event lifecycle.
- Approved changes require auditable approver identity and timestamp.
- Claim Record supports extension-of-time, compensation, variation and delay categories.
- Decided/settled/closed claims require auditable decision identity and timestamp.
- Both resources carry tenant, project, authoritative revision, audit and evidence boundaries.
- Change and Claim may link to schedule, cost, dependency and impact records without reimplementing their calculations.
- Generic P0 change resource envelopes are used for transport.
- Existing ChangeNotice and ChangeClaimImpact contracts remain authoritative and backward-compatible.
- Python, Client and PostgreSQL runtime verification is required before merge.

## Non-goals

- No EOT calculation.
- No cost/quantum formulas.
- No CPM/P6 rescheduling implementation.
