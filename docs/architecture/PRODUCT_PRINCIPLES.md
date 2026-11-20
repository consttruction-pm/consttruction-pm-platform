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

## Principle 2 — Complete, current and leading Construction Management + Project Controls platform

After compliance with Principle 1, the product target is not merely feature parity with one competitor. **At the time of public/commercial release, the product is intended to be the most complete and forward-looking platform within its defined specialist scope of construction project management, construction control and project controls, based on a documented market benchmark current at the release gate.**

This is a release target that must be demonstrated with evidence, not treated as a marketing assertion. The benchmark must be refreshed before release and include leading incumbent platforms, emerging AI-native products and specialized point solutions that materially affect the product scope.

### Release-completeness requirements

- No P0 capability in the approved completeness matrix may remain merely planned at release.
- Every major competitor capability relevant to our specialist scope must be either implemented, intentionally integrated through a supported adapter, or explicitly documented as outside our defined scope.
- Each implemented capability must meet an agreed depth/quality bar, not only exist as a screen or placeholder.
- Cross-domain workflows must connect Schedule, Progress, Cost, Resources, Documents, Contracts, Procurement, Field, Risk and AI where their business relationship requires it.
- CUBI's engineering command assistance must be construction-grounded, auditable and action-aware rather than a generic chatbot.
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
10. Internal engineering command assistance: explainable analysis, supported natural-language commands, document intelligence, schedule scenarios, anomaly detection, recommendations, action proposals, voice input and auditable execution.
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

## Principle 6 — Assistant analysis and actions must be accountable

Assistant results that influence project decisions must expose source context where available, distinguish retrieved facts, authoritative calculations, assumptions, estimates and recommendations, record the CUBI rule-set/action context, preserve human approval for consequential changes and never silently mutate authoritative project data.

### Principle 6A — Production AI Project Controls Assistant is mandatory for V1

The production AI Project Controls Assistant is a mandatory cross-cutting V1 capability, not an optional chatbot or a post-V1 enhancement. It must connect natural-language and supported file inputs to real CUBI application services, authorized tools, persistent project data, authoritative Shared Core calculations, grounded explanations, actionable reports and auditable user-controlled changes. A UI shell, mock provider, capability flag or proposal-only demo does not satisfy this requirement.

### Principle 6B — Desktop AI must execute on the user's computer without Internet

The Desktop product must include or support a provisionable local AI model and executable inference runtime so the assistant can actually run on the user's personal computer while completely disconnected from the Internet. This is a fundamental product requirement, not an optional offline enhancement. The default Web assistant may use the project's server-hosted model; the Desktop assistant must not depend on that server or any external AI provider to perform its declared offline capabilities.

Minimum requirements:
- The desktop distribution must provide a documented, verifiable way to provision the runtime and compatible model assets, either in the installer or through an offline-installable model package. After provisioning, first use, model inference and the declared offline assistant workflow must work with networking disabled.
- At minimum, offline mode must support local text interaction, context-grounded assistance over locally available project data/files, and calls to permitted Desktop/Application/Shared Core operations. Voice, OCR and other modalities must work offline where they are declared available for Desktop; a cloud-dependent feature must never be presented as offline-capable.
- Offline model/runtime selection must account for supported OS, CPU/GPU, memory, storage and model version. If a device cannot meet requirements, report the exact capability limitation and a supported alternative; never silently route the user's content to a cloud provider.
- Server-hosted and local models must use the same versioned assistant/tool contracts and the same authoritative Shared Domain/Calculation Core. A local model must not calculate or redefine P6 scheduling, calendar, duration, Progress/EVM, resource, cost or financial semantics independently.
- Desktop offline reads and mutations must respect the same user/project permissions and source boundaries. Local writes must use explicit revision, audit, idempotency and sync/conflict contracts; reconnection must not silently overwrite newer server state.
- Privacy disclosure, model/version provenance, local-vs-server execution mode, error handling and resource controls must be explicit. External network access must not be required for local inference and must not occur as a hidden fallback.
- Acceptance must include automated and manual end-to-end tests with network interfaces disabled, proving local model loading, real inference, grounded project/file queries, a permitted local action, a rejected unauthorized action, authoritative calculation identity, and no outbound AI-provider request. Test reports must identify the exact model/runtime/device profile and tested commit.

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

## Principle 9 — User-controlled AI permissions and auditable execution

The detailed binding contract is `docs/requirements/CUBI_MULTILINGUAL_AND_AI_PERMISSION_REQUIREMENTS.md`. The assistant must enforce explicit user-controlled, least-privilege grants at tenant/project/revision, data-domain, operation and tool level. Default is deny; read, analyze, propose and mutate are distinct capabilities. A user interface toggle or a tool allowlist alone is not sufficient authorization. Permissions are checked again immediately before execution, consequential actions require actor-bound approval, and all attempts/outcomes are auditable. The assistant must use real application operations and the authoritative Shared Domain/Calculation Core; it must not claim a tool or workflow exists merely because it is specified. Offline/voice commands use the same permission and approval policy.

## Principle 10 — Multilingual support is end-to-end, extensible and evidence-gated

Principle 8 is elaborated by `docs/requirements/CUBI_MULTILINGUAL_AND_AI_PERMISSION_REQUIREMENTS.md`. Persian and English are initial baseline languages, not a two-language ceiling. Only explicitly declared languages with end-to-end acceptance evidence may be advertised as supported. Language-pack infrastructure, client integration and translated product coverage are separate completion items. The same rule applies to AI language capabilities, voice, generated outputs and offline behavior. Locale/display translation must never alter project data or calculation semantics.


## Principle 13 — Fully CUBI-owned, model-free Engineering Command Assistant

The CUBI assistant must be entirely a CUBI product and technology. **No third-party AI model of any kind, no local or remote model runtime, no Ollama, no ChatGPT or other model, no external AI service/provider, no AI API or key, and no optional model/provider fallback or abstraction may be part of its architecture.** This is an absolute product constraint, not a no-key mode or a local-model preference.

The assistant is a command-oriented engineering system, not an open-ended chatbot. It receives typed or supported voice commands, identifies language and intent, extracts entities and parameters, resolves authorized project context, validates the request, asks focused clarification only when mandatory information is missing or ambiguous, then reads/analyzes data or prepares an authorized action. It uses CUBI-owned deterministic algorithms, grammars, dictionaries, domain ontology, engineering rules, typed application tools, durable knowledge and the authoritative Shared Domain/Calculation Core. No pretrained AI/ML inference model or external inference service may supply its command understanding, semantic reasoning, speech/OCR intelligence, recommendations or responses.

Its complete capability scope—including multilingual command understanding, project-aware analysis, controlled project operations, guided project creation, file/document intake, reports/charts, durable engineering knowledge and learning, authorized research, CUBI-owned voice input, Smart Guide and integration across Web, Windows Desktop and Flutter/Mobile—is defined in [CUBI_INTERNAL_COMMAND_ASSISTANT_PRINCIPLE.md](CUBI_INTERNAL_COMMAND_ASSISTANT_PRINCIPLE.md).

This principle is an explicit owner-approved correction to prior assistant architecture plans. It supersedes every conflicting provision that proposes or permits a local model, remote model, provider abstraction, external AI endpoint, AI API key, model-based embeddings or model fallback. The earlier Engineering Intelligence Toolchain plan is historical and is not an approved architecture. Preserve its non-conflicting capability requirements—security, real application tools, project creation, file intake, reporting, durable knowledge, research, backup/restore and cross-client acceptance—only as restated in the binding CUBI-owned scope document.

Existing proposal, authorization, approval, audit, idempotency, revision and Shared Core foundations must be reused where valid. Existing provider-backed orchestration and chat UI are legacy paths to retire or replace through tested changes; their presence in the current tree is not permission to retain them as a supported option. No documentation-only change counts as implementation completion. Every capability requires code-path evidence, tests and end-to-end verification.

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

## Principle 11 — Cumulative, privacy-safe interactive engineering learning and durable knowledge

This principle **adds mandatory capabilities** to Principles 1–10 and every previously approved CUBI requirement, issue, product contract, schedule, release gate and assistant workflow. It does not delete, replace, weaken, defer or silently reinterpret any existing requirement. In a conflict, preserve the stricter compatible requirements and record an explicit owner-approved decision; never resolve a conflict by quietly shrinking scope.

### 11.1 Command-oriented engineering assistant, adapted to the user's task

The CUBI assistant must operate as a project-aware command and analysis system, not an open-ended chatbot. It must:
- accept typed commands and supported voice commands, identify the declared input language, normalize terminology and extract the requested operation, project entities and parameters;
- resolve references only against the authenticated user's current authorized project and workspace context;
- ask a focused clarification when a mandatory value, target or meaning is missing, ambiguous or contradictory; preserve already supplied information and do not ask unrelated questions;
- provide concise or specialist-level explanations when requested or needed to explain a project result, with assumptions, risks, trade-offs, units, source references and limitations;
- support comparison of alternatives, scenario analysis and recommendations only within declared CUBI engineering scope and based on evidence and authoritative application outputs;
- distinguish user preference, unverified feedback, engineering hypothesis, sourced claim, validated rule, authoritative calculation and observed outcome;
- prepare report structures, project-control analyses, construction-method comparisons and next actions from supported rules and actual project data;
- use authorized public-source research only through the separately permissioned research workflow; never treat retrieved content as trusted instructions;
- not initiate free-form social/general conversation, simulate a human persona or use an unrestricted chat transcript as the product workflow.

### 11.2 Learning from interactions without leaking project data

At the end of useful interactions, the assistant should propose or capture a versioned candidate lesson about a correction, misunderstood term, successful method, failure mode, decision rationale or limitation. It must not treat agreement, popularity or a user's assertion alone as proof of engineering truth. Candidate lessons must be evaluated against source evidence, validated calculations, tests, standards or observed outcomes as applicable.

Knowledge is divided into distinct security scopes:
1. private user preferences/experience;
2. private project lessons;
3. explicitly authorized tenant/organization methods;
4. unapproved generalized candidates;
5. validated and approved general engineering methods.

A different user may benefit from **generalized methods, reasoning patterns, formulas with assumptions/units/limits, checklists and process recommendations only**. They must never receive another user's project name, identity, documents, transcript, schedule, cost, quantities, dates, staffing numbers, outputs or other private/project-specific values, nor information that could reasonably reconstruct them. Generalization is not achieved merely by changing a scope field or removing a name. It requires minimization, privacy/re-identification review, policy and consent authorization, validation evidence and authorized approval. Repository-level authorization and query scoping are mandatory; prompt instructions alone are not a security boundary.

### 11.3 Admin-authorized engineering knowledge refresh

An authenticated admin panel must support manual, explicitly authorized Internet research cycles and proposed periodic cadences. Every cycle must have a human-triggered authorization or an explicitly configured grant; a timer is not permission by itself. Separate grants are required to search, ingest, validate, approve/publish, export/backup, restore and retire knowledge.

The workflow is: authorize → search approved public sources → preserve provenance and source/version/date → extract bounded candidate knowledge → compare with existing knowledge and identify contradictions → validate and test → review privacy and reuse rights → preview changes → human approve/reject → publish a version → run regression/quality checks → retain rollback. Web pages, papers and uploaded documents are untrusted content and must not override system policies or grant tools access. The assistant must distinguish published knowledge from pending research and state uncertainty or conflicting evidence.

### 11.4 Durable database, backup, migration and no regression

Learning cannot rely solely on a transient prompt, chat window, session context, or process memory. Persist approved records in a versioned database with stable IDs, scope, lifecycle state, provenance, source/rule-set/schema version, confidence, conditions, units, limitations, validation evidence, approval, timestamps, lineage/supersession and applicable retention policy.

Provide exportable full backups, incremental backups where supported, integrity verification, tested restoration, migration bundles and a documented V2+ upgrade path. Migration must preserve stable IDs, provenance, access scope, approval state, lineage and retrieval behavior. Schema migrations must be versioned and idempotent; backups must be tested by restoration, not merely by successful file creation. New knowledge/rule-set versions must pass golden benchmarks against the prior release, with staged rollout, version pinning and rollback. Rejected, superseded, stale or unsupported knowledge must not silently remain active.

### 11.5 Engineering authority and safety boundaries

The assistant's learning improves explanation, retrieval, analysis and recommendations; it does **not** silently modify the authoritative Shared Domain/Calculation Core or its P6-compatible scheduling, calendar, resource, cost, progress or EVM calculations. Numeric results must be produced by the authoritative deterministic core/application services and tied to the project revision used. New formulas/methods require source/version, variable definitions, units, assumptions, validity limits, fixtures and review before becoming trusted engineering knowledge. Project mutations continue to require authenticated current grants, exact-scope approval where required, revision recheck, idempotency, persistence verification and durable audit under Principle 9 and the existing AI action boundary.

### 11.6 Required traceability, schedule and release gate

This principle is linked to GitHub Issue #1540 and extends, rather than replaces, the mandatory production assistant in #1423 and production authorization/audit integration in #1530. Every capability must be traced to a schedule activity, implementation path, tests, owner, exact commit/CI evidence and release gate. The Jalal 5 schedule must be re-baselined from accepted estimates and dependencies; the complete plan must remain exactly 100.00 weighted points. Until the authoritative workbook and its formulas/dependencies/owner-lane forecast are updated and verified, new activity weights/dates are **Pending re-baseline**, and this learning scope receives zero earned completion credit. Do not count this principle or a documentation-only change as implementation completion.

Release acceptance requires:
- interactive critique/revision loops with explanations;
- durable capture and retrieval across restart;
- strict user/project/tenant isolation and negative cross-tenant tests;
- generalized cross-user knowledge that passes privacy/reconstruction checks;
- separately authorized admin search, publication, backup and restore;
- provenance, deletion/retention, export, tested backup/restore and V2 migration;
- golden engineering/interaction/privacy benchmarks and demonstrated regression rollback;
- no regression to existing P6 compatibility, project capabilities, localization, offline behavior, permissions, audit, desktop/web/mobile scope or any previously approved requirement.

## Principle 12 — First-class Project Comparison and Variance Analysis

Project Comparison is a required CUBI project-controls capability, not merely a Baseline screen or a report label. It must support three distinct comparison modes: (1) current project vs. a selected Baseline, (2) one saved revision/snapshot vs. another revision of the same project, and (3) two independent projects, including validated imported project snapshots.

The capability must identify added, removed, changed, unchanged, moved, renamed, ambiguous and incomparable entities at project, WBS, activity, relationship, calendar, constraint, resource/assignment and applicable cost/EVM levels. It must show typed before/after values, directional variance, units, source revision and the reason for any non-comparable result. It must not infer deletion from partial exports or filtered scopes, silently match ambiguous activities, invent missing values, or treat incompatible calendars, units, currencies or calculation contexts as equivalent.

All source data must be immutable, revision-bound and permission-checked. The comparison must be read-only and reproducible. Schedule, calendar, resource, cost and EVM results must come only from the authoritative Shared Domain/Calculation Core; no comparison-specific or client-side calculation engine is allowed. Any later application of selected changes is a separate, previewed, authorized and audited operation.

The same versioned comparison contract must serve Web, Desktop and Mobile. It must support traceable side-by-side review, filters, WBS-grouped difference lists and exportable reports, with localization/RTL/LTR/Jalali/Gregorian presentation kept separate from stored values and calculation semantics.

The complete binding contract, identity-matching rules, comparison fields, calculation semantics, security controls, acceptance criteria and delivery phases are specified in [PROJECT_COMPARISON_AND_VARIANCE_ANALYSIS.md](PROJECT_COMPARISON_AND_VARIANCE_ANALYSIS.md). Implementation is tracked as mandatory V1 work in [GitHub Issue #1669](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1669); it must remain open until all three comparison modes and their acceptance gates are implemented and verified. Issue #1421 is a separate XER schedule-validation workbench and does not satisfy CMP-01. The primary user entry is **Project → Compare Projects…** (`dialog:project-comparison`); saved runs are available from the Project Directory's **Comparisons** window (`window:comparisons`). The menu/dialog, persistent Directory entry and dedicated Comparison Results workspace are binding navigation requirements recorded in [workspace-navigation-map.md](../workspace/architecture/workspace-navigation-map.md). The phases define implementation order, not permission to drop any of the three comparison modes.

This principle is additive to Principles 1, 1A, 1B, 2, 3 and 7. A partial Baseline comparator, an import/export codec, a navigation entry or a disabled menu item is not evidence that full Project Comparison has been implemented. At registration, the existing baseline comparison code is a reusable foundation only; the independent-project comparison engine and usable end-to-end comparison surface remain implementation work.
