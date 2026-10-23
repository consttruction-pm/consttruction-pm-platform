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

## Principle 1A.1 — Documentation-first calculation conformance evidence

Every formula and calculation in the P6-overlap scope must be assessed against applicable, versioned official P6 documentation before semantic implementation changes. This covers CPM dates and float, relationships and lag, constraints, activity/resource calendars, duration and unit arithmetic, resource leveling and priority order, progress/actuals, EVM, cost/spreads, calculated columns/rollups, and calculation-related import/export.

The source-derived rule, exact official source and section, edge cases, owning Shared Core implementation, regression tests, exact tested commit SHA and independent semantic review must be traceable in the [P6 Calculation Conformance Matrix](P6_CALCULATION_CONFORMANCE_MATRIX_2026-10-18.md). Every applicable row must be VERIFIED or have an approved OUTSIDE SCOPE disposition before a conformance claim. UNVERIFIED/BLOCKED semantics must not be guessed; tests must not be made green by weakening constraints, assertions or final resource-capacity validation.

This documentation-first gate is tracked in [Issue #1447](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1447). Passing one focused test does not certify the whole calculation family.

## Principle 1A.2 — Mandatory end-to-end Definition of Done: inputs, outputs, conformance, correction and acceptance

This cross-team rule applies to every implementation, defect, integration, calculation, API/data contract, import/export path, client workflow, AI action, test task and documentation task. It applies to all developers, reviewers, QA, and human/AI agents. **Starting an audit or obtaining a passing test is not completion. Any known discrepancy must be corrected and re-verified, not merely reported.** The mandatory task and acceptance checklist is [Issue #1492](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1492).

### Required work loop

1. **Establish the governing contract first.** Read current-main implementation, approved requirements, architecture/API/data contracts, existing tests and authoritative sources. For P6-overlap behavior, cite the applicable official, versioned source and exact section; never infer undocumented semantics.
2. **Map every input.** Record source, field, type, unit, null/empty/default meaning, validation and boundaries, tenant/project scope, revision/version, calendar/calculation context and provenance. Confirm that the real production entry point receives the expected values.
3. **Map every output and side effect.** Record computed/derived values, persistence and fresh read-back, DTO/API/export fields, downstream consumers, errors, constraints, audit/revision effects, permissions, determinism and round-trip behavior.
4. **Trace source → rule → input/output → production code → tests → evidence.** Include normal, boundary, invalid/negative, interaction, persistence, stale-revision, scope-isolation, round-trip and regression scenarios as applicable. A hand-built fixture or test-only adapter is not proof of the actual production path.
5. **Compare and correct.** When behavior diverges from the documented rule or contract, the implementation owner must fix the implementation/mapping, add regression coverage and continue until the supported behavior conforms. Reviewers must verify the correction, not merely leave findings. Never weaken a guard, constraint or fail-closed rule only to make a test pass.
6. **Handle ambiguity honestly.** If source semantics or product scope cannot be established, record the exact evidence and unresolved question as BLOCKED/UNVERIFIED, obtain an authorized decision and keep the item open. Guesswork is not conformance.
7. **Validate the real path on the same final SHA.** Run focused/regression tests, actual production-path persistence/read/execute/output integration tests and all applicable CI gates on the exact final candidate. Prior-SHA checks do not transfer to later commits.
8. **Record the disposition.** Record source version/section, rule, input/output map, changed paths, exact SHA, test commands/results, workflow links and independent reviewer disposition. When mismatch is found, record its fix and successful re-verification.
9. **Only then mark Done or award progress.** Required implementation must be integrated into current main or an explicitly approved delivery ref, exact-SHA checks green, conformance matrix updated, required independent review complete, and evidence linked. An audit, test request, open PR, comment, stale green run or documentation-only note cannot close a code defect.

Each work item must have one named implementation owner and an independent reviewer for calculation-semantic/cross-boundary changes. Link the task to a schedule activity and related issue/PR. The implementation owner remains responsible for fixing findings through acceptance; handing a finding to QA/review is not completion.


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