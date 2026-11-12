# Post-merge audit — Knowledge, assistant and project workflow (V26)

**Audited SHA:** `835c1fc172030155f8a3b8808ca9c6f839f0b6ad` (`main`)
**Merge under review:** PR #1794, feature head `c315ff927a55095a3f3d2e08dac828741f5a3949`,
squash merge `37be1078febbfc9e7a4619e772f87406888f45d0`, merged 2026-11-12T14:31:38Z.
**Audit rule:** the merged code was executed, not read from the branch description.
A claim is only `VERIFIED` when a test or a live probe on the merged tree shows it.

## Verdicts

| # | Claim | Verdict | Decisive evidence |
|---|-------|---------|-------------------|
| 1 | Official HTML Help ingestion (`client_help/en_US/toc.htm`) | VERIFIED | `coverage.json` 982 discovered/converted, 0 failed; live audit HTTP 200, 982 TOC topics; `tests/knowledge/test_ingest.py::test_pipeline_converts_every_discovered_topic` |
| 2 | Official User Guide ingestion (`English/User_Guides/p6_pro_user/toc.htm`) | VERIFIED | `coverage.json` 557/557, 0 failed; live audit HTTP 200, 557 TOC topics; same test family |
| 3 | Stable source identity and content hashes | VERIFIED | `model.topic_id_for(source_id, topic_key)`; 64-char `content_hash` on every topic/card; `test_ingest.py::test_changed_content_is_snapshotted_on_force` |
| 4 | Idempotent ingestion and resumable processing | VERIFIED | `IngestionPipeline._work_queue` resumes `pending/downloaded/parsed/validated/failed`; `test_second_run_is_idempotent`, `test_failed_page_is_retried_on_the_next_run`, `test_max_pages_limits_the_queue_without_losing_discovery` |
| 5 | Cross-source duplicate handling with provenance | VERIFIED | `test_identical_topics_from_two_official_roots_are_merged`; merged cards keep both topic URLs and write `topic_merged` audit; 509 merges of 557 User Guide topics |
| 6 | Card lifecycle Draft → Review → Publish → Retire | VERIFIED | `cards.review_card/publish_card/retire_card` reject illegal transitions; `test_cards.py::test_review_and_publish_lifecycle`, `test_publication_requires_a_reviewer_source_and_steps`, `test_published_card_cannot_be_published_or_reviewed_twice` |
| 7 | Revision history and immutable audit | VERIFIED | `SqliteKnowledgeStore` exposes only `append_audit`/`list_audit` (no update/delete); entities carry monotonic `revision`; translation revisions store `previous` snapshots (`test_translations.py`, `test_http.py::test_translation_revision_keeps_previous_content_and_actor`) |
| 8 | Central / project / user-memory scope isolation | VERIFIED | scope column on cards, `save_memory` keyed by `user_id, tenant_id, project_id`; `test_assistant.py::test_guide_progress_is_isolated_per_user`, `test_preferences_are_scoped_and_validated`; project knowledge requires `authorize_project` in the HTTP layer |
| 9 | Permissions and role grants | VERIFIED | `authorization.py` grants `knowledge.read/contribute/review/publish`, `assistant.action` by role (viewer read-only, contributor, reviewer/administrator); `test_administration_api.py` 4 passed; `test_http.py` viewer 403 on review/publish/retire |
| 10 | Persian and Arabic normalization | VERIFIED | one `normalize_terms` path for query and document; alef/ya/kaf/ta-marbuta folding, tatweel and diacritic removal, no madda over-fold; Arabic/FA variant, diacritic, tatweel, mixed-phrase and query≈document tests in `test_search.py` |
| 11 | CJK tokenization and cross-language retrieval | VERIFIED | character+bigram CJK tokens, Japanese/Korean particle stripping, Russian suffix stems, alias expansion at query and document time; `test_search.py` CJK/technical-term and cross-language cases; `test_locales.py` 20 tests |
| 12 | BM25 ranking and glossary expansion | VERIFIED | deterministic BM25 (k1=1.2, b=0.75) with title bonus; CUBI-owned glossary; ranking assertions in `test_search.py` |
| 13 | Translation lifecycle and provenance | VERIFIED | per-locale `missing/draft/translated/review_required/approved/published/retired`; translator id, source, machine flag, content hash and version stored; approval is independent of card publication and publication requires a human approval (`test_translations.py`, `test_http.py`) |
| 14 | Grounded assistant and explicit knowledge gap | VERIFIED | answers carry card ids + source URLs; `test_training_answer_is_grounded_with_citations`, `test_unknown_question_returns_a_knowledge_gap`; unapproved locale answers are announced as fallback (`test_unapproved_translation_is_treated_as_fallback`) |
| 15 | Smart Guide persistence and progress | VERIFIED | guide progress persisted per user/scope with step index, total and completion; `test_guide_persists_step_progress`, `test_guide_is_localized_with_approved_translation`, `test_guide_without_translation_states_the_fallback` |
| 16 | Project-creation ordering, dependencies, approvals | VERIFIED (backend) | 10 ordered steps (`organization → discipline → identity → review → create → settings → wbs → activities → schedule → control`), 13 guidance items, out-of-order/skip/back rules, dependency validation, review-hash-bound approval token; `test_workflow.py` 22 tests, `test_plan_port.py` 10 tests |
| 17 | Idempotency, optimistic locking, interruption recovery | VERIFIED | `request_key` replay, `expected_version` conflicts, create journal + read-back verification, adoption after interruption (`test_resume_after_restart_reads_persisted_state`); ingest/translation versioning covered above |

## Product gaps (explicit)

| Gap | Status | Why |
|-----|--------|-----|
| Knowledge/assistant surface inside the canonical Visual Workspace | NOT_IMPLEMENTED (merged main) | `apps/web` has no `/api/knowledge*` consumer; the workspace assistant is the provider-backed chat owned by the Web lane |
| Knowledge administration screen (review queue, publish, retire) | NOT_IMPLEMENTED | backend endpoints exist; no client surface |
| Human review/publication of real cards | PARTIAL | the evidence database is 100% `draft`; only the disposable smoke copy publishes one Russian locale |
| Supplementary 815-page PDF | BLOCKED_EXTERNAL | not supplied; recorded MISSING/VERIFY, nothing extracted |
| Browser-level acceptance of the integrated product | NOT RUN | unit/API acceptance only; no browser evidence claimed |
| Knowledge HTTP middleware mounted in a composed application | VERIFIED at `51a83f3` (PR #1813) | the preview composition mounts it and `tests/knowledge/test_runtime_mount.py` serves knowledge beside the real lifecycle app, including a full ten-step creation |

## Independent re-audit (2026-11-12)

Two read-only audits ran against the merged tree: an ingestion/lifecycle audit
and a security/isolation audit. They reproduced the following defects, now
addressed on `fix/knowledge-publication-integrity-2026-11-12` unless marked
otherwise.

| Defect | Verdict | Resolution |
|--------|---------|------------|
| A rejected, retired or never-reviewed card could be published; publication overwrote the reviewer with the publisher | Fixed | `publish_card` requires a `VALIDATED` card with a recorded reviewer and keeps that reviewer; retirement requires a published card and cannot repeat (`test_publication_integrity.py`) |
| `--force` re-ingestion overwrote a published card back to draft, dropping reviewer and publication time | Fixed | ingestion protects non-draft cards, records a `regeneration_blocked` card event and `topic_regeneration_blocked` audit row, and leaves the changed source line pending review (`test_force_reingestion_never_unpublishes_a_reviewed_card`) |
| `get_card?locale=` served rejected/unapproved localized text | Fixed | card reads use `answerable_record`; unapproved or stale locales return the English source with `fallback_used=true` |
| A published locale kept answering after the English source changed | Fixed | publication binds `source_card_hash`/`source_card_revision`; a later source change falls back until republished (legacy records without a binding keep working) |
| Retired cards still advertised answerable locales | Fixed | `available_locales[].available` requires a published card, an approved record and a current source binding |
| An unsupported `?locale=` was silently replaced with English | Fixed | the card route rejects unknown tags with `KNOWLEDGE_LOCALE_UNSUPPORTED` |
| A client could hide machine provenance by sending `machine_translated=false` | Fixed | `translation_source=machine` forces the machine flag, so approval/publication stays blocked |
| Project-scoped cards had no tenant predicate; memory reads skipped the project guard; a negative `limit` bypassed the row cap | Fixed | tenant check on every card operation, guard on memory reads, `LIMIT` clamped to 0..1000 |
| Duplicate merge audit omitted the second official URL | Fixed | `topic_merged` detail now records `duplicate_topic_id` and `duplicate_url` |
| A run that gave up on pages was audited `succeeded` and exited 0 | Fixed | audit outcome is `partial` while topics remain unconverted; the CLI exits non-zero |
| Card/translation writes have no `expected_version` and conflicts are always 400 | Known gap | workflow writes are versioned and idempotent; card and translation writes remain last-write-wins |
| `request_key` start dedupe ignores the payload and only covers active runs; run ids have no extra entropy | Known gap | recorded, not fixed in this slice |
| Merge signature ignores leading body prose, so 59/509 recorded merges attached a non-identical page | Known gap | documented; the merge heuristic is intentional for shared pages but loses the duplicate body |
| Card identity includes `card_type`, so a reclassified topic forks into a second card | Known gap | latent in the recorded corpus |
| Card revision history is write-only (`knowledge_card_event` has no reader) and raw SQL can rewrite audit rows | Known gap | immutability is application-boundary only |
| Smart Guide progress writes with `knowledge.read` | Accepted design | progress is a per-user, self-scoped memory row; no shared state is written |

## Reconciliation notes

- The PR #1794 description still carries branch-era figures (94 knowledge tests,
  2,497 topics including the non-authoritative Professional Help TOC, the
  `knowledge-v26-2026-11-12` evidence path). The merged state is 182 knowledge
  tests, 1,539 authoritative topics and the
  `knowledge-multilingual-v26-2026-11-12` evidence directory.
- 527 and 557 are different official User Guide editions, both live; only 557
  is ingested. The 988-topic Professional Help TOC is also live and not
  ingested.
- All numbers above were re-read from `coverage.json`, `source-audit.json`,
  `translation-matrix.json` and `assistant-smoke.json` on the merged tree.
