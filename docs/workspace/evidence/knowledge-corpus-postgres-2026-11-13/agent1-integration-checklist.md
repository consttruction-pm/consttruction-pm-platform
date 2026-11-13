# Agent 1 integration checklist — knowledge and assistant contract

Base: `f07364f02eb3dc9fa6bfc5301eb523d3edab7e52`.
Contract: `docs/architecture/CUBI_KNOWLEDGE_AGENT1_INTEGRATION_CONTRACT.md`.
Status: every endpoint below is implemented in
`src/construction_pm/knowledge/http_routes.py` and exercised at the HTTP layer
unless the row states an API-level test. Run the named tests with the PostgreSQL
DSN to reproduce.

## Knowledge endpoints

| Method | Path | Handler | Verified by |
| --- | --- | --- | --- |
| GET | `/api/knowledge/locales` | `api.locales` | `test_http.py::test_locales_endpoint_separates_product_and_legacy_locales` |
| GET | `/api/knowledge/coverage` | `api.coverage` | `test_http.py::test_coverage_and_search_routes` |
| GET | `/api/knowledge/search` | `api.search` | `test_http.py::test_coverage_and_search_routes`, `::test_card_and_search_accept_a_locale` |
| GET | `/api/knowledge/cards` | `api.list_cards` | `test_http.py::test_card_visibility_and_review_permissions` |
| GET | `/api/knowledge/cards/{id}` | `api.get_card` | `test_http.py::test_card_visibility_and_review_permissions`, `::test_card_and_search_accept_a_locale` |
| GET | `/api/knowledge/cards/{id}/translations` | `api.list_card_translations` | `test_http.py::test_translation_can_be_retired_without_losing_its_version` |
| GET | `/api/knowledge/cards/{id}/history` | `api.card_history` | `test_http.py::test_card_visibility_and_review_permissions`, `test_concurrency_history_idempotency.py::test_card_history_pages_events_and_revisions` |
| GET | `/api/knowledge/cards/{id}/translations/{locale}/history` | `api.translation_history` | `test_http.py::test_translation_routes_require_the_right_permission` |
| GET | `/api/knowledge/translations` | `api.translation_queue` | `test_http.py::test_translation_queue_is_reviewer_only_and_shows_pending_work` |
| POST | `/api/knowledge/cards/{id}/review` | `api.review` | `test_http.py::test_card_visibility_and_review_permissions` |
| POST | `/api/knowledge/cards/{id}/publish` | `api.publish` | `test_http.py::test_card_visibility_and_review_permissions` |
| POST | `/api/knowledge/cards/{id}/retire` | `api.retire` | `test_http.py::test_card_visibility_and_review_permissions` |
| PUT/POST | `/api/knowledge/cards/{id}/translations/{locale}` | `api.save_translation` | `test_http.py::test_translation_routes_require_the_right_permission` |
| POST | `…/translations/{locale}/review` | `api.review_translation` | `test_http.py::test_translation_routes_require_the_right_permission` |
| POST | `…/translations/{locale}/publish` | `api.publish_translation` | `test_http.py::test_translation_can_be_retired_without_losing_its_version` |
| POST | `…/translations/{locale}/retire` | `api.retire_translation` | `test_http.py::test_translation_can_be_retired_without_losing_its_version` |
| GET | `/api/knowledge/eps` | `api.list_eps` | `test_http.py::test_eps_audit_memory_and_workflow_remaining_routes` |
| POST | `/api/knowledge/eps` | `api.create_eps` | same |
| GET | `/api/knowledge/audit` | `api.audit` | same |
| GET | `/api/knowledge/memory` | `api.memory` | same |
| POST | `/api/knowledge/memory` | `api.set_memory` | same |

## Assistant and workflow endpoints

| Method | Path | Handler | Verified by |
| --- | --- | --- | --- |
| POST | `/api/knowledge/assistant/ask` | `api.ask` | `test_http.py::test_assistant_and_workflow_routes`, `::test_workflow_validation_and_unknown_routes` |
| GET | `/api/knowledge/assistant/guide/{id}` | `api.guide_progress` | `test_http.py::test_guide_progress_reports_the_persisted_step_without_moving_it` |
| POST | `/api/knowledge/assistant/guide/{id}` | `api.guide` | `test_http.py::test_guide_accepts_language_parameter`, `::test_guide_progress_reports_the_persisted_step_without_moving_it` |
| GET | `/api/knowledge/assistant/workflows` | `workflows.list` | `test_http.py::test_assistant_and_workflow_routes` |
| POST | `/api/knowledge/assistant/workflows` | `workflows.start` | `test_http.py::test_assistant_and_workflow_routes`, `test_concurrency_history_idempotency.py::test_same_request_key_same_payload_replays` |
| GET | `/api/knowledge/assistant/workflows/{run_id}` | `workflows.get` | `test_http.py::test_eps_audit_memory_and_workflow_remaining_routes` |
| POST | `/api/knowledge/assistant/workflows/{run_id}/steps/{step}` | `workflows.apply` | `test_http.py::test_assistant_and_workflow_routes`, `test_runtime_mount.py::test_preview_composition_serves_knowledge_beside_the_real_lifecycle_app` |
| POST | `/api/knowledge/assistant/workflows/{run_id}/approve` | `workflows.approve` | `test_http.py::test_eps_audit_memory_and_workflow_remaining_routes`, `test_workflow.py::test_creation_requires_an_approval_token`, `::test_approval_is_bound_to_actor_run_and_review_hash` |
| POST | `/api/knowledge/assistant/workflows/{run_id}/skip` | `workflows.skip` | `test_http.py::test_eps_audit_memory_and_workflow_remaining_routes` (rejection path), `test_workflow.py::test_skip_requires_skippable_step_and_reason` (success path) |
| POST | `/api/knowledge/assistant/workflows/{run_id}/back` | `workflows.back` | `test_http.py::test_eps_audit_memory_and_workflow_remaining_routes`, `test_workflow.py::test_back_clears_downstream_until_creation` |
| POST | `/api/knowledge/assistant/workflows/{run_id}/abandon` | `workflows.abandon` | `test_http.py::test_eps_audit_memory_and_workflow_remaining_routes`, `test_workflow.py::test_abandon_closes_the_run` |

## Project knowledge endpoints

| Method | Path | Handler | Verified by |
| --- | --- | --- | --- |
| GET | `/api/projects/{id}/knowledge` | `api.list_project_knowledge` | `test_http.py::test_project_knowledge_requires_authorization_and_round_trips` |
| POST | `/api/projects/{id}/knowledge` | `api.add_project_knowledge` | same |

## Contract rules Agent 1 must honour

- Render `language_context.direction`; never infer RTL from the locale string.
- Show a fallback notice when `fallback_used` is true. The answer body and citation
  title are then the reviewed English source text, even if the question locale
  has a translated (but unapproved) record.
- `available_locales[].available` is true only for a published, approved,
  non-machine translation whose source binding is current.
- Branch on `code`, not message text. Pass `expected_version` on every mutation.
- Do not read the database directly, and do not add a second assistant shell or
  workflow state machine.

## Current gaps visible to Agent 1

- Only eight seed translations exist (one card: seven product targets plus one
  legacy Russian record) and all are `translated` / `pending`; the workspace
  must show them as unpublished work, not as localized answer content.
- The corpus has 1090 cards but 0 published cards after a plain ingestion run.
  Publication is a deliberate human review action, not an ingestion side effect.
