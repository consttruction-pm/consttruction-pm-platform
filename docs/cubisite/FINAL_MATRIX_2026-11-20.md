# Final execution matrix — CUBI mission #2069

Executed on `main` at `af5a7671ce93e4302c7c393c76d68b94bacab953` (all twelve
mission pull requests merged, #2070 → #2081), plus the follow-up localization
increment recorded below.

## Merge order and result

| Order | PR | Scope | Merged commit |
| --- | --- | --- | --- |
| 1 | #2070 | P0 single canonical shell | `915da0c` |
| 2 | #2071 | P2+P4 localized public site | `65252cc` |
| 3 | #2072 | P1 Help traceability | `5010c42` |
| 4 | #2073 | P3 capability contract | `c8e1183` |
| 5 | #2074 | P5 SEO/security/responsive | `228d0f5` |
| 6 | #2075 | R0+R1 baseline + PostgreSQL proof | `7dfc311` |
| 7 | #2076 | R2 global administration | `eb28df8` |
| 8 | #2077 | R3 ten workspace locales | `9e696a3` |
| 9 | #2078 | R4 twenty-five public routes | `dfbeee5` |
| 10 | #2079 | R5 contextual assistant | `ca3c46c` |
| 11 | #2080 | R6 capability/page/Help matrix | `58b44fe` |
| 12 | #2081 | R7 structured data + idempotency | `af5a767` |

Each dependent branch was retargeted to `main` after its parent merged. Four
integration defects were found by running CI against the real base and fixed
before merge:

- R3/R4/R5/R6/R7 exported public HTML that still declared only the en/fa
  alternates (or, on R5, a stylesheet that was not mirrored): regenerated from
  the merged sources, artifact validation passes with 252 documents.
- R5 moved the Help anchor ahead of the workspace entry, so the browser E2E read
  an empty href: the check now targets `.cubi-assistant-workspace-link`.
- R5 kept the contextual-help CSS only in `apps/web/styles.css`: mirrored into
  `apps/web/public/styles.css`.
- R6/R7 carried generated HTML that conflicted with the R4 artifact: merged
  `main` and regenerated; two consecutive generator runs are byte-identical.

No mission commit was re-inserted or dropped. Shared Scheduling Core, #2068 and
#2048 were not touched.

## Matrix on the merged tree

Environment: PostgreSQL 14.24 on `127.0.0.1:5432` (role and database `cubi_r7`),
Node 22, Python 3.12, Chrome headless via CDP.

| Area | Command | Result |
| --- | --- | --- |
| Python suite + PostgreSQL | `CONSTRUCTION_PM_POSTGRES_DSN=… P6_TEST_POSTGRES_DSN=… pytest tests -q` | **5382 passed, 1 skipped** (the skip is the optional `pmcontrols` module) |
| Web unit/integration | `npm test` (apps/web) | **1237 passed** source tests + **15 passed** preview-server tests |
| Typecheck | `npm run typecheck` | clean |
| Build | `npm run build` | three bundles built |
| Public artifact | `assemble-pages-site.mjs` | validated, **252 HTML documents** |
| Public routes | sitemap | **250 URLs** = 25 routes × 10 locales |
| Generator idempotency | two consecutive runs | byte-identical, `git status` clean |
| Browser E2E | `npm run test:e2e:preview` | **101 checks**, 55 screenshots |
| Responsive audit | `public-site-responsive.mjs` | **18/18** viewports |
| Capability matrix | `npm run cubisite:matrix` | committed docs equal fresh render, C01–C35, 25 pages |
| Helper reconciliation | tests | 53/53 PDF pages, 69/69 official topics |
| Structured data | tests | every indexable page carries matching JSON-LD |
| Branding | grep of shipped site | no Oracle/Primavera/P6 branding |

## Localization status (ten locales: fa, en, de, zh, ar, fr, ja, ko, ru, tr-TR)

| Section | Surface | State |
| --- | --- | --- |
| Engineering, WBS, Gantt, Reports, Settings, Forms, Admin | workspace chrome, menus, dialogs, columns | ten locales, RTL for fa/ar, per-locale `Intl` dates/numbers/collation |
| Enterprise, Activities | same workspace catalogs | ten locales |
| Authentication | `/login` | ten locales, native selector, `dir` and `lang` per locale, choice remembered |
| Public pages, Help, Payments, Security | 25 routes × 10 locales | generated, canonical + all alternates, RTL copy where applicable |
| Assistant | launcher chrome, Help block, next-steps label | ten locales |
| Assistant | operational guidance body | reproduced from the official English Help wording; not paraphrased |

The last row is a deliberate boundary: the step-by-step guidance mirrors the
published Help text and is shown in its source language rather than re-created by
a translator. Every fixed sentence around it is localized.

## Deployment

- GitHub Pages `deploy` job on `af5a767` succeeded; `https://consttruction-pm.github.io/consttruction-pm-platform/features/` and `/de/pricing/` return 200 with the correct canonical.
- `cubi-web-preview` (main branch alias, `foroughichamshir-7811` project) serves the merged build: `/`, `/features/`, `/fa/features/`, `/de/pricing/`, `/features/scheduling/` all 200, with JSON-LD and the ten `hreflang` alternates.
- The stable alias `cubi-web-preview.vercel.app` still resolves to an older deployment (all `/features/` routes 404). It is a domain/project assignment in the Vercel dashboard, not a code defect; no Vercel token is available in this sandbox.
- The legacy projects `consttruction-pm-platform-web` and `consttruction-pm-platform-public` still fail their PR deployments. They are not the reference project and their logs require dashboard access; they do not gate the merge.

## Credential-dependent remains

- Provisioning the first production Global Admin needs the production DSN. The
  supported command is
  `CONSTRUCTION_PM_DATABASE_URL=… python scripts/provision_workspace.py user --tenant platform-owner --email … --roles global_admin --password-stdin`;
  it was executed against local PostgreSQL and the account logged in.
- Reassigning the stable Vercel alias needs Vercel account access.
