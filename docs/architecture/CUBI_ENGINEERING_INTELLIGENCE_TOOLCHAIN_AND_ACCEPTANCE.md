# CUBI Engineering Intelligence — Toolchain, No-Key Architecture and Acceptance Plan

**Requirement reaffirmed by product owner:** 2026-10-28  
**Status:** Mandatory P0 product/release scope; implementation is not complete merely because this plan is committed.  
**Canonical tracking:** [#1423 — production assistant V1](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1423), [#1530 — production authorization and execution](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1530), [#1540 — interactive learning and durable memory](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1540), and [#1546 — reconcile the requirements into the CUBISITE website schedule](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1546).  
**Companion contracts:** `AI_ASSISTANT_V1_REQUIREMENTS.md`, `INTERACTIVE_ENGINEERING_LEARNING_MEMORY.md`, `PRODUCT_PRINCIPLES.md` Principle 11, and `CUBI_MULTILINGUAL_AND_AI_PERMISSION_REQUIREMENTS.md`.

## 1. Product decision: Engineering Intelligence is a core differentiator

The CUBI assistant is a persistent, multilingual construction-engineering and project-controls partner—not a generic chat widget. It must guide users through project creation and editing, learn from verified experience, understand authorized project sources, use the real application's capabilities, recommend defensible schedule/control/reporting options, and explain its reasoning at a suitable level for the user.

The goal is cumulative improvement across releases: validated engineering methods, successful workflows, corrections, documented limitations, and reviewed research become versioned knowledge that can be backed up, transferred to a later product version, evaluated, and rolled back. The assistant must not copy one customer's private project or conversation into another customer's context.

This requirement is additive. It does not remove or weaken any existing CUBI web, desktop, mobile, multilingual, offline, project-controls, calculation, security, import/export or release requirement.

## 2. API-key decision: a key is provider-specific, not a system-wide prerequisite

Do not design CUBI so that every assistant capability stops working when an external AI API key is absent. Separate deterministic application capabilities, local inference, and optional remote inference.

| Capability | Must work without an external AI API key? | Required implementation |
|---|---|---|
| Project, WBS, activity and relationship IDs/codes | Yes | Deterministic ID/code policies and validators |
| Calendar, CPM, dates, float, critical path, resource/cost/EVM calculations | Yes | Authoritative Shared Domain/Calculation Core and application services |
| Read structured Excel and supported Word/PDF/project files | Yes | Format-specific parsers and typed mapping; no LLM required to parse a known structure |
| OCR of scans/images | Yes | Local OCR runtime and language data; for Persian, package and test the relevant `fas` data |
| Speech-to-text | Yes | Local speech model/runtime for true offline operation; browser SpeechRecognition may be an optional fallback, not an offline guarantee |
| Deterministic daily/weekly/monthly/yearly reports and chart data | Yes | Authenticated query services, report templates, and typed chart/report contracts based on persisted data |
| Persistent lessons, memory, provenance, full-text search, backup/restore | Yes | Versioned database/repositories and portable bundle tooling |
| Public article fetch/ingestion | No AI key required for ordinary accessible public pages | Explicitly authorized network fetcher, source/copyright metadata, safe extraction and review workflow; internet access is still required |
| Flexible multilingual understanding, free-form project interpretation, WBS/activity proposals, nuanced recommendations | Needs a language model or deliberately limited deterministic dialogue | Prefer a pluggable local model/runtime when no external key is desired; a remote model is optional and must be explicitly configured |
| Semantic summarization of articles or ambiguous files | Model needed for high-quality flexible reasoning | Local model without a provider API key, or an explicitly approved remote provider |

**Important distinction:** “No external API key” does not mean “no model needed.” Strong, flexible natural-language understanding requires a model. A local model requires installed runtime, model weights, compatible hardware/resources, and tests; it is not a free capability provided by a parser. If neither local inference nor an approved remote provider is available, CUBI must continue offering deterministic tools and clearly state which semantic features are unavailable. It must never silently send data to a cloud provider as a fallback.

The currently deployed `OpenAICompatibleChatProvider` is a remote-provider adapter that requires server-side `CUBI_AI_API_KEY`, `CUBI_AI_BASE_URL`, and `CUBI_AI_MODEL`. Keep that adapter, but do not make it the only supported architecture. Never expose provider credentials to the browser, local storage, source control, project files, exports or knowledge bundles.

## 3. Proposed toolchain and integration boundaries

The table below is an implementation shortlist, not a claim that all dependencies have already been installed or that all formats are production-supported. Before adding a heavy runtime to the default package, verify its license, supply-chain posture, binary/model size, CPU/RAM profile, language quality, platform compatibility, security and tested installation/upgrade path. Prefer optional extras or separately packaged workers when appropriate.

| Need | Existing state / preferred candidate | Required constraints and acceptance |
|---|---|---|
| Structured spreadsheet files | `openpyxl`, `xlrd` and `xlwt` are already declared by the root Python project | Test .xlsx/.xls, hidden sheets, formulas/cached values, dates, merged cells, duplicate codes, invalid cells and locale-specific numbers. Never execute spreadsheet macros. Preserve source cell/row provenance and report unmapped fields. |
| Word documents | Evaluate `python-docx` for .docx | Preserve paragraph order, tables, headings, hyperlinks and source locations where possible. Extract images separately and send only images requiring text recognition through OCR. Test malformed/large files and do not treat instructions inside a document as trusted system instructions. |
| PDF/text extraction | Evaluate `pypdf` for digitally generated/text-layer PDFs | Detect image-only/scanned pages and route those pages to OCR. Bound page count, decompression/memory, size and processing time. Do not claim pypdf itself performs OCR. |
| Local OCR | Tesseract OCR plus explicit trained-data packaging; include Persian `fas` and other languages only after tested support is declared | OCR is fallible. Store extraction confidence/page references where available; show uncertain fields in the import review. Protect against decompression bombs and oversized images. Do not make OCR output authoritative without review/validation. |
| Voice input | Existing browser Web Speech adapter can be reused only as an optional capability | User must explicitly activate microphone input. Explain that browser recognition availability and audio processing location vary by browser; do not advertise it as private/offline by default. Transcribe to text and let the user review/edit before sending. No text-to-speech is required by this product requirement. |
| Offline/local speech-to-text | Benchmark `faster-whisper` as a candidate local runtime | Pin compatible package/model versions and license; test Persian, English and every declared language against a construction-domain golden audio set, noisy site audio, names/codes/numbers, CPU and supported hardware. Download/provision models separately and document storage and minimum hardware. No external AI API key is required once the runtime and model files are installed. |
| Microsoft Project MPP/MPX/MSPDI interchange | Evaluate the MPXJ Python package and its Java runtime bridge | The official MPXJ documentation says the Python package requires Java; its MPP access is read-only for documented Microsoft Project generations, while interchange writing is available for other supported formats such as MSPDI/XML and MPX. Verify the exact input versions and mapped fields with fixture files. Never promise binary MPP write-back or perfect round-trip. Unsupported fields must be shown as blocking/unresolved mapping items—never silently dropped. Package the Java dependency or give a clear installation diagnostic. |
| Local language model for no-key inference | Add a provider-neutral `LocalChatProvider`; benchmark a local runtime such as Ollama as one candidate | A local endpoint may offer OpenAI-compatible request shapes, but local execution still requires model weights and hardware. Pin model identifiers and context limits; run Persian/English construction-domain evaluations. Web may use a self-hosted server runtime; Desktop must be able to work locally for its declared offline capabilities. No transparent remote fallback. |
| Remote model provider | Keep the current server-only OpenAI-compatible adapter, behind explicit operator configuration and user/data-policy disclosure | Remote AI is optional. Only configured endpoints receive prompts/files or project data; secrets stay on the server. Respect cost/rate/latency budgets and tenant retention/processing requirements. |
| Knowledge retrieval | Start with durable relational records and full-text search using the existing database boundary; evaluate local embeddings/vector search only when measured retrieval quality requires it | Keep exact scopes and permission checks in repository queries. Embeddings and indexes must be rebuildable/versioned and must not bypass authorization. No external embedding API is mandatory; local embeddings are an option. |
| Reports, charts and layouts | Extend typed report specifications and existing CUBI report/chart/UI infrastructure | Model may recommend an output; report values and chart series must come from the authorized persisted project read model and the authoritative calculation outputs. Do not let a model fabricate numbers, chart series or completion. |
| Knowledge backup and migrations | Versioned export/import bundle and repository/database migrations | Include stable IDs, schema version, provenance/source refs, record lifecycle state, scope, validation/approval state, lineage, dependencies and model/embedding metadata where relevant. Do not export secrets. Verify checksum, restore, access isolation and forward/rollback compatibility. |

**Research references for implementation review (not a decision to adopt blindly):**
- MPXJ format matrix and read/write limitations: https://www.mpxj.org/supported-formats/
- MPXJ Python package setup and Java requirement: https://www.mpxj.org/howto-start-python/
- Local STT candidate and platform constraints: https://github.com/SYSTRAN/faster-whisper
- Tesseract trained language data, including Persian: https://tesseract-ocr.github.io/tessdoc/Data-Files
- pypdf scope and OCR distinction: https://pypdf.readthedocs.io/en/latest/user/extract-text.html
- Browser SpeechRecognition compatibility/limitations: https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition
- Local-model API option: https://docs.ollama.com/api/introduction
- Existing workbook parser project: https://openpyxl.readthedocs.io/

## 4. End-to-end user workflows

### 4.1 Conversational project builder

The assistant must lead the user through a complete, resumable project-creation workflow. It should ask only questions needed at the current stage and use known/verified source data where available. At minimum, the workflow covers:

1. Project name, unique project code, type, scope, description and the intended output.
2. Project start/data date, selected display calendar and the canonical calculation/calendar configuration.
3. Working days, hours per day, shift/calendar selection, weekends, exceptions, holidays and the treatment of lag.
4. WBS hierarchy, numbering/code policy, levels and work packages.
5. Activity names, stable IDs/codes, activity types, duration estimates and relevant dates/constraints.
6. Logic links (FS/SS/FF/SF), lags/leads and applicable lag calendar, with missing/contradictory relationships highlighted.
7. Resource/role/equipment assignments, units, capacities and calendars when those data are in scope.
8. Baseline, actual starts/finishes, completed/remaining work, quantities, progress and status-data date when provided.
9. Cost/commercial/EVM inputs, only where the user/file supplies the needed evidence and the relevant CUBI tool supports them.
10. Review of assumptions, unresolved items, duplicate codes, unsupported fields, validation errors and proposed schedule results.
11. Save as a **new independent project** or explicitly select an existing project to update. Creating/saving or mutating authoritative project state requires the user's required grant, preview and confirmation.
12. Run the Shared Core through real application services, read back the persisted result, and show the created project/revision identity and any limitations.

The assistant must be able to pause/resume this wizard and continue from the current stage without losing approved answers. It must not invent real progress, calendars, resource facts, quantities, costs or actual dates. Proposed IDs may be allocated deterministically; IDs/codes must be unique, stable after creation and validated by CUBI.

### 4.2 File-to-project conversion

An input file is not a project merely because text was extracted. All imports must follow:

**Upload → safe file classification → isolated extraction → typed normalized staging model → mapping/provenance preview → clarification questions → validation → proposed project creation/update → explicit permission/approval → transaction commit → authoritative calculation → fresh read-back → reconciliation report.**

For an MPP or another schedule file, inspect every supported relevant field the format/parser exposes, including as applicable: project properties, WBS hierarchy, activity IDs/codes/names, durations and dates, activity types, relationships and lag/lead, calendars and exceptions, constraints, resources/assignments, baseline, actual/progress fields, custom fields, notes and source identifiers. For each field, record **mapped**, **not present in source**, **unsupported by current parser**, **ambiguous**, or **rejected by validation**. Preserve a source file checksum and row/task/field provenance where available.

The user must see what will be created, what will not be imported, and what must be answered. A lossy/ambiguous import cannot be marked “complete”. Create a new separate project by default; modifying an existing project is an explicit different action.

### 4.3 Daily, weekly, monthly and annual reports

The assistant must support user-requested reporting periods and audience: e.g. daily site progress, weekly execution, monthly management, annual/portfolio overview. It must:

- Ask for or resolve the reporting period, data date, audience, project/WBS filters and applicable comparison/baseline.
- Read persisted source records and revision-bound Shared Core outputs; show the as-of date and the source revision/scope.
- Distinguish actuals, forecasts, targets, estimates, assumptions, missing data and recommendations.
- Recommend report sections, KPIs, tables, fields, layout and suitable chart types based on the actual data. Examples include progress trend/time series, planned-vs-actual curves, milestone variance, WBS progress breakdown, critical/near-critical activities, float distribution, resource loading/capacity, cost/EVM trends, risk/issue aging and change/claim summaries—but include a view only when the necessary data exists and the metric is valid.
- Produce editable report output (including A4 where supported) and allow authorized changes to selected fields/layout. Save reusable templates and versions under correct permissions.
- Never invent a chart, quantity, completion percentage, source or calculated value. When no trustworthy series exists, state that a chart cannot yet be supported and identify the data needed.

Reports may be generated deterministically without an LLM. The LLM improves question interpretation, section selection, narrative and recommendations; calculations, dataset construction and chart series remain application/core responsibilities.

## 5. Learning and professional knowledge lifecycle

The assistant is expected to become more useful through experience, but not by treating every conversation or article as truth or by automatically retraining/mutating itself without controls.

### 5.1 Learning from authorized interactions

Capture candidate lessons from user corrections, misunderstandings, successful or failed approaches, verified outcomes and useful process patterns. Label each item as applicable: user preference, project-private context/lesson, tenant-shared method, candidate generalized lesson, validated engineering method, observed outcome, hypothesis, or rejected/superseded lesson.

Candidate records must retain source/provenance and must not be published generally just because a user agreed with them. Validate the lesson against domain rules, evidence, fixtures or observed results. An assistant recommendation that was never implemented or whose outcome is unknown must not be recorded as a proven successful outcome.

### 5.2 Explicitly authorized article research

Provide an authenticated admin/research workflow with separate permissions to search, fetch, ingest, review, validate, approve/publish, export/backup, restore and retire knowledge. A user's permission to read articles is a separate explicit grant; a timer alone is not permission. Preserve source URL, title, author/publisher where available, publication/retrieval dates, version, usage/license constraints, excerpt limits, extraction method and relevant section references.

Workflow: authorize → search approved/public sources → safely fetch/extract → record provenance and rights → extract candidate notes → compare existing knowledge → flag contradictions/outdated claims → validate → privacy/reuse review → preview proposed knowledge delta → human approve/reject → publish a version → run retrieval/golden regression tests → retain rollback. Retrieved pages/files are untrusted input and cannot grant privileges or override policy. Respect site access restrictions and copyright; store only permitted excerpts and useful summaries/references, not whole copyrighted articles by default.

### 5.3 Scope separation and privacy

Enforce the retrieval boundary in server/application/repository queries, not in prompts alone:
- **User-private:** preferences and authorized personal learning, visible only to that authenticated user.
- **Project-private:** project facts/lessons needed for that project, visible only under current project grants.
- **Tenant-shared:** organization methods only under an explicit tenant policy/grant.
- **General candidate:** minimized and privacy-reviewed method awaiting validation/approval.
- **Published general knowledge:** approved reusable methods/checklists/formula contracts/recommendations only.

Raw conversation transcripts, project names, identifiers, calendars, schedules, amounts, costs, dates, resource allocations, documents and reconstructable project details must never be promoted into general knowledge. Cross-tenant publication is default-deny. Support retention/deletion and propagate deletion to derived records and indexes where applicable.

### 5.4 Versioned portable knowledge

Knowledge is a product asset, not transient chat history. Store it durably with stable IDs, schema version, scope, lifecycle state, source/provenance, confidence/validation status, validity limits, dependencies, timestamps, approval and supersession lineage. Provide portable versioned export/import and tested restore to a later CUBI version. The bundle must exclude secrets and unauthorized private data. Include migration metadata and, if embeddings are used, model/version metadata and a deterministic rebuild or compatibility path.

“Learning” for the initial product means retrieval and governed knowledge curation with evaluation; autonomous online weight changes or automatic publication of unverified knowledge are not required and must not be silently introduced. New knowledge/model versions require golden interaction/project benchmarks, staged rollout, version pinning and rollback.

## 6. Typed application tools to deliver

These are real server/application tools, not buttons or model-only promises. Every mutation tool has a versioned schema, strict validation, exact-scope grants, idempotency where appropriate, audit, revision recheck, transaction safety, human approval where required, authoritative application/core integration and post-commit fresh-read verification.

- `project.create` / independent-project draft and publication.
- `project.read` / scoped workspace and project facts with source references.
- `calendar.configure` / workweek, exceptions, calendars and lag-calendar semantics.
- `wbs.create`, `wbs.update` / deterministic hierarchy and codes.
- `activity.create`, `activity.update` / activity fields, types, durations, actuals and status.
- `relationship.create`, `relationship.update` / FS/SS/FF/SF, lag and lag calendar.
- `file.inspect`, `file.map_preview`, `file.import_proposal` / extraction, provenance, mapping gaps and no-silent-loss reconciliation.
- `progress.report_import` / actuals, daily work, resources and quantities where supported by the current domain.
- `schedule.recalculate`, `schedule.query` / real Shared Core and revision-bound calculations only.
- `report.build`, `report.template.preview`, `report.template.update` / authorized persisted values, chart specs and layouts.
- `knowledge.lesson.propose`, `knowledge.lesson.review`, `knowledge.publish`, `knowledge.search`, `knowledge.export`, `knowledge.restore` / distinct grants and audit for every sensitive transition.

A listed tool is only a requirement until its application handler and end-to-end evidence exist. The LLM may formulate a proposal, but cannot call a hidden mutation path, bypass a grant, approve its own proposal or run a calculation in its own reasoning.

## 7. Sequenced work packages and release gates

All work below is P0 for the complete Engineering Intelligence Assistant release. The sequence describes dependencies; it is not earned-progress credit. Map the work to explicit activity IDs, owners, person-day estimates, dependencies, tests and evidence in the canonical website-only `cubisite.xlsx` schedule under #1546; preserve its 100.00 total weight exactly. Do not add weight, dates or progress estimates until the workbook and calculations are recalculated and reviewed.

| Work package | Deliverable | Dependency / evidence gate |
|---|---|---|
| EI-01 Provider abstraction | Explicit capabilities, remote adapter, local-inference adapter, no-key behaviour, no cloud fallback, safe diagnostics and cost/resource controls | Model-provider contract tests, secret checks, capability matrix |
| EI-02 Voice input | Click-to-record multilingual STT, transcript preview/edit, clear browser/local privacy behaviour | Persian/English and other declared-language audio fixtures, browser coverage, offline tests |
| EI-03 File/document intake | Isolated upload/parsers, source provenance, normalized typed staging, mapping preview and errors | XLS/XLSX/DOCX/PDF/scan golden files, malformed/oversized/security fixtures |
| EI-04 Schedule-file adapter | MPP/MPX/MSPDI import mapping through validated parser adapter | Version-specific fixture matrix, full field mapping/loss report, Java/package test, import reconciliation |
| EI-05 Conversational builder | Resumable wizard from project name through calendar, WBS, activities, IDs/codes, relations and optional actual/resource/cost inputs | Step/resume tests, missing-field clarification, duplicate-code and invalid-logic tests |
| EI-06 Authorized project tools | Real create/read/update/import/calculation handlers across supported domains | #1530 grants, approvals, audit, idempotency, stale revision, transaction and fresh-read tests |
| EI-07 Engineering reports | Daily/weekly/monthly/annual generation, data-driven chart selection, editable templates and narratives | Revision-bound values, empty-data rules, chart validity, A4/export/locale E2E tests |
| EI-08 Durable memory | Persist candidate lessons, source lineage, scope controls, private retrieval and deletion | Restart/fresh-read, scope isolation, deletion propagation and tenant boundary tests |
| EI-09 Research/review console | Admin-authorized source intake, contradiction checks, rights/privacy review and human publication | Permission denial, prompt-injection corpus, source provenance and publish audit |
| EI-10 Portable backup/migration | Full backup, incremental where supported, integrity checks, export/import, restore and V2+ migrations | Clean-environment restore drill, schema migration and lineage/retrieval compatibility evidence |
| EI-11 Evaluation and release control | Golden engineering conversations, file imports, projects, reports, privacy and language suites; versioned rollout/rollback | Compare candidate knowledge/model with prior release; block material regressions |
| EI-12 Integrated release | Web + Desktop-local + required Mobile integration using the same typed contracts and Shared Core | Exact commit CI, integration/E2E, security/privacy negatives, production deployment evidence |

## 8. Mandatory acceptance criteria

The Engineering Intelligence Assistant is not complete until a single integrated, exact tested commit demonstrates all applicable cases below:

1. A user can speak in a declared supported language, inspect/edit the transcript, and use it as an ordinary text request without text-to-speech.
2. A user can import an MPP fixture as a new independent project; project/WBS/activity IDs, activities, relationships, calendar details and available actuals are mapped or explicitly reported as missing/unsupported. No silent omission.
3. The project wizard asks for calendar/workweek/WBS/activities/relationships as needed, resumes after restart, and creates unique stable codes.
4. Saving or changing project state requires the correct role/grant and explicit proposal approval; denial/rejection/stale revision causes no mutation.
5. After commit and process restart, fresh reads show the created project, WBS, activities, relations, calendars and the corresponding authoritative schedule revision.
6. Schedule dates/floats/critical path and other numeric controls come from Shared Core/application services; model output cannot substitute calculations.
7. Daily, weekly, monthly and annual reports use the requested period and real persisted data. Recommended charts are justified by available measures, and missing data never becomes invented values.
8. A lesson proposed in a conversation persists and can be retrieved later by the same authorized scope; unapproved candidate lessons never appear as published general knowledge.
9. Private user/project/tenant memory is denied outside scope, and raw transcripts/files/project facts cannot leak through general retrieval or model prompts.
10. Internet research requires the correct grant, records source/provenance/rights and cannot auto-publish without a human approval gate.
11. Prompt injection in files or retrieved articles does not alter system policy, grant a tool or trigger a mutation.
12. Knowledge export, backup and restore preserve stable IDs, lifecycle status, provenance, scope, approval and lineage; a version migration is idempotent and recoverable.
13. A model/knowledge update that regresses golden project-building, schedule reasoning, report truthfulness, privacy or language behavior is blocked and can be rolled back.
14. No-external-key mode proves the deterministic features continue working; local semantic features prove that the configured local model really runs. When no model is available, limitations are disclosed and there is no silent cloud fallback.
15. Web, Desktop and Mobile expose only the capabilities that have end-to-end evidence. Localization, security, audit and existing project-control regression suites remain green.

## 9. Implementation status and anti-overclaim rule

At the time this plan is added, the repo has a remote OpenAI-compatible assistant adapter, a browser SpeechRecognition adapter, a conversational chat panel, spreadsheet libraries, a domain-level learning-record contract and partial project-plan action tooling. This does **not** prove a complete no-key semantic assistant, wired speech UI, complete Word/PDF/OCR/MPP intake, complete project-wizard toolset, durable learning/research/publish loop, portable knowledge backup, or report/chart recommendation end to end.

Do not add all large optional runtimes or model weights to the default install merely to make a checklist look complete. Build the adapters and small vertical slices first, review dependency/license/supply-chain and offline packaging, pin supported versions, install into the intended target image, and run the actual integration tests. Every completion claim must cite the changed paths, exact commit, tests, real persisted read-back and any remaining restrictions.

## 10. External technical references

These sources inform the tool shortlist and must be rechecked when implementation begins:
- MPXJ supported formats: https://www.mpxj.org/supported-formats/
- MPXJ Python installation (Java required): https://www.mpxj.org/howto-start-python/
- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- Tesseract language data: https://tesseract-ocr.github.io/tessdoc/Data-Files
- pypdf text extraction and scanned-PDF limitations: https://pypdf.readthedocs.io/en/latest/user/extract-text.html
- MDN SpeechRecognition: https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition
- Ollama local API: https://docs.ollama.com/api/introduction
- openpyxl: https://openpyxl.readthedocs.io/
