# Construction PM Platform

Enterprise Project Management & Construction Control Platform.

## Purpose
A web-ready construction project management platform designed as a structured replacement path for Primavera P6 and Microsoft Project, with multilingual/all-language support, downloadable offline language packs, RTL/LTR and Persian typography support, and Jalali/Gregorian calendar support.

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

## Team responsibility model
The current three-person development ownership model is documented in [`docs/team-responsibilities.md`](docs/team-responsibilities.md):
- **Jalal** — Lead Developer / Architect / Integration; Shared Core, scheduling/calculation, P6 parity, integration and final technical acceptance.
- **Hasan** — Backend / Database / API; PostgreSQL, backend/application/repository, API contracts, sync and database-backed verification.
- **Javad** — Frontend / Web / Desktop / Mobile / UX; client applications, UI, localization, offline/client integration and cross-client parity.

## Current documented implementation point
The project has progressed beyond the original Stage 33.4.30 time-aware CPM milestone. The current implementation point spans **Stage 85+**, with later integrated hardening in Dependency Graph, Project Portability, Typed Reporting, and Web Main Workspace boundaries. Stages 34.1 through 34.2.19 and the later Stage 84/85 multilingual boundaries have been integrated through reviewed PR gates. Stage 34.2.10 passed the full Python 3.11/3.12/3.13 and Web/Desktop/Mobile/Client-Sync runtime gates before merge.

Recent completed gates:
- Stage 33.4.65 — Final Time-Aware P6 Certification & CI Runtime Gate: runtime-verified.
- Stage 33.4.66 — Cross-Client Parity Regression Gate: runtime-verified.
- Stage 33.4.67 — Shared Offline Mutation Queue Client Gate: runtime-verified.
- Stage 33.4.68 — Shared Client API Sync Transport Boundary: runtime-verified.
- Stage 33.4.69 — End-to-End Client Sync Outcome Regression: runtime-verified.
- Stage 33.4.70 — Authoritative Conflict Revision Refresh & Cross-Client Retry Boundary: implemented; runtime verification pending.
- Stage 33.4.71 — PostgreSQL Atomic Idempotency Execution Lock: implemented; runtime-verified through the available execution gate before Stage 34 integration.
- Stage 34.1 — Shared Control Intelligence contract/domain foundation: integrated and runtime-verified.
- Stage 34.2.1 — Backend P0 versioned contracts: integrated and runtime-verified.
- Stage 34.2.2 — Backend P0 persistence/transaction/application/API foundation: integrated and runtime-verified.
- Stage 34.2.3 — P0 context, audit, revision-precondition and idempotency-scope boundary: integrated through PR #116; focused contract tests are present.
- Stage 34.2.4 — P0 resource envelope integration: integrated and runtime-verified.
- Stage 34.2.5 — Field Operations Core: attendance/timecard and equipment status/breakdown; integrated and runtime-verified.
- Stage 34.2.6 — Field Assurance Core: inspection, quality/NCR, safety observation and punch/closeout foundations; integrated and runtime-verified.
- Stage 34.2.7 — Change / Variation / Notice / Claim Core: persistent Change Case and Claim Record boundaries with evidence, approval and decision traceability; integrated and runtime-verified.
- Stage 34.2.8 — Procurement / Commercial Commitments Core: quote, bid comparison, purchase order, commitment and delivery boundaries with exact Decimal transport; integrated and runtime-verified.
- Stage 34.2.9 — Portfolio Control Read Model: cross-project project status/revision/membership snapshot with opaque links to authoritative control results; integrated and runtime-verified.
- Stage 34.2.10 — Portfolio Control Action / Approval Boundary: versioned action contract with tenant/portfolio/revision/idempotency/evidence boundaries and application-layer request/decision authorization; integrated and runtime-verified.
- Stage 34.2.11 — Portfolio Action Transition Boundary: approve/reject/cancel state transitions with authorization and duplicate-decision protection; integrated and runtime-verified.
- Stage 34.2.12 — Portfolio Action Persistence: PostgreSQL portfolio revision and action persistence with tenant/portfolio idempotency and revision checks; integrated and runtime-verified.
- Stage 34.2.13 — Portfolio Action Audit & Revision Transition Boundary: action-level optimistic revision, append-only audit history, transition persistence and stale-revision protection; integrated and runtime-verified.
- Stage 34.2.14 — Portfolio Transition Integrity Boundary: persisted transitions apply the authoritative approved/rejected/cancelled state, preserve immutable action identity/context, and reject event/status mismatches; integrated and runtime-verified.
- Stage 34.2.15 — Portfolio Action Audit Actor Integrity: audit actor/timestamp must match authoritative decision metadata; integrated and runtime-verified.
- Stage 34.2.16 — Portfolio Decision Persistence: PostgreSQL persistence with tenant/portfolio scope, idempotency replay/reuse protection, optimistic decision revision, append-only audit events and approval transition checks; integrated and runtime-verified.
- Stage 34.2.17 — Portfolio Decision PostgreSQL Runtime Verification: DSN-gated live PostgreSQL round-trip coverage for persistence, read-back, approval revision transition and append-only audit history; integrated with Python 3.11/3.12/3.13 and client typecheck gates green.
- Stage 34.2.18 — Portfolio Decision Application Boundary: application-layer authorization, tenant scope, actor integrity, creation and approval orchestration over the authoritative Portfolio Decision domain/persistence boundaries.
- Stage 34.2.19 — Portfolio Decision Lifecycle Application Boundary: reject/cancel/implement/close lifecycle orchestration with tenant/admin authorization, domain transition validation, implementation-reference enforcement and persisted revision/idempotency/audit boundaries; integrated and runtime-verified.
- Stage 84 — Multilingual Core Boundary: shared language registry, client language preference, Python AI language context, translation coverage and TypeScript client language resolution; integrated through PR #166.
- Stage 85 — Language Pack Manifest & Catalog Boundary: versioned language-pack manifest/catalog contracts, deterministic compatibility selection, integrity fields and focused TypeScript tests; integrated through PR #170.
- P0 Dependency Graph Persistence — project-scoped dependency links now have PostgreSQL revision, idempotency and append-only audit boundaries; scheduling/P6 calculation semantics remain outside this layer.
- P0 Document Persistence Boundary — versioned document resource contract, PostgreSQL metadata persistence, tenant/project scope, idempotency replay/reuse protection, optimistic revision checks, SHA-256 content-integrity metadata and append-only audit; integrated through PR #174 with ConstructionPM CI and Client Typecheck green.
- Stage 33.2.5 — Project portability contract: deterministic export/import of versioned project calculation context; integrated through PR #232 and subsequently hardened with strict schema validation.
- Stage 33.2.6 — Cross-module regression suite: Resource/Cost → EVM bridge, revision conflict, project isolation and deterministic portability reload; integrated through PR #233 with Python and client CI green.
- Stage 34.3 typed dependency contract hardening — known dependency resource/type validation and explicit RFI/document relation mapping; integrated through PR #238 with Python and client CI green.
- Stage 32.7 reporting typed dataset foundation — authoritative read-only typed report dataset boundary with separate numeric/date/duration/Boolean fields; integrated through PR #239 with Python and client CI green.
- Web Main Workspace foundation — shared Web workspace state model and framework-neutral renderer for bilingual RTL/LTR, Jalali/Gregorian mode, Project/WBS, Activity Grid, Gantt and Details panels; integrated through PR #240 with Python and client CI green.

Current Stage 34 focus:
- Continue construction control backend with the next Portfolio decision/approval implementation and cross-project control actions.
- Preserve Procurement / Commercial Commitments linkage to Cost, Schedule, Activity and Document authoritative records.
- Extend field records through the same tenant/project/revision/audit/idempotency boundaries.
- Preserve authoritative revision refresh and atomic same-key idempotency semantics across clients.
- Maintain ACK/RETRY/CONFLICT/REJECTED semantics across Web/Desktop/Mobile.
- Keep Shared P6/Scheduling, Progress/EVM and Resource/Cost calculations out of backend resource boundaries.

No Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics are changed by the current sync-platform gates.
