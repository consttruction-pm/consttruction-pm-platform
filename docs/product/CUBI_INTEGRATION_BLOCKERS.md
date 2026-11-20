# CUBI — integration blockers

Audited at `0014928bf`, updated by the Workbench delivery. Each blocker states impact, the contract that unblocks it, and what can proceed independently.

| # | Blocker | Impact | Contract / decision needed | Work that continues anyway |
|---|---|---|---|---|
| B1 | 15 of 16 Enterprise routes are not mounted (`/enterprise/portfolio/`, `tasks/`, `approvals/`, `workflows/`, `organization/`, `operations/`, `portal/`, `integrations/`, `resources/`, `reports/`, `admin/`, `documents/`, `risks/`; dashboard content missing at `/enterprise/`) | Pages 16–19 and 21–25 of the initial delivery cannot be opened or screenshotted | Route ownership and page-level contracts per surface (portfolio read model, approval workflow model, portal grants) | Engineering completion, entry flow, task center, matrices, Help wiring |
| B2 | No portfolio read model or KPI source for Enterprise | Dashboard, portfolio and reports would need duplicate calculations, which the order forbids | Versioned read model served by the Engineering core (`UNVERIFIED` today) | Dashboards can ship without KPIs or stay `MISSING` |
| B3 | No notification API | Workbench notifications, approval alerts and workflow escalation remain absent | Notification contract (server-owned, tenant-scoped) | All read-only surfaces |
| B4 | No workflow/approval engine for Enterprise | Workflow Studio and Approval Center cannot be real | Versioned workflow model with states, transitions, revisions | Everything outside those two pages |
| B5 | External access grants for the Project Portal do not exist | Portal page cannot issue scoped/expiring links | Grant contract (scope, expiration, revocation, audit) | Internal project pages |
| B6 | Vercel token absent in this environment | Legacy Vercel projects (`consttruction-pm-platform-web`, `...-public`) keep failing and the stable alias cannot be repointed | Vercel account access | GitHub Pages deployment and `cubi-web-preview` (reference preview) remain verifiable |
| B7 | `cubi-web-preview` is SSO-protected | Anonymous browser verification of the Vercel alias is impossible from CI | Vercel access token or SSO bypass for the preview domain | Local production-stack browser E2E |
| B8 | Production global-admin account not provisioned | First-admin provisioning on production needs an operator credential | One-time provisioning run with operator secrets | `/admin` surface verified locally against PostgreSQL |
| B9 | Field-level audit incomplete | 66 Engineering and 15 Enterprise surfaces have no per-field row (Tab, Component, Field ID, API, Permission, Audit, Help topic, Test ID) | Extraction pass per window using `v26-complete-window-component-catalog.md` | Page-level matrices and Help URLs (delivered) |
| B10 | PR #2068 and #2048 overlap Scheduling Core and Activities | Any change in those paths would collide with another owner | Explicit coordination or merge of #2068/#2048 first | All entry, Enterprise, docs and non-Activities Engineering work |
| B11 | 15 of 25 initial pages still lack screenshots | Acceptance criterion 22 unmet for those pages | Browser capture run after B1 is resolved | Everything else |

## What is explicitly *not* a blocker

- Deep links: `/app?project=…&view=live` works and is verified.
- Locale coverage for the entry flow: ten locales are shipped for login and the workbench.
- Help topics: the registered direct HTML URLs resolve (sampled HTTP 200); the remaining work is wiring per component, not finding sources.
