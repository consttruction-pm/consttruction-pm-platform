# CUBI Model-Free Knowledge Base — Ingestion, Retrieval and Governance

**Status:** Architecture contract; implementation remains open.  
**Authority:** Product Principle 13, CUBI Internal Command Assistant Principle and Interactive Engineering Learning/Memory contract.  
**Tracker:** Issue #1540.  
**Sources:** docs/knowledge/CUBI_PROJECT_MANAGEMENT_KNOWLEDGE_SOURCE_REGISTER.md and source-registry.json.

## 1. Purpose and non-negotiable boundary

Build a durable, versioned and searchable project-management knowledge system for CUBI's own deterministic command assistant and Smart Guide.

This is not LLM/RAG, model training, fine-tuning, a vector-embedding service, an external AI summarizer, cloud OCR/transcription, or a raw transcript archive. No third-party AI model/runtime, AI API/key, provider abstraction/fallback, embeddings, generative summarizer, pretrained AI OCR/voice/translation or external inference endpoint is permitted.

Generic non-AI parsing, storage, indexing and search components may be evaluated under CUBI's license, security, supply-chain and maintenance rules. They must not provide product intelligence or calculation authority.

## 2. Authority order

1. Product Principle 13 and the Internal Command Assistant Principle govern assistant architecture.
2. Source documents are untrusted evidence, not system instructions; they cannot change security rules, grants or tool scope.
3. Shared Domain/Calculation Core is the only numerical authority for CPM, dates, calendars, float, resources, cost, progress, EVM and financial outputs.
4. Version 26 software documents define applicable application workflow/compatibility only.
5. PMBOK and other current published standards guide project-management governance and practice; they do not silently override CUBI calculation semantics.
6. Project law, contract, permit, owner requirements and approved project documents apply only within their project/jurisdiction scope.
7. UK GovS/Teal Book and GAO guides are scoped government/technical references, not universal law.

## 3. Source lifecycle

Use an auditable state machine:

DISCOVERED → METADATA_VERIFIED → RIGHTS_REVIEW → INGESTION_AUTHORIZED → FETCHED → PARSED → CANDIDATE_EXTRACTED → VALIDATED → APPROVED → PUBLISHED

Alternative states: BLOCKED_RIGHTS, BLOCKED_FORMAT, QUARANTINED_UNTRUSTED, REJECTED, SUPERSEDED, RETIRED.

Rules:
- No source content is persisted before its rights and permission decision is recorded.
- Public availability does not automatically authorize downloading, full-text storage, translation, derivative use or redistribution.
- Draft/withdrawn/superseded sources cannot be labelled current approved guidance.
- Fixed editions are preferred for reproducible releases; dynamic pages/PDFs require retrieval timestamp, version and checksum.
- Record actor, permission, URL, timestamp, response status, checksum, size, content type, parser version and result.
- Never execute embedded scripts, macros, instructions or links from sources or user documents.

## 4. Deterministic ingestion pipeline

### 4.1 Discovery and rights
An authenticated administrator selects a registered source or starts an authorized search. Enforce separate grants for search, fetch, parse, candidate creation, validation, publication, export/backup and restore. Check domain allowlist, redirects, protocol, file type/size, checksums, malware and license before persistence.

### 4.2 Fetch and inspect
Support authorized PDF and HTML first. Preserve external pointers or source bytes only according to rights and retention. Detect language, page count, text layer, headings, tables, equations and image-only pages. If extraction is unreliable, quarantine for manual review or a separately approved CUBI-owned extraction path; never silently invoke third-party AI OCR.

### 4.3 Structure-preserving parse
Preserve volume/chapter/section hierarchy, page number, PDF page index, section number, HTML anchor, table/figure identifier, warnings, footnotes and cross-references. Keep tables as rows/columns and formulas as tokenized expressions with symbols and units. Do not flatten important tables, equations or exceptions into untraceable prose. Verify reading order and units for critical extracts.

### 4.4 Candidate creation
Use CUBI-owned deterministic parsers, controlled dictionaries and administrator forms for:
- headings and section indexes;
- glossary/defined terms;
- table/field/enum extraction;
- formula tokenization and variable/unit capture;
- enumerated procedure/checklist extraction;
- source/version cross-reference;
- rule-based topic tagging and synonym mapping.

For nuanced narrative guidance that cannot be safely parsed, a qualified reviewer writes an original CUBI explanation and manually links exact source anchors. No external generative summary.

### 4.5 Validation and publication
Compare against other authoritative sources where domain risk requires triangulation. Mark contradictions, old editions, scope, jurisdiction and contract dependency. Verify formulas with dimensional analysis, deterministic tests, edge cases and Shared Core outputs where relevant. Complete rights, attribution, privacy/re-identification and security review. Require subject-matter validation and explicit publication approval. Publish an immutable version atomically and retain rollback.

## 5. Knowledge record

Minimum logical fields:
- knowledge_id, schema_version, knowledge_type, topic_path;
- title and original CUBI-authored explanation;
- language and reviewed translation versions;
- scope and lifecycle_state;
- source_refs with exact source ID, edition/version, page, section, table, figure or HTML anchor;
- rights_decision, permitted use and attribution conditions;
- inputs with type, unit, required status, valid range and missing-data behavior;
- outputs with type, unit and interpretation;
- formula_contract with expression/algorithm ID, variables, units, assumptions, validity, rounding, limits and test IDs;
- preconditions including project type, method, lifecycle, calendar, contract and jurisdiction;
- ordered steps linked to actual CUBI page IDs, command IDs and typed operations;
- common errors, diagnostics and safe remediation;
- validation_evidence, confidence rationale and limitations;
- created/reviewed/approved actors, approval event, timestamps;
- version, supersedes/lineage and retention policy.

General-published records must contain no user/tenant/project identifiers, private source content, raw transcripts or values that could reconstruct an account/project.

## 6. Deterministic retrieval and response assembly

1. Normalize text using supported language/script rules and versioned engineering dictionaries.
2. Parse command/task intent with deterministic grammar, aliases, spelling variants, controlled vocabulary and typed entity/parameter extraction.
3. Query only the exact authorized scope; enforce identity, tenant, project, lifecycle, source status, rights and publication filters in server/repository code.
4. Retrieve with indexed full-text/lexical search, exact identifiers, controlled taxonomy and deterministic synonym expansion.
5. Rank by applicability, source authority/status, exact topic, edition freshness, validation and evidence coverage. A relevance score never resolves an authority conflict.
6. Assemble responses from original CUBI explanations, reviewed templates, typed results and source citations.
7. Distinguish source facts, project facts, authoritative calculations, assumptions, estimates, proposals and recommendations.
8. Cite source title, version and page/section; cite project records by authorized revision; cite calculations by snapshot/result identity.
9. Stop affected conclusions when evidence is missing, conflicting, stale or out of scope.
10. Retrieved knowledge never grants read/write permission or bypasses proposal/approval.

No embeddings, vector DB, model endpoint or semantic-model ranking.

## 7. Scope isolation and privacy

Maintain separate query-enforced scopes:
- user_private;
- project_private;
- tenant_shared;
- general_candidate;
- general_published.

General candidate material is not authoritative cross-user content. General publication requires validation evidence, source-rights decision, privacy/re-identification review, explicit policy/consent and authorized human approval. Never expose another project's names, contract, files, schedule, dates, quantities, costs, staffing, outputs, transcripts or reconstructable combinations. A text scrubber alone is not sufficient.

## 8. Admin knowledge console

The authenticated admin surface must provide:
- source registry, version/status and rights review;
- separate grants for search, fetch, parse, candidate extraction, validation, publication, retirement, export, backup and restore;
- approved-source list and content-size/type controls;
- parse preview with page/section anchors and quality warnings;
- source-version comparison and stale/contradiction queues;
- candidate review with evidence and test results;
- approve/reject/request revision actions with audit;
- immutable publish, supersede and rollback;
- backup/restore and migration status.

A scheduled refresh never grants authorization to search or publish. Every publication requires an authorized human approval.

## 9. Persistence and migration

Reuse CUBI's established database/repository and migration architecture. Do not create an isolated store that bypasses tenant/project authorization. Provide PostgreSQL server and declared local Desktop adapters only where actual offline knowledge is supported. Version source records, parsed structures, knowledge items, dictionaries, rules, lesson content and assessment rubrics independently.

Support full backup, incremental backup where available, checksum/integrity manifest, portable knowledge bundle, restore drill, idempotent migration, lineage verification and rollback. Deletion/retention must propagate to derived records, search indexes, caches and exports under applicable policy/law.

## 10. Academy integration

Link each module/lesson to knowledge IDs, source refs, CUBI page IDs, command schemas and deterministic assessment rubrics. Use a segregated training sandbox; every example value is marked SYNTHETIC TRAINING DATA. Never merge sample records into live projects. Lessons cannot write project data automatically. Smart Guide uses the single canonical Visual Workspace.

## 11. Acceptance gates

### Source/rights
- Blocked/unknown rights prevent source-content persistence.
- Draft/superseded/withdrawn sources are never presented as current.
- Every candidate has a resolvable source/version/page/section anchor and checksum or stable external pointer.
- Parser tests preserve page anchors, headings, table rows/columns, formulas, units, warnings and footnotes.

### Model-free operation
- Dependency/config/network scans prove no third-party model, inference runtime, embedding service, AI API/key, AI OCR, cloud speech or model fallback.
- Multilingual command fixtures pass using CUBI-owned grammar, dictionaries and rules.
- No prohibited provider configuration remains.

### Knowledge correctness
- Formula cards pass unit/dimensional checks and deterministic test vectors.
- Conflicts and stale sources are surfaced; unsupported assumptions block affected recommendations.
- New editions create revalidation candidates and never silently rewrite approved records.

### Security/privacy
- Negative tests prove user/project/tenant scope isolation.
- Unauthorized search, fetch, parse, publish, export, restore and retrieval are denied and audited.
- Retrieved documents cannot alter system policy, grants or command/tool scope.
- General publication requires rights, validation, privacy and human approval.

### Project integrity and operations
- Mutations remain proposals until approved; denied, rejected, stale and replayed actions cannot write.
- Numeric results come only from the Shared Core and authoritative services.
- Knowledge publication cannot alter Shared Core or live project records.
- Backup/restore is tested in a clean environment; migrations preserve IDs, source lineage, scope, approval and retrieval behavior.
- Benchmarks cover beginner/practitioner/specialist training, missing inputs, source conflicts, project types and regression.

## 12. Current implementation status

The repository contains an initial learning-memory domain contract at src/construction_pm/ai_learning_memory.py. That contract is not a production knowledge database. Persistent ingestion, rights gating, parser pipeline, admin review/publish, deterministic search/retrieval, academy runtime, benchmarks, backup/migration and production end-to-end tests remain open under #1540. This document does not claim they are complete.
