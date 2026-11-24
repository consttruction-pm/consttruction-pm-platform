# Stage 0 — CUBI P0 repository audit and honest starting point

**Date:** 2026-11-24 (UTC)
**Parent issue:** #2138
**Related:** #2131, #2132, #2136; PR #2129 (merged), PR #2133 (draft), PR #2137 (docs), PR #2139 (docs)
**Status:** VERIFIED (read-only audit) — no code, schema, database row, identity, session, project or deployment was changed.
**Base main SHA:** `17de9bd3004c7bc9420af063d327a4bc7b5f080f`
**Working branch:** `docs/p0-stage0-repository-audit`

This document is the Stage 0 deliverable required by the owner's execution order and by
`docs/implementation/P0_PROJECT_RECOVERY_AND_ENTERPRISE_PROJECT_DEFINITION_HANDOFF_V1.md`
(open PR #2139). It records what the repository actually contains, what is proven, what is
not, and the exact gates that block later stages. Nothing here is a completion claim.

---

## 1. Current state that later stages must start from

| Item | Verified value | Evidence |
| --- | --- | --- |
| Canonical repository | `consttruction-pm/consttruction-pm-platform` | remote |
| Current `main` | `17de9bd3004c7bc9420af063d327a4bc7b5f080f` — `feat(enterprise): complete ENT-07 projects register and project portal (#2130)` | `git log origin/main` |
| `main` CI at that SHA | ConstructionPM CI, PostgreSQL Integration, Sync State Integration, Client Typecheck, Pages deploy — success | `gh run list --branch main` |
| Migration registry | 15 steps, fresh schema = 93 application tables + ledger = 94 | `deployment/migrations.py`, local PostgreSQL 14 |
| Protected reference projects | `CUBI-REF-001/002/003`, imported by merged PR #2129 (squash `1fbc8162`) | PR #2129, live tests |
| Protected Dam workstream | `CUBI-DAM-001`, only on draft PR #2133; **not** in `main` and not persisted in any database this environment can reach | `grep` of `main`, PR #2133 files |
| Erroneous project identities | **Still unknown.** No repository evidence names them; no production database/API access exists here | see §6 |
| Enterprise router | 26 `PageId`s under `/cubi/*`, one shared shell, `apps/web/src/enterprise/router.ts` | source |
| Enterprise icons | 13 registered icons (ENT-07 only) | `apps/web/src/enterprise/icons.ts` |
| Engineering icons | 97 registered icons | `apps/web/src/workspace-icons.ts` |
| Official Preview | Canonical URL returns `404 DEPLOYMENT_NOT_FOUND`; owner-supplied main-alias Enterprise link returns 200 | probes 2026-11-24 02:48 UTC |
| Production database access | **Absent** in this session: no `CONSTRUCTION_PM_DATABASE_URL`, `POSTGRES_URL_NON_POOLING`, Supabase or Vercel token | environment inspection |
| Source workbook | Uploaded file SHA-256 equals `0848454d…fa26` and contains 94 sheets | `sha256sum`, workbook XML |

### 1.1 What is merged versus open

- **Merged in `main`:** three durable reference projects (#2129), Enterprise ENT-07 register/portal (#2130), the 26-PageId Enterprise router/shell, 15-step migration registry, canonical Engineering lifecycle/API/repositories and their tests.
- **Open, not merged:** #2133 (Dam, draft, CI failing), #2137 (vendor interchange standard, docs), #2139 (P0 handoff protocol + ledger, docs), #2138/#2131/#2132/#2136 (issues).
- **Documentation only:** #2137 and #2139; they change no runtime behavior.
- **Local-test only:** all PostgreSQL evidence in this environment, including PR #2129's live suites and the reference import.
- **Real browser evidence:** the owner-supplied main-alias Enterprise deep link loads its login page (200); no authenticated browser session was created, so no deployed project register or project definition was verified.
- **Blocked:** exact erroneous IDs, live database inventory, deletion, live workbook-as-HTML reproduction, Dam persistence, production deployment SHA, Safe Browsing status.

---

## 2. Preview and deployment truth

The standard (`docs/standards/CUBI_PAGE_BY_PAGE_DESIGN_AND_ACCEPTANCE.md` §1) fixes one official entry:

`https://cubi-web-preview-git-feat-vercel-p-8eb184-foroughichamshir-7811.vercel.app/app?project=preview-rps-01&view=live`

Observed on 2026-11-24 02:48 UTC:

| Probe | Result |
| --- | --- |
| Canonical URL | `404` with Vercel `DEPLOYMENT_NOT_FOUND` |
| Owner Enterprise test link (`...git-main.../login?next=/cubi/enterprise/projects?project=CUBI-REF-001...`) | `200` (login document) |
| `...git-main.../cubi/enterprise/projects/` without session | `302` to login |
| `...git-main.../api/projects` without session | `401` |
| `...git-main.../api/health/ready` | `ready`, schema `version 15`, `tables 94`, checksum drift `project-lifecycle` (policy `report`), structure hash equal |
| `/preview/login` on the deployment | `401` — the demo persona login is not exposed there |
| Safe Browsing | not verifiable: no Safe Browsing API credential; the public transparency endpoint's undocumented payload is not acceptable evidence; owner-reported Chrome interstitial remains a **release blocker** |

**Consequence:** per `AGENTS.md`, the canonical Preview cannot be substituted. Its alias is still bound to a deleted/expired deployment of `feat/vercel-preview-fixtures`; this sandbox has no Vercel token to redeploy or re-alias that entry. The deployment SHA behind the main alias is **UNKNOWN** (readiness exposes schema version, not commit).

**Enterprise deep link:** the owner-supplied URL is a legitimate test address on the main alias, but it is **not** the official Preview and does not prove the Enterprise project definition works. It also requires a real login, which this session does not have and must not fabricate.

---

## 3. Database and project inventory status

### 3.1 What can be inspected

- Local PostgreSQL 14 schemas created by the repository's runtime/tests: 15 migrations, 94 boot tables, `drift = None` on a fresh schema.
- Local evidence database (`cubi_final_test`, non-production): `project_lifecycle_projects` contains exactly the three reference projects (`CUBI-REF-001/002/003`, tenant `acme`, revision 1); `cubi_reference_project` has 3 rows; `project_lifecycle_memberships` has 0 rows; `eps_node` is empty; `p6_obs_node` has 24 rows; imported Enterprise registers exist (risks, documents, issues, tasks).
- Preview SQLite (`/data/work/repo/.preview/cubi-preview.sqlite3`, stale local artifact): only the two original fixtures (`preview-rps-01`, `preview-nse-02`); no reference rows in this local copy. It is **not** evidence of the deployed preview database.

### 3.2 What cannot be inspected

The production/canonical PostgreSQL database is unreachable from this session:

- no `CONSTRUCTION_PM_DATABASE_URL`
- no `POSTGRES_URL_NON_POOLING`
- no Supabase service-role/connection secret
- no Vercel token or authenticated dashboard access

Therefore the following Stage 1 requirements are **BLOCKED**, not "not found":

1. complete project inventory with immutable IDs, tenant, workspace, provenance, revision;
2. identification of the three erroneous projects;
3. dependency closure for WBS/activities/relationships/calendars/resources/assignments/baselines/Enterprise;
4. recoverable backup with checksum verification;
5. owner approval of an exact deletion set;
6. confirmation that the reference project rows and their import journals are unchanged.

The absence of names in the repository does **not** prove the erroneous projects do not exist.

### 3.3 Known project identities and non-identity evidence

| Identity | State | Interpretation |
| --- | --- | --- |
| `CUBI-REF-001/002/003` | merged importer + live tests + local PostgreSQL rows | protected; must not be deleted, re-imported or mutated |
| `CUBI-DAM-001` | only in draft PR #2133 | one workstream; not persisted; counts in the PR body are claims pending live read-back |
| `preview-rps-01`, `preview-nse-02` | preview fixtures | not automatically erroneous; must not be swept into deletion |
| Other IDs (`CUBI-RPS-CAL`, `CUBI-DEMO-001`, …) | documents, calendars or visual demo fixtures | not project identities to delete |
| Three erroneous records | **unknown IDs** | no deletion, no rename, no retirement until exact IDs + approval |

---

## 4. Source material (Stage 2 readiness)

| Item | Verified |
| --- | --- |
| File | `CUBI_Three_Reference_Projects_Master_Data_v1-1.xlsx` (user-supplied upload) |
| SHA-256 | `0848454d2b8b77806986eb53cf36e95521d7e789ad8c4f0b2af78acb4e82fa26` — matches the mapping contract |
| Sheets | 94, first sheets `README`, `Project Register`, `Project Settings`, `EPS`, `OBS`, `WBS`, `Project Milestones`, `Project Codes`, `Activity Codes`, `Resource Codes` |
| Runtime use | none; the canonical importer reads the frozen bundle `src/construction_pm/importing/data/cubi_reference_projects.v1.json.gz`, not Excel |
| Workbook rendering | no code path in `main` stores or renders workbook bytes/HTML in Project Description or Project Information; description is normalized plain text ≤ 2000 characters (`MAX_PROJECT_DESCRIPTION`) |
| Reported workbook-as-content defect | not reproducible from `main` source; requires read-only inspection of the live project row/attachment and the deployed build — **BLOCKED** |

The workbook is an ingestion artifact. It must never become a runtime database or a page-rendered document.

---

## 5. Engineering project creation and Project Details

Current `main` implementation:

- Client: `apps/web/src/project-bootstrap.ts` + the empty-state form in `apps/web/src/main.ts`.
- HTTP: `POST /api/projects`, `GET /api/projects`, `GET /api/projects/{id}`, settings update, status, checkout, defaults history.
- Application: `ProjectLifecycleService` / `ProjectLifecycleAPI`.
- Persistence: `PostgresProjectLifecycleRepository` and the SQLite preview twin; table `project_lifecycle_projects` (19 persisted fields + checkout/status).

What the create form actually collects today: **name, business domain, description, planned start, date system**; the project ID is auto-generated by `createProjectId()` (UUID), not entered by the user.

What is missing against P6 Professional V26 (`Create a project`, `defining_project_details.htm`):

| Required capability | Current state |
| --- | --- |
| EPS selection | **absent** — no EPS service/API; `eps_node` table exists but no route writes/reads it in the lifecycle |
| User-controlled unique Project ID | **absent in UI**; API accepts an ID but the form generates a UUID |
| Must Finish By | **absent** — no column/API/UI |
| Responsible Manager from OBS | partial: `obs_responsible_manager` is a free label and `obs_id` exists in the API/service, but the create form does not offer OBS selection |
| Default Rate Type | **absent** — no column/API/UI |
| Project Codes | **absent** |
| Summarization | **absent** |
| Float settings | **absent** |
| Calendar / default activity type / % complete type / duration type / cost account / activity ID numbering | present in the settings model/API and mostly in the settings UI |
| Date ordering validation (start ≤ must finish) | not applicable until Must Finish exists |

Baseline evidence: `tests/test_project_lifecycle_api.py`, `test_project_lifecycle_http_routes.py`, `test_project_lifecycle.py` — **145 passed** in this session. `tests/integration/test_production_login_postgres_live.py` already contains `test_admin_can_create_a_project`, stale-revision and cross-tenant cases; it passes on `main` CI.

So the repository's create path is not dead code. The owner-reported failure on the deployed preview is **not reproduced here**; it must be reproduced against the live deployment with a disposable identity and then tied to a diff or data condition.

---

## 6. The "three incorrect projects" — evidence position

Facts established:

1. #2131 protects `CUBI-REF-001/002/003`.
2. #2132/#2133 own `CUBI-DAM-001`.
3. #2138's issue comment by the owner's audit (2026-11-24 02:20) states the three IDs are **not yet identified**.
4. Repository-wide searches for project IDs find only the references, the Dam ID in the PR branch, preview fixtures and calendar/demo codes — **no candidate set of three erroneous projects**.
5. No production database, API session or deployment token exists in this environment to enumerate them.

**Stage 1 verdict: BLOCKED.** The exact next action is a read-only inventory (query or API export) from the canonical database, executed by an environment that holds the production DSN (or by the owner providing a read-only export). Deletion remains prohibited.

---

## 7. Enterprise environment

- Router: 26 `PageId`s, route base `/cubi`, single shell (`enterprise.html` / `app.ts`). No second shell exists.
- `projects` page (merged #2130): register with search/status filter/sort/refresh, plus a project portal with six tabs — overview, engineering, resources, documents, risks, reports. It reads `/api/projects`, `/api/projects/{id}`, activities, resources, documents, risks, issues and reports.
- Not present: project definition create/edit, General/Dates/Status/Project Codes/Summarization/Defaults/Activity Numbering/Float tabs, EPS/OBS hierarchy navigation, WBS overview, calendar overview, baseline overview, cost/progress summary, project navigation/breadcrumbs beyond the register/portal, Enterprise-side project creation.
- EPS/OBS/WBS pages exist only as generic register pages backed by `enterprise_records` (`kind = "eps"` etc.); they are **not** the canonical EPS tree or OBS hierarchy and must not be presented as such.
- Icons: 13 registered Enterprise icons (all ENT-07); most shell navigation still renders text-only links; the required 30+ icon groups are far from covered.
- Tests: `apps/web/src/enterprise-projects.test.ts` — 16 focused tests pass; they cover register/portal/icon/localization behavior, not project definition.

Enterprise must read the same canonical project IDs; it must not create a second project store or calculate schedule/resource/cost facts.

---

## 8. Import / export and interchange

Code that exists:

- `p6_interchange_api.py`, `p6_interchange_adapter.py`, `p6_interchange_mapping.py`, typed conversion/verification modules.
- Codecs: `p6_xer_codec.py` (XER), `p6_xls_codec.py` / `p6_xlsx_codec.py`, Primavera XML and MSPROJECT XML through the mapping registry; `P6MappingFormat` lists `XER_PROJECT`, `XER_RESOURCE_ONLY`, `XER_ROLE_ONLY`, `PRIMAVERA_XML`, `XLS`, `XLSX`, `MSPROJECT_XML`, `MPX` — **no MPP**.
- Excel exchange service: `exchange_application.py` (preview/apply, typed rows, idempotency, transaction).
- Routes: `POST /api/projects/{id}/p6/interchange/{format}/import|export`, wiring available in the preview runtime (`P6InterchangeAPI` constructed there).

Gaps:

- Production runtime does **not** construct `P6InterchangeAPI`; those routes are not wired in production.
- No MPP converter exists; PR #2137 is documentation only and explicitly claims no new runtime behavior.
- Round-trip certification in the target applications (P6 XER/XML, MS Project) has not been performed here; no vendor application is available in this sandbox.

---

## 9. Migrations, schema and database safety

- `PRODUCTION_STEPS` in `src/construction_pm/deployment/migrations.py` has 15 steps (identity, global admin, enterprise tasks, organization access, project lifecycle revision 2, engineering masters, presentation, scheduling state, risk, forms, knowledge, AI actions, username identity, reference engineering, reference enterprise).
- A fresh schema produces 94 tables including `cubi_schema_migration`; local PostgreSQL tests confirm no drift on a fresh database.
- The existing preview database reports checksum drift for step 5 because the step revision was bumped to 2 when the shared registry table was added — documented behavior (`report` policy, structure hash equal).
- Draft PR #2133 adds **migration 16** (RLS/direct-client deny hardening). Its exact-head CI currently fails 3 tests because the suite still asserts version 15 (`test_cubi_database_operationalization_postgres_live.py`) and one tenant/identity assertion differs (`test_production_login_postgres_live.py`). PR #2133 is therefore **not mergeable in its current state**.
- Any new project-definition columns must be an additive migration **after** the Dam/RLS numbering is settled (17+), not an edit of an applied step.
- No destructive DDL, no RLS change and no data mutation was performed in this audit.

---

## 10. Tests and CI state

| Area | Evidence |
| --- | --- |
| Engineering lifecycle | `python -m pytest -q tests/test_project_lifecycle_api.py tests/test_project_lifecycle_http_routes.py tests/test_project_lifecycle.py` → **145 passed** |
| Enterprise projects UI | `npm test -- --test-name-pattern enterprise` in `apps/web` → **16 passed** |
| Reference PostgreSQL | `tests/integration/test_postgres_reference_projects_live.py` → **10 passed** (earlier in this session) |
| Database operationalization | `tests/integration/test_cubi_database_operationalization_postgres_live.py` → **13 passed** |
| `main` CI | all five workflows green at `17de9bd3` |
| PR #2133 | postgres/test 3.11–3.13 fail; typechecks pass; Vercel deployment rate-limited (24 h) |
| PR #2137/#2139 | documentation PRs; Python/typecheck checks pass; Vercel public/web failures are pre-existing infrastructure failures |

No deployed browser test was executed because no authenticated disposable session or password was available.

---

## 11. File-level disposition (key surfaces)

Status vocabulary: **KEEP** (reuse as-is), **MODIFY** (needed change in a later stage), **REUSE** (share, do not duplicate), **REMOVE ONLY AFTER PROOF** (no removal authorized in Stage 0), **UNKNOWN** (insufficient evidence).

| Path | Purpose | Last change | Data source | Tests | Disposition |
| --- | --- | --- | --- | --- | --- |
| `apps/web/src/main.ts` | Engineering bootstrap shell, selection and project-details form | `e1c72ccb` | `/api/projects` | bootstrap/lifecycle tests | MODIFY (Stage 3 form/fields) |
| `apps/web/src/project-bootstrap.ts` | Client create/list/open contract | `2f39c1de` | HTTP API | `project-bootstrap.test.ts` | MODIFY |
| `src/construction_pm/application/project_lifecycle.py` | Lifecycle domain/service | `2f39c1de` | repository | 145 lifecycle tests | MODIFY |
| `src/construction_pm/application/project_lifecycle_api.py` | API contract | `2f39c1de` | service | lifecycle API tests | MODIFY |
| `src/construction_pm/http/project_lifecycle_routes.py` | HTTP routes (projects, P6, interchange, enterprise) | `666a30e7` | application services | HTTP route tests | KEEP / MODIFY (wiring) |
| `src/construction_pm/postgres_project_lifecycle.py` | PostgreSQL lifecycle repository + shared visibility | `17de9bd3` | PostgreSQL | `test_postgres_project_lifecycle.py` | REUSE / MODIFY |
| `src/construction_pm/preview/storage.py` | Preview SQLite repository | `17de9bd3` | SQLite | preview tests | MODIFY (parity) |
| `src/construction_pm/preview/runtime.py` | Preview seeding and composition | `1eb4e225` | SQLite + bundle | preview suites | KEEP |
| `src/construction_pm/importing/reference_persistence.py` | Bundle → canonical repositories | `1fbc8162` | frozen bundle | reference tests | KEEP / MODIFY |
| `src/construction_pm/importing/reference_postgres.py` | PostgreSQL import adapter | `1fbc8162` | PostgreSQL | live suites | KEEP |
| `src/construction_pm/importing/reference_enterprise.py` | Enterprise register import | `1fbc8162` | PostgreSQL/SQLite | enterprise tests | KEEP |
| `src/construction_pm/importing/reference_journal.py` | Import journal/registry | `1fbc8162` | PostgreSQL/SQLite | live suites | KEEP |
| `src/construction_pm/importing/data/cubi_reference_projects.v1.json.gz` | Frozen source bundle for refs | `1fbc8162` | file | bundle hash tests | KEEP (immutable) |
| `scripts/import_reference_projects.py` | Durable import CLI | `1fbc8162` | PostgreSQL | live CLI evidence | KEEP |
| `src/construction_pm/importing/dam_reference_project.py` | Dam bundle (draft PR #2133) | PR #2133 | generated | 1 test | UNKNOWN / VERIFY |
| `scripts/import_dam_reference_project.py` | Dam import CLI (draft) | PR #2133 | generated | none verified | UNKNOWN / VERIFY |
| `apps/web/src/enterprise/router.ts` | 26 PageIds, `/cubi/*` | `d21da25d` | static | route tests | KEEP |
| `apps/web/src/enterprise/app.ts` | Shared Enterprise shell | #2130 | session/API | enterprise tests | KEEP |
| `apps/web/src/enterprise/pages/projects.ts` | Register + six-tab portal | `17de9bd3` | `/api/projects…` | 16 tests | MODIFY (definition) |
| `apps/web/src/enterprise/pages/registers.ts` | Generic Enterprise registers (EPS/OBS/etc.) | #2130 | `enterprise_records` | register tests | KEEP (do not present as EPS tree) |
| `apps/web/src/enterprise/api.ts` | Enterprise API client | `17de9bd3` | HTTP API | enterprise tests | MODIFY |
| `apps/web/src/enterprise/icons.ts` | 13 Enterprise SVG icons | `17de9bd3` | static | icon tests | MODIFY (expand) |
| `apps/web/src/enterprise/i18n.ts` | Enterprise 10-locale catalog | #2130 | static | localization tests | MODIFY |
| `apps/web/src/workspace-icons.ts` | 97 Engineering icons | `75025011` | static | icon tests | KEEP |
| `src/construction_pm/deployment/migrations.py` | 15-step schema registry | `1fbc8162` | PostgreSQL | operationalization tests | MODIFY (new additive steps) |
| `src/construction_pm/deployment/production_runtime.py` | Production composition/boot | `1fbc8162` | PostgreSQL | live suites | MODIFY (interchange/definition wiring) |
| `src/construction_pm/http/production_composition.py` | Runtime composition | #2066 | services | HTTP tests | MODIFY |
| `src/construction_pm/p6_interchange_api.py` + codecs | Native interchange | older | application services | interchange suites | KEEP / REUSE |
| `src/construction_pm/exchange_application.py` | Excel exchange preview/apply | #1882 | repositories | exchange tests | KEEP |
| `tests/test_project_lifecycle*.py` | Lifecycle unit/HTTP/API | ongoing | — | 145 pass | KEEP / EXTEND |
| `tests/integration/test_postgres_reference_projects_live.py` | Shared reference acceptance | #2129 | PostgreSQL | 10 pass | KEEP |
| `tests/integration/test_cubi_database_operationalization_postgres_live.py` | Migration/readiness acceptance | #2129 | PostgreSQL | 13 pass | MODIFY if registry grows |
| `tests/integration/test_production_login_postgres_live.py` | Production auth/create/tenant flow | #2110 | PostgreSQL | currently failing on PR #2133 only | KEEP / MODIFY after investigation |
| `apps/web/src/enterprise-projects.test.ts` | Enterprise register/portal | #2130 | fixtures | 16 pass | KEEP / EXTEND |
| `docs/engineering/CUBI_REFERENCE_PROJECTS_IMPORT_MAPPING.md` | Mapping and import record | #2129 | — | document | KEEP / MODIFY (duplicate section numbers, status refresh) |
| `docs/database/CUBI_DATABASE_ARCHITECTURE.md` | Database operating contract | #2129 | — | document | KEEP / MODIFY |
| `docs/architecture/CUBI_CANONICAL_DATABASE.md` | Canonical DB decision (older snapshot says zero users/empty DB) | #2110 | — | document | REUSE with reconciliation (conflicts with current state) |
| `docs/governance/PROJECT_STATE_LEDGER.md` | Continuity ledger | last entry 2026-11-20 | — | document | MODIFY (stale; #2129/#2130/#2138 absent) |
| `docs/implementation/P0_PROJECT_RECOVERY_…md` | Handoff protocol (PR #2139) | `cdac2fd3` | — | document | REUSE (not merged) |
| `docs/standards/CUBI_PAGE_BY_PAGE_DESIGN_AND_ACCEPTANCE.md`, `AGENTS.md`, `README.md`, continuity protocol | Binding rules | current | — | — | KEEP |

---

## 12. Stage plan and exact next actions

| Stage | Status | Exact next action |
| --- | --- | --- |
| 0 — repository audit | **VERIFIED (this document)** | Commit this audit, post the checkpoint, no runtime change |
| 1 — identify three wrong projects | **BLOCKED** | Obtain read-only production DSN/export or an authenticated register export; run the inventory query (§3) and record exact IDs/provenance; do not delete |
| 2 — recover source files | **PARTIAL** | Source workbook and hash verified; inspect live import journal/attachments before any re-import; confirm no workbook bytes are stored in project description |
| 3 — P6 V26 creation/Project Details | READY (code) but blocked by #2133 numbering | Add typed fields (EPS, user Project ID, Must Finish By, Responsible Manager, rate type, codes, summarization, float) end-to-end after migration 16/17 is settled; extend tests and UI |
| 4 — Dam project | **BLOCKED** | Resolve #2133 CI failures (version 15→16 assertions, tenant mismatch), then verify persistence/counts on a real PostgreSQL and the shared-workspace separation; do not duplicate the bundle |
| 5 — Enterprise Project Definition | READY (UI) / needs API | Add definition tabs and project edit through the canonical lifecycle/API; read EPS/OBS/WBS from Engineering-owned services; do not build a second store |
| 6 — icons | READY | Extend the Enterprise icon registry from 13 to the real page/control inventory; verify hover/focus/selected/disabled/RTL/tooltips per page |
| 7 — PostgreSQL connectivity | **BLOCKED for live verification** | Wire interchange and definition reads; verify against the canonical database when access exists; no fixtures as production data |
| 8 — page-by-page tests | NOT STARTED | Build the page matrix and run browser/API/DB checks after each connected page |
| 9 — Preview/security | **BLOCKED** | Restore the canonical alias from the Vercel owner, determine deployment SHA, resolve Safe Browsing; no substitution |

---

## 13. Blockers (exact, with the action needed)

1. **Canonical Preview 404.** The official alias points to a deleted deployment of `feat/vercel-preview-fixtures` in `cubi-web-preview` under `foroughichamshir-7811`. Required: Vercel owner redeploys the current build behind that same alias (no new project/URL). Needed here: a Vercel token or owner action.
2. **No production PostgreSQL/Supabase access.** No DSN, password, service-role key. Required: read-only connection/export to inventory projects and verify rows. Without it, Stage 1 and destructive gates cannot start.
3. **No authenticated disposable Preview identity.** `/preview/login` is 401 on the deployment, and no test user credentials exist. Required: a disposable test account/session for browser verification; never the owner's account.
4. **PR #2133 CI is red** (3 failures from the added migration 16 and a tenant/identity assertion) and Vercel is rate-limited. Required: update versioned assertions, investigate the tenant mismatch, rerun exact-head checks. Do not merge while red.
5. **PR #2137 and #2139 are documentation-only** and unmerged; they do not provide runtime capability. The ledger is stale and does not record #2129/#2130/#2138.
6. **Reported workbook-as-HTML behavior is not in `main` source.** Required: inspect the live project row/attachment and the deployed build to find whether it is data, an unmerged branch, or a document attachment; do not guess a code cause.
7. **Safe Browsing warning** is unverified and remains a release blocker; no browser protection may be bypassed.

---

## 14. Non-regression guarantees for this stage

- No password, hash, identity, session, role, tenant, membership or dashboard was read or changed.
- No project row, import journal, reference record, Dam record or Enterprise register was created, deleted or mutated.
- No migration, schema, RLS policy, Vercel alias, deployment or environment variable was changed.
- Only read-only repository inspection, local test execution and documentation were performed.

---

## 15. Stage 0 checkpoint (GitHub format)

- **Parent Issue:** #2138
- **Related Issue/PR:** #2131, #2132, #2136, #2129, #2133, #2137, #2139
- **Stage:** 0 — repository-first audit and starting point
- **Status:** VERIFIED (audit); downstream stages partially BLOCKED
- **Base Main SHA:** `17de9bd3004c7bc9420af063d327a4bc7b5f080f`
- **Working Branch:** `docs/p0-stage0-repository-audit`
- **Exact Head SHA:** recorded in the PR/issue checkpoint after commit
- **Changed Files:** this audit document and a ledger entry (docs only)
- **Evidence Inspected:** README, AGENTS, continuity protocol, page standard, Enterprise crosswalk, Enterprise router/pages/icons, Engineering lifecycle/API/repositories, import/bundle/interchange code, migrations/runtime, DB architecture, the 94-sheet workbook and hash, issues #2131/#2132/#2136/#2138, PRs #2129/#2130/#2133/#2137/#2139, local PostgreSQL schemas, live Preview probes
- **Completed:** read-only inventory, route/API/DB mapping, source/hash verification, Preview and CI truth, blocker list, stage plan
- **Not Completed:** live project inventory, three wrong IDs, backup, deletion, live browser/DB verification, Dam persistence, Enterprise definition, icon expansion
- **Database Impact:** none (read-only)
- **Migration IDs:** main = 15; draft PR #2133 = 16 (RLS), not merged, CI red
- **Project IDs:** `CUBI-REF-001/002/003` protected; `CUBI-DAM-001` only in PR #2133; erroneous IDs unknown
- **Owner Password/Identity Preservation:** untouched; no credential read or emitted
- **Dashboard Preservation:** untouched
- **Tests and Results:** lifecycle 145 passed; Enterprise UI 16 passed; live reference 10 passed; operationalization 13 passed; `main` CI green; PR #2133 red
- **Browser Verification:** none (no authenticated disposable session); only HTTP probes
- **PostgreSQL Verification:** local PostgreSQL only; no production claim
- **Known Blockers:** canonical Preview 404; no production DB access; no disposable session; PR #2133 CI; Safe Browsing unverified
- **Next Exact Action:** obtain read-only production DB/API access, run the inventory query, publish exact IDs for owner approval; in parallel, fix PR #2133 CI without changing migration semantics
- **Next Agent Read-First:** this file, latest #2138 checkpoint, #2131, #2132/#2133, `AGENTS.md`, page standard, Enterprise crosswalk

---

**Bottom line:** the repository already contains a solid canonical lifecycle, durable reference import, one Enterprise shell and a 26-page router. It does **not** contain evidence for the three erroneous project IDs, the Dam project in `main`, the P6-complete create wizard, the Enterprise project-definition workflow, a complete Enterprise icon set, or live production verification. Stage 1 and the destructive gates are blocked on real database/Preview access, not on missing code alone.
