# CUBI Internal Command Assistant — Binding Product Principle and Capability Scope

**Decision date:** 2026-11-04  
**Status:** Owner-approved, binding product and architecture principle  
**Authority:** Product Principle 13 in PRODUCT_PRINCIPLES.md  
**Applies to:** Web, Windows Desktop, Flutter/Mobile, shared services, project data, documents, reporting, knowledge, voice and all assistant workflows.

## 1. Binding decision: CUBI owns the complete assistant technology

The CUBI Engineering Command Assistant must be entirely a CUBI product, implemented and controlled within CUBI's own product architecture. Its command understanding, engineering analysis, knowledge handling, action planning, workflow logic and user-facing responses must be developed as CUBI-owned technology.

The following are prohibited, both as required dependencies and as optional alternatives or future fallbacks:

- Ollama.
- ChatGPT, OpenAI models, or any other third-party AI model.
- Any local, hosted, remote, downloadable or self-hosted third-party AI/ML inference model or inference runtime.
- Any external AI service, AI provider, model endpoint, inference API, embedding API or provider gateway.
- Any AI API key, provider credential, provider-specific environment configuration or remote-model account.
- Any provider abstraction, adapter, plug-in point, fallback route or configuration whose purpose is to connect a third-party AI model/provider.
- Silent or explicit fallback to an external model/service when an internal capability is unavailable.

This is not a "no API key by default" policy. It is not a local-model-first policy. It is not an optional-provider architecture. **No third-party AI model or AI provider is part of the CUBI assistant architecture.**

CUBI must not depend on a model or provider belonging to another product or organization, even as an optional replacement. Existing provider-backed code and configuration are legacy paths to be retired or replaced under controlled implementation and migration work; they are not a permitted target architecture.

Generic non-AI infrastructure or format libraries may be evaluated under the existing product security, license and supply-chain rules. They must not provide the assistant's language understanding, reasoning, semantic inference, engineering decisions or calculation authority. Product intelligence and command logic remain CUBI-owned.

## 2. Product identity: command-oriented, not an open-ended chatbot

The assistant is a project-aware engineering command system, not a general-purpose chat service or free-form conversational companion.

It receives a user instruction by text or supported voice input, identifies the requested operation, resolves its project context and parameters, checks facts and permissions, then returns a result or a controlled action proposal. It asks a focused clarification only when a required value or target is missing, ambiguous or contradictory.

It must not be designed around:
- open-ended general conversation or social chat;
- a chatbot transcript as the primary product workflow;
- a persona or simulated human conversational identity;
- unrestricted answers outside CUBI's declared command and engineering knowledge scope;
- guessing unsupported intent or inventing missing project facts.

The user-facing interaction may use concise natural-language explanations, but those explanations are produced by CUBI's rule-based, template-based and data-grounded response system. Typed and voice inputs converge on the same normalized command contract.

## 3. Internal command-understanding engine

Build and maintain a CUBI-owned command-understanding engine from explicit algorithms, structured data and versioned rules. It must include:

1. Input normalization: Unicode normalization, Persian/Arabic/Latin digit handling, punctuation, whitespace, units, dates, decimal and locale normalization while preserving the original input.
2. Language identification: deterministic script, vocabulary and grammar cues for each language explicitly supported by CUBI.
3. Domain vocabulary: versioned engineering dictionaries, synonyms, aliases, abbreviations, spelling variants, multilingual terms, project-specific names and user-approved terminology.
4. Command grammar: patterns, phrase structures, finite-state/rule-based parsing and explicit command schemas.
5. Intent classification: identify read, search, filter, inspect, calculate, analyze, compare, create, update, delete, import, export, report, configure and other explicitly supported operations.
6. Entity and parameter extraction: project, EPS, WBS, activity, relationship, calendar, resource, cost, contract, document, dates, durations, quantities, units and status values.
7. Context resolution: resolve references such as "this activity" or "the previous WBS" only against authorized, current project context.
8. Ambiguity and contradiction handling: detect multiple matches, missing mandatory parameters, incompatible units, invalid dates, contradictory instructions and unsupported commands.
9. Confidence and safety rules: use deterministic match/validation evidence; consequential low-confidence or ambiguous commands must stop and ask for clarification.
10. Response construction: localized templates and structured explanations grounded in retrieved facts, validated rules and authoritative calculation outputs.

No external or pretrained semantic, embedding, language, classification or generative model may be introduced into this engine. The supported command grammar and its coverage must expand through CUBI-owned dictionaries, rules, parsers, schemas and tested software releases.

## 4. Complete assistant capability scope

The following capabilities define the required product scope. A capability is not complete merely because it is documented, has a menu, has a type or has a test fixture; completion requires a real authorized application path and end-to-end evidence.

### 4.1 Command input and language handling
- Typed command input.
- CUBI-owned automatic language identification for declared supported languages.
- Multilingual normalization of words, dates, numbers, units and identifiers.
- Engineering terminology, synonyms, spelling variants and user/project dictionaries.
- Intent recognition, entity resolution and typed parameter extraction.
- Reference resolution against the active authorized project and current selection.
- Missing-field, ambiguity, contradiction and unsupported-command detection.
- One focused clarification at a time, preserving already resolved values.
- Localized, deterministic command responses and result explanations.

### 4.2 Project understanding and engineering analysis
- Read project properties, EPS, WBS, activities, relationships, calendars, resources, assignments, costs, progress, actuals, baselines, contracts, documents and other authorized domains.
- Search, filter, group, sort and compare project information.
- Identify critical and near-critical activities, float, open ends, invalid relationships, constraints, date conflicts and schedule anomalies.
- Analyze delay, progress, forecast, resource capacity, resource conflicts, cost, cash flow, EVM and applicable commercial measures.
- Compare current schedule with baselines, project revisions and other projects.
- Run what-if scenarios using actual application services and the authoritative Shared Domain/Calculation Core.
- Explain the evidence, assumptions, calculation context, source revision and limitations behind each result.

### 4.3 Authorized project operations
- Create, read, update, move, archive and delete supported project records.
- Manage EPS/WBS hierarchy, activity fields and IDs/codes, relationships and lag/lead, calendars and exceptions, resources and assignments, progress/actuals, cost, contracts and other supported domains.
- Create and manage baselines and approved scenarios.
- Invoke authoritative recalculation and read back persisted results.
- Support forms, document workflows, field operations, procurement, claims, risk and other connected CUBI domains as their real application tools become available.

Every mutation must use the existing security boundary: typed proposal, exact actor/tenant/project/revision/domain/operation/tool grants, validation, approval where required, stale-revision recheck, idempotency, transaction safety, audit and fresh persisted read-back. The assistant must not grant itself permission.

### 4.4 Guided project creation
A resumable project-creation wizard must:
1. Ask for project sector/domain or EPS parent category first.
2. Ask for project name.
3. Ask for a unique project ID/code and validate it through CUBI.
4. Collect project scope and description where applicable.
5. Configure start date, data date, timezone, calendar system, workweek, shifts, holidays and exceptions.
6. Build WBS hierarchy and code policy.
7. Define activities, activity types, durations, constraints and dates.
8. Define FS/SS/FF/SF relationships and lag/lead semantics.
9. Collect resource, assignment, quantity and capacity information where supplied.
10. Collect baseline, actual, progress, cost, contract and EVM inputs only where supported by evidence and tools.
11. Validate duplicates, missing fields, contradictions, unsupported data and logic cycles.
12. Present the complete proposal and authoritative schedule results.
13. Save a new independent project by default, or update an existing project only through a separate explicitly approved operation.
14. Resume after interruption without re-asking already accepted information.

### 4.5 File and document intake
- Inspect and classify supported XLS/XLSX, DOC/DOCX, PDF, CSV and approved project interchange formats such as MPP, MPX and MSPDI/XML.
- Extract structured text, tables, dates, codes, relationships, calendars, resources and other supported fields.
- Provide CUBI-owned recognition/extraction for scanned documents and image-based inputs if that capability is released; no third-party AI/OCR model may be used.
- Preserve source file checksum, page/sheet/row/cell/field provenance where available.
- Map extracted values into a typed staging model and show mapped, absent, unsupported, ambiguous and rejected fields explicitly.
- Never silently drop unsupported fields or treat extracted text as permission to mutate project data.
- Require mapping review and applicable approval before project persistence, followed by authoritative calculation and reconciliation.

### 4.6 Reports, charts and dashboards
- Generate daily, weekly, monthly, annual and user-defined-period reports from persisted, revision-bound data.
- Support project, WBS, activity, contract, resource and portfolio reporting where authorized.
- Produce progress, planned-versus-actual, critical-path, float, milestone, resource, cost, cash-flow, EVM, risk, procurement, change and claim views only when the required source data exists.
- Select suitable tables and chart types through explicit data-availability and validity rules.
- Generate editable templates, A4 layouts and supported PDF/Excel outputs.
- Build narrative summaries from structured facts, templates and approved engineering rules; never invent values, trends, causes or recommendations.
- Preserve report period, data date, source revision, filters and calculation provenance.

### 4.7 Engineering knowledge, memory and controlled learning
- Maintain versioned terminology dictionaries, engineering rules, formulas, variables, units, assumptions, validity ranges, sources, limitations and verification evidence.
- Retain user-approved preferences in user-private scope.
- Retain project lessons only in the corresponding authorized project scope.
- Retain organization methods only within explicit tenant authorization.
- Maintain candidate generalized lessons separately from validated and published general knowledge.
- Capture structured corrections, validated outcomes and approved lessons; do not treat user agreement alone as engineering proof.
- Require evidence, privacy/reuse review and authorized human approval before general publication.
- Provide durable retrieval, versioning, audit, deletion, export, backup, restore and schema migration.
- Learn through governed knowledge and dictionary/rule updates, not model-weight training or autonomous inference-model modification.
- Do not retain unrestricted chat transcripts as the assistant's memory system.

### 4.8 Research and knowledge administration
- Allow explicitly authorized research of public or otherwise approved technical sources.
- Capture source title, publisher/author where available, URL, date, version, relevant sections and usage restrictions.
- Extract structured candidate facts and references using CUBI-owned parsing and classification rules.
- Compare with existing rules, detect conflicts and stale references, and present review evidence.
- Require human validation and approval before publishing reusable knowledge.
- Keep private project/user data out of general knowledge and maintain rollback to prior knowledge versions.
- Internet research may use ordinary permitted network access; it must never use an external AI service or AI summarization endpoint.

### 4.9 Voice input
- Provide microphone activation controlled by the user.
- Develop a CUBI-owned speech capture and recognition pipeline without third-party pretrained speech/AI models or cloud transcription.
- Support declared languages and construction-domain terms only after audio-fixture acceptance tests.
- Convert recognized speech into the same command contract as typed input.
- Display the recognized transcript for review/edit when required.
- Preserve language, timestamp, source and recognition-quality evidence.
- Never execute consequential commands from ambiguous or unreliable transcription without clarification and approval.

### 4.10 Workspace and product integration
- Use the existing CUBI assistant entry/avatar as the single launch point; do not create a separate chat product that displaces the workspace.
- Provide access to command input/results in the existing workspace layout and permitted toolbar/panel surfaces.
- Connect the assistant to Gantt, Timeline, WBS, activity grid, calendars, resources, costs, reports, forms, documents, procurement, field operations, contracts, risk, dashboards and project comparison through real application contracts.
- Provide Smart Guide navigation using actual menu/control identifiers and current workspace state.
- Keep the shared command engine and typed contracts reusable by Web, Windows Desktop and Flutter/Mobile; clients must not implement separate command or calculation semantics.

## 5. Technical design rules

- Use deterministic, testable and explainable CUBI-owned algorithms for command parsing, normalization, matching, rule evaluation, planning and response generation.
- Keep language resources, dictionaries, command grammars, tool schemas, knowledge records and rule sets versioned.
- Keep the assistant outside the calculation authority: CPM, calendars, dates, float, progress, resource, cost, EVM and financial results come exclusively from Shared Domain/Calculation Core and authoritative application services.
- Keep business logic out of UI clients. Use versioned application APIs and repositories, with the same typed command contract across clients.
- Preserve original input, normalized form, identified language, parsed command, resolved entity IDs, validation outcomes, evidence references and rule-set version for traceability, subject to data-retention policy.
- Enforce permissions in authenticated server/application/repository paths, never by natural-language instructions or client claims.
- Use the existing product security, privacy, database, audit, backup, localization and supply-chain governance.
- No hidden network call, external AI endpoint, provider credential, pretrained inference runtime or fallback path is permitted.
- Commodity non-AI libraries may be used only under the existing dependency/license/security review and must not become a source of product intelligence or calculation truth.

## 6. Explicitly prohibited architecture and migration requirements

The following are not acceptable design options:
- Local or remote model selection settings.
- Provider-neutral AI abstraction layers.
- Optional local-model and remote-model adapters.
- OpenAI-compatible chat/completions endpoints used for assistant intelligence.
- AI/ML embedding or semantic-vector services.
- Pretrained AI speech, OCR, vision, translation, ranking, classification or language models.
- Environment variables, secrets, keys, setup screens or diagnostics for third-party AI providers.
- An external service used only as a fallback when CUBI cannot parse a command.

The current repository contains legacy provider-backed assistant orchestration and a chat-oriented UI path. These are not compliant with this decision. They must be assessed, retired or replaced in controlled, tested changes; preserve reusable authorization, proposal, audit, idempotency and application-tool infrastructure. Do not remove safety infrastructure simply because its previous caller is being replaced.

Migration acceptance must include source/configuration scans for prohibited provider/model paths, tests that assistant flows make no external AI calls and require no AI key, removal of obsolete provider setup/disclosure UI, and regression tests proving the CUBI-native command path works independently.

## 7. Delivery order

1. Retire the prohibited provider-backed assistant path and record the replacement boundary without damaging action security.
2. Design the versioned command envelope, supported command catalogue, language normalization and domain vocabulary.
3. Implement the internal deterministic command parser and ambiguity/missing-field resolver.
4. Connect read-only project queries and authoritative calculations first.
5. Expand typed application tools for project, WBS, activities, relationships, calendars, resources, progress, costs and other approved domains.
6. Complete the guided project-creation workflow and safe action lifecycle.
7. Complete structured file intake, mapping preview and import reconciliation.
8. Complete reporting, chart selection and report templates.
9. Complete durable engineering knowledge, learning administration, research and backup/restore.
10. Develop and validate CUBI-owned voice recognition.
11. Integrate the same command engine into Web, Windows Desktop and Flutter/Mobile as those clients are delivered.
12. Run end-to-end, security, localization, performance and regression acceptance across every declared capability.

This order is a dependency sequence, not permission to drop any approved capability.

## 8. Acceptance and release gates

The assistant is not complete until the integrated release demonstrates all applicable checks:

- No third-party AI/ML model, model runtime, AI provider, external AI service, AI API key or provider fallback is required, configured or called.
- No provider abstraction or provider-selection UI remains as a supported assistant architecture.
- Typed commands in each declared supported language map to correct typed intents/entities/parameters across a versioned golden command suite.
- Ambiguous, incomplete, contradictory, unsupported and low-confidence commands stop safely and ask a focused clarification or report the limitation.
- Project-context resolution respects tenant/project/revision and current selection, with negative cross-scope tests.
- Read, search, analysis and comparison results match persisted records and authoritative Shared Core outputs.
- Every mutation uses scoped grants, proposal/approval policy, revision recheck, idempotency, audit, transaction behavior and fresh persisted read-back.
- Project creation and updates are resumable, validated and reproducible.
- File imports show provenance and all unsupported/ambiguous fields; no silent data loss occurs.
- Reports and charts use real persisted data and valid measures only.
- Knowledge capture, retrieval, approval, publication, deletion, backup and restore pass scope-isolation and provenance tests.
- Voice recognition, when released, uses only the CUBI-owned pipeline and passes declared-language audio tests without cloud transcription or third-party AI models.
- Web, Windows Desktop and Flutter/Mobile use the same command schemas and Shared Core semantics; unsupported client capabilities are not advertised.
- All existing security, privacy, multilingual, Jalali/Gregorian, scheduling, calculation, audit and project-control regression tests remain valid.

## 9. Current repository status — no overclaim

The repository already contains reusable foundations, including:
- A typed action runtime and proposal/approval/execute boundary with authorization, stale-revision checks, idempotency and audit.
- An activity creation tool and additional bounded action/tool structures.
- A deterministic Smart Guide connected to workspace states and real controls.
- Language context contracts and existing localization infrastructure.
- A learning-memory record contract with scope and publication gates.
- Browser speech adapters, which are not by themselves a compliant CUBI-owned offline speech engine.
- Document parsing/persistence foundations and an OCR protocol, which are not proof of a completed in-house scanned-document recognition pipeline.

The current main branch also contains a provider-backed orchestration/chat path. That path does not satisfy this principle and is legacy work to retire or replace. A language tag contract is not automatic language detection; an action runtime is not a complete command-understanding engine; a memory schema is not durable memory; a menu is not an integrated tool. Every capability must be verified by its actual code path, exact commit, tests and end-to-end evidence.

No documentation update, architecture diagram, mock, unmerged branch or planned tool earns implementation completion credit.
