# Product Principles — Authoritative Baseline

Effective date: 2026-09-25

This document is the top-level product-governance reference. New requirements, architecture changes, calculations, workflows, client features and release decisions must be checked against these principles before implementation or release.

## Principle 1 — Primavera P6 + PMBOK alignment

For every capability that overlaps Primavera P6 scheduling/project-controls behavior, P6 semantics are the compatibility baseline and must be explicitly documented, implemented in the Shared Domain/Calculation Core and regression-tested.

PMI's PMBOK Guide — Eighth Edition (November 2025), together with ANSI/PMI 99-001-2025, is the project-management framework baseline for governance, value, scope, schedule, finance, stakeholders, resources, risk, procurement and adaptive tailoring. PMBOK is guidance, not a replacement for product-specific scheduling semantics.

No client, API adapter, external package or AI agent may silently redefine P6/shared calculation semantics.

## Principle 1A — P6 complete-field, calculation and interoperability parity / no silent omission

For every capability applicable to the product's P6-overlap scope, the latest approved P6 baseline is a **completeness floor, not only a semantic reference**. We must not silently omit a P6 field, input option, calendar rule, calculation option, output column, import/export mapping, or user-configurable field capability when an equivalent concept belongs in our product.

The parity surface includes, at minimum:
- all applicable standard and computed P6 fields by subject area;
- writable/read-only/filterable/orderable semantics and stable data types;
- UDF/custom-field support and typed custom columns;
- column/view capabilities including add, remove, hide/show, reorder, rename, width, pinning where applicable, and persistent layouts;
- formula fields/columns with safe parsing, type checking, dependency tracking, cycle detection, deterministic evaluation and summary/rollup rules;
- calendar pools, assignments, inheritance, exceptions, detailed work time and hours-per-time-period conversions;
- scheduling/calculation options that affect dates, float, criticality, progress treatment, resource leveling, costs and summaries;
- import/export mappings and round-trip preservation for P6/XER/XML/XLS/XLSX/Microsoft Project and other approved exchange formats.

A requirement may be marked **Outside Scope** only with an explicit documented decision. A feature is not considered P6-compatible merely because a screen or similarly named field exists; the behavior, data type, calculation semantics, portability and interchange contract must be covered.

The parity baseline is release-versioned. It must be refreshed against the current Oracle P6 baseline before each release certification gate, and a newly discovered applicable P6 capability becomes a gap item until dispositioned.


## Principle 1B — Authoritative calculation conformity to the applicable P6 documentation

For every calculation or calculation-affecting behavior within the defined P6-overlap scope, the applicable official Primavera P6 documentation for the release-versioned compatibility baseline is the normative semantic reference. This is a fundamental project rule, not a preference, optional enhancement, or AI prompt instruction.

This includes, where applicable, scheduling dates and passes, relationships and lag/lead, calendars and time conversions, constraints, early/late dates, total/free float, critical-path/longest-path/multiple-float-path behavior, out-of-sequence progress treatment, data date, resource leveling, progress/actuals, baselines and summaries, EVM/Earned Schedule, assignment/resource calculations, costs, formulas, units, and calculation-affecting options.

Mandatory controls:
- Maintain a versioned semantic inventory linking every applicable calculation and calculation-affecting option to its authoritative documentation, canonical Shared Core implementation, test fixtures, import/export behavior and release disposition.
- Implement semantics in the Shared Domain/Calculation Core only. UI, API adapters, repositories, external libraries and AI may call or present the authoritative result but must not redefine, approximate, silently replace or independently recalculate it.
- Derive expected regression results from documented semantics, independently validated fixtures and/or controlled reference comparisons, not from the implementation under test alone.
- Any ambiguity, version change, documented incompatibility or deliberate superset must have an explicit, reviewed decision with impact analysis and evidence. No silent simplification is allowed.
- A screen, field, formula name, passing unit test or AI explanation is not proof of conformity by itself. Accepted behavior requires typed data semantics, persistence/replay where applicable, interoperability behavior and regression evidence.
- AI may extract, explain and propose; it must invoke the authoritative calculation service for computed values. It must label predictions/assumptions separately and never claim that a computation succeeded unless the engine returned a verified result.
- Release claims must state the tested reference baseline and remaining limitations. “100% compatible” must not be claimed until the complete applicable inventory has an accepted disposition and the conformance evidence passes.

This rule governs every product release and takes precedence over schedule pressure, UI convenience and generic-model suggestions.

## Principle 2 — Complete, current and leading Construction Management + Project Controls platform

After compliance with Principle 1, the product target is not merely feature parity with one competitor. **At the time of public/commercial release, the product is intended to be the most complete and forward-looking platform within its defined specialist scope of construction project management, construction control and project controls, based on a documented market benchmark current at the release gate.**

This is a release target that must be demonstrated with evidence, not treated as a marketing assertion. The benchmark must be refreshed before release and include leading incumbent platforms, emerging AI-native products and specialized point solutions that materially affect the product scope.

### Release-completeness requirements

- No P0 capability in the approved completeness matrix may remain merely planned at release.
- Every major competitor capability relevant to our specialist scope must be either implemented, intentionally integrated through a supported adapter, or explicitly documented as outside our defined scope.
- Each implemented capability must meet an agreed depth/quality bar, not only exist as a screen or placeholder.
- Cross-domain workflows must connect Schedule, Progress, Cost, Resources, Documents, Contracts, Procurement, Field, Risk and AI where their business relationship requires it.
- AI features must be construction-grounded, auditable and action-aware rather than generic chat-only features.
- The production V1 AI Assistant is mandatory and cannot remain an architectural requirement or static UI; it must pass the acceptance gate in `docs/architecture/AI_ASSISTANT_V1_REQUIREMENTS.md`.
- Release certification must include functional, calculation, interoperability, security, offline/online, performance, localization and usability evidence.
- New market developments found before release become release-gate inputs; the roadmap must be re-ranked rather than allowing a stale benchmark to define completeness.

### Required product layers

1. Preconstruction: estimate, 2D/3D takeoff, tender/bid, bid comparison, prequalification.
2. Planning and controls: WBS, activities, CPM/P6, baselines, scenarios, risk, EVM, earned schedule, resource/cost control.
3. Procurement and commercial: RFQ, supplier quotations, PO, commitments, delivery, required-on-site dates, invoices and commercial status.
4. Field operations: daily logs, labor/timecards, equipment, observations, issues, inspections, quality, safety, punch list, corrective actions, photos and location.
5. Contract/change/claims: contracts, notices, variations/change orders, entitlement, delay analysis, claims, evidence and approvals.
6. Documents and information: drawings, specifications, correspondence, RFI, Submittal, revisions, OCR, search, approvals, immutable issued records and audit trail.
7. BIM/CDE/4D/5D: model/document coordination and links from model objects to WBS/activity/resource/cost where applicable.
8. Reality/progress intelligence: photo/360/drone/model-assisted progress verification and planned-vs-actual evidence.
9. Portfolio/executive control: project and portfolio control rooms covering schedule, cost, progress, risk, procurement, change, contracts and forecast.
10. AI-native assistance: explainable analysis, natural-language queries, document intelligence, schedule scenarios, anomaly detection, recommendations, action proposals, voice input and auditable agent execution.
11. Completion and handover: commissioning, punch closeout, as-built, O&M, warranties and asset handover.
12. Enterprise integration: API, ERP/accounting, BI/data warehouse, identity, e-signature and external collaboration.

### Architectural rule
The scope above does not permit client-specific business-calculation engines. Scheduling/P6, calendar, duration, progress/EVM, resource/cost and financial semantics remain owned by the Shared Domain/Calculation Core.

## Principle 3 — One project truth

Schedule, progress, cost, resource, document, contract, procurement, field and risk records must be linkable through stable project identifiers and revision-aware relationships.

## Principle 4 — Offline-first parity

Web, Desktop and Mobile are first-class clients. Offline-supported workflows must use the same contracts and Shared Core semantics. Synchronization, conflict resolution, idempotency and revision behavior are explicit platform contracts.

## Principle 5 — Reuse infrastructure, not product intelligence

Open-source components may be used for commodity infrastructure, document processing, UI foundations, storage, search or validation when license, security, architecture and long-term maintenance are acceptable.

External libraries must not become an ungoverned second source of truth for P6 scheduling, duration, calendar, Progress/EVM, Resource/Cost or financial semantics.

## Principle 6 — AI must be accountable

AI results that influence project decisions must expose source context where available, distinguish facts from predictions, record the model/action context, preserve human approval for consequential changes and never silently mutate authoritative project data.


## Principle 6A — Production AI Project Controls Assistant is mandatory in V1

A capable, project-aware AI Assistant is a required V1 product capability and a release blocker. It must not be deferred to P3/post-V1, treated as a generic chat panel, or counted complete by static Smart Guide cards or contracts alone.

For V1, the assistant must be integrated through real application services and support the released project lifecycle: interpret supported-language requests; understand the active authorized project context; ingest supported project files and structured inputs; propose and create project/WBS/activity/calendar/relationship data; invoke authoritative scheduling and applicable project-control calculations; analyze returned facts and exceptions; prepare, preview and execute authorized changes; generate charts, reports and exports from persisted results; and report verified outcomes and failures.

The assistant must be grounded in scoped CUBI data, revision-aware and auditable. The server enforces user/project/tenant permissions on every operation. Consequential changes require explicit human approval according to policy. Rejection must produce no mutation. The assistant may not elevate access, fabricate a result, silently mutate authoritative data, or replace calculation authority.

V1 assistant personalization must let the user configure supported language/terminology, explanation depth, report/output preferences, reusable workflows and allowed autonomy/approval policy without granting permissions beyond the user's existing authority.

The normative implementation and acceptance specification is `docs/architecture/AI_ASSISTANT_V1_REQUIREMENTS.md`. Every release candidate must satisfy its integrated acceptance gate; incomplete criteria must be stated as limitations and block a claim of full/professional V1 readiness.

## Principle 7 — Typed interoperability

Dates, durations, decimals, currencies, quantities, IDs, versions, revisions and statuses must be represented as typed contracts. Excel, Project, API and offline packages must preserve calculation-ready types.

## Release Gate

Every release candidate must pass two sequential product gates:
1. **Gate A — P6/PMBOK conformance:** verified compatibility with the applicable P6/shared calculation baseline and alignment with the PMBOK/PMI governance baseline.
2. **Gate B — market completeness and leadership:** refreshed competitive benchmark, P0 closure, evidence-based depth review, cross-domain workflow coverage, AI/automation readiness, interoperability, client parity and release-quality verification.

Gate B does not override Gate A. A feature that increases market breadth but changes established P6/shared calculation semantics is rejected or redesigned.

## Decision gate

Every new feature is classified as P6/PMBOK baseline behavior, modern construction completeness, shared platform infrastructure, client presentation/integration, AI intelligence, or external validation/reuse.

Conflicts are resolved in this order:
1. Explicit P6 compatibility requirement for overlapping behavior.
2. Shared Core/domain integrity.
3. PMBOK/project-governance alignment.
4. Construction lifecycle completeness.
5. Market benchmark/release leadership target.
6. Cross-client parity and portability.
7. User experience and implementation convenience.

## Current market benchmark

The 2026 competitive review considered Oracle Primavera Cloud/P6, Procore, InEight, Autodesk Construction Cloud/Forma, Bentley SYNCHRO, nPlan, ALICE, Planera, Pillar, MeltPlan, Jet.Build, Anyset AI, Mastt, Nodes & Links, Trunk Tools, OpenSpace, Buildots and Document Crunch. The benchmark must be refreshed before release.

This is a product-governance benchmark, not a claim that every listed vendor implements every capability.