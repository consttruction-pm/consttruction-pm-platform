# Construction PM Platform

Enterprise Project Management & Construction Control Platform.

## Purpose
A web-ready construction project management and construction-control platform designed as a structured replacement path for Primavera P6 and Microsoft Project, with bilingual Persian/English support, Jalali/Gregorian calendars, offline-capable clients and modern construction lifecycle coverage.

## Governing principles
1. **Principle 1 — Primavera P6 + PMBOK alignment:** overlapping scheduling/project-controls behavior follows P6 compatibility semantics; PMBOK Guide Eighth Edition (November 2025) and ANSI/PMI 99-001-2025 guide project-management governance and capability design.
2. **Principle 2 — Complete modern Construction Management + Project Controls:** after Principle 1, the product must cover the construction lifecycle from preconstruction through field execution, commercial control, risk, claims, closeout and portfolio management.
3. Shared Domain/Calculation Core is the single authority for Scheduling/P6, Calendar, Duration, Progress/EVM, Resource/Cost and financial semantics.
4. Web, Desktop and Mobile consume versioned contracts and must not duplicate authoritative business calculations.
5. Typed interoperability, deterministic calculations, revision/auditability and offline/online synchronization are mandatory.
6. Open-source reuse is allowed only behind explicit boundaries; external libraries cannot become an ungoverned second source of truth.

## Repository structure
- `docs/` — product requirements, architecture, domain rules, scheduling, progress, reporting and implementation specifications.
- `src/` — shared/application source code.
- `tests/` — automated tests and conformance tests.
- `infra/` — deployment, database and environment definitions.
- `tools/` — developer and migration utilities.
- `docs/roadmap/` — staged implementation roadmap and completion tracking.

## Current documented implementation point
Stage 33.4.69 — End-to-End Client Sync Outcome Regression: runtime-verified 2026-09-25.

### Current engineering gates
- Stage 33.4.70 — Authoritative Conflict Revision Refresh & Cross-Client Retry Boundary: implemented; runtime verification pending.
- Stage 33.4.71 — PostgreSQL Atomic Idempotency Execution Lock: implemented; runtime verification pending.
- Stage 33.4.65+ P6 time-aware scheduling and cross-client parity foundations have runtime evidence; this is engineering compatibility evidence, not Oracle certification.

## Current product-completeness work
The next product expansion is governed by `docs/architecture/COMPETITIVE_COMPLETENESS_MATRIX.md`: P0 AI Project Controls Copilot, cross-domain dependency graph, field operations, change/claims, portfolio control room, procurement/commercial integration and ERP/accounting interfaces; followed by preconstruction, BIM/4D/5D, reality intelligence, quality/safety and closeout.

## Non-regression
New product domains integrate with the existing Shared Core through versioned contracts. No new domain may rewrite established P6, calendar, duration, Progress/EVM, Resource/Cost or financial semantics.