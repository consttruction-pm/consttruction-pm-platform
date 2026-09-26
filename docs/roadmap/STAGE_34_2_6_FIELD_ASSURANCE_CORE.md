# Stage 34.2.6 — Field Assurance Core

Status: implementation in progress.

## Scope

Backend P0 foundations for inspection, quality/NCR, safety observation and punch/closeout workflows.

## Contract boundaries

- Inspection records support checklist-based results and link to an authoritative subject/activity.
- Quality records support severity, lifecycle, inspection/specification linkage, corrective action and evidence.
- Safety observations require explicit immediate action for high/critical severity and traceable evidence.
- Punch items support responsibility, due dates and a verification gate before closed status.
- All four resources carry tenant, project, authoritative project revision, audit metadata and evidence references.
- Generic P0 field resource envelopes are transport wrappers; concrete contracts remain payload authority.

## Non-goals

- No new scheduling, calendar, progress/EVM, resource/cost or financial calculations.
- No client-specific business rules.

## Definition of done

- Contracts parsed and structurally tested.
- Domain validation covered for normal, invalid and lifecycle boundary cases.
- SQLite persistence round-trip covered.
- Generic resource envelope mapping covered.
- Python 3.11/3.12/3.13 runtime tests pass.
- Web/Desktop/Mobile/Client-Sync typecheck and existing client-sync runtime coverage pass.
