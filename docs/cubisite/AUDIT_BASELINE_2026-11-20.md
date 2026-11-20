# CUBISITE — Audit Baseline (2026-11-20)

Issue #2069 · owner: product owner · executor: single Qoder agent
Baseline `main`: `ae6e72e48be624c841b579fb9a54dcc36890b99d`
Mounted reference: `p6-professional-help.pdf` (G57535-02, 815 pages) — committed at
`docs/reference/help/engineering-v26/P6_PROFESSIONAL_HELP_G57535-02.pdf`.

This file is the written baseline required by Section 1 of the CUBISITE brief. It records
what exists **today**, before any change in this increment. Nothing below is aspirational.

---

## 1. Architecture Map

| Layer | Location | Runtime | Notes |
| --- | --- | --- | --- |
| Public website (static) | `apps/web/public` + `apps/web/site` | assembled to `_site` | 116 HTML files, 114 sitemap URLs, 25 routes × locales |
| Web client (workspace) | `apps/web/src` (265 modules), `apps/web/index.html`, `app.html`, `login.html` | esbuild bundle | `/` marketing, `/login`, `/app`, `/enterprise` |
| HTTP boundary | `api/index.py` → `src/construction_pm/deployment/production_runtime.py`, `production_web.py` | Vercel Python WSGI | single runtime; `/api/*` only |
| Domain / application | `src/construction_pm` (257 modules) | Python 3 | repositories, application services, shared core adapters |
| Shared core (read-only for this mission) | `src/construction_pm` scheduling/EVM modules, `shared/` | Python | CPM, calendars, EVM — **must not change** |
| Schema bootstrap | `src/construction_pm/deployment/schema.py` | idempotent DDL | `CREATE TABLE IF NOT EXISTS` only |
| Tests | `tests/` (pytest), `apps/web/src/**/*.test.ts` (node:test), `apps/web/e2e` | mixed | 37 pytest, 1191 web tests at baseline |
| Deploy | `vercel.json`, `infra/`, `.github/workflows` | Vercel | 3 projects: `cubi-web-preview` (green), `-public`/`-web` (pre-existing failure) |

No `AGENTS.md` exists in the repository (root or nested). Governing documents:
`docs/DEVELOPMENT-AND-TESTING-RULES.md`, `TEAM_WORK_ALLOCATION.md`, `docs/governance/*`.

## 2. Route Map

**Public routes today** (`apps/web/site/routes.mjs`, 25 in `ROUTE_PATHS`):

```
/ /platform /features /features/scheduling /features/project-controls /features/resources
/features/cost /features/documents /features/risks /features/reporting /features/ai-assistant
/solutions /integrations /pricing /resources /documentation /help /faq /about /security
/payments /contact /get-started /privacy /terms
```

**Target matrix in the brief** (PUB-01…PUB-25) differs on ten routes:

| Brief route | Current state | Action (R4) |
| --- | --- | --- |
| `/features/planning-scheduling` | `/features/scheduling` | new canonical route + redirect |
| `/features/resources-cost` | `/features/resources` + `/features/cost` | merge into one page, keep old URLs |
| `/features/progress-evm` | — | build |
| `/features/documents-contracts` | `/features/documents` | rename + contracts content |
| `/features/field-operations` | — | build (field assurance exists server-side) |
| `/features/change-claims` | — (only `control` in workspace) | build |
| `/features/forms-compliance` | — (forms exist server-side) | build |
| `/solutions/contractors` | — | build |
| `/solutions/owners-developers` | — | build |
| `/solutions/project-controls-teams` | — | build |
| `/faq` | exists | keep |

Routes that exist but are not in PUB-01…25: `/payments`, `/get-started`, `/privacy`, `/terms`
(kept, not counted toward the 25).

**Authenticated surfaces:** `/login` (static + session API), `/app` (workspace shell, 21 menus),
`/enterprise` (environment/router), `/environments` (selection page).

**Workspace menus** (`apps/web/src/workspace-navigation.ts`, 21): project, wbs, schedule, progress,
resources, assignments, roles, calendars, cost, expenses, documents, reports, tracking, issues,
risks, thresholds, control, settings, administration, exchange, backup.
Status at baseline: 1 implemented (schedule), 12 partial, 8 preview.

## 3. Database Map

- Engine: PostgreSQL only. DSN is `CONSTRUCTION_PM_DATABASE_URL` (must start with `postgres://`),
  enforced by `ProductionSettings.from_environment`; SQLite is rejected in production by
  `production_readiness.py` (`SQLITE_FORBIDDEN_IN_PRODUCTION`).
- Pool: bounded, `psycopg` with `autocommit=False`, statement timeout 30 s, pool size ≤ 8.
- Bootstrap: `initialize_production_schema()` — 16 repository `initialize()` calls, all
  `CREATE TABLE IF NOT EXISTS`; no DROP / TRUNCATE anywhere.
- Tables: **183 distinct tables** across 25 families:
  `project_*` 57, `p6_*` 36, `enterprise_*` 15, `knowledge_*` 10, `form_*` 7, `portfolio_*` 5,
  `preview_*` 5, `activity_*` 4, `ai_action_*` 4, `backend_p0_*` 4, `calendar_*` 4, `claim_*` 4,
  `assistant_*` 3, `identity_*` 3, `resource_*` 3, `sync_*` 3, plus 20 single-table families.
- Identity tables at baseline: `identity_users(user_id, tenant_id, email, display_name,
  roles_json, password_hash, active)`, `identity_sessions`, `identity_login_attempts`.
  There is **no** user-management table, no role catalog table and no audit table for
  administrative actions.
- No ORM, no Alembic. Versioning is per-repository idempotent DDL. Any new table in this mission
  must follow the same pattern and must not duplicate an existing one.

## 4. Authentication & Authorization Map

- `src/construction_pm/identity_session.py`: scrypt password hashing, session tokens stored as
  hashes, CSRF token derived from session + secret, login attempt throttling, session revoke.
- `IdentityService.login/resolve/logout/verify_csrf`; roles are tokens in `roles_json`
  (`validate_role_tokens`), not a permission table.
- Session transport: HttpOnly secure cookie issued by `/api/session`; `load_identity_settings`
  requires `csrf_secret` ≥ 32 chars and an `https://` public origin.
- Enterprise: `enterprise_identity.py` adapter + `enterprise_organization_access_repository.py`
  (members/roles/teams, server-side authorization, audit tables `enterprise_access_audit`,
  `enterprise_task_audit`).
- Workspace client: `session-api.ts`, `workspace-roles.ts`, `entry-routing.ts`.
- **Gap:** there is no system-level role, no Global Admin surface, no admin user CRUD, no session
  administration UI, no administrative audit log view. `roles_json` accepts any validated token,
  so a Global Admin must be introduced as a server-side gate, never as a selectable signup role.

## 5. Path Ownership Matrix

| Path | Owner | Rule for this mission |
| --- | --- | --- |
| `src/construction_pm/**` scheduling/CPM/EVM/calendar core | Shared Core (Jalal lane) | read + call only; no edits |
| `apps/web/src/activity-*`, PR #2048 paths | Activities lane | untouched |
| `src/construction_pm/enterprise_*`, PR #2068 runtime | P0n lane | no edits, no rebase |
| `apps/web/public`, `apps/web/site`, `apps/web/src` public UI | CUBISITE | editable |
| `src/construction_pm/identity_session.py` | CUBISITE (additive only) | new admin module preferred over editing |
| `docs/traceability`, `docs/reference` | CUBISITE | editable |
| `apps/web/src/main.ts` (4,964 lines) | shared shell | add modules, minimal edits |

## 6. PR Dependency Matrix

Verified with `gh pr view --json commits`; branches are cumulative, in this order:

| PR | Base | Head | Commits ahead of `main` |
| --- | --- | --- | --- |
| #2070 | main | `e88df9f` | 2 |
| #2071 | main | `2e0c9c2` | 5 |
| #2072 | main | `6bcfeb2` | 6 |
| #2073 | main | `c8b6aa9` | 7 |
| #2074 | main | `8ca5218` | 8 |

`#2071` contains `#2070`'s commits, and so on. Merge order must be #2070 → #2071 → #2072 →
#2073 → #2074, each after a green run on the exact head. #2068 (runtime) and #2048 (Activities)
are out of scope and must not be merged in this sequence.

## 7. CUBISITE Capability Gap Matrix (C01–C35, preliminary)

Status vocabulary: `IMPLEMENTED` (server + UI + test), `PARTIAL`, `PLANNED`, `CUBI_OWNED`, `MISSING`.

| ID | Capability | Server evidence | UI evidence | Status |
| --- | --- | --- | --- | --- |
| C01 | Workspace / Projects | `postgres_project_lifecycle.py` | `workspace-project*`, `/app` | PARTIAL |
| C02 | WBS / Activities | `wbs_master_repository.py`, `activity_master_repository.py` | `p6-activity-wbs-grid.ts` | PARTIAL |
| C03 | Field Registry | `p6_field_registry_repository.py` | `p6-field-chooser.ts` | IMPLEMENTED |
| C04 | Grid / Layout | `p6_layout_definition_repository.py` | `p6-columns-dialog.ts` | PARTIAL |
| C05 | *not named in the brief* | — | — | MISSING_EVIDENCE |
| C06 | Calendar | `calendar_*_repository.py` (5) | `calendar-holidays.ts` | PARTIAL |
| C07 | Schedule Options | schedule option APIs | workspace schedule menu | PARTIAL |
| C08 | Relationships | `relationship_master_repository.py` | schedule grid | PARTIAL |
| C09 | CPM Engine | shared core (do not edit) | run schedule | IMPLEMENTED (core) |
| C10 | Progress / Actuals | `activity_progress_history.py` | progress menu | PARTIAL |
| C11 | Baselines | `tests/integration/test_p6_baseline_postgres_live.py` | — | PARTIAL |
| C12 | Resources / Assignments | `field_resource_persistence.py` | assignments menu | PARTIAL |
| C13 | Cost / Financial Periods | `cost_persistence.py`, period register | `workspace-administration.ts` | PARTIAL |
| C14 | EVM / Earned Schedule | shared core | — | PARTIAL |
| C15 | Codes / Steps / Issues / Risks | `risk_persistence.py`, code APIs | issues/risks menus | PARTIAL |
| C16 | Interchange | `p6-interchange-api.ts`, exchange_persistence | import/export menu | PARTIAL |
| C17 | Dashboard / Analytics | `enterprise_dashboard*` | `/enterprise` | PARTIAL |
| C18 | Charts | client gantt/profile | tracking menu | PREVIEW |
| C19 | Reporting | `report_persistence.py` | reports menu | PREVIEW |
| C20 | Forms | `form_*` tables | — | PARTIAL |
| C21 | Form Calculations | `p6-formula-*` | `p6-formula-editor.ts` | PARTIAL |
| C22 | Workflow / Approvals | `form_approval_event`, `claim_submissions` | — | PARTIAL |
| C23 | PMBOK Layer | `docs/` contracts | — | PARTIAL |
| C24 | AI Permissions | `ai_action_boundary.py` | — | PARTIAL |
| C25 | AI Project Bootstrap | `ai_action_project_plan_tools.py` | `ai-action-*` | PARTIAL |
| C26 | AI Schedule Analysis | `ai_action_activity_tools.py` | ai panel | PARTIAL |
| C27 | AI Document / Form Support | `ai_assistant_orchestration.py` | assistant | PARTIAL |
| C28 | AI Reliability | `ai_action_tool_idempotency` | — | PARTIAL |
| C29 | Localization | `workspace-localization.ts` | 10 locales public, en/fa workspace | PARTIAL |
| C30 | RTL / Calendar / Fonts | locale dir + Jalali | partial | PARTIAL |
| C31 | Language Packs | `apps/web/site/locales` (10) | public only | PARTIAL |
| C32 | Help / Documentation | `docs/traceability` 67+16 rows | `/help` | PARTIAL |
| C33 | AI / Product Guide | `assistant-guide.ts` | `global-assistant-launcher.ts` | PARTIAL |
| C34 | Security / Tenancy | `identity_session.py`, tenant isolation tests | — | PARTIAL |
| C35 | Release / Quality | CI workflows | — | PARTIAL |

**Open item:** C05 is absent from the brief's own enumeration (C04 Grid/Layout → C06 Calendar).
It is registered as `MISSING_EVIDENCE` until the `CUBISITE/cubisite.xlsx` v8 sheet
«ماتریس قابلیت‌ها» is provided; no row will be invented for it.

---

## Baseline evidence (reproducible)

```
npm test                1191 passed, 0 failed (+15 preview-server)
pytest                  37 passed
preview smoke           26/26
responsive CDP audit    18/18
_site assembly          116 HTML files, 114 sitemap URLs
Help URLs               60/60 HTTP 200
```

## Next increments (dependency order from Section 1)

1. R1 — PostgreSQL persistence proof on a real cluster (write → commit → fresh read, idempotent
   bootstrap, tenant isolation).
2. R2 — CUBI Global Administration (users, roles, test users, sessions, audit).
3. R3 — Ten-locale coverage across workspace, admin and auth.
4. R4 — PUB-01…PUB-25 final route matrix.
5. R5 — Contextual Help assistant on every page, backed by the committed Help reference.
6. R6 — C01–C35 inheritance + Help matrix.
7. R7 — remaining operational capabilities.
8. R8 — full quality gate, preview, sequential merges.
