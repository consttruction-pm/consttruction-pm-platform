# CUBI — integration blockers

Audited at `0014928bf`; updated by the Workbench delivery and again on
2026-11-21 (`feat/cubi-entry-enterprise-operational`, PR #2089). Each blocker
states impact, the contract that unblocks it, and what can proceed independently.

## Blocker status after the V26 entry/operations increment

| # | Blocker | Status | Impact | Contract / decision needed | Work that continues anyway |
|---|---|---|---|---|---|
| B1 | Enterprise routes under `/enterprise/*` were not mounted | **Resolved** | — | — | All 20 routes now served under `/cubi/*` by `enterprise.html`; `/enterprise` answers `308` to `/cubi/` |
| B2 | Production composition mounts only `EnterpriseTaskHttpMiddleware`; the `/api/enterprise/{kind}` workbench store is preview-only | **Open** | Dashboards, risks, documents, EPS, timesheets, notifications, settings, forms, directory would 404 in the production runtime even though the UI is complete | Merge the production composition change (PR #2068 is the open runtime activation PR and must not be disturbed) | Preview runtime verification; UI and contracts remain valid |
| B3 | No Engineering read model for schedule, EVM or capacity | **Open** | Portlet/portfolio/EVM routes answer `503 ENGINEERING_SOURCE_NOT_CONNECTED`; no number is displayed | Versioned, revision-stamped read model served by Engineering | Dashboard/portfolio layout, decisions, registers, tasks, approvals |
| B4 | No external notification delivery worker | **Open (scope)** | Notification *records* are stored and readable; no proof that email/webhook delivery occurred | Delivery contract with retry/audit owned by the notification service | Notification register, indicator, approvals |
| B5 | No workflow scheduling/escalation engine | **Open (scope)** | Workflow drafts and publish validate the graph; no timed escalation or approval routing | Workflow execution contract | Workflow studio, approval queue |
| B6 | External access grants for the Project Portal do not exist | **Open** | Portal cannot issue scoped/expiring links | Grant contract (scope, expiration, revocation, audit) | Internal project pages |
| B7 | Vercel token absent in this environment | **Open (external)** | Legacy Vercel projects keep failing and the stable alias cannot be repointed | Vercel account access | GitHub Pages deployment and `cubi-web-preview` remain verifiable |
| B8 | `cubi-web-preview` is SSO-protected | **Open (external)** | Anonymous browser verification of the Vercel alias is impossible from CI | Vercel access token or SSO bypass for the preview domain | Local production-stack browser E2E |
| B9 | Production global-admin account not provisioned | **Open (external)** | First-admin provisioning on production needs an operator credential | One-time provisioning run with operator secrets | `/admin` surface verified locally against PostgreSQL |
| B10 | Field-level audit incomplete | **Open** | Page-level matrices and Help URLs exist; per-field rows are still partial | Extraction pass per window using `v26-complete-window-component-catalog.md` | Page-level matrices and Help URLs (delivered) |
| B11 | PR #2068 and #2048 overlap Scheduling Core and Activities | **Open (coordination)** | Any change in those paths would collide with another owner | Explicit coordination or merge of #2068/#2048 first | Entry, Enterprise, docs and non-Activities Engineering work |
| B12 | Preview port 4180 was occupied by an unrelated stale server | **Workaround** | Evidence run used 4191; no product change | Free the port or document the assigned port | Same shared preview implementation; no parallel preview added |

## Resolved since the first audit

- Enterprise routes: all 20 data pages are served and reachable.
- Entry flow: `/login` is canonical in the preview, `/workbench/` is the
  post-login default, hostile `next` values fall back safely, `/enterprise`
  never serves the Engineering shell.
- Session sign-out: `DELETE /api/session` revokes the preview session; both
  shells return to `/login`.
- Screenshots: entry flow, 20 data routes and the 1366/1280 widths are captured
  in `artifacts/enterprise-preview/v26/`.

## What is explicitly *not* a blocker

- Deep links: `/app?project=…&view=live` works and is verified.
- Locale coverage for the entry flow: ten locales are shipped for login and the
  workbench; Enterprise dictionaries cover all ten locales with English fallback.
- Help topics: the registered direct HTML URLs resolve (sampled HTTP 200); the
  remaining work is per-component wiring, not finding sources.
