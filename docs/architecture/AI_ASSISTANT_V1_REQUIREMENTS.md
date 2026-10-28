# CUBI AI Project Controls Assistant — Cumulative V1 Contract

**Status:** Mandatory V1 release contract.  
**Governance:** Principles 1–11 in `docs/architecture/PRODUCT_PRINCIPLES.md`; product-owner scope in #1423, #1530 and #1540.  
**Purpose:** Consolidate previously approved assistant requirements in one traceable place. This document is additive: it does not remove, replace, defer or reduce any approved CUBI capability, client scope, calculation rule, security requirement or release gate.

## 1. Product goal

CUBI's assistant is a professional construction-engineering and project-controls partner, not merely a chat panel. It should help users understand, plan, build, analyze, control, explain and report on real construction projects. It must support different user expertise levels—from beginner/practitioner to specialist/professor—by adapting explanation depth to the current conversation and explicit user preference, asking focused questions, discussing options, accepting critique, revising recommendations and explaining why they changed.

The assistant should make recommendations for project structure, WBS and activity breakdown, relationships, calendars, resources, person-days and equipment, construction methods, risks, controls, reporting, page/layout organization and next steps. It must state assumptions, unknowns, units, confidence and evidence, and request missing project-specific inputs rather than inventing facts.

## 2. Cumulative capability inventory

All of the following remain required; a new learning/memory feature adds to this inventory and does not replace any item.

### 2.1 Project understanding and intake
- Understand natural-language instructions and supported voice input.
- Ingest supported Excel/workbook, document and other approved project files, with extraction/OCR only where the real runtime and format are verified.
- Identify project type, lifecycle stage, scope, constraints, known data and missing inputs.
- Preview, validate, reconcile and explain imported/proposed changes before committing them.
- Preserve source provenance and clearly surface unsupported fields, ambiguous mappings, contradictions and unresolved import items.

### 2.2 Project construction and editing
With current server-enforced grants and required approval, the assistant must be able to create and configure projects, project calendars, WBS, activities, activity details, relationships, lag/lead, resource assignments and supported project-control records through real CUBI application services. It must support project analysis and controlled modifications without bypassing ordinary authorization, revision, audit or validation rules.

### 2.3 Scheduling and project-controls analysis
- Invoke the authoritative Shared Domain/Calculation Core for schedule calculations and use its versioned result identity and project revision.
- Explain schedule logic, dates, constraints, float, criticality, progress and schedule performance using authoritative outputs and source evidence.
- Support the existing approved CUBI scope for resources, cost, progress, EVM, earned schedule, cash flow, contracts, procurement, claims, payments, risk and related project controls where implemented.
- Never invent a result for a missing or unsupported calculation path. State the limitation and create/retain a gap rather than silently approximating it.
- The assistant may propose methods and improvements, but it must not create a second CPM/calendar/resource/cost/progress/EVM engine or automatically modify the calculation core.

### 2.4 Professional outputs and recommendations
- Prepare grounded explanations, comparisons, risks, recommended actions, professional reports, charts and Gantt/report views from actual persisted/calculated state.
- Suggest appropriate monthly reports, report sections, page layouts, table columns, KPIs, charts and supporting evidence for the project type and reporting audience.
- Suggest staffing/person-day and equipment approaches with explicit productivity basis, assumptions, units, ranges, source, limitations and project inputs needed.
- Support editable A4/report and approved spreadsheet export workflows where their real implementation is available.
- Identify missing report information and distinguish required evidence from optional recommendations; never claim that a template or output is complete without runtime evidence.

### 2.5 Interaction and user adaptation
- Ask concise clarification questions when uncertainty materially affects the result.
- Offer alternatives with trade-offs, evidence, risks and conditions; invite the user to challenge or correct the recommendation.
- Revise advice when user constraints, feedback or verified evidence changes; explain what changed and why.
- Adapt terminology/detail based on demonstrated context and explicit user settings, not inferred demographic traits or assumed credentials.
- Preserve user choice. Feedback, agreement, disagreement and popularity are signals, not proof of technical correctness.

### 2.6 Learning from experience and knowledge research
The assistant must implement the learning lifecycle specified in `docs/architecture/INTERACTIVE_ENGINEERING_LEARNING_MEMORY.md` and tracked by #1540:
- Capture candidate lessons from corrections, misunderstandings, useful methods, failures, observed outcomes and validated research.
- Store private user, private project, tenant-shared and general knowledge in separate authorized scopes.
- Support admin-authorized Internet research of public engineering sources, preserving source, version/date, provenance, validity conditions and contradictions.
- Require validation, privacy/re-identification review, explicit policy/consent authorization and human approval before general cross-user publication.
- Reuse only approved generalized methods, formula contracts, checklists and process recommendations across users. Never disclose another account's project names, files, transcripts, schedules, quantities, costs, dates, staffing figures, results or reconstructable details.
- Store records durably in a versioned database; support retention/deletion, audit, export, backup/restore, V2+ migration, golden benchmarks, staged rollout and rollback.
- Never treat unvalidated interaction memory as authoritative engineering truth.

### 2.7 Permission, approval and audit
- Derive user, tenant, project and revision identity from trusted authenticated application context, never from model output or client-supplied identity claims.
- Apply least-privilege, default-deny grants separately for read, analyze, propose, create, update, delete, import, export, calculate and admin operations.
- Enforce project/tenant/domain/operation/tool scope in the server and repository; re-check current grant and base revision immediately before mutation.
- Bind consequential approval to the authenticated actor, exact proposal and base revision. Support rejection, stale-revision rejection, idempotency, transaction safety, rollback and fresh-read verification.
- Persist audit for successful and denied actions, approval/rejection, stale revision, errors and partial failures.
- Voice, import/OCR, background tools and offline queues use the same permission and audit rules.

### 2.8 Server Web and local Desktop modes
- Web assistant uses secure server-side orchestration and typed tools connected to real persisted application services.
- Desktop assistant must have a real local-inference runtime and work without Internet for the declared offline capabilities. A capability flag or mock provider is not proof.
- No hidden cloud fallback for Desktop-local AI. Device/model compatibility and capability limitations must be disclosed; the user must not unknowingly send local project content to a remote model.
- Local grounding uses authorized local project snapshots/files and the same versioned application contracts and authoritative Shared Core.
- Offline actions must remain auditable and safely reconcile through the declared sync/conflict contract. Unsupported disconnected actions must fail clearly rather than report phantom success.
- Native Mobile is part of V1 alongside Web and Desktop. It must use the same versioned application contracts and authoritative Shared Core. Voice/OCR/offline/mobile AI claims require real runtime evidence.

### 2.9 Model/provider, reliability and cost controls
- Provide a supported model/provider abstraction and secure server-side orchestration for Web; provide a genuine local model/runtime abstraction for Desktop.
- Use versioned typed tools mapped to real application use cases, not UI-only stubs or mock repositories.
- Enforce request, latency, token/compute, concurrency, resource and budget guardrails, telemetry, cancellation, error handling and controlled rollout.
- Support model replacement and version pinning without changing calculation semantics or permission policy.
- Keep retrieved web pages, papers, project files and tool output untrusted; resist prompt injection and do not let retrieved text grant permissions or override policy.

### 2.10 Multilingual and accessible behavior
- Respect the end-to-end multilingual-by-design principles for all declared languages, RTL/LTR layouts, accessible controls, help, voice, error/approval flows, reports and offline behavior.
- Preserve original user-authored content and distinguish display locale, language, timezone and calculation/calendar settings.
- Do not advertise a language, voice or offline feature as supported until end-to-end acceptance evidence exists.

### 2.11 Provider-key and toolchain rule

An external AI API key is **not** a universal prerequisite for CUBI; for the product profile it is not a dependency at all. The supported product path uses a local model/runtime, with no remote provider selection, no external model URL, and no hidden cloud fallback. Deterministic application capabilities must continue to work without a model where the relevant tools are implemented: project/WBS/activity ID allocation, known-format file parsing, local OCR/speech-to-text when packaged, persistence and approved-scope retrieval, Shared Core calculations, and deterministic reports/chart datasets.

Flexible natural-language understanding and semantic synthesis require a language model (or a deliberately limited deterministic dialogue). The local runtime needs installed model assets, compatible resources and explicit provisioning; it is not a promise of unlimited inference. If the local runtime/model is unavailable, deterministic tools must still work and semantic limitations must be explained. The product runtime factory must reject non-local provider selections and must never send user/project data to an external model.

The legacy remote adapter remains an isolated compatibility artifact in source and tests only; the CUBI production and preview compositions must use the local-only provider factory. The implementation shortlist, package boundaries, security requirements, file/MPP conversion limitations, local STT/OCR options, work-package order and acceptance tests are maintained in [CUBI Engineering Intelligence — Toolchain, No-Key Architecture and Acceptance Plan](CUBI_ENGINEERING_INTELLIGENCE_TOOLCHAIN_AND_ACCEPTANCE.md). That plan complements rather than replaces #1423, #1530, #1540, #1546 and #1617. No feature is complete until the real runtime, permission boundary, persistence and exact-head tests prove it.


### 2.12 Quantity takeoff, estimating, resources/equipment, risk, Form Builder and PMBOK reports

The product-owner-confirmed capabilities below are mandatory V1 scope and are tracked as a separate implementation work package in [#1617](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1617). This list is additive to the capabilities above; a conversational answer or mock form does not satisfy implementation.

**Quantity takeoff, BOQ and cost estimate**
- Provide an auditable quantity/measurement and bill-of-quantities workflow for explicitly supported source types. Keep source measure, formula/basis, unit, classification, waste/allowance, quantity, rate/currency, source/date/version, assumptions, inclusions/exclusions, estimate range, reviewer and approval state.
- Preserve the distinction between extracted/measured source values, deterministic calculated quantities, provisional assumptions and user-approved estimates. Reconcile source document/page/row/cell/object and mapping status wherever available.
- Deterministic CUBI application/calculation services must calculate unit conversions, quantities, waste, subtotals and financial totals. AI may interpret/organize evidence and suggest assumptions for review; it must not fabricate quantity, rate, productivity or price values.
- Link accepted quantity lines to WBS/work packages, activities, resources, procurement and cost records only through supported typed services. Show unsupported or ambiguous mappings and prevent a lossy import from appearing complete.

**Crew, resource and equipment recommendations**
- Propose role/crew composition, person-hours/person-days, equipment type/count, production basis, shifts, calendars and resource assignments only when sufficient scope/quantity and a defensible productivity basis exist.
- Every estimate includes units, source/version/date, assumptions, project/work-method applicability, uncertainty/range, evidence completeness and limitations. Unknown rates and capacities must remain unknown; do not fill gaps with invented market facts.
- Check current assignments, availability, capacity and calendars through CUBI's authoritative resource/scheduling services. Offer alternatives when overloaded; never duplicate or replace the Shared Domain/Calculation Core.
- Add or revise project data only as a versioned proposal bound to the authenticated actor, exact project revision and current grants. Require explicit user approval, transaction/idempotency protection, durable audit and fresh read-back.

**Risk identification and corrective action**
- Correlate only authorized, persisted project data with authoritative control indicators and supported field, safety, quality, equipment, issue, change and dependency records.
- A risk finding carries its category, affected WBS/activity/domain, likelihood, impact, confidence, horizon, source/revision references, trigger, consequence, owner, due date and uncertainty. Clearly label inferred risk versus an existing recorded issue.
- Suggest preventive, mitigation, corrective and contingency actions with rationale, sequence/dependencies, owner role, expected outcome and measurable follow-up. Actions remain recommendations until accepted through the application's permissioned, auditable workflow.

**Real Form Builder**
- Provide a persisted, versioned form-definition domain and interactive Form Builder. Generate typed sections/fields, requiredness, validation, conditions, attachments, localized labels, role visibility, responsible reviewer, approval route, layout and output mappings from a user brief or approved procedure.
- Provide preview, validation, version history, publish/share controls, submission capture, approval workflow, audit and fresh read-back. Connect responses to daily logs, quantities, resource consumption, inspections, issues or progress only using explicit mappings to real application services.
- Preserve submitted-data integrity when form definitions change, and test viewer/role denials, stale revisions, malformed/duplicate submissions, required fields and approval boundaries. A response that merely returns HTML or a suggested JSON form is not a Form Builder implementation.

**PMBOK-aligned report guidance**
- Tailor reporting suggestions to project context, lifecycle stage, audience and the repository's approved PMBOK baseline. Recommend appropriate deliverables, registers, decision records, report sections, KPIs and chart types without forcing irrelevant artifacts or implying certification.
- State each section's purpose, source data, as-of date, revision, evidence gaps, required/optional status and assumptions. Distinguish actuals, forecasts, estimates and recommendations.
- Reports and chart series must be built from authorized persisted datasets and authoritative calculation outputs; use only charts with valid underlying data. Provide localized, editable report output and A4 layout where the report infrastructure supports it.

**Acceptance rule:** #1617 remains an open P0 implementation gate until the source modules, contracts, repositories/migrations, UI, golden fixtures, authorization and approval paths, persistence/read-back, local-inference tests and exact-head CI/E2E evidence all pass. It must be reconciled into both CUBISITE and whole-product planning without silently changing either 100-point denominator. No documentation-only or open-PR progress counts as delivered functionality.

## 3. Hard architecture boundaries

1. **Shared Core authority:** the deterministic Shared Domain/Calculation Core remains the only authority for schedule, calendar, resource, cost, progress and EVM calculations.
2. **Application service boundary:** the assistant may act only through versioned typed application use cases and repository contracts.
3. **Identity and authorization:** client/model claims are never trusted as actor, tenant, project, grant or revision identity.
4. **Data isolation:** private user/project/tenant memories cannot be queried or returned outside their authorized scope. Cross-user reuse is restricted to approved generalized knowledge.
5. **No silent fallback:** missing evidence, unsupported behavior, unavailable model, offline limits or incomplete mapping must be disclosed and handled explicitly.
6. **No automatic core mutation:** learning and public research may improve recommendations and retrieval but may not silently modify the authoritative calculation core or project data.
7. **Evidence-gated completion:** a screen, prompt, document, mock, open PR or unit contract alone does not prove a production workflow. Require merged code, exact-head CI, integration/E2E tests and fresh persisted read-back.

## 4. V1 production vertical slice

The production assistant is not complete until an integrated end-to-end path proves:
1. authenticated user starts a natural-language or supported file-based request;
2. runtime identifies missing inputs and previews/reconciles candidate changes;
3. versioned typed tools call real authorized application services;
4. current grants and exact project revision are checked;
5. proposed mutations are shown and approved/rejected as required;
6. accepted mutations commit atomically and are auditable;
7. authoritative Shared Core calculations run against the correct persisted revision;
8. fresh read-back proves the committed state and result identity;
9. assistant explains outcomes with source/evidence and uncertainty;
10. report/chart/export comes from the real persisted/calculated state;
11. negative tests prove denied, rejected, stale, replayed, malformed, cross-tenant and partial-failure cases do not cause unauthorized mutation.

The production integration blocker remains #1530. The full V1 assistant blocker remains #1423.

## 5. Release gates and no-regression rule

The assistant is not release-complete until all relevant requirements in this document and #1423/#1530/#1540 pass on a single exact tested commit. Learning/memory cannot be used to mark the broader assistant complete. Existing P6 compatibility, PMBOK governance layer, website, desktop-local AI, mandatory mobile, localization, offline behavior, project features and release gates remain in force.

Jalal 5 must carry explicit activities for the complete assistant and learning/memory lifecycle. Activity estimates, dependencies, owners, dates and weights must be recalculated in the authoritative workbook with its total exactly 100.00 points and its dependency/owner-lane/forecast sheets verified. Until that workbook re-baseline is complete, learning/memory weights and dates are Pending re-baseline and earned completion credit is zero.

## 6. Evidence and current status

- #1423: open production V1 assistant end-to-end blocker.
- #1530: open production authorization, persistent audit and execution wiring blocker.
- #1540: open interactive learning, privacy-safe general knowledge, admin research and durable memory blocker.
- PR #1541: merged first contract slice—Principle 11, domain record contract, architecture specification and tests. It does not prove production learning.
- PR #1542: persistence repository slice is in review/CI; do not treat as complete until exact-head CI and review pass.
- Production assistant runtime, admin panel research/publish flow, end-to-end retrieval, backup/restore, V2 migration and learning benchmarks remain open until separately evidenced.

This contract is cumulative and must be reviewed alongside all existing product principles, issue acceptance criteria, scheduling/calculation contracts and release requirements. No previous capability is removed by this document.
