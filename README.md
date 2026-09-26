# Construction PM Platform

Enterprise Project Management & Construction Control Platform.

## Purpose
A web-ready construction project management platform designed as a structured replacement path for Primavera P6 and Microsoft Project, with bilingual Persian/English support and Jalali/Gregorian calendar support.

## Repository structure
- `docs/` — product requirements, architecture, domain rules, scheduling, progress, reporting and implementation specifications.
- `src/` — application source code (to be populated from approved implementation artifacts).
- `tests/` — automated tests and conformance tests.
- `infra/` — deployment, database and environment definitions.
- `tools/` — developer and migration utilities.
- `docs/roadmap/` — staged implementation roadmap and completion tracking.

## Core engineering rules
1. Primavera P6 logic is the baseline for overlapping scheduling/project-control behavior.
2. Shared Domain/Calculation Core must remain independent from UI, Windows, PostgreSQL, filesystem and authentication.
3. API/Application/Repository boundaries are mandatory for web readiness.
4. Project-specific calendars, calculation settings, rules and context must travel with project export/import.
5. Excel/Project exports must use typed numeric/date/duration fields.
6. Every calculation must be deterministic and testable.
7. Audit/revision history is append-only for effective project changes.
8. **GitHub/Codex is the canonical development, code-execution and test environment. ChatGPT is a coordination/review/support environment. The temporary rule that moved full development and testing into ChatGPT is revoked.**
9. Database-backed and runtime verification must use the intended SQL/PostgreSQL-capable GitHub/Codex environment.

## Current documented implementation point
The project has progressed beyond the original Stage 33.4.30 time-aware CPM milestone. The current documented sync/platform work is at **Stage 33.4.71 — PostgreSQL Atomic Idempotency Execution Lock**, implemented with runtime verification pending.

Recent completed gates:
- Stage 33.4.65 — Final Time-Aware P6 Certification & CI Runtime Gate: runtime-verified.
- Stage 33.4.66 — Cross-Client Parity Regression Gate: runtime-verified.
- Stage 33.4.67 — Shared Offline Mutation Queue Client Gate: runtime-verified.
- Stage 33.4.68 — Shared Client API Sync Transport Boundary: runtime-verified.
- Stage 33.4.69 — End-to-End Client Sync Outcome Regression: runtime-verified.
- Stage 33.4.70 — Authoritative Conflict Revision Refresh & Cross-Client Retry Boundary: implemented; runtime verification pending.
- Stage 33.4.71 — PostgreSQL Atomic Idempotency Execution Lock: implemented; runtime verification pending.

Current sync/platform focus:
- Preserve authoritative revision refresh before stale-revision retry.
- Serialize same-key idempotent mutation execution at the PostgreSQL transaction boundary.
- Keep distinct idempotency keys concurrently executable.
- Maintain ACK/RETRY/CONFLICT/REJECTED semantics across Web/Desktop/Mobile.
- Complete runtime verification only when GitHub Actions provides executable job steps and test results.

No Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics are changed by the current sync-platform gates.
