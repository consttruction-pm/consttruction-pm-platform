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

## Current documented implementation point
Stage 32.7 — Reporting, Print Engine & Professional Project Reports: 100%.

Next planned stage:
Stage 32.8 — Resource & Cost Control Center.
