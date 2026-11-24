# CUBI database architecture and operational status

Updated: 2026-11-21. Scope: the production runtime served by `apps/web/api/index.py`
on Vercel and the reference Supabase project `CUBI-Platform-Core-DB`
(`pbgosszuzemljgoccppk`, Frankfurt).

This document is the audit and the operating contract for the database chain:

```
Browser → Vercel function → ProductionRuntime → PostgreSQL (reference project)
```

It records what is actually wired, what is only locally proven, and what is
blocked. A row may only claim `VERIFIED_ON_SUPABASE` after a reproducible run
against the reference project; the local PostgreSQL evidence in this repository
does **not** satisfy that bar.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| `WIRED_READ` | The production runtime serves reads from the durable repository and the route is covered by tests. |
| `WIRED_WRITE` | The production runtime performs authorized writes through one domain service/repository; covered by tests. |
| `VERIFIED_ON_SUPABASE` | The behaviour was observed on the reference Supabase project through a deployed Preview. Requires external evidence. |
| `PARTIAL` | Some path is wired, or the request path is deterministic but a dependent capability is missing (for example a chat provider). |
| `BLOCKED` | Cannot proceed without an external dependency (credentials, an owner action, an unimplemented contract). |
| `NOT_IMPLEMENTED` | No production persistence or route. |

Current overall position: every entity below is `WIRED_*` and was proven against
a real local PostgreSQL 14 in 470 integration tests. Nothing in this change may
be labelled `VERIFIED_ON_SUPABASE` because this environment has no Supabase
connection string, Vercel token or deployment access. See
`docs/deploy/PREVIEW_SUPABASE_CONNECTION.md` for the exact owner actions.

## Runtime topology

- One `ProductionRuntime` per warm Vercel instance.
- One pooled PostgreSQL connection per request, published as a `RequestConnection`
  ContextVar. Repositories are constructed once and resolve the current request
  connection through that proxy.
- The request owns the transaction: the runtime commits on success and rolls
  back on any exception. PostgreSQL repositories therefore never commit.
- SQLite repositories (preview/local) retain their own commit/rollback hooks;
  the shared business logic lives in dialect-neutral base classes.
- Schema is created once per instance by the versioned registry in
  `src/construction_pm/deployment/migrations.py`; the ledger is
  `cubi_schema_migration`.

## Migration registry

`apply_migrations()` validates contiguous versions, fails closed when the
database is ahead of the code (`MIGRATION_HISTORY_UNKNOWN`), records a per-step
checksum (version|name|revision|module.qualname), fingerprints
`information_schema.columns` for `current_schema()`, and reports or fails on
drift (`CUBI_SCHEMA_DRIFT_POLICY=report|fail`).

| Version | Step | Tables introduced/owned |
| --- | --- | --- |
| 1 | `identity` | `identity_users`, `identity_sessions`, `identity_login_attempts` |
| 2 | `global-administration` | `global_admin_audit` |
| 3 | `enterprise-tasks` | `enterprise_tasks`, `enterprise_teams`, `enterprise_team_memberships`, `enterprise_task_dependencies`, `enterprise_task_idempotency`, `enterprise_task_audit` |
| 4 | `enterprise-organization-access` | `enterprise_access_audit` |
| 5 | `project-lifecycle` | `project_lifecycle_projects`, `project_lifecycle_memberships`, `project_lifecycle_status_event`, `project_lifecycle_defaults_event`, `project_org_binding`, `eps_node`, `cubi_reference_project` |
| 6 | `engineering-masters` | `activity_master`, `activity_wbs_assignment`, `wbs_master`, `wbs_milestone`, `relationship_master`, `p6_cost_account`, `p6_obs_node` |
| 7 | `presentation` | `p6_field_registry`, `p6_layout_definition_revisions`, `p6_user_defined_fields`, `p6_user_defined_field_values` |
| 8 | `scheduling-state` | `schedule_input_snapshot`, `schedule_calculation_context`, `project_schedule_settings` |
| 9 | `risk-register` | `project_risk`, `project_risk_audit` |
| 10 | `forms-library` | `form_template_head`, `form_template_version`, `form_submission`, `form_submission_revision`, `form_approval_event`, `form_asset`, `form_audit_event` |
| 11 | `knowledge-assistant` | `knowledge_source`, `knowledge_topic`, `knowledge_card`, `knowledge_card_revision`, `knowledge_card_translation`, `knowledge_card_event`, `knowledge_topic_snapshot`, `knowledge_translation_revision`, `knowledge_audit`, `knowledge_schema_migration`, `project_knowledge`, `assistant_memory`, `assistant_request`, `assistant_workflow` |
| 12 | `ai-action-runtime` | `ai_action_proposals`, `ai_action_audit_events`, `ai_action_tool_idempotency` |
| 13 | `username-identity-and-password-reset` | `identity_users.username`, `identity_password_reset_tokens` |
| 14 | `reference-engineering` | Engineering tables the reference import writes (`activity_master`, `wbs_master`, `relationship_master`, `p6_*`, `schedule_*`, `project_budget_*`) plus `cubi_reference_project`, `cubi_reference_import`, `cubi_reference_schedule_run` |
| 15 | `reference-enterprise` | Enterprise registers the import writes (`project_risk`, `p6_issue`, `project_documents`, `enterprise_records`, `enterprise_tasks`, budget lines) |

A fresh schema migrates 93 application tables plus the ledger (94 total).
Re-running the registry applies zero steps and reports no drift. Adding a column outside the
registry is detected; the drift policy is `report` by default because a legacy
database may legitimately differ, and `fail` stops readiness.

### Changing a step safely

1. Additive change inside an existing step: bump `revision`. The checksum
   changes and the next run reports registry drift; explain it during rollout.
2. New dependency: add a new version. Never renumber or delete history.
3. No `DROP`, `TRUNCATE`, table rewrite or type narrowing in this module.
   A destructive change requires a backup, an explicit migration, count checks
   and a documented rollback, plus approval.
4. The registry is additive and repeatable; the server's `initialize()` remains
   compatible with databases created by an older release.

## Entity audit matrix

`API` lists the production route prefix; all routes enforce a session, tenant
scope and (for writes) CSRF.

| Domain | Entity | Repository | Storage adapter | DB table(s) | Migration | API | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Identity | User | `PostgresIdentityStore` | `RequestConnection` | `identity_users` | 1 | `/api/session` | WIRED_WRITE |
| Identity | Session | `IdentitySessionRepository` / `PostgresIdentityStore` | `RequestConnection` | `identity_sessions`, `identity_login_attempts` | 1 | `/api/session`, `/app` | WIRED_WRITE |
| Tenancy | Project | `PostgresProjectRepository` | `RequestConnection` | `project_lifecycle_projects`, `project_lifecycle_memberships` | 5 | `/api/projects*` | WIRED_WRITE |
| Tenancy | Membership | `PostgresProjectRepository` | `RequestConnection` | `project_lifecycle_memberships` | 5 | implicit in project authorization | WIRED_READ |
| Engineering | WBS | `PostgresWBSMasterRepository` | `RequestConnection` | `wbs_master`, `wbs_milestone` | 6 | `/api/projects/{id}/p6/wbs` | WIRED_WRITE |
| Engineering | Activity | `PostgresActivityMasterRepository` | `RequestConnection` | `activity_master`, `activity_wbs_assignment` | 6 | `/api/projects/{id}/p6/activities` | WIRED_WRITE |
| Engineering | Relationship | `PostgresRelationshipMasterRepository` | `RequestConnection` | `relationship_master` | 6 | `/api/projects/{id}/p6/relationships*` | WIRED_WRITE |
| Engineering | Cost account / OBS | `PostgresP6CostAccountRepository`, `PostgresP6OBSRepository` | `RequestConnection` | `p6_cost_account`, `p6_obs_node` | 6 | `/api/projects/{id}/p6/cost-accounts`, `/p6/obs` | WIRED_WRITE |
| Presentation | Field registry / layout / UDF | `PostgresP6FieldRegistryRepository`, `PostgresP6LayoutRepository`, `PostgresP6UserDefined*Repository` | `RequestConnection` | `p6_field_registry`, `p6_layout_definition_revisions`, `p6_user_defined_fields`, `p6_user_defined_field_values` | 7 | `/api/projects/{id}/p6/fields`, `/p6/layouts` | WIRED_WRITE |
| Scheduling | Snapshot / context / settings | `PostgresScheduleInputSnapshotRepository`, `PostgresCalculationContextRepository`, `PostgresProjectScheduleSettingsRepository` | `RequestConnection` | `schedule_input_snapshot`, `schedule_calculation_context`, `project_schedule_settings` | 8 | workspace read, scheduling jobs | WIRED_WRITE |
| Risk | Risk | `PostgresRiskStore` | `RequestConnection` | `project_risk`, `project_risk_audit` | 9 | `/api/projects/{id}/risks` | WIRED_WRITE |
| Forms | Template / version | `PostgresFormBuilderRepository` | `RequestConnection` | `form_template_head`, `form_template_version` | 10 | `/api/projects/{id}/forms/templates`, `/api/forms/organization` | WIRED_WRITE |
| Forms | Submission / approval | `PostgresFormBuilderRepository` | `RequestConnection` | `form_submission`, `form_submission_revision`, `form_approval_event`, `form_asset`, `form_audit_event` | 10 | `/api/projects/{id}/forms/submissions` | WIRED_WRITE |
| Knowledge | Cards / sources / project knowledge | `PostgresKnowledgeStore` | `RequestConnection` | `knowledge_*`, `project_knowledge`, `assistant_*` | 11 | `/api/knowledge*`, `/api/projects/{id}/knowledge` | WIRED_WRITE |
| AI | Proposal / decision / execution / audit | `PostgresAIActionRuntimeStore`, `AIActionExecutionIdempotencyStore` | `RequestConnection` | `ai_action_proposals`, `ai_action_audit_events`, `ai_action_tool_idempotency` | 12 | `/api/projects/{id}/ai/actions/*` | WIRED_WRITE |
| AI | Conversational assistant | `OpenAICompatibleChatProvider` + knowledge assistant | server environment | `ai_action_*`, `assistant_*` | 12 | `/api/projects/{id}/ai/assistant/turn` | PARTIAL (fails closed 503 without a configured HTTPS provider) |
| Enterprise | Tasks | `PostgresEnterpriseTaskRepository` | `RequestConnection` | `enterprise_*` | 3 | `/api/enterprise/tasks*` | WIRED_WRITE |
| Enterprise | Organization access | `PostgresEnterpriseOrganizationAccessRepository` | `RequestConnection` | `enterprise_access_audit` | 4 | global administration gate | WIRED_READ |
| Administration | Audit | `PostgresGlobalAdministrationStore` | `RequestConnection` | `global_admin_audit` | 2 | `/api/administration*` | WIRED_READ |
| Budget | Budget line | SQLite only | — | — | — | not mounted in production | NOT_IMPLEMENTED |
| Cost | Cost/expense | SQLite only (P6 cost accounts are separate and wired) | — | — | — | not mounted in production | NOT_IMPLEMENTED |
| Threshold | Threshold | SQLite only | — | — | — | not mounted in production | NOT_IMPLEMENTED |
| Document | Document / OCR / search | separate modules, not composed in production | — | — | — | not mounted in production | NOT_IMPLEMENTED |
| Reporting | Report definitions/schedules | separate modules, not composed in production | — | — | — | not mounted in production | NOT_IMPLEMENTED |
| Exchange / backup | Import staging / backup | separate modules, not composed in production | — | — | — | not mounted in production | NOT_IMPLEMENTED |

## The ten per-entity questions

For every wired entity the same questions were answered; the table below
records the decisive answer, and any `—` means "not applicable to this release".

| Question | Identity/Project | WBS/Activity/Relationship | Risk | Forms | Knowledge | AI actions |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Where is the entity defined? | `identity_session.py`, `application/project_lifecycle.py` | `wbs_master_repository.py`, `activity_master_repository.py`, `relationship_master_repository.py` | `risk_persistence.py` | `form_builder.py` / `form_builder_api.py` | `knowledge/model.py` | `ai_action_runtime.py`, `ai_action_boundary.py` |
| 2. Which service owns writes? | `IdentityService`, `ProjectLifecycleService` | `P6WBSMasterAPI`, `P6ActivityMasterAPI`, `P6RelationshipAPI` | `RiskApplicationService` | `FormBuilderAPI` | `KnowledgeAPI` | `AIActionRuntime` |
| 3. Authoritative repository? | `PostgresIdentityStore`, `PostgresProjectRepository` | `PostgresWBSMasterRepository`, `PostgresActivityMasterRepository`, `PostgresRelationshipMasterRepository` | `PostgresRiskStore` | `PostgresFormBuilderRepository` | `PostgresKnowledgeStore` | `PostgresAIActionRuntimeStore` |
| 4. Table + migration | see matrix | see matrix | `project_risk` v9 | `form_*` v10 | `knowledge_*` v11 | `ai_action_*` v12 |
| 5. API route | `/api/session`, `/api/projects*` | `/p6/wbs`, `/p6/activities`, `/p6/relationships` | `/risks` | `/forms/*` | `/api/knowledge*` | `/ai/actions/*` |
| 6. Transaction owner | request | request | request | request | request | request (tool requires the same connection for runtime, repository, idempotency and audit) |
| 7. Tenant isolation | session tenant + membership | `BackendScope` re-validated in repository | `AuthorizationContext` + tenant/project predicate | tenant/project predicate on every statement | `AssistantPrincipal` + project guard | `AIActionRuntimeContext` + permission adapter |
| 8. Optimistic locking | project `record_revision` | `record_revision` with `expected_revision` | `expected_revision` → 409 | `record_revision` / template version pin | knowledge revision + advisory lock | pinned `expected_revision`; stale proposal → 409 |
| 9. Idempotency | login throttle / session uniqueness | activity idempotency helpers | caller `Idempotency-Key` replay returns the stored risk | submission id + content equality; immutable versions | card revision uniqueness | tool-level `ai_action_tool_idempotency`; second execution rejected without mutation |
| 10. Audit + retention | session/login audit, status events | progress history, defaults events | `project_risk_audit` append-only | `form_*_event`, revisions, approvals, audit | `knowledge_audit`, card events/revisions | `ai_action_audit_events` append-only |

## Security invariants

- Every write is authorized server-side. Roles come from the session, never from
  the request body.
- A client-supplied tenant/project pair is only a scope header; the server
  compares it with the session and project membership. Body `tenant_id` is
  ignored or rejected.
- CSRF: unsafe methods require a same-origin `Origin`/`Referer` and the
  `X-CSRF-Token` derived from the caller's own session secret.
- Session revocation is checked per request; a logged-out cookie is rejected
  immediately (`SESSION_NOT_FOUND`).
- Errors returned to the browser are stable codes. Driver messages, DSNs and
  secrets never appear in responses or logs.
- AI proposals never mutate data before an explicit approval; execution runs
  through the same domain service as a human write and records an audit event.

## Reference project data (CUBI-REF-001/002/003)

The three frozen reference projects are durable tenant data, not fixtures.

- **One importer, two adapters.** `importing/reference_persistence.py` holds the
  dialect-neutral import; `SQLiteReferenceJournal` backs the preview and
  `PostgresReferenceJournal`/`ensure_reference_projects_postgres` back
  production. Both write the same project, WBS, activity, relationship,
  calendar, resource, assignment, baseline, progress and budget rows and record
  the same import manifest.
- **Idempotent.** A project already present is skipped; its rows are never
  rewritten or duplicated. `cubi_reference_import` stores the bundle contract,
  source SHA-256, revision and per-domain counts; `cubi_reference_schedule_run`
  stores each canonical-engine manifest.
- **Shared reference visibility without memberships.** `cubi_reference_project` is the
  registry for the existing CUBI-REF reference projects and the separately
  scoped CUBI-DAM build workspace. The existing CUBI-REF rows remain in the
  ordinary project register for the prior all-user preview contract. The
  in-progress `CUBI-DAM-001` workspace is excluded from `list_for_user` and is
  returned only by the authenticated `GET /api/shared-projects` surface, so it
  is not counted or mixed with user-owned projects. Both repositories use the
  same tenant-scoped registry; no mass memberships or copied project data are
  created. Only this exact project gets a registry-verified read-only
  authorization-context exception; write/schedule/admin permissions still
  require the usual policy grants.
- **Calculations are never imported.** CPM dates, float, critical path and EVM
  are produced during the import by `AuthoritativeScheduleSnapshotPublisher`
  and `evaluate_schedule_snapshot`; the workbook's calculated columns are only
  cross-checked.
- **Operator path.**
  `python scripts/import_reference_projects.py --tenant <tenant-id>` applies the
  additive migrations and runs the import; `--list` prints the stored manifests.
  The command prints counts and identifiers only.
- **Boot path.** Setting `CUBI_REFERENCE_TENANT=<tenant-id>` makes
  `ProductionRuntime._initialize()` run the same idempotent importer right after
  the migrations, so a deployment can provision its shared projects without a
  manual step. Importers serialize on `pg_advisory_xact_lock`, so warm instances
  racing the first request cannot double-import.
- **Preview.** `open_preview_runtime` calls the SQLite importer at startup, so a
  recreated preview database re-registers the same bundle deterministically.

## Verification evidence (local PostgreSQL)

| Check | Result |
| --- | --- |
| `pytest tests --ignore=tests/integration` | 5005 passed, 20 skipped |
| `pytest tests/integration` | 470 passed |
| New live module `tests/integration/test_cubi_database_operationalization_postgres_live.py` | 13 passed |
| `tests/integration/test_postgres_reference_projects_live.py` | 10 passed — 3 roles, 3 shared projects, isolation, HTTP reads from durable rows, viewer denial, owner write, restart persistence, engine manifests, partial-import recovery, env boot seeding |
| Fresh schema migration | 15 steps, 94 tables, drift `None` |
| Re-run migration | 0 steps, drift `None` |
| Reference import (fresh database) | 3 projects, 540 activities, 403 WBS, 3 manifests `COMPLETE`, 0 missing Enterprise records |
| Reference import re-run | 0 new rows, 3 manifests unchanged |
| Injected column | structural drift reported; `fail` policy raises `SCHEMA_DRIFT_DETECTED` |
| Unknown future ledger version | raises `MIGRATION_HISTORY_UNKNOWN` |

The live module drives the real `ProductionRuntime` WSGI app: login, project
open, WBS/activity save, workspace v2 read, logout, revoked-session rejection,
new-session restore, revision conflict, risk CRUD/history, forms publish →
submit → review → approve with history, AI proposal → approval → execution
with no pre-approval mutation, duplicate execution rejection, tenant isolation,
viewer denial, CSRF denial and knowledge durability.

## Known limitations and honest gaps

1. **No Supabase or Vercel access in this environment.** The production import
   was verified end-to-end against a local PostgreSQL 14 database only. The
   live Supabase database must be migrated and seeded with
   `scripts/import_reference_projects.py --tenant <tenant-id>` by the owner;
   until then `VERIFIED_ON_SUPABASE` is not claimed.
2. **Conversational AI is provider-gated.** The deterministic proposal surface
   is always composed; `/ai/assistant/turn` answers `503` unless
   `CUBI_AI_ENABLED` and a valid `CUBI_AI_*` HTTPS provider are configured.
   There is no fake provider.
3. **Budget, cost, threshold, document, reporting, exchange and backup** remain
   outside the production composition; they are not persisted in PostgreSQL and
   must not be presented as operational.
4. **Schedule Query** is not deployed; the route raises an explicit
   configuration error rather than evaluating with an empty calendar set.
5. **File attachments in forms** persist as `BYTEA` in `form_asset`; there is no
   external object store. Large binary retention policy is not defined.
6. **Drift policy defaults to report.** A production rollout should set
   `CUBI_SCHEMA_DRIFT_POLICY=fail` once the baseline is known clean.


## Supabase Data API security boundary (2026-11-24)

The public schema is not a browser-facing data API for CUBI. All 59 public base tables present at the security-hardening point have RLS enabled, a restrictive `cubi_block_direct_api_clients` policy for `anon` and `authenticated`, and no direct table or sequence privileges for those roles. The CUBI server connection retains the required database access; client reads and writes must pass through authenticated CUBI routes and their tenant/project authorization checks. Two trigger functions also have fixed `search_path=pg_catalog`. Supabase Security Advisor returned zero security lints after these changes.

Application schema migration 16 (`post-reference-state-and-data-api-hardening`) is the single additive step for post-reference state and security: it creates the `cubi_reference_enterprise` import-state table and then repeats this hardening after reference Engineering/Enterprise migrations 14/15, so every newly created public table is secured before the reference-project importer is allowed to proceed. The state table deliberately lives in step 16, not in the already-applied step 15, because editing an applied step would leave existing databases without the table. The importer preflight checks RLS, the explicit restrictive policy, direct client grants and all required Engineering/Enterprise tables. Do not enable direct client table access as a shortcut for shared project visibility; use the authenticated CUBI shared-workspace route instead.
