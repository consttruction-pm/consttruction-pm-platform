# Product Principles — Authoritative Baseline

Effective date: 2026-09-25

This document is the top-level product-governance reference. New requirements, architecture changes, calculations, workflows, client features and release decisions must be checked against these principles before implementation or release.

## Principle 1 — Primavera P6 + PMBOK alignment

For every capability that overlaps Primavera P6 scheduling/project-controls behavior, P6 semantics are the compatibility baseline and must be explicitly documented, implemented in the Shared Domain/Calculation Core and regression-tested.

PMI's PMBOK Guide — Eighth Edition (November 2025), together with ANSI/PMI 99-001-2025, is the project-management framework baseline for governance, value, scope, schedule, finance, stakeholders, resources, risk, procurement and adaptive tailoring. PMBOK is guidance, not a replacement for product-specific scheduling semantics.

No client, API adapter, external package or AI agent may silently redefine P6/shared calculation semantics.

## Principle 2 — Complete, current and leading Construction Management + Project Controls platform

After compliance with Principle 1, the product target is not merely feature parity with one competitor. **At the time of public/commercial release, the product is intended to be the most complete and forward-looking platform within its defined specialist scope of construction project management, construction control and project controls, based on a documented market benchmark current at the release gate.**

This is a release target that must be demonstrated with evidence, not treated as a marketing assertion. The benchmark must be refreshed before release and include leading incumbent platforms, emerging AI-native products and specialized point solutions that materially affect the product scope.

### Release-completeness requirements

- No P0 capability in the approved completeness matrix may remain merely planned at release.
- Every major competitor capability relevant to our specialist scope must be either implemented, intentionally integrated through a supported adapter, or explicitly documented as outside our defined scope.
- Each implemented capability must meet an agreed depth/quality bar, not only exist as a screen or placeholder.
- Cross-domain workflows must connect Schedule, Progress, Cost, Resources, Documents, Contracts, Procurement, Field, Risk and AI where their business relationship requires it.
- AI features must be construction-grounded, auditable and action-aware rather than generic chat-only features.
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