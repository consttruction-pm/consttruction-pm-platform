# CUBI Engineering Intelligence Engines — Methods, Prerequisites and Delivery Scope

**Decision date:** 2026-11-04  
**Status:** Owner-approved product backlog and architecture target; implementation is not claimed  
**Tracking:** [Issue #1706](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1706)  
**Governing assistant rule:** [Principle 13 — Fully CUBI-owned, model-free Engineering Command Assistant](PRODUCT_PRINCIPLES.md) and [CUBI_INTERNAL_COMMAND_ASSISTANT_PRINCIPLE.md](CUBI_INTERNAL_COMMAND_ASSISTANT_PRINCIPLE.md).

This is the durable architecture and method catalogue for the engine suite. The linked issue is the active delivery work order; its capability, method, prerequisite, navigation and acceptance detail is reproduced below so the requirements are available with the architecture documents.

---

## Owner-approved scope

Add the following CUBI-owned, deterministic engineering and project-control engines to the product backlog and the internal command assistant. This is additive to Principle 13 and must obey the absolute no-model/no-provider rule: no Ollama, no third-party AI/ML model or inference runtime, no external AI service/provider, no AI API/key, no provider abstraction, no embeddings model and no fallback. These are software algorithms, rule systems, statistical methods, mathematical optimization and typed application services developed and governed by CUBI.

**Explicit exclusion:** BIM/model coordination, drawing/model interpretation, 4D/5D, map/model integration and the previously discussed item 8 are not part of this issue. Do not reserve menu items, create prerequisites or implement a partial scaffold for that scope. It remains subject to a separate product discussion and decision.

## Capability modules and required method coverage

### ENG-01 — Engineering Reasoning & Root-Cause Engine
- Versioned rules, decision tables, rule matching, forward/backward chaining, dependency/precedence reasoning, constraint propagation and deterministic rule scoring.
- Causal/dependency graphs; path tracing; root-cause trees; fault isolation; evidence-to-condition tracing; alternative/counterfactual checks.
- Explain each conclusion with source records, applied rules, assumptions, units and calculation revision; distinguish proven cause from plausible contributor.
- Assistant intents: explain, diagnose, trace cause, compare remedies, validate engineering rule.

### ENG-02 — Project Watchdog & Event Monitoring
- Event-triggered, scheduled and threshold-based monitoring.
- Absolute/relative thresholds, rate-of-change, rolling window, baseline deviation, moving averages, EWMA, control charts, CUSUM and robust outlier rules where the underlying data supports them.
- Hysteresis, debounce, de-duplication, suppression windows, severity, escalation, acknowledgement, snooze, assignment and resolution.
- Monitor schedule, float, constraints, progress, resource capacity, cost, procurement, material delivery, contractual deadlines, issues and risks.
- Every alert has source, detected time, rule/version, threshold, affected records and reproducible explanation.

### ENG-03 — Scenario Lab & Simulation
- Immutable revision-bound scenario fork/snapshot; isolated scenario edits; compare and discard/promote under approval.
- Deterministic what-if changes to durations, logic, constraints, calendars, shifts, capacities, crews, procurement dates, quantities, costs and progress inputs.
- Single-factor, multi-factor, sensitivity, batch and boundary scenarios; scenario matrix; scenario comparison and variance waterfall.
- Recalculate only through authoritative Shared Core/application services.
- Probabilistic runs are available through ENG-05; scenario runs must retain seeds, distribution assumptions and inputs for reproducibility.

### ENG-04 — Project & Portfolio Optimization
- Resource assignment/leveling, crew/equipment allocation, time-cost trade-off and schedule compression under explicit constraints.
- Linear programming, mixed-integer linear programming, constraint programming, branch-and-bound, greedy construction, local search, tabu search, simulated annealing and Pareto/multi-objective optimization where suited.
- Objective functions may include finish date, cost, resource peaks, overtime, productivity, risk exposure and contractual milestones; weights/priority must be visible and user-controlled.
- Feasibility checks, infeasibility explanation, bounds, algorithm/version, runtime limit and reproducible result.
- No optimizer may silently mutate an approved project; output is a scenario/proposal first.

### ENG-05 — Risk & Uncertainty Analysis
- Risk register scoring, probability-impact matrix, categories, risk owners, response/mitigation and residual risk.
- Qualitative/quantitative methods: FMEA/RPN, fault-tree and event-tree analysis, bow-tie analysis, expected monetary value, three-point estimates, PERT/Beta-PERT and triangular/normal/lognormal distributions where assumptions are justified.
- Monte Carlo and Latin-hypercube sampling, correlated risks, sensitivity/tornado analysis, risk exposure and schedule/cost confidence ranges (P50/P80/P90).
- Schedule risk analysis tied to actual activity network and calendars; reproducible seed, input provenance and distribution fit/assumption disclosure.
- Never present unsupported precision or a probability without adequate inputs.

### ENG-06 — Schedule & Project Quality Audit
- Logic/open-end checks, dangling relationships, cycles, invalid links, excessive/negative float, long-duration activities, excessive constraints, leads/lags, out-of-sequence progress and calendar/data-date inconsistencies.
- WBS completeness, duplicate/missing codes, invalid activity types, incomplete actuals, baseline integrity, resource/cost/quantity inconsistency and import/interchange losses.
- Configurable policy packs and transparent weighted quality index, with every score component and threshold visible.
- Pre-publication audit, continuous audit and remediation register; re-run after correction.

### ENG-07 — Construction Production & Productivity Intelligence
- Quantity/production-rate calculations, unit-rate and earned-quantity methods, earned hours, planned-vs-actual productivity and productivity variance.
- Crew composition/balancing, work sampling, time study, shift output, cycle-time analysis, equipment utilization/haul-cycle analysis, material consumption and production-capacity calculations.
- Location-based/repetitive-work planning, Line of Balance, takt planning, production-flow and workface constraint analysis.
- Production curves, deterministic learning/productivity curves, bottleneck detection and short-interval control.
- Method statements, construction method comparison, production assumptions and resource/quantity evidence.
- No image/BIM/model-based recognition is included in this issue.

### ENG-08 — Contract, Change, Claims & Delay Analysis
- Contract obligation/notice register, event chronology, notice deadline control, change/variation log, entitlement matrix, contemporaneous records and evidence register.
- Delay methods: Time Impact Analysis (TIA), impacted as-planned, as-planned vs as-built, windows/time-slice analysis, collapsed as-built/but-for, longest-path analysis, fragnet insertion and concurrency review.
- Criticality and causation checks, responsibility/compensability categories when contract rules support them, prolongation/disruption cost build-up and quantum tracking.
- Link events and evidence to activities, WBS, calendars, baseline/revisions, correspondence, instructions and cost records.
- Produce technical analysis and draft schedules of evidence; never claim to make a final legal determination.

### ENG-09 — Project Data Reconciliation
- Schema/field mapping, normalization of identifiers, dates, numbers, currencies, units and status vocabularies.
- Exact-ID, composite-key, multi-field and deterministic similarity matching (e.g. edit distance, Jaro-Winkler, token overlap/trigram) with explicit candidate ranking and match rationale.
- Duplicate detection, one-to-one/many-to-one conflict detection, source precedence, tolerance rules and missing/extra/changed/ambiguous/rejected classification.
- Two-way and three-way reconciliation for schedule, progress, quantities, timesheets, equipment, materials, procurement, costs, invoices, commitments and claims.
- Preview diffs; no silent overwrite or automatic match where ambiguity exceeds policy; source and row/field provenance retained.

### ENG-10 — Workflow & Automation Engine
- Event, schedule, threshold, state-change and manual triggers.
- Condition/decision branches, sequential and parallel steps, human tasks, approval gates, wait states, timers, SLA escalation, retry/backoff, idempotency, cancellation and compensating actions.
- Visual workflow builder, templates, versioning, run history, permissions, execution limits and failure/recovery queue.
- Enforce actor/project scope on every step; automation cannot broaden its own grants or bypass approvals.

### ENG-11 — Portfolio Capacity & Cross-Project Allocation
- Consolidated resource pools, role/skill calendars, time-phased demand/supply, availability, conflicts, utilization and capacity forecast.
- Cross-project allocation and leveling based on user-set priorities, contractual milestones, skills, location/availability constraints and project permissions.
- What-if allocation, bottleneck/shortage detection, multi-project scenario comparison and optimization through ENG-04.
- No unauthorized cross-tenant/project data aggregation.

### ENG-12 — Engineering Standards & Methods Library
- Versioned standards, clauses, specifications, work methods, checklists, procedures, formulas and engineering rules.
- Metadata: source/publisher, edition/version, effective dates, discipline, jurisdiction, applicability, clauses/sections, units, assumptions and rights.
- Rule-to-field/tool mapping, applicability conditions, conflict detection, supersession and review/approval lifecycle.
- Project/tenant/general scopes with permissions; cite the exact source and version used in a check.

### ENG-13 — Project & Work-Method Templates
- Organization-controlled and project-specific template libraries.
- Templates for EPS/WBS, activity networks, calendars, codes, resources/roles, quantities/productivity norms, cost structures, risk registers, quality checklists, reports and workflows.
- Versioning, ownership, release/deprecation, inheritance, clone/customize, diff/compare and controlled project instantiation.
- Template application always previews the proposed project delta and uses current application validation.

### ENG-14 — Decision Register & Decision Support
- Versioned decision records with problem, context, options, criteria, constraints, evidence, assumptions, owners, approvers and review date.
- Weighted decision matrix, pairwise comparison/AHP and TOPSIS where suitable; expose weights, normalization and sensitivity to criteria changes.
- Decision-to-project-record links, implementation status, outcome review and supersession history.
- User/authorized governance owner makes the decision; the engine presents traceable options rather than silently selecting policy.

### ENG-15 — Deadline, Reminder & SLA Control
- Contractual, procurement, submittal/RFI, approval, payment, notice, inspection, deliverable and handover deadlines.
- Business/working calendar-aware due-date calculation, timezone and Jalali/Gregorian display, recurring rules, lead-time reminders, escalation ladders and acknowledgement.
- Escalate by configured owner/role and effective permission; deduplicate reminders and audit delivery/acknowledgement.

### ENG-16 — Data Quality Profiler
- Completeness, validity, consistency, uniqueness, referential integrity, timeliness, provenance, range, distribution and cross-domain consistency checks.
- Dataset/record/field-level quality profiles, configurable weights and transparent score composition.
- Trend of data-quality debt, remediation assignment and regression checks after import/update.
- Distinguish missing source information from invalid or contradictory information.

### ENG-17 — Change Recovery, Undo & Decision History
- Typed command/change ledger, before/after snapshots, transaction boundaries and correlation IDs.
- Undo/redo for reversible supported actions; compensating transactions for non-reversible workflows; restore points and preview-before-restore.
- Permission and revision validation on every reversal; idempotent recovery; partial-failure reporting and audit.
- Do not claim external side effects (e.g. sent notices) can be erased; create a compensating record instead.

### ENG-18 — User/Organization Command Dictionary
- User, project and tenant-scoped abbreviations, synonyms, custom names, aliases, discipline vocabulary and preferred command phrases.
- Multilingual terms, transliteration and Persian/Arabic digit variants; collision detection, test phrase preview, versioning and import/export.
- User can add/correct terminology; tenant publication requires authorized review; the dictionary feeds the CUBI-owned parser only.

### ENG-19 — Contextual Smart Guide & Workspace Navigation
- Context-sensitive page/menu/selection help, task paths, field/option descriptions, prerequisite checks and actionable navigation.
- Detect current workspace window, selection, permission and capability availability; route users to real existing controls only.
- Step-by-step operational procedures, contextual warnings and shortcut lookup; do not fabricate a control or claim an unavailable function exists.

## Shared technical prerequisites (must be designed before dependent engines)
1. CUBI command envelope and intent/tool registry; normalized typed inputs, source language, selected project/window/record, actor, tenant, revision and correlation ID.
2. Canonical domain read models and application contracts for schedule, WBS, progress/actuals, resources, cost, procurement/materials, field operations, risks, contracts/claims, documents and portfolio.
3. Shared Core snapshot/query/recalculation API with immutable revision and calculation-context references; no engine-specific CPM/cost/EVM implementation.
4. Transactional domain-event/outbox contract, event subscriptions, scheduled job runner, durable queue, retries, cancellation, idempotency and dead-letter/recovery visibility.
5. Versioned rule registry, command dictionaries, policy packs, formula/method definitions and effective-date/applicability metadata.
6. Revision-bound scenario snapshot/fork/diff store; deterministic random seed and simulation run registry.
7. Optimization/simulation worker boundary with compute/time/memory limits, progress, cancellation, reproducibility and result provenance.
8. Typed units/quantities/currencies/timezones/calendars and controlled conversions; preserve Jalali/Gregorian metadata and working-calendar semantics.
9. Permission matrix and grants by tenant/project/revision/domain/operation/tool; approval binding, audit, fresh read-back and cross-scope isolation.
10. Data lineage/provenance and reconciliation framework, source precedence policies, immutable import staging and explicit unresolved mappings.
11. Notification, reminder, report and workflow infrastructure with localized templates and delivery/acknowledgement records.
12. Versioned engineering knowledge, standards and templates repositories, governance/review/publish flows, retention, backup/restore and migrations.
13. Golden datasets and deterministic acceptance harnesses for schedule, cost, risk, production, claims, imports, alert rules, optimization and multi-language commands.
14. Workspace command registry, navigation map, per-window Details inventories and toolbar/menu targets; every not-yet-built entry must remain disabled/planned until its real path is verified.

## Workspace menu reservation (design requirement; not a claim of live implementation)

Reserve one grouped entry under **Tools → Engineering Intelligence** rather than adding a new top-level menu or spreading controls across the shell. Keep the existing CUBI Assistant launcher as the single command entry point. Its command registry may invoke each engine's approved tools under the same grants.

Planned targets (all marked planned/disabled until end-to-end verified):
- Engineering Analysis & Root Cause — `window:engineering-analysis`
- Project Watchdog — `window:project-watchdog`
- Scenario Lab — `window:scenario-lab`
- Optimization Studio — `window:optimization-studio`
- Risk & Uncertainty — extends `window:risks` / `window:risk-analysis`
- Schedule & Project Quality — `window:project-quality`
- Construction Productivity — `window:construction-productivity`
- Contract & Claims Analysis — extends `window:changes-claims`
- Data Reconciliation — `window:data-reconciliation`
- Portfolio Capacity — `window:portfolio-capacity`
- Automation Center — `window:automation-center`
- Engineering Standards & Methods — `window:engineering-standards`
- Project Templates — `window:project-templates`
- Decision Register — `window:decision-register`
- Deadlines & SLA — `window:deadline-monitor`
- Data Quality — `window:data-quality`
- Recovery & History — `window:recovery-center`
- Command Dictionaries — `window:command-dictionaries`

Add relevant shortcuts to the existing Project/Organization/Insights navigation tree only where the object is naturally project-scoped or organization-scoped. Reuse existing Risks, Changes & Claims, Reports and Smart Guide surfaces rather than creating duplicate engines/windows.

## Delivery sequence and gating
- Phase A — foundations: command schema/registry; canonical read models; event/outbox + job queue; rule/dictionary registry; provenance, permissions, audit, localization and test harness.
- Phase B — read-only value first: Engineering Reasoning, Schedule/Project Quality, Data Quality, Data Reconciliation previews, Watchdog read/alert-only.
- Phase C — decision support: Scenario Lab, Risk & Uncertainty, Optimization, Portfolio Capacity, Construction Productivity.
- Phase D — governed workflows: Contract/Claims analysis, Decision Register, Deadlines/SLA, Workflow Automation, Recovery/Undo.
- Phase E — reusable knowledge/productization: Standards & Methods, Templates, Command Dictionaries and Smart Guide expansion; integrate assistant intents and all workspace entry points.

Phase labels are dependency order, not completion claims. Each engine is delivered as a tested vertical slice. Do not block read-only engines on write tools when their data is available; do block execution on missing permission, revision or source-data contracts.

## Acceptance
- All engines are called through typed CUBI-owned application tools and the shared assistant command registry.
- No third-party AI model/runtime/provider/service/key, model-derived embedding, or provider fallback exists in the shipped assistant path.
- Each method has an explicit input contract, preconditions, units, assumptions, deterministic behavior where applicable, source/version and test fixtures.
- Every analysis is reproducible and distinguishes fact, calculation, assumption, scenario, forecast and recommendation.
- All scenario/optimization/risk outputs are revision-bound and do not mutate the source project.
- All consequential changes use scoped proposal/approval, stale revision recheck, idempotency, audit, transaction safety and fresh read-back.
- All new menu entries are planned/disabled until real application path, permission tests, localization and browser E2E evidence pass.
- No changes to the existing visual workspace geometry or unrelated menu/window behavior are authorized by this issue.
- Excluded BIM/4D/5D scope is not implemented or represented in menus by this issue.
- No effort, weight or dates are baselined until the owner-approved schedule re-baseline is reviewed; earned progress remains zero until implementation acceptance.

## Related governing documents
- Principle 13 and `docs/architecture/CUBI_INTERNAL_COMMAND_ASSISTANT_PRINCIPLE.md`
- Workspace navigation: `docs/workspace/architecture/workspace-navigation-map.md`
- Window inventory: `docs/workspace/architecture/workspace-window-inventory.md`
- Visual shell: `docs/workspace/architecture/workspace-visual-shell-master-audit.md`

