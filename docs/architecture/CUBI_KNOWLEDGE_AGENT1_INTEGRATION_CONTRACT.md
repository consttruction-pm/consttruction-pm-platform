# CUBI knowledge and assistant — integration contract for the Visual Workspace

**Owner of this contract:** Knowledge / assistant backend (Agent 2)
**Consumer:** canonical Visual Workspace, application shell, knowledge administration screens (Agent 1)
**Mount point:** `KnowledgeHttpMiddleware` wraps the composed application; it handles only
`/api/knowledge…` and `/api/projects/{id}/knowledge` and delegates everything else unchanged.
**Rule:** Agent 1 renders; this contract decides permissions, validation, state and audit.
No screen may re-implement a lifecycle rule, and no second assistant shell may exist.

## 1. Authentication and authorization

Every request carries the existing session cookie `cp_session`. The middleware reads the
session through `lifecycle.get_session(session_id, now=…)`; project-scoped calls additionally
pass `lifecycle.authorize_project(session_id, project_id, permission, now=…)`.

| Permission | Granted to (default policy) |
| --- | --- |
| `knowledge.read` | viewer, planner, project_admin |
| `knowledge.contribute` | planner, project_admin |
| `knowledge.review` | project_admin |
| `knowledge.publish` | project_admin |
| `assistant.action` | planner, project_admin |
| `project.admin` | project_admin |

Missing session → `401 SESSION_INVALID` / `401 SESSION_REQUIRED`.
Known session without the permission → `403` with the authorization message.
Unknown/foreign project → `403` from the lifecycle guard, never a 404 leak.

## 2. Response envelope

Success bodies are objects; lists are nested under a named key (`cards`,
`translations`, `events`, `workflows`, …). No bare arrays.

Errors are always:

```json
{"code": "KNOWLEDGE_CARD_VERSION_CONFLICT", "message_key": "error.knowledge_card_version_conflict"}
```

Status mapping is stable and computed from the code, not the message:

| Status | Codes |
| --- | --- |
| 400 | validation, unsupported locale, illegal transition, malformed body |
| 401 | `SESSION_REQUIRED`, `SESSION_INVALID` |
| 403 | authorization failures |
| 404 | `*_NOT_FOUND`, `*_NOT_PUBLISHED`, `ROUTE_NOT_FOUND` |
| 405 | `METHOD_NOT_ALLOWED` |
| 409 | `*_VERSION_CONFLICT`, `*_IDEMPOTENCY_CONFLICT`, `*_ALREADY_PUBLISHED`, `*_ALREADY_RETIRED`, `*_CONFLICT` |

A client must branch on `code`. Localisation of the message happens client-side from
`message_key`; the server never returns a translated error sentence.

## 3. Endpoints

### Knowledge

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/api/knowledge/locales` | read | registry, default/fallback/source language |
| GET | `/api/knowledge/coverage` | read | ingestion coverage + card counts + translation coverage |
| GET | `/api/knowledge/search?q=&locale=&limit=&project_id=` | read | BM25, `hits`, `insufficient_knowledge` |
| GET | `/api/knowledge/cards?status=&type=&limit=` | read | non-published statuses require review |
| GET | `/api/knowledge/cards/{card_id}?locale=` | read | localized payload, `fallback_used`, `available_locales`, `language_context` |
| GET | `/api/knowledge/cards/{card_id}/translations` | read | one row per locale, `missing` included |
| GET | `/api/knowledge/cards/{card_id}/history?limit=&before=` | read | revisions + events, newest first, `next_before` cursor |
| GET | `/api/knowledge/cards/{card_id}/translations/{locale}/history?limit=` | read | translation versions |
| GET | `/api/knowledge/translations?status=&locale=&limit=` | review | reviewer queue across all cards |
| POST | `/api/knowledge/cards/{card_id}/review` | review | body `{"accept": bool, "expected_version": int}` |
| POST | `/api/knowledge/cards/{card_id}/publish` | publish | body `{"expected_version": int}` |
| POST | `/api/knowledge/cards/{card_id}/retire` | publish | body `{"expected_version": int}` |
| PUT/POST | `/api/knowledge/cards/{card_id}/translations/{locale}` | contribute | content + `expected_version` |
| POST | `/api/knowledge/cards/{card_id}/translations/{locale}/review` | review | `{"accept": bool, "expected_version": int}` |
| POST | `/api/knowledge/cards/{card_id}/translations/{locale}/publish` | publish | `{"expected_version": int}` |
| POST | `/api/knowledge/cards/{card_id}/translations/{locale}/retire` | publish | `{"expected_version": int}` |
| GET | `/api/knowledge/eps` | read | EPS nodes for the tenant |
| POST | `/api/knowledge/eps` | assistant.action + project_admin | create EPS node |
| GET | `/api/knowledge/audit?project_id=&limit=` | review | append-only audit rows |
| GET | `/api/knowledge/memory?project_id=` | read | user preferences / assistant memory |
| POST | `/api/knowledge/memory` | assistant.action | `{"key", "value", "project_id"?}` |

### Assistant and workflow

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| POST | `/api/knowledge/assistant/ask` | read | `{"question", "mode": "training"|"guide"|"execution", "project_id"?, "language"?}` |
| GET | `/api/knowledge/assistant/guide/{card_id}?project_id=` | read | persisted progress; `started: false` when never opened |
| POST | `/api/knowledge/assistant/guide/{card_id}` | read | `{"action": "start"|"next"|"back"|"complete", "project_id"?, "language"?}` |
| GET | `/api/knowledge/assistant/workflows` | read | the caller's runs |
| POST | `/api/knowledge/assistant/workflows` | assistant.action | `{"request_key"?, "locale"?}` |
| GET | `/api/knowledge/assistant/workflows/{run_id}` | read | run view |
| POST | `/api/knowledge/assistant/workflows/{run_id}/steps/{step}` | assistant.action | `{"payload": {…}, "expected_version": int}` |
| POST | `/api/knowledge/assistant/workflows/{run_id}/approve` | assistant.action + project_admin | `{"expected_version": int}` → `approval_token` |
| POST | `/api/knowledge/assistant/workflows/{run_id}/skip` | assistant.action | `{"step", "reason", "expected_version"}` |
| POST | `/api/knowledge/assistant/workflows/{run_id}/back` | assistant.action | `{"expected_version"}` |
| POST | `/api/knowledge/assistant/workflows/{run_id}/abandon` | assistant.action | `{"reason", "expected_version"}` |

### Project knowledge

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/api/projects/{project_id}/knowledge?limit=` | project read | tenant + project scoped |
| POST | `/api/projects/{project_id}/knowledge` | project contribute | `{"title", "kind", "content", "source_ref"?}` |

## 4. Optimistic concurrency

Every mutable entity carries a version the client must echo back:

- card: `revision` (from any card payload) → `expected_version` on review/publish/retire;
- translation: `translation_version` → `expected_version` on save/review/publish/retire;
- workflow run: `version` → `expected_version` on every step/approve/skip/back/abandon.

A stale value returns `409` with `KNOWLEDGE_CARD_VERSION_CONFLICT`,
`KNOWLEDGE_TRANSLATION_VERSION_CONFLICT` or `ASSISTANT_WORKFLOW_STALE_VERSION`.
`expected_version: 0` on a translation means "create only"; a non-zero value on a
missing record is a conflict.

Every accepted mutation writes the superseded row to a revision table before updating,
so `…/history` can show previous revisions after the fact. Audit and card-event tables
reject `UPDATE` and `DELETE` at the database level.

## 5. Language and direction

`language_context` is present on card payloads and assistant answers:

```json
{
  "locale": "fa", "language_code": "fa", "source_language": "en",
  "question_language": "fa", "response_language": "fa",
  "default_language": "en", "fallback_language": "en",
  "direction": "rtl", "translation_status": "published",
  "review_status": "approved", "published_language_version": 3,
  "technical_glossary": [["WBS", "ساختار شکست کار"]],
  "localization_metadata": {"source_card_hash": "…"}
}
```

`direction` is the only source of truth for RTL/LTR. `fallback_used: true` means the
content is the English source even though a locale was requested; render the fallback
notice. `available_locales[].available` is `true` only for a published card with an
approved, non-machine translation whose source binding is current.

## 6. Pagination

`limit` is clamped server-side (cards 1–1000, history/events 1–200, queue 1–200).
History and events are newest-first and return `next_before` (event id) when a full
page was returned; pass it as `before` for the next page. No offset paging.

## 7. Contract examples

`POST /api/knowledge/cards/{id}/review` with `{"accept": true}` →
`200` card payload (`revision` incremented). Same call again with
`{"accept": true, "expected_version": <old>}` → `409 KNOWLEDGE_CARD_VERSION_CONFLICT`.

`POST /api/knowledge/assistant/workflows` twice with the same `request_key` and the
same body → the same `run_id`, `version: 1`. The same key with a different `locale` →
`409 WORKFLOW_IDEMPOTENCY_CONFLICT`. The same key after completion or abandonment
returns the stored run rather than starting a second project.

`GET /api/knowledge/cards/{id}/history?limit=2` →

```json
{
  "card_id": "KC-…", "current_revision": 3,
  "revisions": [{"revision": 2, "content_hash": "…", "recorded_at": "…", "snapshot": {…}}],
  "events": [
    {"event_id": 12, "card_id": "KC-…", "action": "reviewed", "actor_id": "admin-1",
     "occurred_at": "2026-11-12T…", "detail": {"revision": 3}}
  ],
  "next_before": 11
}
```

## 8. What Agent 1 must not do

- Do not read the SQLite/PostgreSQL tables directly; use these endpoints so audit and
  permission rules stay identical across Web, Flutter and Windows clients.
- Do not publish or approve on behalf of a user without their session and permission.
- Do not show an unapproved or machine translation as published content; use
  `fallback_used`, `translation_status`, `machine_translated`.
- Do not add a second assistant surface or a separate workflow state machine.

## 9. Verification

Every endpoint above is exercised by `tests/knowledge/test_http.py` and
`tests/knowledge/test_concurrency_history_idempotency.py` (status codes, permission
failures, conflict codes, history pagination, idempotent replay). The middleware is
mounted in the composed application and proven by
`tests/knowledge/test_runtime_mount.py`.
