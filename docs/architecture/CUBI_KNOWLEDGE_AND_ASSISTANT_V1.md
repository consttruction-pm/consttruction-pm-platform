# CUBI Engineering Knowledge and Assistant V1

Status: implemented module, evidence recorded 2026-11-12
Branch: `feature/cubi-knowledge-assistant-v1`
Base commit: `fe3f55c66de3570cdddf199fa0c997a4441420fd`

This document describes the independent knowledge, assistant and project-creation
workflow slice. It does not change the Visual Workspace Shell, Activities/Gantt
workspaces, toolbars, layout selector, Activity Details, Gantt context menus,
shared toolbar CSS/theme or the shell icon registry. No shared UI file is modified.

## 1. Design principles

- **CUBI-owned and model-free at runtime.** Every answer is produced by
  deterministic retrieval, extraction and workflow rules. No external model,
  provider SDK, API key or environment-variable configuration participates.
  `tests/knowledge/test_architecture.py` enforces this by scanning the package.
- **Source-first.** Knowledge comes only from the registered official Version 26
  sources. A card cannot be published without a validated source record, and a
  page is never reported as extracted unless its bytes were downloaded, parsed,
  validated and stored.
- **Provenance everywhere.** Topics carry source id, stable topic key, canonical
  URL, content hash, breadcrumb, headings, extraction state and snapshots.
  Cards carry source URL, source title, release and extraction time.
- **Honest gaps.** Unknown queries return `insufficient_knowledge`; stub pages
  record an explicit limitation instead of turning a heading into a procedure.
- **UI-independent.** Domain, storage, ingestion, card, search, assistant,
  permission, workflow and HTTP modules are reusable by Web, Flutter and Windows.

## 2. Module map

| Module | Responsibility |
| --- | --- |
| `knowledge/model.py` | Immutable domain types, ids, hashes, language detection, validation |
| `knowledge/sources.py` | Five official sources, topic URL resolution, mandatory coverage areas |
| `knowledge/html.py` | Dependency-free Help/User Guide page and TOC parser |
| `knowledge/ingest.py` | Resumable discovery → fetch → parse → validate → convert pipeline |
| `knowledge/cards.py` | Card classification, generation, review, publish, retire |
| `knowledge/search.py` | Persian/Arabic normalization, BM25 ranking, scope filtering |
| `knowledge/store.py` | Storage protocol used by the domain |
| `knowledge/sqlite_store.py` | Versioned SQLite repository, snapshots, append-only audit |
| `knowledge/assistant.py` | Training answers, Smart Guide progress, execution routing |
| `knowledge/workflow.py` | Ordered, resumable project-creation workflow |
| `knowledge/plan.py` | Real WBS/activity/relationship/schedule port adapters |
| `knowledge/api.py` | Transport-neutral audited application facade |
| `knowledge/http_routes.py` | WSGI middleware for knowledge and assistant routes |
| `tools/ingest_v26_help.py` | Operational ingestion command with coverage/report output |

## 3. Official source registry

Five Version 26 sources are registered. Three expose a parseable table of
contents and are ingestable:

- `p6-26-help` — Professional Help (`pro-help/toc.htm`, 988 topics)
- `p6-26-user-guide` — Professional User Guide (`pro-user/toc.htm`, 527 topics)
- `p6-26-html-help` — legacy HTML Help (`cd/G48902_01/client_help/en_US/toc.htm`, 982 topics)
- `p6-26-books` — documentation index (`books.html`), registered, not ingestable
- `p6-26-docs-home` — documentation set home, registered, not ingestable

The 815-page PDF is supplementary. It was not available in the workspace during
this run and is recorded as **MISSING / VERIFY** in
`docs/workspace/evidence/knowledge-v26-2026-11-12/SOURCE_STATUS.md`. Its pages
are not claimed as extracted.

## 4. Ingestion state machine

Each topic moves through:

`Pending → Downloaded → Parsed → Validated → Converted → Published`

`Failed` is terminal only while its retry budget remains. A later run retries
failed pages until `MAX_RETRIES` is exceeded. Converted pages are skipped unless
`--force` is supplied.

The pipeline is idempotent and restartable:

- Topic identity is `(source_id, topic_key)`, where the key is the stable
  relative HTML file name. Re-running does not duplicate topics or cards.
- Content hashes determine whether a changed page is stored as a new immutable
  snapshot.
- Cards are regenerated in place only when their content hash changes and the
  existing card is still a draft; published/reviewed cards are never silently
  overwritten by ingestion.
- The run is resumable at any page boundary. A partial database is valid input
  for the next run.
- HTTP fetches may run in parallel (`--fetch-workers`), while parsing, card
  generation and database writes remain ordered on one thread.

## 5. Knowledge tiers and cards

- **Central** knowledge: extracted official topics and their cards.
- **Project** knowledge: project-scoped records, isolated by tenant and project.
- **User operational memory**: private per-user preferences and workflow state.

Ten card types are supported: training, operation, configuration, concept,
workflow, troubleshooting, limitation, relationship, decision and reference.
Generation is rule-based and deterministic. A card always starts as
`DRAFT`; review moves it to `VALIDATED`, publication requires an authorized
reviewer, and retirement preserves history. Revisions and card events are kept.
Thin source pages produce an explicit "no body content" purpose and limitation
rather than a fabricated procedure.

## 6. Search

Search ranks by lexical relevance over title, category, purpose, steps,
prerequisites, inputs, outputs, warnings and limitations. Persian/Arabic
character variants and Persian digits are normalized; stopwords are dropped.
A CUBI-owned engineering glossary expands Persian query terms (for example
پروژه → project, ایجاد → create) so English official sources remain reachable;
the glossary never adds content or bypasses the lexical match threshold.
Scope filtering happens before ranking:

- central cards only when requested,
- project records only for the matching tenant/project,
- user memory only for its owner.

When no result clears the relevance threshold, the response states
`insufficient_knowledge` instead of inventing an answer.

## 7. Assistant modes

1. **Training answer** — grounded answer with citations, prerequisites, steps,
   warnings and limitations from validated/published knowledge.
2. **Smart Guide** — step-by-step progression with persisted progress; `next`,
   `back` and `complete` are audited.
3. **Real execution** — routes an approved operation to a real workflow adapter.
   It requires identity, the relevant permission, validation, a review hash,
   explicit approval and an audit record. Chat text alone never grants
   permission.

The assistant API accepts text and is voice-transport-ready: a Web, Flutter or
Windows client may supply recognized text. No voice engine is bundled here.

## 8. Project-creation workflow

The workflow enforces this order:

1. organization / EPS
2. discipline / project type
3. name and unique project id
4. review and confirmation
5. real idempotent project creation
6. base settings
7. WBS
8. activities
9. FS/SS/FF/SF relationships, lag/lead, data date and calendar
10. final control and verification

Properties:

- Optimistic concurrency: every mutation supplies `expected_version`; stale
  writes fail with a stable error code.
- `request_key` makes start requests idempotent.
- Back navigation is allowed before creation but clears downstream state; after
  creation it is locked.
- WBS, activities and schedule may be skipped only when marked skippable and a
  reason of at least eight characters is supplied. Each skip is audited.
- Creation is adopted after an interruption instead of duplicated.
- Approval is bound to `run_id | actor | review_hash`; the review hash covers
  the canonical collected JSON.
- The real lifecycle and plan boundaries are injected through protocols
  (`ProjectLifecycleAPI`, `P6WBSMasterAPI`, `P6ActivityMasterAPI`,
  `P6RelationshipAPI`, schedule/settings ports). A missing real port fails
  closed; no in-memory project pretends to be persistent.

## 9. Permissions and audit

New permissions: `KNOWLEDGE_READ`, `KNOWLEDGE_CONTRIBUTE`, `KNOWLEDGE_REVIEW`,
`KNOWLEDGE_PUBLISH`, `ASSISTANT_ACTION`.

- viewer: project read, form read, knowledge read
- planner: project write/schedule, form read/contribute/submit/review/export,
  knowledge read/contribute, assistant action
- project_admin: project administration, form publish/approve/library admin,
  knowledge read/contribute/review/publish, assistant action

Every coverage read, search, card review/publish/retire, knowledge write,
assistant ask, guide transition, workflow transition and creation attempt
writes an append-only audit row with actor, tenant, action, entity, outcome,
time and detail. Audit rows are never updated or deleted by the package.

## 10. HTTP surface

The WSGI middleware owns only `/api/knowledge*` and
`/api/projects/{id}/knowledge`, delegating every other path unchanged.

- `GET /api/knowledge/coverage`
- `GET /api/knowledge/search?q=&project_id=&limit=`
- `GET /api/knowledge/cards?status=&type=&limit=`
- `GET /api/knowledge/cards/{id}`
- `POST /api/knowledge/cards/{id}/review|publish|retire`
- `GET|POST /api/knowledge/eps`
- `GET /api/knowledge/audit`
- `GET|POST /api/knowledge/memory`
- `POST /api/knowledge/assistant/ask`
- `POST /api/knowledge/assistant/guide/{topic_key}`
- `GET|POST /api/knowledge/assistant/workflows`
- `GET /api/knowledge/assistant/workflows/{run_id}`
- `POST /api/knowledge/assistant/workflows/{run_id}/steps/{step}`
- `POST /api/knowledge/assistant/workflows/{run_id}/approve|skip|back|abandon`
- `GET|POST /api/projects/{id}/knowledge`

Sessions come from the existing `cp_session` cookie. Project routes call the
real lifecycle `authorize_project`; the middleware never infers project access
from request bodies. Unknown routes return `404`, malformed JSON `400`, missing
or invalid sessions `401`.

## 11. Verification and evidence

- Knowledge tests: `python -m pytest -q tests/knowledge` → 94 passed.
- Full Python suite (excluding three modules whose optional `xlrd`/`xlwt`
  dependencies are not installed in this image): 3616 passed, 113 skipped.
- Live Version 26 ingestion: 2,497 topics converted, 0 failed:
  - help 988/988
  - user guide 527/527
  - legacy HTML Help 982/982
- Mandatory coverage: 31/31 areas covered in help and legacy HTML Help;
  29/31 in the user guide (combined set covers all 31).
- Evidence: `docs/workspace/evidence/knowledge-v26-2026-11-12/` contains the
  SQLite database, coverage JSON, ingestion report JSON, provenance summary,
  source-status notes and an assistant smoke report.

## 12. Deliberate non-goals and open items

- No external AI/provider integration, by design.
- No Visual Workspace or Gantt UI change; the assistant surface is API/domain
  only in this slice.
- No claim that the supplementary PDF was extracted; its absence is recorded.
- Voice capture is a client concern; this slice accepts text.
- UI wiring into the shell must be performed by the shell owner in a separate
  change, preserving the visual boundaries recorded in the mission.
