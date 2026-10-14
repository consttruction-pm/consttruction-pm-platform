# V1 AI Project Controls Assistant — Product and Engineering Requirements

Status: **Mandatory V1 release scope**
Effective: 2026-10-13
Authority: `docs/architecture/PRODUCT_PRINCIPLES.md`, Principles 1 / 1A / 1B / 6 / 6A.
Related workstreams: #78 Shared Control Intelligence, #79 Backend/API/AI orchestration, #80 Web experience, #459 V1 Web Beta, #389 P6 parity.

## 1. Product commitment

CUBI V1 must ship a professional, project-aware AI assistant integrated into the actual application. It is not satisfied by a generic chat panel, a static Smart Guide, an architecture contract, or cards that merely display proposed actions.

The assistant must help a user create, populate, configure, calculate, inspect, correct, and report on a real project through CUBI's authoritative application services and Shared Domain/Calculation Core. It must remain useful to a project-controls professional and must be treated as a release capability, not optional post-V1 polish.

The target is a guided but capable executor: it can perform actions already authorized by the user, asks for clarification when required inputs are ambiguous, and requests explicit approval for consequential or broadly mutating actions. The application, not the language model, remains authoritative for permissions, validation, storage, calculations, and final outcomes.

## 2. Required V1 user journeys

### 2.1 Conversational project initialization
- Accept natural-language requests in supported languages and clearly communicate unsupported capabilities.
- Collect and validate project metadata, project start/data date, work calendar, units, schedule options and other required settings.
- Propose a draft WBS and activity list from user descriptions and supported files; identify assumptions, unknowns, duplicate IDs and missing fields.
- Propose milestones, relationships (FS/SS/FF/SF), lag/lead, activity types/durations, constraints and resource assignments as supported by the canonical domain.
- Show a reviewable change set before committing a bulk initialization.
- Create/update the project through real, authorized application use cases; confirm only what the server has actually committed.

### 2.2 Import and reconcile information
- Support the released import formats and typed import contracts (including applicable XER/XML/XLS/XLSX/Microsoft Project formats where release parity declares support).
- Read supported documents and spreadsheets through explicit parsers/OCR/document services; preserve source references and confidence/validation findings.
- Map imported values into canonical CUBI fields; flag unsupported, ambiguous, malformed or lossy mappings rather than silently dropping or inventing data.
- Provide an import preview, validation summary, rejected-row report and explicit user choice before committing material/bulk changes.
- Preserve project/tenant scope, revision semantics, idempotency and traceability.

### 2.3 Project configuration and editing
- Read and, when authorized, create/edit project settings, calendars, WBS, activities, relationships, constraints, codes/custom fields, resources, assignments, progress, costs, documents and other released subject areas.
- Use the same canonical application/domain APIs as the normal UI. Do not create an AI-only repository, field registry, calendar engine, formula engine or scheduler.
- Respect field read-only metadata and operation-level authorization. Never infer write permission from visibility or from the user's natural-language instruction alone.

### 2.4 Calculation and project-controls analysis
- Invoke the authoritative CUBI scheduling and applicable Progress/EVM/Resource/Cost engines through typed application services.
- Read back the committed input revision, calculation-run identity and result; make claims only from those returned results.
- Explain early/late dates, total/free float, criticality, project finish, out-of-sequence behavior, constraints, baseline variance, resource overload and other metrics only where the active engine result and supported evidence expose them.
- Distinguish stored facts, calculated results, model-generated explanations, assumptions and predictions.
- Produce schedule queries, filters, comparison and what-if proposals. A scenario proposal is non-mutating until an authorized commit flow is completed.
- Never let a model-generated answer replace, recompute or overwrite authoritative project-control formulas.

### 2.5 Reporting and visualization
- Generate project status summaries, exception lists, management reports and user-requested tables/charts from typed, versioned CUBI data.
- Provide Gantt and other supported visualizations from the actual project/result models rather than fabricated chart data.
- Support available report profiles, field selection, print/export workflows and language/date presentation options.
- Include reporting date, project revision, calculation identity, data sources and material assumptions where relevant.
- If data is missing or stale, say so and do not present a fabricated complete result.

### 2.6 Guided multi-step execution
- Break a multi-step request into a visible plan with progress, prerequisites, expected effects and approval boundaries.
- Maintain project-scoped conversation context with an explicit way to switch/clear context; do not mix tenants or projects.
- Resume safely after failure. Use idempotency keys and operation status to avoid duplicate mutations.
- After each consequential step, verify the authoritative result, identify partial completion and show the next action.
- Provide a coherent completion report: succeeded, rejected, skipped, needs approval, failed, and not attempted.

## 3. Assistant personalization

V1 must provide user-controlled personalization for:
- input/output language and terminology profile;
- explanation depth and preferred report format;
- role/working context and project-specific assumptions, if authorized;
- allowed autonomy mode (read/analyze only, prepare proposals, execute permitted low-risk actions, or execute after approval);
- notifications/confirmations and saved reusable prompt/workflow templates;
- accessible output preferences, including RTL/LTR and date-display preferences.

Personalization may not grant permissions. Permissions come only from the application's trusted authorization system. User/customer data must not be silently used to train or fine-tune a shared model. Any future memory or learning feature requires explicit policy, scoping, retention and deletion behavior.

## 4. Tool and capability contract

Every assistant tool must have a versioned, typed schema with:
- stable tool name and version;
- explicit project/tenant scope and authenticated actor context supplied by the server;
- input validation, required fields, allowed enums and bounds;
- read/write classification and required permission;
- side-effect classification, idempotency behavior and expected revision precondition;
- clear result/error contract;
- source references and calculation-run identity where applicable;
- audit and telemetry policy.

Initial required tool families:
1. project/context read and project creation/opening;
2. WBS and activity read/create/update;
3. relationship/constraint and schedule-option read/create/update;
4. calendar read/create/update/assign and supported exception operations;
5. resource/role/assignment and cost/progress operations released for V1;
6. authoritative schedule/recalculate and supported control-query/scenario functions;
7. documents/spreadsheets import preview, validation and commit;
8. Gantt/report/chart generation and export;
9. proposal review, approve/reject, operation status and audit lookup;
10. contextual Help/Smart Guide and capability discovery.

An unavailable or not-yet-released tool must be explicitly marked unavailable; the assistant must not simulate its completion.

## 5. Permission and approval model

Authorization must be enforced server-side on every tool call. Effective access is the intersection of:
- the user's current role/permissions;
- tenant and project membership/scope;
- the operation's required permission;
- any additional policy or resource restrictions;
- project revision and state preconditions.

Minimum privilege families:
- project read / analysis;
- project create;
- project metadata write;
- calendar read / write / assign;
- WBS read / write;
- activity read / write;
- relationship / constraint / schedule-option write;
- calculate / recalculate;
- resource / assignment read / write;
- progress / actuals write;
- cost / financial write;
- document read / import / write / issue / approve;
- reports / export;
- custom fields / formulas / layouts;
- administrative permissions, separate from normal project editing.

The user may select a stricter policy. The assistant cannot elevate the user's role or bypass a denied action. Read-only users cannot mutate by asking the model. Project-level approvals cannot substitute for a missing base permission.

Require explicit approval, bound to the exact proposal and base revision, for at least:
- bulk imports or bulk modifications;
- deletes and destructive/irreversible actions;
- setting/changing an official baseline or issuing a controlled record;
- changing actual progress, cost/financial facts, or other audited actuals;
- applying a material schedule change affecting many activities;
- externally publishing, sending or exporting sensitive project data;
- changing permissions, users, tenant settings or security configuration.

Approval must identify the authenticated human actor, exact diff/effect preview and revision. Approval expires or must be revalidated if the underlying project revision changes. Rejected actions make no mutation. Every decision and execution outcome must create durable audit events. A model response that says "approved" is not a user approval.

## 6. Security, privacy and reliability

- Use authenticated sessions/service credentials with least privilege; never expose model/provider API keys to the client.
- Treat uploaded documents, comments and retrieved content as untrusted data, not as instructions that can override system policy or tool authorization.
- Keep tenant/project isolation in every query, tool and result.
- Validate outputs from the model against schemas before calling tools.
- Prevent prompt injection from expanding tool permissions, changing project scope or bypassing approval.
- Apply rate limits, token/model budgets, request timeouts, retries with idempotency, cancellation and partial-failure handling.
- Record model/provider/model-version where policy allows, prompt/workflow version, tool inputs/outputs or redacted digests, acting user, approval evidence, project revision and result identity.
- Define data retention, deletion, export, secrets handling and incident response for AI requests.
- Offline mode must expose only genuinely available local capabilities; no AI result may imply an unavailable network/model action succeeded.

## 7. Calculation authority and evidence

- Scheduling/P6, calendar, duration/lag, Progress/EVM, resource loading/leveling, cost and financial computations remain in the Shared Domain/Calculation Core.
- The assistant is a client of calculation services and explains their results; it never becomes a competing calculation engine.
- Every answer that reports a project fact or calculation must be grounded in scoped source data, a validated application result or a clearly labelled user-provided assumption.
- Results must be revision-aware. If inputs change after calculation, the assistant must detect stale results and recalculate or ask before proceeding.
- Maintain regression fixtures and documented semantic dispositions for applicable P6 fields, options and calculations. “Equivalent” requires behavior and test evidence, not a similarly named field or a model's assertion.

## 8. Mandatory V1 acceptance gate

V1 AI Assistant is accepted only when all applicable criteria below pass on an integrated current-main build:

1. A user can ask in a supported language to create a representative construction project from provided project information.
2. The assistant previews assumptions and validates input, then creates the project, WBS, activities, relationships and calendar via actual APIs when approved.
3. The authoritative CUBI engine calculates the schedule; the UI and assistant show the same result and calculation identity.
4. The assistant can explain schedule results and exceptions with project-scoped sources and correct revision context.
5. The assistant can prepare and execute a permitted edit, handle approval/rejection correctly, and prove that rejection creates no mutation.
6. Read-only, cross-tenant, cross-project, stale-revision and insufficient-permission cases fail closed.
7. A bulk import retains valid values, reports invalid/unsupported values, and cannot silently drop required fields.
8. Gantt/report/export outputs correspond to persisted and calculated data.
9. Retry/timeout/partial failure do not cause duplicate writes or false success messages.
10. Conversation context, personalization and language/date preferences do not leak across projects or tenants.
11. Usage/cost limits, telemetry, privacy/retention behavior and accessible error states are covered by tests/docs.
12. CI includes focused tool-contract, authorization, approval, end-to-end workflow, schedule regression and client tests; release evidence identifies the exact tested commit.
13. The UI's approval controls are functional, not static cards, and the final result shows completed/failed/skipped/pending operations.
14. Help/Smart Guide content is versioned with the product and only documents behaviors that have been accepted and released.

A staged prototype may be used during implementation, but it does not satisfy the V1 release gate. If any mandatory item is incomplete, publish an explicit limitation and do not label the assistant “full/professional” or mark it complete.

## 9. Definition of Done

A capability is complete only after its typed tool/API, real application behavior, authorization, persistence, result verification, audit/approval behavior, UI interaction, localized errors/help and relevant automated evidence are integrated. Static contracts, placeholder cards, mocked providers or passing isolated unit tests alone do not prove the end-to-end assistant is ready.
