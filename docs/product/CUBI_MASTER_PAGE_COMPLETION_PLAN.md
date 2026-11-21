# CUBI — master page completion plan

**Mission:** one continuous order to complete every page, field and cross-environment connection.
**Repository:** `consttruction-pm/consttruction-pm-platform`
**Baseline SHA at audit:** `0014928bf` (`main`, 2026-11-20)
**Audit date:** 2026-11-20
**Owner:** single agent execution (no delegation in the audited revision)
**Machine-readable twin:** `CUBI_MASTER_PAGE_COMPONENT_MATRIX.csv` / `.json` (86 rows)

> **Correction (2026-11-21).** The audit below is a snapshot at `0014928bf`.
> Since then the Enterprise Workbench was delivered on `/cubi/*` (PRs #2085–#2088)
> and the entry path was corrected on PR #2089: `/login` is the canonical sign-in,
> `/workbench/` is the post-login default, `/enterprise` answers `308` to `/cubi/`,
> and all 20 Enterprise data routes are served by `enterprise.html`. The
> statement in the table that "15 of 16 Enterprise pages have no route" is no
> longer true; see
> `docs/enterprise/ENTERPRISE_V26_ENTRY_ROUTING_AND_OPERATIONS.md`.


## 1. What this plan is and is not

This plan records the **real** state of every registered page, the inheritance it must respect, and the work that remains. It deliberately separates four things the order treats as different:

- what a document *specifies*;
- what code exists;
- what a server route actually serves;
- what a browser proof has observed.

A route, a file or a unit test alone never promotes a row to `VERIFIED`. The status vocabulary is the one required by the mission (`VERIFIED`, `WIRED_WRITE`, `WIRED_READ`, `SHELL_ONLY`, `MISSING`, `NOT_AUDITED`, `BLOCKED_EXTERNAL`).

## 2. Audit of the repository at `0014928bf`

| Item | Finding |
|---|---|
| `main` | `0014928bf` — all mission PRs #2070–#2081, #2083 and #2084 merged; CI (CI, Web CI, PostgreSQL sync, Pages) green |
| Open PRs | #2068 (Scheduling Core runtime) and #2048 (Activities V30) remain open and untouched — both are outside this mission's authority |
| Branch collision | `feat/p0n2-runtime-activation` (#2068) owns `src/construction_pm/scheduling*`, worker and calendar-registry files; `feat/2047-activity-workspace-v26` (#2048) owns `apps/web/src/workspace-*activity*`, `e2e/activity-*`, `p6-*activity*` and the Activities route |
| Engineering shell | One canonical shell at `/app`; no second shell is mounted; legacy visual-demo URLs canonicalise into it |
| Enterprise routes | Only `/enterprise/` is served. `/enterprise/portfolio/`, `/tasks/`, `/approvals/`, `/workflows/`, `/organization/`, `/operations/`, `/portal/`, `/integrations/`, `/resources/`, `/reports/`, `/admin/`, `/documents/`, `/risks/` return the marketing 404 — **15 of 16 Enterprise pages have no route** |
| Workbench | Did not exist at `0014928bf`; `/login` defaulted to the static `/environments/` page. This revision adds the real `/workbench/` surface |
| Shared core | `Shared Calculation Core` and `p6` repositories are the only calculation source; no duplicate KPI maths was introduced |
| Help sources | P6 Professional V26 and P6 EPPM V26 HTML Help; sampled topic URLs return HTTP 200 (see acceptance report) |

### Interference boundaries (no writes performed)

- **Scheduling Core / OfflineSchedulingBundle:** `src/construction_pm/scheduling*`, `scheduling_jobs*`, `calendar_registry*`, `worker*`, `apps/client-sync/src/scheduling-*`. PR #2068.
- **Activities scope:** `apps/web/src/workspace-*activity*`, `apps/web/src/p6-*activity*`, `e2e/activity-*-v26.mjs`, `e2e/activities-v26-scenarios.mjs`, `apps/web/src/workspace-view.ts` activity table/Gantt blocks. PR #2048.
- This revision touches none of those paths.

## 3. Inheritance model applied to the 25 initial pages

| Surface | Inherits from | CUBI-owned | Help source |
|---|---|---|---|
| Public Homepage, Login, Workbench, Environment selector | Public site + entry flow (`CUBI_PRODUCT_SURFACE_ARCHITECTURE` §2–§3) | Entry copy, locale handling, grant display | CUBI-owned (no Oracle topic) |
| Engineering shell, Projects/EPS, WBS, Activities, Details, Network, Gantt, Resources, Calendars, Tracking | Canonical Visual Workspace + P6 Professional V26 | Visual identity, command registry, locale layer | P6 Professional V26 HTML Help |
| Enterprise dashboard, portfolio, projects, organization, tasks, approvals, workflows, capacity, operations, portal | P6 EPPM V26 concepts; **no** Engineering shell copy | Enterprise layout, org workflows | P6 EPPM V26 HTML Help |

## 4. Status of the 25 initial pages at this revision

| # | Page | Route | Status | Evidence | Remaining gap |
|---|---|---|---|---|---|
| 1 | Public homepage | `/` (+9 locales) | VERIFIED | Pages deployment + 18/18 responsive audit | — |
| 2 | Login / entry | `/login` | VERIFIED | production-login E2E, pytest, ten locales | — |
| 3 | Role and working context | `/workbench/` identity block | WIRED_READ | session roles from `/api/session` | dedicated role picker not needed after real login |
| 4 | Personal workbench | `/workbench/` | WIRED_READ | new surface + 5 unit tests + server probes | browser screenshot |
| 5 | Environment selector | `/workbench/` cards + `/environments/` | WIRED_READ | grants from `/api/projects` and `/api/enterprise/tasks` | per-project enterprise grants |
| 6 | Engineering shell | `/app` | VERIFIED | 101-check preview E2E | — |
| 7 | Projects / EPS | `/app/projects/` | WIRED_WRITE | project register, lifecycle HTTP tests | EPS grouping depth audit |
| 8 | WBS | `/app/wbs/` | VERIFIED | preview E2E WBS scenarios | — |
| 9 | Activities | `/app/activities/` | VERIFIED | preview E2E table/columns/grouping | — |
| 10 | Activity details | `/app/activities/` | VERIFIED | preview E2E details tabs | — |
| 11 | Relationships / network | `/app/activities/` | VERIFIED | preview E2E network + trace logic | — |
| 12 | Gantt | `/app/activities/` | VERIFIED | preview E2E Gantt/bar styles/data date | — |
| 13 | Resources / assignments | `/app/resources/` | WIRED_WRITE | assignment repositories + tests | browser proof |
| 14 | Calendars | `/app/calendars/` | WIRED_WRITE | calendar HTTP tests | browser proof |
| 15 | Reports / tracking | `/app/reports/`, `/app/tracking/` | WIRED_READ | report/print field selection tests | full report catalog |
| 16 | Enterprise dashboard | `/enterprise/` | MISSING (dashboard) | route mounts the task center instead | dashboard + portlet registry |
| 17 | Portfolio / executive | `/enterprise/portfolio/` | MISSING | no route | reads model + scorecards |
| 18 | Enterprise projects | `/enterprise/projects/` | MISSING | no route | authorized register + EPS view |
| 19 | Organization & access | `/enterprise/organization/` | MISSING | identity APIs exist, no page | org/access UI |
| 20 | Team & task center | `/enterprise/` | WIRED_WRITE | task API + tests + revision guard | route rename to `/enterprise/tasks/` |
| 21 | Workflow studio | `/enterprise/workflows/` | MISSING | no route | versioned workflow model |
| 22 | Approval center | `/enterprise/approvals/` | MISSING | no route | submission → decision flow |
| 23 | Resources & capacity | `/enterprise/resources/` | MISSING | no route | capacity read model |
| 24 | Operations & reports | `/enterprise/operations/` | MISSING | no route | job infrastructure UI |
| 25 | Project portal / documents | `/enterprise/portal/` | MISSING | no route | scoped external grants |

Totals for the initial set: **8 VERIFIED, 4 WIRED_WRITE, 4 WIRED_READ, 9 MISSING**.

## 5. Work sequence from this revision

1. **Entry flow (done here):** `/workbench/` route, session-gated server entry, ten locales, grant-driven environment cards, login default target.
2. **Engineering incremental completion:** promote WIRED_READ rows to WIRED_WRITE where APIs exist (resources, calendars, tracking/reports), then to VERIFIED with browser evidence; keep the single shell.
3. **Enterprise route foundation:** mount the fourteen missing routes as real pages with their own navigation, loading/empty/error/permission states, driven by versioned contracts — never as Engineering copies.
4. **Field and dialog audit:** complete the per-field matrix rows (currently one surface fully audited, 66 engineering and 15 enterprise surfaces marked `NOT_AUDITED`).
5. **Help wiring:** every audited component gets its direct HTML Help topic; no topic list page alone counts.
6. **Integration contract:** implement the shared contract in `docs/architecture/CUBI_TWO_ENVIRONMENT_INTEGRATION_CONTRACT.md`; endpoints that do not exist stay `UNVERIFIED`.

## 6. Honest boundaries recorded for the product owner

- The 25-page initial delivery is **not complete**: nine Enterprise surfaces still have no route. This plan does not claim otherwise.
- The field-level audit is complete for one Engineering surface only.
- Browser screenshots exist for the public site and the Engineering workspace; they do not exist yet for `/workbench/` or Enterprise beyond `/enterprise/`.
- Changing the default post-login target from `/app?view=live` to `/workbench/` was **not** done for server-side redirects; only the direct `/login` visit now lands on `/workbench/`. Deep links keep their requested target.
