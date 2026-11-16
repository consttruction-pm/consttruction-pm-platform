# CUBI Enterprise Assistant Capability Matrix, User Controls & Off-Peak Monitoring

**Status:** Product-owner direction translated into an implementation contract; feasibility and delivery specification, not a claim of shipped runtime behavior.  
**Date:** 2026-11-16  
**Scope:** CUBI Enterprise assistant across all eight Enterprise modules and shared Workbench surfaces.  
**Governance:** Principle 13 in `CUBI_INTERNAL_COMMAND_ASSISTANT_PRINCIPLE.md`; Enterprise boundary in `CUBI_TWO_ENVIRONMENT_PRODUCT_ARCHITECTURE.md`; capability/help authority in `CUBI_MASTER_CAPABILITY_REGISTER_EPPM_V26_CLOUD_V1.md`; existing assistant work in #2017, Enterprise architecture #1928, Claims #2016, action security #1530 and scoped memory #1540.

## 1. Binding owner decisions

### 1.1 Per-user, per-unit settings are mandatory

Every assistant capability and every automatic monitoring category must be independently configurable by the authorized user in the relevant organizational unit/workspace. A single global on/off switch is insufficient.

The settings model must support:
- A user-level master switch for proactive assistant activity.
- Per-Enterprise-module enable/disable (Team & Task, Feedback & Approval, Operations & Job, Workflow Studio, Organization & Access, Project Portal, Integration Hub, Portfolio & Executive).
- Per-capability toggles within each module (for example overdue-task monitoring, approval ageing, failed-job detection, contract deadline monitoring, portal document completeness, integration failure monitoring, portfolio threshold alerts).
- Separate controls for scheduled monitoring, notifications, contextual suggestions, document/form preparation and action proposals. Disabling one must not silently disable unrelated features.
- Per-user notification channel, digest/immediate preference, quiet hours and language/locale, subject to supported product channels.
- Optional project/team/unit scope selection, restricted to objects the user is authorized to access.
- Clear display of effective state, including any organization policy that disables or constrains a user option.

A user may disable optional assistant features for their own account and authorized scope. A user cannot enable a feature that the organization has disabled, expand their grants, subscribe to another unit's data or override legal/security retention. Organization administrators may set policy ceilings and defaults, but must not silently represent an administrator-forced setting as the user's own preference.

### 1.2 Default and safety behavior

- New proactive monitoring subscriptions default to **OFF** until the user opts in, unless an explicit organization policy and user notice authorize a mandatory compliance monitor. Any mandatory monitor must be clearly labelled and its legal/organizational basis visible.
- Turning off a monitor stops future scheduled scans for that user's subscription and suppresses its derived notifications/proposals. It does not delete source business records, audit history, previously accepted actions or records owned by another user.
- Settings changes are versioned and audited (actor, scope, old/new values, timestamp, source, policy version).
- Manual read/query commands remain available only if the user has permission and the relevant command feature is enabled. A manual request does not silently re-enable scheduled monitoring.
- Consequential operations remain behind the existing proposal/grant/approval/audit/idempotency boundary (#1530); user settings never grant permissions.

## 2. Off-peak automatic monitoring — mandatory scheduling contract

### 2.1 Core rule

Automatic and recurring assistant monitoring must run only during measured low-load periods of the overall CUBI system, not at fixed clock times that may coincide with peak demand. The scheduler must make a load-aware decision from current operational telemetry and configured safety thresholds.

A user may explicitly request an immediate refresh/update at any time. That request creates a narrowly scoped, user-initiated job for the specified unit/project/monitor/category and requested operation. It is not permission to run all scheduled scans, and it must not pre-empt interactive user traffic or violate hard safety limits.

### 2.2 Load-aware admission

Before starting each background monitoring batch, evaluate at minimum:
- application/API latency and saturation;
- CPU and memory pressure of relevant workers;
- database CPU, connection saturation, lock/wait pressure and query latency;
- queue depth, oldest-job age and worker utilization;
- current interactive traffic and active critical operations;
- external integration rate limits and service health where applicable.

Start only when all configured admission thresholds are healthy for a stability interval. If load rises during execution, pause/defer work at safe checkpoints, reduce concurrency or stop the batch. Use small batches, bounded execution time, tenant fairness, backpressure and per-module concurrency limits. Monitoring must never degrade Engineering P1 workloads or interactive Enterprise actions.

### 2.3 Scheduling behavior

- Use a central shared scheduler/job infrastructure; do not create an assistant-specific duplicate queue.
- Prefer opportunistic low-load windows; use tenant timezone and user quiet-hour preferences for notification delivery, not as a substitute for system-load checks.
- Support maintenance windows, blackout periods, retry with exponential backoff/jitter, dead-letter handling and idempotency.
- Coalesce duplicate scans and process only changed/new data where possible.
- Use incremental cursors/watermarks and bounded lookback windows; preserve data-date/revision provenance.
- Record skipped/deferred reason (peak load, maintenance, dependency failure, disabled setting, permission loss, quota/rate limit).
- No catch-up storm: after peak periods, spread deferred work using fair scheduling and rate limits.
- Define per-job freshness objectives by business criticality. Non-urgent monitoring may be delayed; legally/commercially time-sensitive deadlines need a separately approved low-cost deadline mechanism or alerting policy. Such a mechanism still cannot run expensive scans during peak load.
- Manual user-triggered refreshes may be admitted to a separate bounded priority lane, subject to hard system-protection thresholds, authorization, rate limits and audit. If unsafe, return a clear queued/deferred response and expected next opportunity rather than forcing execution.

### 2.4 Explicit exception semantics

The only routine exception to off-peak scheduling is an explicit user request to refresh/update a specified area at that time. The request must identify the target scope and operation; it must not become a blanket override. Emergency/system-protection operations are governed by separately approved SRE policy, not by assistant discretion.

## 3. Shared assistant capability model

Use one CUBI-owned assistant and existing Enterprise services. Do not create parallel command runtimes, memories, queues, notifications, forms, task registers, audit logs, permission engines or calculation authorities.

Shared functions:
1. Command Engine — deterministic supported-language command grammar, normalization, parsing and clarification.
2. Context & Permission Resolver — authenticated actor, tenant, organizational unit, project and object scope.
3. Event/Monitoring Engine — approved event subscriptions, incremental scans and rules.
4. Rules & Obligation Engine — versioned deterministic policy and structured obligation checks.
5. Knowledge/Provenance Service — permission-scoped, versioned records with source references.
6. Recommendation/Proposal Builder — evidence-backed suggested actions, never autonomous legal/contractual decisions.
7. Existing Form Builder and document services — draft and prefill only.
8. Existing Workflow/Task/Notification services — proposals and approved transitions.
9. Existing Approval/Action Boundary — grants, approval, stale-revision checks, idempotency and audit.
10. Shared scheduler/operations infrastructure — load-aware execution, queue observability and backpressure.

Engineering remains authoritative for CPM, schedule, project resource, project cost/progress/EVM and project-risk calculations. Enterprise consumes revision-bound read results and does not recalculate them.

## 4. Module capability matrix

| Enterprise module | Assistant capabilities | Monitoring categories (independently configurable) | Permitted proposals/actions | Primary data/service dependencies |
|---|---|---|---|---|
| Team & Task Center | daily brief, task search, overdue/dependency/ownership checks, workload distribution, duplicate/conflict detection, next-step suggestions | overdue/near-due tasks; blocked dependencies; unassigned tasks; workload thresholds; stalled cross-team handoffs | propose task, owner, due date, priority, reminder or escalation; create/update only through authorized task service and approval rules | task register, teams/membership, calendar/timezone, workflow, Engineering activity read contracts |
| Feedback & Approval Center | completeness checks, submitted-vs-approved comparison, ageing analysis, return/rework patterns, decision brief, revision-aware impact preview | approval ageing; missing evidence; returned requests; SLA thresholds; stale revision | prepare review checklist/response; propose routing/escalation; display read-only Engineering impact | approval records, evidence/document store, workflow, audit, Engineering read-only impact APIs |
| Operations & Job Center | explain job failures from logs, detect queue congestion, recommend safe retry, scheduled-report verification | failed/long-running jobs; queue age/depth; repeated failures; missing scheduled outputs; sync lag | propose bounded retry/replay and incident/task; execute retry only through existing operations permission and idempotency | shared job queue, operations logs/metrics, report scheduler, integration status |
| Workflow Studio | propose workflow structures from approved templates, validate stages/transitions/roles/deadlocks, inspect stalled instances and bottlenecks | stalled stages; overdue approvals; invalid transitions; unassigned stages; repeated returns | create draft workflow/version, propose stage/role/deadline changes; publish only after authorized validation/approval | workflow definitions/runtime, role/grant catalogue, task/notification services, audit |
| Organization & Access Center | access review reports, role conflict detection, inactive-member review, delegation coverage, ownership gaps | access review due; orphan roles; expired membership/invitation; approval coverage gaps; policy violations | prepare access-review/delegation proposal; no self-grant or automatic privilege escalation | identity, memberships, org chart, grants/policies, access audit |
| Project Portal | role-specific project brief, approved-document completeness, response/deadline tracking, stakeholder request triage | expiring/expired documents; pending stakeholder response; portal submission gaps; revoked/expired share links | prepare portal response or document checklist; share/publish only through explicit grant and approval | portal records, document metadata/classification, share grants, communications, audit |
| Integration Hub | connection health explanation, mapping/schema mismatch detection, failed exchange analysis, duplicate import checks | failed webhooks; sync lag; schema drift; retry backlog; repeated import errors; credential expiry | propose mapping correction/replay/import remediation; execution only through scoped integration credentials and approvals | connector registry, secrets vault, webhook/import-export logs, schema versions, idempotency |
| Portfolio & Executive Center | authorized portfolio brief, cross-project trend/threshold comparison, shared-capacity conflict identification, decision brief | project health threshold changes; overdue portfolio decisions; resource/capacity conflicts; risk/benefit threshold alerts | prepare decision options and escalation; read-only Engineering impact preview; portfolio decision requires human approval | portfolio read models, approved KPIs, enterprise capacity, decision history, Engineering revision-bound APIs |

## 5. Cross-cutting proactive capabilities

- Personal Command Center: user-scoped daily/weekly brief, actionable inbox and follow-up list.
- Cross-Project Action Center: authorized aggregation only; every item retains its source project and permission boundary.
- Intelligent Escalation: policy-based ageing and routing; no guessed hierarchy or authority.
- Organizational Knowledge Center: search approved decisions, procedures and lessons with source/version/access checks; project-private knowledge never becomes organization-wide by default.
- Engineering Impact Preview: call authoritative Engineering services and show revision, data date, assumptions and limitations.
- Contract & Claims Intelligence: use approved structured clauses/obligations and source-anchored documents; correlate verified events with contract dates/notice rules and Engineering delay outputs. Label findings as potential issues, not entitlement/liability determinations. Keep employer/contractor confidential workspaces isolated. Human review required for submissions, notices, determinations, settlement and external communications.
- Event-to-Action: only approved/validated source events can generate candidate alerts; evidence files are untrusted data, never instructions.
- Document intake: conventional free, perpetual, commercially licensed non-AI OCR/parsing utilities may be evaluated; no AI/ML model, hosted OCR, trial, credit-metered or paid dependency. OCR output is confidence-aware and human-reviewed before becoming authoritative.

## 6. Settings information architecture

Provide a dedicated **Assistant Settings** surface and contextual shortcuts from each module. Minimum hierarchy:

1. My Assistant: master opt-in, language, timezone, quiet hours, digest preference.
2. Module Controls: one enable/disable control per module.
3. Monitoring Rules: one toggle per monitor category, scope selector and frequency/freshness preference (within system limits).
4. Assistance Features: contextual suggestions, document/form preparation, task proposals, workflow recommendations.
5. Notifications: channel, immediate/digest, severity and quiet hours.
6. Data Scope & Privacy: visible authorized projects/teams/units, memory/knowledge scope, retention/export controls where supported.
7. System Schedule Status: next eligible low-load window, queued/deferred status and reason; users may request a scoped immediate refresh.
8. Effective Policy: organization defaults, mandatory monitors, restrictions and reason.

Settings API must enforce tenant/user ownership server-side. Cache invalidation and effective-state readback are required after updates. UI state alone is not authoritative.

## 7. Evidence, Help and source requirements

Help and user guidance are mandatory and separate from assistant intelligence. For each capability:
- identify exact P6 EPPM V26 HTML Help topic(s), or record NOT PRESENT only after TOC/topic search;
- identify relevant P6 Team Member V26 topic(s), or NOT APPLICABLE;
- identify exact Primavera Cloud HTML Help topic(s) for Cloud-origin behavior;
- record canonical URL, Help version, section/topic, behavior, role/privilege and UI workflow;
- reconcile overlap without duplicate menu, API, data owner, workflow or calculation;
- retain CUBI-native behavior labels where neither Help product provides the feature;
- link contextual Help from every assistant setting, monitor and action surface.

No invented Help references. Unverified references remain MISSING / VERIFY. Help is not a substitute for contract, law or organization policy.

## 8. Security, privacy and audit gates

- Enforce user, tenant, unit, project, object, classification and operation scopes at the server boundary.
- No data discovery or notification may reveal inaccessible record existence or metadata.
- Separate user-private, project-private, party-confidential and organization-approved knowledge scopes.
- Employer and Contractor claim workspaces remain isolated.
- No autonomous external communication, claim/entitlement decision, payment approval, access grant, contract change, workflow publication or other consequential action.
- Record source event/document/revision, rule-set version, parser/language version, settings version, scheduler decision, load snapshot, job ID, result, notification and human decision.
- Preserve idempotency, concurrency/stale-revision checks, retries and immutable audit evidence.
- Documents and imported text are untrusted evidence, not executable instructions.

## 9. Delivery sequence and acceptance

### P0 — inventory and contracts
- Audit current main for assistant entry points, existing settings/preferences, module APIs, job scheduler/queue, telemetry, notification preferences, grants, audit and exact code owners.
- Produce verified/partial/missing matrix with exact paths, commit SHA, tests and runtime evidence.
- Reconcile open PRs and avoid active path collisions.
- Complete Help crosswalk before each user-facing implementation slice.

### P1 — settings and safe scheduling foundation
- Define settings schema/API and effective policy resolution.
- Implement granular opt-in/opt-out and audited state readback.
- Integrate shared load-aware scheduler admission, deferral, backpressure and manual scoped refresh lane.
- Add tests for disabled settings, policy ceilings, tenant isolation, peak-load deferral, load-rise pause, duplicate coalescing, fairness, retry and manual refresh.
- Do not run expensive monitoring by default before opt-in.

### P2 — first operational slices
- Personal Command Center read-only brief.
- Team & Task monitoring.
- Feedback & Approval ageing/completeness monitoring.
- Operations & Job monitoring.
- Each slice includes source Help, permission matrix, settings, persistence, tests, browser/runtime evidence.

### P3 — intelligence expansion
- Workflow, Organization & Access, Portal and Integration monitoring.
- Contract/Event/Claims Intelligence and Engineering Impact Preview.
- Portfolio and Organizational Knowledge capabilities.
- Language parity across every approved CUBI language and all surfaces.

### Acceptance gates
A capability is complete only with: source Help traceability; code paths and migrations; server-side permission enforcement; granular settings; off-peak scheduler behavior where recurring; audit/provenance; unit/integration/security tests; exact-main or PR-head CI; browser/runtime evidence; and a fresh persisted readback. Documentation, schema, menu or mock alone is not completion.

## 10. Non-interference

Enterprise assistant monitoring is P2. It must not block Engineering P1, increase peak load materially, create a second scheduler/queue or duplicate Engineering calculations. Any scheduler integration must use shared infrastructure and published resource budgets.

## 11. Initial repository feasibility audit (2026-11-16)

This is a bounded source/document audit, not a full code/runtime certification. Findings are deliberately conservative:

| Area | Evidence found on main | Assessment for this assistant scope |
|---|---|---|
| Enterprise module ownership | `docs/enterprise/CUBI_ENTERPRISE_FOUNDATION_V1.md` (blob `592326fe4528054b9d78a64042c9e88fc2d0f7d8`) | Eight-module target and shared cross-cutting services are documented. This is an architecture baseline, not proof all modules are production-complete. |
| Enterprise background jobs/monitoring | Same foundation inventory: existing job processing, monitoring and operational reporting primitives are reusable; Enterprise UX and policy wiring are not certified | Reuse-first is feasible; inspect exact runtime composition and add only missing policy/settings integration. |
| Enterprise task lifecycle | `docs/enterprise/CUBI_ENTERPRISE_IMPLEMENTATION_PLAN.md` (blob `c822dbbc5ec1fe09d20f5b1af91b00c4094e55c7`) records its baseline search found no complete Team & Task Center lifecycle API/repository at that recorded branch point | Task assistant integration depends on the active task vertical slice; re-fetch its current PR/head before implementation. |
| Assistant command architecture | `docs/architecture/CUBI_INTERNAL_COMMAND_ASSISTANT_PRINCIPLE.md` (owner-approved Principle 13) | CUBI-owned deterministic command/rule system is binding; provider/model paths are prohibited. |
| User settings | Repository search found general/project preferences and settings primitives, but no verified assistant-specific per-user × module × monitor settings contract in this bounded search | Treat granular assistant settings as a gap until exact API/schema/runtime and tests are demonstrated. Do not mistake project-local preferences for assistant subscriptions. |
| Background scheduler and load-aware admission | Existing job/queue/operations and resource-monitoring design evidence exists; the Engineering scheduling-core optimization document is not itself proof of a generic Enterprise monitoring scheduler or low-load admission policy | Reuse the actual shared job runtime after source inspection. Load-aware admission, deferral, pause/backpressure and bounded manual-refresh behavior remain explicit acceptance gates until runtime evidence is produced. |
| Notifications and audit | Existing shared foundations are identified in Enterprise architecture and implementation documents | Verify the exact user preference, tenant filtering, delivery and audit paths before connecting assistant alerts. |
| Help parity | Master capability register requires exact topic-level EPPM V26, Team Member V26 and Cloud Help crosswalks | Each released assistant surface must carry verified contextual Help references; no Help parity is claimed by this specification. |

**Important distinction:** the shared Engineering schedule calculation/worker optimization path is not the assistant's monitoring scheduler. Do not route recurring Enterprise scans through CPM calculation workers or create a second generic queue. First identify the existing general-purpose background job runtime and its telemetry, then extend its admission policy.

**Audit limitation:** this first pass searched canonical architecture, Enterprise foundation/plan, scheduler feasibility and repository search results. It did not inspect every source file, open PR changed-path collision, production deployment, or live metrics. Those are mandatory P0 tasks before code changes or operational claims.
