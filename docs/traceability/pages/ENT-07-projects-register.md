# ENT-07 — Projects register and project portal

| Field | Value |
|---|---|
| Page ID | ENT-07 |
| Route | `/cubi/enterprise/projects/` (selection, tab, `q`, `status`, `sort` in the query string) |
| Environment | CUBI Enterprise Workbench (separate document under `/cubi/`) |
| Status | Implemented; verified in the local full-stack Preview runtime. Official-hosted Preview: **blocked** (see Known gaps). Visual parity: **not claimed**. |
| Owner | Enterprise surface (this change set) |
| Base | `main` @ `1fbc8162512a59c9231396eee8c2e9b8795257d2` (continuation of PR #2129) |

## Inheritance chain and sources

Enterprise document (`apps/web/src/enterprise-entry.ts`) → shell (`app.ts`) → router (`router.ts`) → project register and portal (`pages/projects.ts`) → shared UI helpers (`pages/shared.ts`, `ui.ts`) → semantic icons (`icons.ts`) → API transport (`api.ts`) → server routes (`http/project_lifecycle_routes.py`, `p6_resource_api.py`, `document_api.py`, `risk_api.py`, `p6_issue_api.py`, `report_api.py`).

The three reference projects are durable shared data created by PR #2129 (`importing/reference_persistence.py`, `reference_postgres.py`, bundle `importing/data/cubi_reference_projects.v1.json.gz`). This change set does not re-import, duplicate or fixture them.

## Capability and Help mapping

| Item | Reference |
|---|---|
| Register and EPS page behavior | [About Projects (6636)](https://docs.oracle.com/cd/G48897_01/p6help/en/6636.htm), [About EPS (6621)](https://docs.oracle.com/cd/G48897_01/p6help/en/6621.htm), [Configuring EPS Views (44026)](https://docs.oracle.com/cd/G48897_01/p6help/en/44026.htm) |
| Page/tab/detail-window behavior, lists, fields, buttons, refresh, help | [Working with the P6 User Interface (9038)](https://docs.oracle.com/cd/G48897_01/p6help/en/9038.htm) |
| Icon register | `nav-projects`, `projects-search`, `projects-filter-status`, `projects-sort`, `project-open`, `project-overview`, `project-engineering`, `project-resources`, `project-documents`, `project-risks`, `project-reports`, `action-refresh`, `top-help` |

No Oracle, Primavera or P6 branding is rendered. Help links open the official English V26 topics in a new tab; the UI itself stays CUBI-branded.

Behavior taken from V26: the register is a flat EPS-style list with toolbar views/filters/sorting, a detail area for the selected project, explicit status/revision, and a user-driven refresh. V26 documents no EPS-page search box; the search control is a CUBI addition for the flat register and is labelled as a register search. V26 data-currency concepts map to the explicit receipt time and the per-tab source/revision stamp. The EPS hierarchy is shown where it belongs — in the register — and because `ProjectSummary` carries no EPS node or parent reference it is honestly reported as **Source not connected**, never inferred from names.

## Functional control inventory

Register (`data-testid="projects-register"`):

- Search (`projects-search`) filters name, project id and business domain; keeps `q` in the URL.
- Status filter (`projects-filter-status`) offers `all` plus exactly the statuses returned by the server.
- Sort (`projects-sort`) by name, revision (descending), start, finish; sortable headers carry `aria-sort`.
- Refresh (`action-refresh`) re-reads `GET /api/projects`, keeps the selection and updates the receipt time.
- Shown/total count (`projects-count`) and receipt time (`projects-freshness`).
- Row selection (click or Enter) marks the row (`aria-current`, `is-selected`) and opens the portal; `project-open` is a real anchor that preserves the tab and toolbar state.
- Register states: loading, empty, error, forbidden, disconnected — each with retry. The EPS panel (`projects-eps`) states the missing hierarchy source.

Portal (`data-testid="projects-portal"`) with six tabs, each drawing its registered SVG:

| Tab | Source | Rendering |
|---|---|---|
| Overview (`project-overview`) | `GET /api/projects/{id}` | Identity, schedule fields, revision and receipt stamp, boundary note, Engineering/portfolio links |
| Engineering (`project-engineering`) | probes `GET /p6/workspace`, `/p6/issues`, `/p6/earned-value` | Three connection rows with path/HTTP state; states the Engineering boundary; no calculation |
| Resources (`project-resources`) | `GET /p6/resources` then the project read (`api.listResources`) | Resource master table with revision column, or the source state |
| Documents (`project-documents`) | `GET /documents` | Document register table (`resource_type` column); revision reported as not provided |
| Risks & Issues (`project-risks`) | `GET /risks`, `GET /p6/issues` | Risk table (`exposure_level`) and issue table (`priority`, `record_revision`) |
| Reports (`project-reports`) | `GET /reports`, `GET /reports/catalogue` | Report definitions table (or empty line) and the catalogue subject table |

Tab ids are validated from the URL; unknown values fall back to Overview. `pageEpoch`/`paintEpoch` discard any tab read that belongs to a previous project, tab or refresh, so switching never leaves the previous project's data on screen.

## API, data and persistence

- `GET /api/projects` returns policy-filtered projects plus the reference union. **Fixed:** the preview and PostgreSQL adapters joined the membership table, so a reference project with several members was returned once per member (14 rows instead of 5 in the preview). Both list/get queries now use `EXISTS` for membership and reference visibility (`preview/storage.py`, `postgres_project_lifecycle.py`).
- `GET /api/projects/{id}` is read for the Overview; a reference project is readable without a membership row, and denial is a `403`, which the page renders as a forbidden state rather than an empty project.
- The Enterprise client adds no schedule, CPM, progress, resource-master or EVM computation. `probe()` only records the exact HTTP state of each official route.
- `api.listReports` was corrected to read the server's `reports` array (falling back to `definitions`).

## Permission mapping

- Session roles come from `/api/session`; `global_admin` and every role use the same register and gain no implicit write.
- The three references are visible to same-tenant authenticated users with no membership row and no write grant.
- `401` triggers `onUnauthorized()`; `403`, network/disconnected and generic failures each render a distinct state with retry.

## Acceptance evidence

| Check | Result |
|---|---|
| `npm run typecheck` (`apps/web`) | Pass |
| `npm run build` (`apps/web`) | Pass |
| `npm test` (`apps/web`) | 1320 TypeScript tests + 16 preview-server tests pass (includes 17 new ENT-07 tests) |
| `npm run test:e2e:preview` | Pass — 133 recorded checks, 61 screenshots |
| `pytest tests/test_preview_runtime.py tests/test_project_lifecycle.py tests/test_project_lifecycle_wsgi.py tests/test_reference_api.py tests/test_reference_persistence.py tests/test_reference_enterprise.py` | 85 pass |

New unit tests (`apps/web/src/enterprise-projects.test.ts`): fixtures read the real bundle; references listed once with other projects; no-membership visibility; per-project data separation; search by name/id/domain incl. Persian; status filter; all four sorts; no input mutation; tab/sort URL validation; six tabs with registered icons; all 13 icon ids draw shapes; no legacy flat icon on the page; localized status labels in ten locales; error mapping; every `ent07.*` key authored in all ten locales; register copy differs from English outside `en`; RTL locales.

Browser E2E (real WSGI runtime, real SQLite, headless Chrome): register shows exactly the five seeded projects once; three references present with bundle names; count `5 of 5`; receipt time; SVG icons; EPS Not Connected; search to 1 row with `q` in the URL; status options from the server; revision sort; row selection keeps `project` in the URL and Overview reads `/api/projects/CUBI-REF-002`; Engineering 3 sources; Resources 40, Documents 15, Risks 15, Issues 8, catalogue 3; project switch replaces data; refresh re-reads `/api/projects`; Persian RTL with translated tabs; 390 × 844 layout without horizontal scroll and with all tools and tabs visible. The newcomer first-run check now expects exactly the three shared references and no fixture membership.

Screenshots (local full-stack runtime, `apps/web/e2e/artifacts/`): `enterprise-projects-register.png` (1440 × 900), `enterprise-projects-portal.png`, `enterprise-projects-fa.png` (RTL), `enterprise-projects-mobile.png` (390 × 844 @2x).

## Visual review

Measured at 1440 × 900 and 390 × 844. The register uses the existing CUBI card/table system with 16 px SVG icons at a single stroke weight, sortable headers, a visible receipt time and a status badge per row. Persian flips the whole document to RTL and keeps the six tabs labelled. No Help screenshot was available on the official preview host, so pixel-level visual parity with the V26 reference is **not claimed**; beyond the Help behavior mapping above, the review is limited to layout, overflow, icon presence and RTL at the recorded viewports. There is no retained "before" screenshot: the pre-change page was the source baseline, and this record does not replace it with a passing visual claim.

## Known gaps and decisions

- **Official Preview host blocked.** The documented branch alias `cubi-web-preview-git-feat-vercel-p-8eb184-foroughichamshir-7811.vercel.app` returns `DEPLOYMENT_NOT_FOUND`. No Vercel token/CLI is available. Restoring it needs dashboard/API access to project `prj_E1psnPyPs9doA82oZ4OcmiIqarle` to re-alias that host to a current READY deployment of the branch (or reconnect/redeploy the branch behind it). This record therefore reports local full-stack evidence only.
- `ProjectSummary` has no finish date. The Finish column shows `—` and its sort is a no-op until the server supplies the field; no date is derived or fabricated.
- The EPS hierarchy is not present on the project read, so it is reported as Not Connected rather than constructed from names.
- The document register supplies no revision, so the Revision stamp says "not provided".
- The preview runtime returns no stored report definitions (only the catalogue), so Reports shows the real empty line and the three catalogue subjects.
- Business-domain values are shown as stored; seeded fixtures store the code and references store their sector text.
- The temporary local runtime used for probing was started from this worktree with its own SQLite file; no shared database was touched.
