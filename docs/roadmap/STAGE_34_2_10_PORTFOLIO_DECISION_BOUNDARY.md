# Stage 34.2.10 — Portfolio Decision & Approval Boundary

Status: implementation in progress.

## Scope

Define an auditable, human-approval-first boundary for portfolio decisions derived from cross-project control snapshots and impact evidence.

## Acceptance criteria

- Decision records identify portfolio, tenant, decision type and affected projects.
- Decisions preserve source snapshot and impact/action references.
- Approval is required by default.
- Approved state requires approver identity and timezone-aware approval timestamp.
- Implementation requires prior approval when approval is required.
- Implementation records an opaque application/mutation reference; this boundary never executes project mutations itself.
- Evidence references are mandatory and revision-safe.
- Contract is shared and client-independent.
- Python and client runtime verification is required before merge.

## Non-goals

- No automatic project mutation.
- No schedule/resource/cost/EVM calculation.
- No authorization provider implementation; final authorization remains Application/API-owned.
