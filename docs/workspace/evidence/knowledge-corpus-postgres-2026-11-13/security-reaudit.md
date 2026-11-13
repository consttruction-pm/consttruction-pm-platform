# Security and data-integrity re-audit — knowledge backend

Base: `f07364f02eb3dc9fa6bfc5301eb523d3edab7e52`.
Scope: knowledge API, assistant, workflow, SQLite and PostgreSQL stores.
Result: every row below has an implemented control and a regression test.
No permissive production fallback was found.

| Threat | Control | Regression test |
| --- | --- | --- |
| Unauthenticated request | middleware rejects a missing session before routing | `test_http.py::test_missing_session_is_rejected`, `test_runtime_mount.py::test_missing_session_is_rejected` |
| Unauthorized action | `Permission` check in every API method; 403 with a message key | `test_http.py::test_card_visibility_and_review_permissions`, `::test_translation_routes_require_the_right_permission`, `::test_eps_audit_memory_and_workflow_remaining_routes` |
| Foreign project access | `lifecycle.authorize_project` on every project-scoped path; no 404 leak | `test_http.py::test_project_knowledge_requires_authorization_and_round_trips` |
| Cross-tenant card read | scope predicate on card reads; project cards require tenant + project | `test_publication_integrity.py::test_project_cards_are_not_readable_across_tenants`, `test_postgres_store.py::test_project_scoped_cards_and_knowledge_are_tenant_isolated` |
| Cross-tenant/project search | `SearchScope` filters central/project/memory documents | `test_search.py::test_project_knowledge_is_isolated_by_tenant_and_project`, `test_corpus_retrieval.py::test_project_knowledge_is_not_visible_to_another_project_or_tenant` |
| Session bleed between requests | runtime creates one request-scoped session stack per call | `test_runtime_mount.py::test_request_session_does_not_leak_into_the_next_call`, `::test_each_request_uses_its_own_session_for_project_reads` |
| Fail-open gateway | production composition fails closed without a bound session | `test_runtime_mount.py::test_gateway_fails_closed_without_a_bound_session` |
| Concurrent card writers | row lock + revision guard; exactly one winner | `test_concurrency_history_idempotency.py::test_two_contributors_second_write_conflicts`, `test_postgres_store.py::test_concurrent_writers_have_exactly_one_winner` |
| Stale card revision | `expected_version` compared to stored revision | `test_concurrency_history_idempotency.py::test_stale_card_review_is_rejected_and_keeps_the_newer_revision`, `test_postgres_store.py::test_stale_card_write_is_rejected_and_previous_revision_is_kept` |
| Lost superseded revision | snapshot written before update; history pages read both tables | `test_concurrency_history_idempotency.py::test_card_revision_snapshot_keeps_the_superseded_row`, `::test_card_history_pages_events_and_revisions` |
| Approval-token misuse | token bound to actor, run and review hash; single use; creation requires it | `test_workflow.py::test_creation_requires_an_approval_token`, `::test_approval_is_bound_to_actor_run_and_review_hash`, `::test_planner_cannot_approve_or_create` |
| Idempotency replay | `request_key` returns the stored run | `test_concurrency_history_idempotency.py::test_same_request_key_same_payload_replays`, `::test_request_key_survives_store_restart`, `::test_request_key_stays_replayable_beyond_the_recent_run_window` |
| Idempotency payload mismatch | same key + different body → 409 | `test_concurrency_history_idempotency.py::test_same_request_key_different_payload_conflicts` |
| Partial write after failure | one transaction per mutation; rollback leaves nothing | `test_postgres_store.py::test_transaction_rollback_leaves_no_partial_write` |
| Audit immutability | database triggers reject `UPDATE`/`DELETE` on audit and card events | `test_concurrency_history_idempotency.py::test_audit_rows_reject_update_and_delete`, `test_postgres_store.py::test_audit_and_events_are_immutable_in_the_database` |
| Translation approval/publication race | version guard on review/publish; published translation must be approved | `test_concurrency_history_idempotency.py::test_translation_approval_and_publication_conflicts`, `test_publication_integrity.py::test_publication_requires_a_completed_human_review` |
| Stale published translation | source-card hash binding checked before answering | `test_publication_integrity.py::test_published_translation_stops_answering_after_the_source_changes`, `test_translations.py::test_coverage_does_not_count_a_stale_translation_as_answerable` |
| Unreviewed translation served as published | search marks it as fallback; assistant falls back and cites the source title | `test_assistant.py::test_unapproved_translation_is_treated_as_fallback`, `test_corpus_retrieval.py::test_engineering_question_answers_in_each_language` |
| Rejected translation text served | rejected record excluded from retrieval and answers | `test_publication_integrity.py::test_rejected_translation_text_is_never_served` |
| Retired card answering | retirement removes the card from answerable locales | `test_publication_integrity.py::test_retired_card_has_no_answerable_locale` |
| Machine translation disguised as human | provenance is server-owned and cannot be overridden by the client | `test_publication_integrity.py::test_machine_provenance_cannot_be_hidden_by_the_client` |
| Workflow restart/recovery | persisted run state resumed; adoption does not duplicate | `test_workflow.py::test_resume_after_restart_reads_persisted_state`, `::test_adoption_after_interruption_does_not_duplicate` |
| Negative/oversized limits | limits are clamped server-side | `test_publication_integrity.py::test_negative_limit_cannot_defeat_the_row_cap`, `test_postgres_store.py::test_event_pagination_uses_a_stable_cursor` |
| SQLite/PostgreSQL divergence | same logical schema and locks; parity measured on the full corpus | `tools/knowledge_corpus_verify.py` (`parity.equal: true`), `test_postgres_parity.py` |

## Engine guarantees

- Both engines enforce revision guards inside a transaction and write the
  superseded row before the update.
- PostgreSQL adds server-side immutability triggers, advisory locks and a
  unique request index; SQLite enforces the same rules with transactions and
  unique constraints.
- The owned PostgreSQL connection uses `autocommit=True` so a caller's read
  cannot turn a later write into a savepoint that is rolled back at close; this
  was the write-loss defect fixed in this phase and is covered by
  `test_postgres_store.py::test_owned_connection_persists_writes_made_after_a_read`.
