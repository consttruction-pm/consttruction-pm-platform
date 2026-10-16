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

## Principle 1B — Calendar configuration and user-selected changes must travel with project export/import

A project is not portable unless its complete effective calendar context is portable. Every project export/import, backup/restore, clone/template transfer and supported interchange workflow must preserve and round-trip:

- The referenced calendar definitions and immutable/version-pinned identities, including the calendar system (Jalali/Gregorian), working-day/working-time kind, work periods, weekly patterns, holidays, exceptions, special dates and effective-from/version metadata.
- The user's selected calendar for the project and each applicable activity, resource, relationship lag and other calendar-aware assignment, including explicit overrides, inheritance/source, precedence and the distinction between inherited defaults and user choices.
- Every user-created or user-edited calendar change and its effective settings, not merely the built-in/default calendar or a calendar display name.
- Calendar-related scheduling options, duration/lag interpretation settings, data date and the other calculation context required to reproduce results.
- Stable IDs, version references, project/tenant scope, source metadata and any dependencies required to resolve those references safely.

**Round-trip is mandatory:** export → import into a clean project/context → resolve the same selected/effective calendars and settings → recalculate through the one authoritative Shared Domain/Calculation Core → compare normalized inputs and results deterministically. Tests must prove that customized calendars and selections survive, including Jalali/Gregorian projects, resource/activity overrides, inherited calendars, holidays/exceptions, changed work hours, version conflicts and legacy packages.

Never silently replace a missing, conflicting or unsupported custom calendar with a default. Reject the import or mark the affected data as an explicit blocking/unresolved import item requiring user resolution; preserve the original source package and report what could not be mapped. Display locale and language must not rewrite the stored calendar system or scheduling semantics.

This is a release-blocking portability requirement, not an optional convenience. Calendar export/import must be covered by typed schemas, migration/version policy, audit history, user-facing import preview/errors, and regression tests for every supported project package/interchange format.

## Principle 1C — Documentation-first P6 calculation conformance and independent review

For every production-code change that implements or alters behavior overlapping P6 activity relationships, scheduling, resource-leveling priorities, calendars, constraints, scheduling calculations, or AI-generated numerical/project-control outputs, **source verification and independent semantic review must happen before implementation**.

Mandatory sequence:

1. **Pin the applicable source.** Record the product/profile (for example, P6 Professional or P6 EPPM), exact release/version, official Oracle document, section/field name, and direct URL. Do not infer one product's UI label, field meaning, wire type, or sort semantics from another product profile.
2. **Write the rule before code.** Record the source-derived rule and edge cases in the versioned calculation-conformance matrix. State what is known, what is not specified by the source, and which input/output contract is affected.
3. **Trace rule to behavior.** Link the canonical Shared Domain/Calculation Core field or function and deterministic regression tests to the conformance-matrix entry. Cover relevant interactions with relationships, calendars, constraints, resource capacity, sort direction, multi-row precedence and tie/blank/missing values.
4. **Obtain independent review before implementation.** A reviewer who did not author the interpretation must verify the source and proposed rule and record approval or rejection on the issue/PR. The code author must not self-certify this gate.
5. **Unclear means BLOCKED.** If the official source does not define a necessary semantic or interchange rule, mark the exact item `UNVERIFIED`/`BLOCKED`, keep production behavior unchanged, and obtain authoritative vendor evidence or a controlled versioned runtime fixture. Do not guess, silently coerce, or substitute a convenient default.
6. **Carry the evidence in every PR.** The PR must include a “Documentation-first conformance” section linking the source/version/section, matrix entry, independent review, affected code paths and tests, exact-head CI, and remaining blockers. A test-only change must explicitly state that production semantics are unchanged.
7. **No merge on missing evidence.** A green CI run verifies tested paths only; it does not prove P6 parity. Any unresolved applicable conformance item or missing independent sign-off blocks merge and release claims.

This rule applies to all human contributors and AI coding agents. It complements Principles 1 and 1A and Issue #1447; it does not authorize any change to Shared Core calculation semantics without the documented source-to-rule-to-test chain.

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

## Principle 8 — Global multilingual-by-design experience across every product layer

**Multilingual support is a foundational product requirement, not an optional UI translation task.** Every design, architecture, implementation, test, documentation update and release decision must account for every language supported by CUBI, across every surface and workflow. The language catalogue must be extensible without redesign and must not be limited by hard-coded language assumptions.

### Mandatory coverage

- **Navigation and interaction:** every menu, submenu, ribbon, tab, command, button, tooltip, dialog, field label, placeholder, validation message, error, notification, permission prompt, onboarding step and settings screen.
- **Planning and visual controls:** Gantt charts, timelines, networks, WBS trees, calendars, resource histograms, curves, dashboards, maps, chart axes, legends, annotations, data labels, status names, hover details, filters, grouping, sorting, table/grid columns and context menus.
- **Project information and outputs:** project names and descriptions, WBS/activity/resource/document/contract records, user-defined fields and values where localization is applicable, templates, imports, exports, reports, A4 print layouts, PDFs, spreadsheets, help content and user-facing technical documentation.
- **AI assistant:** language selection and detection, prompts, answers, reasoning summaries, voice input/output where supported, transcription, file/document extraction, clarifying questions, proposed actions, approval/rejection flows, citations/source labels, uncertainty statements, audit summaries and all failure/fallback messages. The assistant must respect the user's permissions and preserve the underlying project meaning and calculation authority in every language.
- **All client and service layers:** Web first, Desktop, and Mobile when delivered; API contracts, background jobs, emails, offline workflows, cached content, synchronization/conflict messages and server-generated documents must not introduce untranslated or inconsistent behavior.

### Required localization architecture

- Use stable language-neutral IDs/keys and centralized localization resources; do not hard-code user-facing strings in client, server, chart, report, or AI workflows.
- Support language-specific pluralization, grammatical forms, collation, search, sorting, text expansion, fonts, line wrapping, accessibility names and locale-aware formatting of dates, numbers, decimal separators, currencies, units and percentages.
- Support both left-to-right (LTR) and right-to-left (RTL) layouts, bidirectional/mixed-script text, and appropriate fonts. Layout direction and display locale must not alter stored values or Shared Core calculations.
- Keep language, locale, time zone, calendar system and calculation settings distinct. Display conversion/localization must never silently change stored project data, scheduling semantics, dates, durations, currency values or authoritative calculations.
- Provide versioned, downloadable/offline language packs for supported offline workflows; keep language fallback explicit and visible rather than silently mixing languages.
- Preserve original user-authored project content. Translation or transliteration of project data must be explicit, reversible where applicable, and must not overwrite the source text without authorization.
- AI responses, imports, OCR/document extraction and external integrations must report unsupported-language limitations clearly. They must never fabricate a translation or silently discard content.

### Acceptance and release gate

A language is not considered supported merely because a selector or a few translated labels exist. Each declared supported language must pass end-to-end coverage for navigation, forms, grids, Gantt/timeline, charts, calendars, reports/print/export, help, offline behavior, accessibility, RTL/LTR layout where applicable, AI input/output and error/approval flows. Tests must include long strings, plural forms, localized dates/numbers, mixed scripts, language switching during a project session, and round-trip preservation of project data.

Every feature PR must state which localization resources, languages, layouts and tests it affects. A missing translation, broken RTL/LTR layout, untranslated generated output, or language-dependent change to calculation results is a defect and release blocker for the affected supported language. Language coverage must be re-audited at each release gate.

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