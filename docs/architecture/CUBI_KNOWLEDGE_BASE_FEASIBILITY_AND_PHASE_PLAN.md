# CUBI Model-Free Project Management Knowledge — Feasibility and Deferred Delivery Plan

**Assessment date:** 2026-11-05  
**Status:** Feasible with a bounded, deterministic scope; production build explicitly deferred.  
**Priority:** After completion and acceptance of the single canonical CUBI Visual Workspace shell.  
**Implementation tracker:** #1540.  
**Binding architecture:** Product Principle 13 and CUBI Internal Command Assistant Principle.  
**Repository evidence baseline:** main at 49201ddfbec83550e7147ce2fa3cc961e39eef55.

## 1. Executive feasibility decision

The proposed capability is technically feasible without any third-party AI model, AI provider, inference runtime, embedding service, external AI API/key, generative summarizer, AI OCR, or cloud speech service, provided that CUBI keeps its assistant command-oriented and its knowledge domain bounded, structured, source-grounded and deterministic.

The feasibility decision is **GO for phased engineering after the Visual Workspace release gate**, with these qualifications:

- The core knowledge repository is not a greenfield task: a versioned domain record and an append-only SQLite/PostgreSQL repository adapter already exist on main.
- The remaining work is substantial: source licensing/rights management, document parsing, structured knowledge records, search indexing, deterministic assistant integration, admin review/publication, full audit, deletion/retention, backup/restore, migrations, benchmarks, localization and end-to-end security tests.
- Ordinary digitally generated PDFs and structured HTML can be processed with non-AI parsing libraries after license/security review. Scanned/image-only PDFs are a separate and much harder problem under the no-third-party-AI/OCR rule.
- Without embeddings or a language model, retrieval can still be reliable for a defined construction/project-controls vocabulary using normalization, aliases, taxonomies, exact fields, full-text search, deterministic ranking and clarification. It will not provide unrestricted semantic understanding of arbitrary prose. This is an intentional boundary, not a defect to hide.
- Educational content can be comprehensive and useful when CUBI authors original lessons, procedures, tables, formulas, checklists and synthetic examples, all linked to verified sources. It cannot autonomously generate expert-quality narrative explanations from every newly discovered book or PDF.
- The system must not begin implementation while the Visual Workspace shell remains the agreed first priority. Current work is limited to source/architecture registration and review; no new Qoder implementation scope is opened by this assessment.

**Conclusion:** Buildable as a CUBI-owned deterministic engineering knowledge and learning system. Not feasible as a general-purpose generative AI assistant under the approved architecture—and the product must not quietly reintroduce one.

## 2. Binding product constraints

The following are non-negotiable:

1. No third-party AI/ML model, whether local, hosted, downloaded or self-hosted; no external AI provider/service/endpoint/API/key; no optional provider adapter or fallback.
2. No model or embedding-based semantic search, vector database, generative summarization, pretrained AI classification/ranking/translation/OCR/voice model or cloud transcription.
3. All language understanding, intent classification, entity extraction, ambiguity handling, rules and response assembly are CUBI-owned deterministic software.
4. The assistant is a command-oriented project engineering system, not an open-ended chatbot.
5. Numeric schedule, calendar, CPM, float, resource, cost, progress, EVM and financial results come only from the authoritative Shared Domain/Calculation Core and approved application services.
6. Source documents, Internet content, user files and extracted text are untrusted data. They cannot change system rules, grants, command permissions or calculation semantics.
7. A project mutation requires a typed proposal, authenticated server-side authorization, revision check, required user approval, audit, transaction safety and fresh persisted read-back.
8. Knowledge scope is isolated into user-private, project-private, tenant-shared, general-candidate and general-published records.
9. General knowledge publication is default-deny and requires source/rights review, validation evidence, privacy/re-identification review, explicit policy/consent and authorized human approval.
10. Learning means versioned knowledge, dictionary, rule, procedure and lesson curation—not model training and not unrestricted conversation retention.
11. CUBI-authored help and UI must use CUBI terminology and branding. Proprietary vendor names, logos, copied prose and source branding must not leak into user-facing product help or UI. Exact bibliographic source identity/page pointers remain in the restricted internal provenance registry and admin review record.
12. The feature must work through the single canonical Visual Workspace and the same versioned contracts for Web, Desktop and Mobile; it must not introduce a competing chat/help workspace.

## 3. Existing repository foundations — verified code evidence

### 3.1 Already implemented on main

- src/construction_pm/ai_learning_memory.py defines the versioned record contract, lifecycle/status and signal enums, trusted retrieval scope, exact scope checks and fail-closed conditions for general publication.
- src/construction_pm/ai_learning_memory_repository.py defines the repository protocol and append-only SQLite and PostgreSQL adapters. Stored records use immutable (record_id, record_version) identity, idempotent same-version append and fail-closed conflicting-payload handling. Retrieval uses explicit SQL predicates for user-private, project-private, approved general-published and grant-enabled tenant-shared data, followed by domain eligibility checks.
- tests/test_ai_learning_memory_repository.py covers SQLite persistence across independent connections, exact user/project scope isolation, tenant-shared grant enforcement, candidate exclusion, approved general retrieval, idempotency/conflicting version payloads and caller-owned transaction behavior.
- PR #1542 is merged and is the source of the persistence repository slice.

### 3.2 What this code does not prove

- The repository is not a production assistant composition/retrieval workflow merely because its classes exist.
- The current record payload is a small lesson/conditions/limitations/evidence contract. It is not yet the full source/document/knowledge-card schema required for concepts, definitions, ordered procedures, formula contracts, units, input/output types, page anchors, rights decisions, test cases, localization, reviewer lineage and validity conditions.
- The repository does not itself provide the source registry, URL fetcher, PDF/HTML parser, rights gate, candidate extraction, full-text index, deterministic ranker, admin console or Academy runtime.
- Current repository tests inspected for this slice are SQLite-focused. The existence of a PostgreSQL adapter is not equivalent to proven PostgreSQL integration, migration and concurrency acceptance.
- The retrieved record set is not yet shown wired into the live CUBI command engine, Smart Guide, workspace UI or typed project tools.
- End-to-end authorization, durable audit, retention/deletion, export, backup/restore, schema migration, generalization privacy review, knowledge benchmarks and rollback remain open under #1540/#1530.
- The currently declared pyproject.toml dependencies include spreadsheet libraries and test/database packages but no explicit PDF parser or knowledge-ingestion package. No production PDF/HTML ingestion pipeline was found in the inspected code.

This is a strong start, but it is a foundation slice—not a completed learning system.

## 4. Feasibility by capability

| Capability | Feasibility without external AI | Assessment and boundary |
|---|---|---|
| Durable knowledge records | High; partly implemented | Reuse existing typed contract and SQLite/PostgreSQL adapters. Extend schema additively with immutable versions and migrations. |
| Source registry and metadata | High | Deterministic records for title, publisher, document ID, edition, date, checksum, status, rights, page anchors and source lineage. |
| Authorized Internet research | High, controlled | Ordinary HTTP/search access is allowed by the product principle, subject to separate admin permission, source allowlist, retrieval logs and rights checks. No AI summarization. |
| Digital PDF text extraction | High for clean text-layer PDFs | Standard non-AI parsing libraries can extract text and page anchors. Reading order, multi-column layouts, footnotes and tables need validation. |
| HTML extraction | High | Deterministic HTML parsing with sanitization, canonical URL, headings, table preservation and anchor tracking. |
| DOCX/XLSX/CSV extraction | High for supported structured formats | Existing spreadsheet ecosystem is a starting point; typed import staging and exact source provenance are required. |
| PDF table/formula extraction | Medium | Extract structural candidates; complex tables, merged cells, equations and symbols need manual validation and deterministic tests. |
| Scanned/image-only PDF OCR | Low for an initial release | Do not use third-party pretrained OCR/AI. Manual review or user-provided searchable originals are the initial path. A CUBI-owned OCR capability is a separate R&D program, not a dependency for the knowledge-base MVP. |
| Automatic expert narrative understanding | Not feasible as general-purpose behavior | No external or pretrained model is allowed. Use CUBI-authored knowledge cards, rules, taxonomies and reviewer-written explanations. |
| Deterministic knowledge-card creation | High for structured material; medium for narrative prose | Extract headings, definitions, enumerated steps, tables and formula tokens; a qualified reviewer authors/approves nuanced explanations. |
| Search and retrieval | High for the defined domain | Exact IDs, controlled topic hierarchy, normalized full-text, synonym dictionaries, phrase matching and deterministic scoring. No embeddings/vector DB. |
| Command/question understanding | High for declared command coverage | Finite-state/rule grammars, parameter schemas, terminology dictionaries and ambiguity questions. Coverage grows by tested software releases. Arbitrary open-ended questions remain unsupported. |
| Step-by-step Academy | High | Original authored lessons, prerequisites, examples, exercises, rubrics and links to actual CUBI page/command IDs. |
| Formulas and engineering rules | High with strict controls | Store variable definitions, units, assumptions, validity, source/version and test vectors; numerical project calculations call Shared Core, never a second engine. |
| Learning from user feedback | High as private candidate capture | Capture structured corrections/outcomes as candidates; feedback alone is not truth. Validation and approval are mandatory. |
| Cross-user general knowledge | Medium/high with human governance | Technically possible; privacy/re-identification and data leakage risks make publication strictly gated. |
| Multilingual knowledge | Medium/high in finite supported languages | CUBI-maintained dictionaries and human-reviewed lesson translations per language. No machine translation service; no promise of unlimited free-form multilingual comprehension. |
| Voice input | Separate, difficult workstream | CUBI-owned recognition is possible in principle, but requires a dedicated speech pipeline, domain audio corpora and language acceptance. Not a knowledge-base MVP dependency. |
| Backup/restore and migration | High | Extend platform database backup/migration; preserve versions, provenance, scope, rights and approvals. Must be tested by clean restore. |
| Offline Desktop knowledge | Medium/high | Package approved static knowledge and a local indexed store; explicitly reconcile admin-published updates. Private project scope remains local/authorized. |

## 5. Deterministic design that replaces external AI

### 5.1 Input and query understanding

Pipeline:
1. Preserve original user input.
2. Normalize Unicode, Persian/Arabic/Latin digits, punctuation, whitespace, dates, decimals, unit spellings and locale without changing original meaning.
3. Identify supported language through deterministic script and vocabulary cues.
4. Expand controlled aliases, abbreviations, spelling variants and reviewed synonyms.
5. Parse the request using versioned phrase grammars and typed command schemas.
6. Extract topic, project entity, target object, operation, date/range, unit and other parameters.
7. Resolve references only against the authenticated active project and current selection.
8. Validate required fields, types, units, permissions and ambiguity.
9. If confidence/uniqueness is insufficient for a consequential action, stop and ask one focused question.
10. Return a localized response assembled from approved templates, knowledge records and actual typed outputs.

### 5.2 Retrieval without embeddings

Use:
- exact source/knowledge IDs;
- normalized lexical/full-text indexes;
- title, section and topic fields;
- controlled topic hierarchy and cross-domain tags;
- CUBI-owned multilingual synonyms/aliases;
- deterministic phrase and field matching;
- scoring based on source authority/status, version freshness, topic match, applicability, validation and evidence coverage;
- hard conflict detection and explicit authority precedence.

Do not present lexical ranking as semantic reasoning. If the query cannot be mapped reliably to a supported topic or procedure, ask a focused clarification or report that the knowledge is not yet registered.

### 5.3 Response construction

Build answers from:
- CUBI-authored definitions and explanations;
- ordered procedures and checklists;
- typed fields/inputs/outputs;
- verified formula contracts and test results;
- actual Shared Core calculations;
- authorized project records;
- localized phrase templates;
- source title/version/page/section references in restricted provenance or neutral CUBI citations.

Never generate unsupported causes, lessons, productivity norms or project values.

## 6. Target architecture

1. **Source Registry:** immutable source identities, editions, current/superseded status, topic map and rights metadata.
2. **Rights and Authorization Gate:** separate server-enforced search, fetch, parse, candidate, validate, publish, export and restore permissions.
3. **Source Fetcher:** allowlisted HTTP(S), redirect/SSRF controls, content-type/size limits, timeout, checksum, malware checks and audit.
4. **Document Adapters:** non-AI PDF text, HTML, DOCX, XLSX and CSV parsers with versioned extraction contracts.
5. **Source Document Store:** rights-permitted bytes or external reference, metadata, checksum and stable anchors.
6. **Candidate Extractor:** deterministic headings, term, table, enum, formula-token, checklist and procedure extractors.
7. **Knowledge Authoring/Validation:** original CUBI explanations, formula cards, evidence, tests, limitations and subject-matter approval.
8. **Knowledge Repository:** extend existing immutable versioned record patterns and SQLite/PostgreSQL adapters.
9. **Search Index:** deterministic full-text and exact-field indexes; per-scope query enforcement.
10. **Command Engine Connector:** typed retrieval functions used by the CUBI command parser and template renderer.
11. **Admin Console:** source review, rights, candidate comparison, contradiction queue, approval, publish, retire and rollback.
12. **Academy/Smart Guide:** integrated into the one canonical workspace after shell acceptance; lesson pages and actions link to actual UI command IDs.
13. **Audit/Recovery:** append-only publication/retrieval events as required, retention/deletion, backup, restore and migration.
14. **Desktop/Offline Package:** authorized, version-pinned local knowledge subset using the same schema and rule versions.

## 7. Data model additions required

Do not overload the existing small learning-memory record with every source/document field. Add versioned domain records with stable IDs and relations:

- SourceRecord: publisher, title, identifier, edition, date, canonical URL, status, rights, allowed use, checksum, retrieval log and supersession.
- SourceDocumentVersion: source ID/version, permitted content pointer, parser version, language, page count and extraction status.
- SourceAnchor: PDF page/index, printed page, section, paragraph, table, figure or HTML anchor.
- ExtractionCandidate: candidate type, raw extracted structure if rights allow, source anchor, deterministic parser provenance and validation state.
- KnowledgeItem: concept, definition, procedure, checklist, formula, rule, command pattern, mapping, worked example or assessment.
- FormulaContract: expression/algorithm ID, typed variables, units, assumptions, range, limitations, rounding, Shared Core dependency and deterministic test IDs.
- Lesson/Module: objective, prerequisites, ordered steps, example-data classification, task, rubric, localization and actual CUBI page/command mapping.
- KnowledgeApproval: reviewer/approver, permissions, evidence, rights/privacy decisions, timestamps and decision.
- KnowledgeVersionRelation: supersedes, derived-from, translated-from and related IDs.
- SearchDocument: stable record reference, normalized tokens, controlled topics and index version; no duplicated private content outside its authorized partition.
- LearningProgress: user-private or tenant-authorized module/lesson progress, assessment outcomes and timestamps.
- AuditEvent: authenticated actor, operation, target/version, authorization decision, before/after references and result.

Every record must include schema version, lifecycle state, scope, source lineage and retention policy. Never mutate a published knowledge version in place; publish a new version and retain rollback history.

## 8. Copyright and source rights feasibility

- Oracle Version 26 manuals: use as an internal behavior reference. Do not commit or redistribute their PDF/text/screenshots. Full-text persistence or substantial derivative extraction requires license/legal approval for the exact intended use.
- PMBOK and ISO standards: obtain a legitimate licensed copy and explicit rights determination before persistent full-text processing. Public product pages and tables of contents are not full standards.
- UK Government and GAO sources: review the specific open-government/publication terms, attribution requirements and third-party embedded material for each document.
- Where rights do not allow full-text ingestion, store bibliographic metadata, exact source pointers and original CUBI-authored notes written independently; do not copy protected passages.
- Internal provenance may retain exact publisher/source identity and page references. User-facing workspace/help must use approved CUBI terminology and must not reveal prohibited vendor branding or copied prose.
- Rights decisions are per source/version and may change; ingestion must fail closed until an authorized decision exists.

This is a product engineering assessment, not a legal opinion.

## 9. Risk register and mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Users expect arbitrary LLM-style conversation | High | Define a supported command/learning grammar; show supported topics, examples and clear unsupported-query behavior. |
| Incorrect extraction from complex PDFs | High | Page/section provenance, table integrity checks, parser confidence flags and mandatory expert review for critical content. |
| Scanned PDFs cannot be read automatically | Medium/high | Prefer digital originals/searchable PDFs; quarantine scans for human handling; keep custom OCR outside MVP. |
| Copyright infringement | High | Per-source rights gate, restricted storage, page pointers, no public source-copy repository, original CUBI explanations. |
| Wrong or obsolete engineering guidance | High | Source version/status, effective dates, contradiction review, subject-matter approval, test cases and supersession. |
| Cross-project data leakage | Critical | Query-enforced tenant/project scopes, separate indexes or partitioned filters, negative tests, privacy review and immutable audit. |
| External content injection or malicious files | High | Treat all content as untrusted, sanitize, sandbox parsers, disable scripts/macros, URL allowlist, size limits and security scanning. |
| Formula duplication or divergent calculation | Critical | Formula contracts point to Shared Core; prohibit independent CPM/EVM/calendar computations; differential tests. |
| Multilingual ambiguity | High | Per-language dictionaries, reviewed translations and tests; clarify rather than guess. |
| Search misses relevant knowledge without embeddings | Medium | Taxonomy, curated synonyms, exact identifiers, phrase indexes, evaluation datasets and explicit unsupported response. |
| Admin approval becomes bottleneck | Medium | Role-specific queues, review templates, high-quality candidate extraction, source tiers and transparent status. |
| Backup appears successful but restore fails | High | Clean-environment restore drills and lineage/permission/retrieval comparison. |

## 10. Deferred priority and delivery gates

**Owner priority decision (2026-11-05): the Visual Workspace shell is the first priority. Knowledge-base implementation begins only after the canonical workspace shell passes its owner-approved acceptance gate.**

Before that gate:
- keep the source register, curriculum and architecture documents only;
- do not open Qoder implementation tasks for the knowledge base;
- do not add dependencies or start PDF/OCR experiments;
- do not redirect effort from the workspace shell;
- maintain #1540 as a deferred P0 product capability with no earned implementation credit for documentation.

After the workspace gate, use this dependency order:

### Phase A — Reconcile current foundations
- Read latest main and all merged learning-memory code/tests.
- Complete independent SQLite and PostgreSQL tests and migration proof.
- Review the current record contract; define new source/knowledge schemas rather than stretching the existing lesson record.
- Wire authenticated trusted scope and application service boundaries.

### Phase B — Rights-aware source registry and ingestion
- Implement source metadata, rights decisions, allowlist, fetch audit and checksums.
- Begin with sources whose terms explicitly permit the intended processing.
- Add PDF/HTML deterministic parsers and page/section/table anchors.
- Add parser fixtures and human review; scans remain manual.

### Phase C — Knowledge authoring and validation
- Implement definitions, procedures, checklists, formula contracts, worked examples and lesson records.
- Author the initial Riverside Pump Station curriculum from reviewed sources.
- Add expert review, deterministic formula tests, conflict/staleness detection and publication workflow.

### Phase D — Search and command-engine integration
- Add deterministic full-text/lexical, topic, exact-field and synonym indexes.
- Connect read-only knowledge search to the CUBI-owned command engine.
- Use templates and typed records to construct localized explanations.
- Prove ambiguity handling and no fabricated facts.

### Phase E — Admin publication and operational governance
- Implement separate permissions for search, ingestion, validation, publish, retire, export, backup and restore.
- Add immutable versions, approval audit, rollback, retention/deletion and generalization privacy checks.

### Phase F — Client, localization and offline parity
- Integrate Smart Guide in the existing canonical workspace (no separate help/chat workspace).
- Use shared schemas across Web, Desktop and Flutter/Mobile.
- Add only language packs that pass terminology, lesson, command and end-to-end tests.
- Package an approved offline knowledge subset and verify synchronization/version conflicts.

### Phase G — Separate advanced input R&D
- Evaluate CUBI-owned voice recognition and OCR independently.
- No scanned-PDF OCR or multilingual speech capability is claimed until it passes accuracy, privacy, offline and domain-vocabulary acceptance without third-party pretrained AI.

## 11. Work packages and indicative sizing

These are engineering person-day ranges for planning only, not an approved schedule or earned progress. They exclude the Visual Workspace work and assume the existing memory repository is reused.

| Work package | Indicative effort |
|---|---:|
| A. Foundation reconciliation, schema, migrations and PG/SQLite tests | 8–14 person-days |
| B. Source registry, rights workflow, fetcher, PDF/HTML parsers and audit | 18–30 person-days |
| C. Knowledge authoring, structured extraction, validation and initial academy | 18–28 person-days |
| D. Deterministic indexing, query mapping and command integration | 15–24 person-days |
| E. Admin review/publish, privacy, lifecycle and audit | 15–25 person-days |
| F. Workspace integration, initial localization, offline packaging and benchmarks | 15–25 person-days |
| **Core production capability total** | **89–146 person-days** |
| Separate CUBI-owned OCR R&D | Not estimated; independent research gate |
| Separate CUBI-owned multilingual speech R&D | Not estimated; independent research gate |

The ranges are uncertain until Phase A verifies the production assistant composition, repository adapters, auth, migrations and database deployment. Do not convert these estimates to calendar dates or CUBISITE weights until the authoritative Jalal 5 workbook is re-baselined and dependencies/owners are approved. Documentation or this feasibility assessment earns zero implementation credit.

## 12. Production acceptance criteria

The knowledge base is not complete until all relevant tests pass on one exact tested commit:

1. No forbidden model/provider/runtime/API/embedding/OCR/voice endpoint exists in dependency, configuration, source or network traces for the knowledge workflow.
2. Approved PDF/HTML fixtures preserve page/section anchors, heading hierarchy, table columns, units, equations, warnings and footnotes.
3. Unknown or blocked source rights stop persistent content ingestion.
4. Every published knowledge record has a resolvable source/version/page anchor or approved independently authored basis, plus validation evidence and human approval.
5. Draft, stale, withdrawn and superseded sources are labelled and cannot be silently returned as current rules.
6. Exact user/project/tenant scope tests prove no unauthorized retrieval across SQLite and PostgreSQL.
7. General publication requires rights, consent/policy, privacy/re-identification, validation and admin approval.
8. Candidate/rejected/unvalidated lessons never appear as approved general knowledge.
9. Deterministic queries retrieve expected lessons across the declared supported language fixtures; ambiguous/unsupported input requests clarification or reports the gap.
10. Formula records pass unit/dimensional checks and deterministic fixtures; all schedule/cost/resource/progress/EVM numeric outputs come from Shared Core.
11. Academy exercises distinguish synthetic data from live project data and do not write to a live project by passing a lesson.
12. Admin actions are permission-separated, denied actions are audited, and publication/rollback is versioned.
13. Retention/deletion, full backup, clean restore, migration and rollback preserve IDs, lineage, rights, approval, scopes and retrieval behavior.
14. Browser tests prove the guide operates in the one canonical workspace without displacing it or changing its dimensions unexpectedly.
15. Gold benchmarks cover beginner/practitioner/specialist explanations, common project types, missing inputs, source conflicts, false positives, privacy leaks and regression.
16. All relevant existing workspace, assistant, authorization and Shared Core tests remain green.

## 13. Final recommendation

Proceed with the capability after Visual Workspace acceptance, using the existing learning-memory contract and repository as a foundation. Start the first implementation slice with database/auth/migration reconciliation and source-rights controls—not with an AI integration, vector search, automatic textbook summarizer or scanned-PDF OCR.

The realistic product promise is a professional, auditable, source-grounded, multilingual project-management knowledge and command-guide system for a defined construction/project-controls domain. It can be reliable and valuable without external AI, but its coverage grows through authored knowledge, tested dictionaries, explicit rules, source maintenance and qualified human review.

The current state is **feasible / deferred / not production-complete**.
