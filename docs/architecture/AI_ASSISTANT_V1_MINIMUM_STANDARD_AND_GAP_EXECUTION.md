# CUBI AI Assistant V1 — Minimum Standard, Internal Tooling and Gap-Closure Execution Plan

**Status:** Owner-directed product/architecture baseline  
**Date:** 2026-11-22  
**Repository:** `consttruction-pm/consttruction-pm-platform`  
**Priority:** P0 — Engineering first; Enterprise reuses the same orchestration and shared primitives  
**Related work:** #2093, #2090, #2019, #1423, #1530, #1799, #1989, #1706

> This document records the minimum product standard and the concrete internal tools/services that must be reused, completed, built or connected. It is not evidence that every listed capability is already implemented. Current code, tests and exact-head runtime evidence determine delivery status.

## 1. Binding product decision

CUBI AI Assistant is the product's internal operational assistant, not merely a chat panel. It must understand a user's request in the active project/module context, read authoritative project facts, analyze and validate them, prepare a typed proposal, show evidence and expected effects, obtain explicit human approval for consequential writes, execute through canonical CUBI application services, verify persisted results by fresh read, and record a durable audit trail.

The assistant is CUBI-owned and must not require OpenAI, Claude, Gemini, Qoder, or another third-party model/provider/API as its runtime intelligence or execution dependency. Qoder and other coding agents are development tools only. Do not introduce provider-key gates, hosted inference, external embeddings, model downloads, or an external fallback into the product runtime. Use the existing CUBI-owned deterministic command/intent, domain-rule, knowledge and orchestration architecture. Where intent cannot be resolved safely or facts are missing, ask a focused question or abstain; never fabricate a result.

The assistant is not the owner of domain facts or calculations. It is an orchestrator and user-facing reasoning/interaction layer over canonical CUBI services. There must be one command/orchestration entry point, one shared scheduling/calculation authority, canonical repositories and one authoritative persisted project state. No parallel scheduler, browser-side authoritative calculation, duplicate importer, duplicate risk engine, client-side proposal creation, or shadow database is allowed.

## 2. Minimum V1 capability standard

V1 is not complete until all applicable requirements below are demonstrated end-to-end on the exact tested commit.

1. **Context:** resolve authenticated subject, tenant/organization, active environment, project, selected object, current revision, data date, locale/timezone and applicable permissions from trusted server-side context.
2. **Command intake:** accept typed/free-text command input and supported project-file intake; resolve it to a versioned typed command with explicit objective, scope, constraints, units, dates/calendars and requested operation. Do not trust model/client claims for identity or permission.
3. **Grounded reads:** retrieve current persisted facts through canonical read models/services; label fact, derived value, forecast, user assumption, missing and stale data distinctly; include source/revision/calculation provenance.
4. **Analysis and validation:** use domain services and authoritative calculation outputs; expose diagnostics, warnings, blockers, unsupported fields and uncertainty. Never infer missing project facts.
5. **Proposal and preview:** create a durable typed proposal/change set with exact target objects, before/after values, impact, assumptions, validation, source revision, tool identity and idempotency identity. Display a reviewable preview in AI Workbench.
6. **Simulation:** run calculations only through the authoritative Shared Core and supported domain services. Simulations must be isolated and revision-bound; they must not mutate the live project.
7. **Human decision:** require explicit approval for consequential writes, bound to exact proposal version, actor, scope and base revision. Support approve, reject with reason and request-changes where implemented. No blanket or future approval.
8. **Execution:** reauthorize immediately before execution; re-read and compare revision; validate preconditions; execute via canonical application use cases and atomic transaction where supported; enforce idempotency and fail closed on stale/unauthorized/invalid requests.
9. **Verification:** perform fresh read-back from the authoritative repository and compare the persisted result to the approved change set and expected calculation identity. A successful HTTP response alone is not proof.
10. **Audit and recovery:** durably record intake, tool selection, reads/provenance, proposal, decision, execution, denial, stale conflict, failure and verification. Preserve immutable run/version history and expose rollback/compensation only where a real safe contract exists.
11. **Security:** default-deny grants scoped by subject, tenant, organization, project, domain, operation, tool and revision. Enforce read/analyze/propose/create/update/delete/import/export/calculate/admin as distinct capabilities. No cross-tenant/project leakage.
12. **Honest availability:** every unavailable capability returns an explicit blocked/partial state with the exact missing service or permission. No decorative enabled controls, fabricated data, silent fallback or false completion claim.
13. **UX:** chat is the command intake, clarification and status surface; complex analysis, import, scenario and decision outputs open in AI Workbench specialist studios. Every action maps to a real API/service.
14. **Portability:** shared domain contracts and orchestration remain usable by Web, Windows and Flutter clients; clients do not own business rules or authoritative calculations.
15. **Localization/accessibility:** command schemas, diagnostics, dates, numbers, units, RTL/LTR and all supported product locales use the canonical localization conventions.

## 3. Canonical architecture and responsibility boundaries

```text
User
  -> Engineering / Enterprise workspace context
  -> one CUBI Assistant command entry
  -> Command Orchestration Layer (#2093)
  -> trusted Context Resolver
  -> Assistant Tool Registry + typed schemas
  -> policy / scoped-grant / authorization gate
  -> AI Workbench (analysis, import, scenario, decision studios)
  -> canonical domain application services
  -> Shared Scheduling & Calculation Core (single authority)
  -> canonical repositories / primary database
  -> fresh read-back + calculation/provenance verification
  -> append-only audit / immutable run history
```

AI Workbench is a presentation and interaction layer. It does not own project state, scheduling logic, import persistence or domain calculations. Assistant tools call application use cases, not raw database writes and not UI handlers. Domain services remain callable without the assistant.

## 4. Internal tool registry — required contract

Complete or extend one central registry attached to the existing Command Orchestration Layer. Do not create a second registry/orchestrator per studio. Every registered tool must declare:

- stable tool ID and version; canonical capability/domain owner;
- typed input/output schema, required fields, units, date/calendar semantics and locale behavior;
- read/write/calculation classification and side-effect declaration;
- tenant/project/object scope and required grant;
- required source revision and stale-revision behavior;
- preconditions, validation rules and explicit abstention conditions;
- whether human approval is required and the exact proposal type;
- idempotency/replay behavior and transaction boundary;
- audit event/provenance contract;
- error taxonomy and fresh-read verification procedure;
- authoritative service/repository and calculation engine identity;
- capability state: LIVE_VERIFIED, WIRED_READ, WIRED_WRITE, PARTIAL, SHELL_ONLY, PLANNED, BLOCKED or VERIFY.

### Minimum tool families

| Tool family / example IDs | Required behavior | Canonical owner to reuse or complete |
|---|---|---|
| `project.read`, `project.create`, `project.update` | Project facts/configuration and controlled lifecycle | Project lifecycle/application services |
| `workspace.read`, `wbs.read`, `activity.read` | Revision-bound project context and domain objects | Canonical workspace/project read models |
| `import.inspect`, `import.validate`, `import.map`, `import.preview`, `import.apply` | Secure intake, inventory, mapping, validation, diff, approved atomic apply | Project exchange/import application service (#1799) |
| `schedule.calculate`, `schedule.read`, `schedule.compare` | Calculate/read/compare with engine identity and revision | Shared Scheduling Core and schedule snapshot/read services |
| `scenario.create`, `scenario.edit`, `scenario.run`, `scenario.compare` | Isolated fork, immutable run, deterministic comparison | Revision-bound Scenario service (#1989), Shared Core |
| `resource.read`, `resource.analyze`, `resource.level` | Assignment, capacity, availability and leveling | Canonical resource/leveling services |
| `cost.read`, `cost.analyze`, `evm.calculate` | Cost/EVM only when source data and method are sufficient | Canonical cost/EVM services |
| `risk.read`, `risk.create`, `risk.update`, `risk.analyze` | Risk register and supported quantitative analysis | Existing Risk API/repository; extend only missing quantitative services |
| `progress.read`, `tracking.read` | Actual progress and tracking | Canonical progress/tracking read models |
| `document.search`, `document.read`, `document.version` | Scoped document retrieval and version provenance | Existing document content/version repository |
| `report.preview`, `report.generate`, `report.export` | Reproducible outputs from persisted facts/calculation runs | Canonical report-run/export services |
| `decision.propose`, `decision.approve`, `decision.reject`, `decision.execute` | Exact-version proposal lifecycle | Existing AIActionRuntime/Decision & Approval; close Engineering contracts |
| `audit.read` | Authorized history and execution evidence | Append-only audit/event repositories |

Tool names are illustrative stable contract IDs; reconcile with existing canonical IDs before implementation. Do not register a tool until its real service, authorization and tests exist. A registry entry must never disguise a stub as live.

## 5. Existing implementation to preserve and connect

The following are established by the current AI Workbench implementation ledger (updated 2026-11-21); re-verify current main before each implementation slice:

- Command foundation: PR #2093 merged as `eed937de1`.
- Workbench route, server boundary, command panel, context resolver, authorization, status and audit integration.
- Risk Studio: risk create/update with revision guard and audit history (`WIRED_WRITE`).
- Project Analysis: canonical workspace read, baseline register and earned-value read with insufficient-data handling (`WIRED_READ`).
- AI action proposal lifecycle: propose → human decision → guarded execution; stale-revision and duplicate guards in the mounted runtime.
- Forms library CRUD/version/submission/review/audit and Knowledge Store read path.
- PostgreSQL migration ledger (15 steps / 94 tables) and integration verification; production PostgreSQL composition exists, but the preview browser journey must not be described as proof of Supabase/production PostgreSQL.
- Assistant turn route uses the canonical AI action client and server-side proposal creation; transcript does not approve or execute.
- Preview browser journey and automated tests exist; current ledger records Python, web, typecheck/build and browser checks.

These existing pieces must be inspected and reused, not rewritten from scratch. Verify exact current implementation and runtime composition; documentation is not proof by itself.

## 6. Verified gap register and required closure

| ID | Gap / current evidence | Required work | Priority / dependency |
|---|---|---|---|
| G-01 | Project import staging validates the 94-sheet reference workbook but has no complete project-import persistence/apply engine. Existing exchange application is register-level and incomplete for whole project import. | Complete versioned project exchange/import contract; support project/EPS, WBS, activities, relationships, calendars, resources/roles/assignments, baselines, progress, constraints, costs/expenses and supported metadata; mapping, row-level diagnostics, deterministic diff, safe file intake, transaction, idempotency, immutable run, audit and fresh read-back. | P0; #1799 |
| G-02 | Seven-tab Import Staging UI is PARTIAL; only source validation is proven. | Connect Source, Inventory, Mapping, Validation, Schedule Preview, Options and Final Review to real staging services. No live project creation before exact confirmation. | P0; G-01 + #2090 |
| G-03 | Scenario Lab is a shell; no persisted revision-bound scenario service is verified. | Implement isolated scenario records/snapshots, typed change sets, run identity/hashes, canonical scheduler invocation, comparison/diff, immutable history, authorization and PostgreSQL tests. | P0; #1989 |
| G-04 | Scenario-specific approval/promotion and general Engineering proposal execution contract are incomplete; preview has limited activity.create proof only. | Define typed Engineering action contracts bound to source revision; reauthorize, atomic apply, idempotency, audit, conflict handling and fresh read-back. Keep scenario promotion separate and later-gated. | P0; #1989 + #1530 + existing AIActionRuntime |
| G-05 | Scoped grant adapter exists but production identity/grants are not proven wired through every action path. | Wire trusted authenticated subject/current grants into every text, import, voice/offline and background action entry point; default deny; re-check immediately before mutation; persistent denial/success audit. | P0; #1530 |
| G-06 | Assistant tool availability is not yet demonstrated as one complete versioned registry covering canonical domain services. | Inventory all current service/API contracts; add central typed registry to #2093 orchestration; capability discovery and explicit BLOCKED/PARTIAL reasons; tool contract tests. Reuse existing services. | P0 |
| G-07 | Resource/capacity/forecast and some resource leveling outputs are not fully exposed to the assistant. | Connect existing authoritative assignment, capacity and leveling services; build only missing domain contracts; no synthetic capacity or second leveling engine. | P1 after core P0 |
| G-08 | Cost/EVM reads are conditional; cost forecasting and complete source data are not established in preview. | Connect authoritative cost/expense and EVM services; expose missing baseline/currency/data-date inputs; calculate only with sufficient persisted data and provenance. | P1 |
| G-09 | Risk register writes exist, but quantitative risk/uncertainty coverage is incomplete. | Connect supported deterministic risk analysis; implement quantitative/Monte Carlo only with approved distributions, correlation, seed, reproducibility and evidence. | P1 |
| G-10 | Document repository and report-run export primitives exist, but assistant discovery/analysis/report tools need complete scope and evidence contracts. | Connect scoped document search/read/version and report preview/generate/export; cite source document/version, report run and calculation identity. | P1 |
| G-11 | Workbench integrated acceptance remains partial across import, scenario and decision. | Build real-browser end-to-end journeys against supported real persistence; prove read → analyze → stage/simulate → propose → approve → execute → fresh read → audit, plus negative cases. | P0 after G-01..G-06 |
| G-12 | Non-English Workbench strings and assistant contextual behavior are incomplete. | Complete canonical localization, RTL/LTR, dates/numbers/units and contextual capability coverage without duplicating assistant logic. | P1 / V1 release gate per localization standard |

### Explicitly not gaps to solve by duplication

- Do not create another CPM/scheduling engine.
- Do not create a second resource-leveling, risk, import, report, approval or audit system where a canonical service exists.
- Do not create a separate assistant runtime for each studio or environment.
- Do not add a third-party model/provider dependency to satisfy "AI" branding.
- Do not treat a shell, fixture, mock, deterministic planner response or successful HTTP response as proof of real domain execution.
- Do not make Enterprise a dependency for Engineering V1; Enterprise consumes shared primitives after Engineering contracts stabilize.

## 7. Ordered implementation plan

Execute in coherent, dependency-aware slices. Refresh main SHA, active PRs, ownership and tests before every slice. Coordinate shared composition files; do not collide with other agents' assigned paths.

### Phase 0 — exact-main audit and service inventory
- Refresh current main SHA, open PRs/issues, branch ownership and active changes.
- Read #2093, #2090, #2019, #1423, #1530, #1799, #1989 and the current architecture/status/traceability docs.
- Trace every existing tool candidate to a real application service, API, repository, authorization gate and test.
- Publish a service-to-tool matrix with file paths, contracts, owner, runtime composition, proof and gap.
- Mark every item with the status vocabulary; no speculative "done".

### Phase 1 — one central Tool Registry and secure orchestration
- Extend the existing Command Orchestration Layer; no second orchestrator.
- Define versioned schemas and typed tool invocation/result envelopes.
- Bind trusted server session identity, tenant, project and current revision.
- Integrate scoped grants and operation-level policy; default deny.
- Add registry capability discovery, validation, stable errors, provenance, idempotency and audit hooks.
- Add tests for each tool's schema, authorization, stale revision, denial and service-unavailable behavior.

### Phase 2 — complete Import Engine and staging
- Complete the canonical project exchange/import service under #1799.
- Preserve source bytes/digest; validate malware/file type/size and parser safety using available internal scanning capability; if a scanner is unavailable, expose the exact security gate and do not claim a clean scan.
- Implement all seven staging steps and a deterministic preview/diff.
- Apply only after exact human confirmation, fresh authorization and target-revision check.
- Use an all-or-nothing transaction where supported; record explicit partial semantics only if unavoidable and tested.
- Fresh-read every imported entity and verify counts, relationships, calendars, baselines and digests.
- The imported project becomes visible in live Engineering only after successful verification.

### Phase 3 — revision-bound Schedule Scenario Service
- Complete #1989's persisted scenario contract and isolated fork semantics.
- Pin source snapshot, revision, data date, calendars, source baselines and calculation context.
- Invoke only Shared Scheduling Core; store immutable run inputs/outputs, engine version and hashes.
- Produce authoritative comparison and impact reports.
- Never mutate source schedule during create/edit/run/compare.
- Keep promotion/merge a separate future gate requiring its own exact diff, conflict handling, reauthorization, atomicity and approval.

### Phase 4 — Engineering action and decision execution
- Complete typed action contracts for supported project/WBS/activity/resource/risk operations.
- Connect AIActionRuntime to real Engineering services and trusted scoped grants in all production paths.
- Bind proposals and decisions to exact actor, project, tool, proposal version and base revision.
- Reauthorize/re-read immediately before apply; enforce transaction and idempotency.
- Persist audit and verify with fresh read-back.
- A rejection, denial, stale revision or failed transaction must cause no unauthorized/partial mutation.

### Phase 5 — connect canonical engineering tools
- Resource/capacity/leveling, cost/EVM, risk, progress/tracking, documents and reports.
- Reuse canonical service contracts; implement only proven missing service boundaries.
- Each connection includes input/output schema, permission, revision, evidence, calculation identity, failure behavior and tests.
- Capability is exposed to assistant only after real service and tests are wired.

### Phase 6 — integrated acceptance and release gate
- Use the three approved reference projects as repeatable integration fixtures where their source data is applicable; verify all values against source workbook and database. Do not hard-code project-specific import behavior into the general engine.
- Exercise full browser journey: file intake → staging → validation → Gantt/schedule preview → explicit confirmation → persistence → fresh read → schedule calculation → scenario → comparison → proposal → approval → execution → audit/report.
- Verify database rows and relationships independently of the UI.
- Negative tests: malformed/unsupported file, duplicate IDs, dangling/cyclic relationships, missing calendar, invalid mappings, formula injection, stale revision, revoked grant, viewer write, cross-tenant access, duplicate replay, rejected proposal, transaction failure, partial failure and read-back mismatch.
- Run exact-head CI, typecheck/build, SQLite and PostgreSQL integration, browser E2E and security review. Record tested SHA, CI links, preview URL, screenshots and DB evidence.
- V1 cannot be declared complete while any mandatory P0 gap or acceptance case remains open.

### Phase 7 — Enterprise reuse
- Reuse the same assistant entry/orchestration, tool registry, grant model, audit, proposals and Workbench interaction primitives.
- Add Enterprise-owned domain tools only when their canonical service contracts and permissions exist.
- Do not duplicate Engineering schedule facts or calculation authority.

## 8. Acceptance evidence required per tool and per end-to-end journey

Every tool is accepted only with:
- exact source file/API and canonical service/repository path;
- schema and contract tests;
- read/write/side-effect classification;
- tenant/project/role/grant tests;
- stale-revision and idempotency tests;
- database persistence and fresh-read proof for writes;
- append-only audit evidence;
- exact tested commit SHA and CI links;
- browser proof where a user-facing action exists;
- explicit unsupported/missing-data behavior.

Overall V1 evidence must prove a real persisted workflow, not just a unit test or preview fixture. Distinguish SQLite preview proof from PostgreSQL integration proof and from Supabase/production deployment proof.

## 9. Ownership and non-interference

- Jalal/product owner: approve semantics, calculation authority, acceptance fixtures and release decision.
- Backend/shared-core owner: canonical domain services, import/exchange, repositories, transactions, migrations, grants and audit.
- Assistant/orchestration owner: command layer, typed registry, context, tool routing and deterministic interpretation.
- Web/workspace owner: Workbench and studio wiring only; do not move domain logic into the browser.
- Parallel agents must claim non-overlapping paths and coordinate shared composition/API contracts before edits.
- Qoder is an implementation agent, not a CUBI runtime dependency.
- Never overwrite or rebase another active agent's work without inspecting ancestry and coordinating ownership.

## 10. Definition of Done

The assistant V1 standard is satisfied only when:
- one CUBI-owned assistant entry invokes one central, typed tool registry through the existing orchestration layer;
- all P0 tools are connected to canonical internal services and real persisted data;
- import and scenarios are real, isolated/revision-bound and use the shared core;
- proposals, approval, execution, authorization, transactions, audit and read-back are proven end-to-end;
- no third-party model/provider is required at runtime;
- no parallel domain engines or fake controls/data exist;
- all mandatory positive and negative tests pass on the exact final commit;
- browser and database evidence is recorded;
- all unresolved external/deployment prerequisites are stated honestly and do not get labelled verified.

**This document is the minimum standard and execution baseline. It does not itself mark any implementation gap complete.**
