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
- `docs/roadmap/` — staged implementation and completion tracking.

## Core engineering rules
1. Primavera P6 logic is the baseline for overlapping scheduling/project-control behavior.
2. Shared Domain/Calculation Core must remain independent from UI, Windows, PostgreSQL, filesystem and authentication.
3. API/Application/Repository boundaries are mandatory for web readiness.
4. Project-specific calendars, calculation settings, rules and context must travel with project export/import and must never silently fall back to a default calendar.
5. Excel/Project exports must use typed numeric/date/duration fields.
6. Every calculation must be deterministic and testable.
7. Audit/revision history is append-only for effective project changes.
8. **GitHub/Codex is the canonical development, code-execution and test environment. ChatGPT is a coordination/review/support environment.**
9. Database-backed and runtime verification must use the intended SQL/PostgreSQL-capable GitHub/Codex environment.
10. **CUBI is one product platform with two complementary environments: CUBI Engineering and CUBI Enterprise.** The personal workbench is the entry/personal coordination surface, not a third environment. See [CUBI Two-Environment Product Architecture](docs/architecture/CUBI_TWO_ENVIRONMENT_PRODUCT_ARCHITECTURE.md).
11. **CUBI Engineering is the active primary completion workstream.** The first development agent implements it; ChatGPT coordinates and issues scoped instructions. CUBI Enterprise is a separate parallel workstream owned/coordinated by ChatGPT and must not block, delay, destabilize or become a prerequisite for Engineering or website completion.
12. PMBOK-aligned management and organizational collaboration capabilities belong to CUBI Enterprise. **Form Builder is shared** by both environments, with context-specific permissions/workflows and a common safe calculation contract. Existing form specifications and issues remain implementation requirements, not proof of completion.
13. Until final authentication is delivered, role selection is a temporary login substitute for development navigation only. The intended flow is personal workbench → role/context selection → authorized environment selection (Engineering or Enterprise). This temporary mechanism is not production authentication or authorization.
14. Engineering remains authoritative for engineering calculations and records. Cross-environment operations require explicit, versioned, permission-checked contracts. No duplicated engineering calculation engines or Enterprise work that degrades Engineering runtime/release gates.

## Mandatory continuity entrypoint

Before implementation, read [PROJECT_CONTINUITY_PROTOCOL.md](docs/governance/PROJECT_CONTINUITY_PROTOCOL.md) and [PROJECT_STATE_LEDGER.md](docs/governance/PROJECT_STATE_LEDGER.md). Check current main/exact SHA, correct workstream schedule, evidence-based status, scope and handoff requirements. For website-only CUBISITE work use its designated schedule; do not infer whole-product completion from the website plan.

## Team responsibility model
The current development ownership model is documented in [docs/team-responsibilities.md](docs/team-responsibilities.md). This product-owner decision adds the environment/workstream split described in the two-environment architecture record.

## Current documented implementation point
See the current project state ledger and workstream-specific evidence. Stage names, merged status and runtime verification must be reported from current repository evidence; documentation alone is not implementation proof.

## No-regression rule
No CUBI Enterprise or platform-entry change may silently alter the existing CUBI Engineering shell, engineering calculation authority, routes, data contracts, tests or delivery priority. Any cross-boundary change requires an explicit scoped proposal, approval, and exact-head verification.
