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

### 5.1 Ten locales, nine working languages

The product ships `fa`, `en`, `de`, `zh-CN`, `zh-TW`, `ar`, `fr`, `ja`, `ko`
and `ru` behind the registry in `construction_pm.knowledge.locales`. Simplified
and Traditional Chinese are separate locales that share the language code `zh`.
Persian and Arabic are RTL; every other locale is LTR. No subsystem hard-codes a
locale check: search, assistant, workflow, API and HTTP all resolve through the
registry, so a new locale is a registry entry, not scattered branching.

The registry also defines `source_language`, `default_language` and
`fallback_language` (all `en` today) and returns direction/script metadata to the
client.

### 5.2 Per-locale translation lifecycle

Translation is not a property of a card. Every locale owns one
`TranslationRecord` with independent content, version, review state and
publication state:

- status: `missing`, `draft`, `translated`, `review_required`, `approved`,
  `published`, `retired`;
- review: `pending`, `approved`, `rejected`;
- source: `official_source`, `cubi_authored`, `human`, `machine`, `imported`;
- fields: `locale`, `language_code`, `source_language`, title, summary, body,
  steps, prerequisites, warnings, limitations, relations,
  `technical_glossary`, `source_note`, `translation_status`, `review_status`,
  `translation_version`, `published_language_version`, `localization_metadata`,
  `content_hash`, reviewer and timestamps.

Rules enforced by the model and the service layer:

- a locale with no stored record is reported as `missing`, never replaced
  silently by English;
- machine output (`machine_translated: true`) can never be approved or
  published, even when a reviewer accepts it;
- approval requires a named human reviewer and sets `reviewed_at`;
- publication requires the source card to be published, the locale record to be
  approved and not machine output, and records `published_language_version`;
- publishing one locale never touches another. Russian can be published while
  Persian remains `translated`;
- editing an approved translation creates a new version and resets review to
  `pending`; the replaced version's title, summary, steps, hash and status are
  preserved in the immutable audit detail, and the contributor identity and
  translation source are stored on the record;
- retiring an approved or published locale keeps `published_language_version`
  for traceability but removes it from answerable content;
- a client-facing payload that borrows English title/summary/steps lists those
  fields in `fallback_fields` and sets `mixed_language: true`.


## 6. Search

Search ranks by lexical relevance over title, category, purpose, steps,
prerequisites, inputs, outputs, warnings and limitations. The tokenizer is
script-aware and deterministic:

- Persian/Arabic: letter forms, digits and diacritics are normalized; tanween
  and the accusative alif are folded so `مشروعاً` matches `مشروع`;
- Russian: common inflectional suffixes are reduced to one stem (`проект`,
  `проекта`, `проектом` share an index term);
- Chinese: no whitespace is required; text is tokenized into characters and
  bigrams for both Simplified and Traditional;
- Japanese/Korean: own scripts plus shared Han characters, with particles and
  verb suffixes stripped;
- Latin: German, French and English terms expand to the English official term.

The CUBI-owned glossary expands queries in every working language (for example
پروژه → project, создать → create, 创建 → create) and the same expansion is
applied at index time, so retrieval works in both directions: a Russian question
finds an English card, and an English question finds an approved Russian
translation. Expansion never invents a result; ranking still requires a real
lexical token match. BM25 (`k1=1.2`, `b=0.75`) with a title bonus is preserved.

Search accepts `locale` and the filters `language`, `category`, `source_id`,
`source_version`, `card_type` and `translation_status`. When a locale has no
usable translation, hits report the English content explicitly with
`fallback_used: true`, `translation_available: false` and the requested
translation status. Every hit carries retrieval evidence: query/response locale,
requested locale, content language, source language, translation status and the
matched terms and fields.

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

Language handling in every mode:

- the question locale is detected from script; the response locale is resolved
  with the precedence explicit request → saved profile locale → detected
  question language → product default;
- an explicit unsupported locale fails with `KNOWLEDGE_LOCALE_UNSUPPORTED`;
- only an approved (or published) translation may answer in that language;
- when the requested locale is not approved, the answer is still expressed in
  that language but the quoted content is the official English source, marked
  with `fallback_used: true`, `content_language: "en"` and the actual
  `translation_status`; the missing translation is stated in the response text;
- citations and card ids always point at the same card; source URL and title
  are preserved;
- every answer carries a `language_context` with locale, language code, source,
  question and response language, default/fallback language, direction and
  translation/review state, so a client never has to guess RTL/LTR or hide a
  missing translation.

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

### 8.1 Thirteen-item creation guidance

Every workflow view carries a `guidance` checklist with thirteen explicit items
and a localized title: organization/EPS, discipline and project
type, project name, unique identifier, identifier uniqueness, working calendar,
timezone, locale, permissions, reviewed summary, explicit approval, real
creation and creation audit trail. The checklist is derived from actual collected
state, not from UI assumptions.

Identity collection accepts `timezone`, `locale` and `permissions` in addition to
name and identifier. The timezone is validated as an IANA-style tag, the locale is
canonicalized through the locale registry, and permissions are validated
identifiers. Base settings persist timezone and locale, and the view reports
`locale`, `language_code` and `direction` so the client renders step titles and
the form RTL/LTR correctly.

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
- `GET /api/knowledge/locales`
- `GET /api/knowledge/search?q=&project_id=&limit=&locale=&language=&category=&source_id=&source_version=&card_type=&translation_status=`
- `GET /api/knowledge/cards?status=&type=&limit=`
- `GET /api/knowledge/cards/{id}?locale=`
- `GET /api/knowledge/cards/{id}/translations`
- `PUT /api/knowledge/cards/{id}/translations/{locale}`
- `POST /api/knowledge/cards/{id}/translations/{locale}/review`
- `POST /api/knowledge/cards/{id}/translations/{locale}/publish`
- `POST /api/knowledge/cards/{id}/translations/{locale}/retire`
- `POST /api/knowledge/cards/{id}/review|publish|retire`
- `GET|POST /api/knowledge/eps`
- `GET /api/knowledge/audit`
- `GET|POST /api/knowledge/memory`
- `POST /api/knowledge/assistant/ask` (body: `question`, `mode`, `project_id`, `language`)
- `POST /api/knowledge/assistant/guide/{topic_key}` (body: `action`, `project_id`, `language`)
- `GET|POST /api/knowledge/assistant/workflows` (body may carry `locale`)
- `GET /api/knowledge/assistant/workflows/{run_id}`
- `POST /api/knowledge/assistant/workflows/{run_id}/steps/{step}`
- `POST /api/knowledge/assistant/workflows/{run_id}/approve|skip|back|abandon`
- `GET|POST /api/projects/{id}/knowledge`

### 10.1 Contract for the workspace/UI owner

- `GET /api/knowledge/locales` returns `{locales: [...]}` in registry order with
  `locale`, `language_code`, `display_name`, `english_name`, `direction`,
  `script`, `aliases`, `source_language`, `default_language` and
  `fallback_language`.
- Search response: `{query, query_locale, response_locale, filters, hits,
  insufficient_knowledge}`. Each hit contains `title`, `snippet`, `score`,
  `source_url`, `card_id`, `language`, `source_language`, `translation_status`,
  `translation_available`, `fallback_used`, `matched_terms`, `matched_fields`
  and `evidence`.
- Card response: localized content plus `requested_locale`,
  `content_language`, `fallback_used`, `translation_status`, `review_status`,
  `missing_fields`, `fallback_fields`, `mixed_language`, `available_locales`
  and `language_context`. Render `fallback_used`/`mixed_language` visibly; do
  not present borrowed English text as a translation.
- Translation write/response: `locale`, `language_code`, `source_language`,
  `translation_status`, `review_status`, `translation_version`,
  `published_language_version`, `translation_source`, `machine_translated`,
  `technical_glossary`, `localization_metadata`, `content_hash`.
- Assistant response: `kind`, `message`, `language`, `source_language`,
  `response_language`, `content_language`, `translation_status`,
  `fallback_used`, `citations[]`, `card_ids[]`, `language_context`.
  `language_context.direction` (`rtl`/`ltr`) rules text alignment.
- Workflow response: `locale`, `language_code`, `direction`, `steps[]` with
  localized titles, `guidance[]` with `{key, title, complete}` and the existing
  `run_id`, `version`, `current_step`, `collected`, `review`, `approval_ready`.
- Per-locale publishing is explicit: call review per locale, then publish per
  locale. There is no bulk "publish all locales" endpoint.

Sessions come from the existing `cp_session` cookie. Project routes call the
real lifecycle `authorize_project`; the middleware never infers project access
from request bodies. Unknown routes return `404`, malformed JSON `400`, missing
or invalid sessions `401`.

### Mounting in the composed application

`construction_pm.knowledge.runtime.build_knowledge_runtime` binds the slice to
a composed WSGI application and returns a `KnowledgeRuntime` holding the
middleware, the store, the API and the workflow engine.

- `build_project_lifecycle_wsgi_app(..., knowledge_database=...)` wraps the
  lifecycle application with the knowledge middleware; omitting the argument
  keeps the previous application unchanged, so the surface is never served by
  accident.
- The managed preview composition always passes a database
  (`CUBI_KNOWLEDGE_DB`, default `<preview database directory>/knowledge.sqlite3`)
  and a `MasterDataPlanPort` over the authoritative WBS, activity and
  relationship APIs, so WBS and activity steps write real records.
- The workflow gateway is session-bound. The middleware publishes the
  authenticated `cp_session` through a context variable, each workflow call
  builds a `LifecycleProjectGateway` for that session, and the variable is
  reset after the request. A call with no bound session fails closed with
  `PROJECT_GATEWAY_SESSION_REQUIRED` instead of borrowing another identity.
- The schedule step still needs a schedule-settings port. Until a deployment
  supplies one, `apply_schedule` fails closed with
  `PROJECT_PLAN_SCHEDULE_SETTINGS_UNAVAILABLE`; the step may be skipped with a
  recorded reason, and no data date or calendar is invented.

## 11. Verification and evidence

- Knowledge tests: `python -m pytest -q tests/knowledge` → 182 passed.
- Full Python suite: 3,778 passed, 116 skipped, 3 warnings.
- Live Version 26 ingestion from the two authoritative HTML sources:
  - HTML Help (`client_help/en_US/toc.htm`): 982/982 converted, 0 failed.
  - User Guide (`English/User_Guides/p6_pro_user/toc.htm`): 557/557 converted,
    0 failed.
  - 1,539 topics converted in total; 509 cross-source duplicates merged onto
    canonical cards with `topic_merged` audit records; 1,030 unique cards
    retained.
- Source audit: every official HTML TOC and landing page was re-fetched and
  hashed. The alternate `pro-help` (988) and `pro-user` (527) editions are
  official but not ingested; the 527/557 discrepancy is resolved as two
  different User Guide TOCs, with only the G48902 edition (557) using the
  `p6-26-user-guide` id.
- Mandatory coverage: 31/31 areas covered by HTML Help; 29/31 by the User Guide
  alone (the combined corpus covers all 31).
- Multilingual evidence: ten locales, nine seeded translations
  (`translated`/`pending`, never published in the evidence database), published
  Russian exercised only in a disposable copy, ten localized searches, Russian
  and Persian workflow starts. Translation revisions keep the replaced content
  in immutable audit detail and a retired locale keeps its published version.
- Evidence: `docs/workspace/evidence/knowledge-multilingual-v26-2026-11-12/`
  contains the draft SQLite database, ingestion and coverage reports, the live
  source audit, the per-locale translation matrix, assistant smoke output,
  translation seed report and `SOURCE_STATUS.md`.

## 12. Deliberate non-goals and open items

- No external AI/provider integration, by design.
- No Visual Workspace, Gantt or client-side change: the surface is now served
  by the composed backend application, but rendering it in the workspace shell
  remains the shell owner's change.
- No claim that the supplementary PDF was extracted; its absence is recorded.
- Voice capture is a client concern; this slice accepts text.
- UI wiring into the shell must be performed by the shell owner in a separate
  change, preserving the visual boundaries recorded in the mission.
