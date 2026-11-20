# CUBISITE PR chain and deployment status (2026-11-20)

This note records the real dependency structure of the CUBISITE pull requests, the
correct base branch for each one, and the difference between a code failure and a
deployment-infrastructure failure. It exists so review and merge happen in one
predictable order and so a rollback can target a single increment.

## Dependency graph

The increments were developed as a linear chain on top of `main`
(`ae6e72e48be624c841b579fb9a54dcc36890b99d`). Each branch contains every commit of
the branch above it; the diffs below are the *unique* commits, measured against the
immediate parent.

| Order | PR | Branch | Base (after retarget) | Unique commits | Files changed |
| --- | --- | --- | --- | --- | --- |
| 1 | #2070 | `feat/cubi-p0-slice1-single-shell-integration` | `main` | `eddcdf9`, `e88df9f` | 12 |
| 2 | #2071 | `feat/cubi-p2-p4-localized-public-site` | `feat/cubi-p0-slice1-single-shell-integration` | `458d27c`, `5b0f751`, `2e0c9c2` | 137 |
| 3 | #2072 | `feat/cubi-p1-help-traceability` | `feat/cubi-p2-p4-localized-public-site` | `6bcfeb2` | 11 |
| 4 | #2073 | `feat/cubi-p3-capability-contract` | `feat/cubi-p1-help-traceability` | `c8b6aa9` | 7 |
| 5 | #2074 | `feat/cubi-p5-hardening` | `feat/cubi-p3-capability-contract` | `8ca5218` | 5 |
| 6 | #2075 | `feat/cubi-r0-baseline-help-reference` | `feat/cubi-p5-hardening` | `2e1564f`, `8d3e858` | 11 |
| 7 | #2076 | `feat/cubi-r2-global-admin` | `feat/cubi-r0-baseline-help-reference` | `73f15ac`, `192036c`, `ad47fc9`, `f4ade7c` | 15 |
| 8 | #2077 | `feat/cubi-r3-ten-locales` | `feat/cubi-r2-global-admin` | `8302980`, `5e48f8d`, `f515e99` | 40 |
| 9 | #2078 | `feat/cubi-r4-public-pages` | `feat/cubi-r3-ten-locales` | `3d519c5`, `1074889`, `e5ec850`, `e0c84cc`, `8cc98bf`, `84dc26f`, `5ba3487`, `2b2f2ac` | 128 |
| 10 | #2079 | `feat/cubi-r5-contextual-help` | `feat/cubi-r4-public-pages` | `93369b8` | 11 |
| 11 | #2080 | `feat/cubi-r6-capability-matrix` | `feat/cubi-r5-contextual-help` | `d7fc646` | 8 |

Each PR previously targeted `main` while containing all of its ancestors. That is
what produced the appearance of duplicate commits and one ambiguous giant diff.
The bases are now the immediate parent branch, so `gh pr diff <n>` shows only that
increment. Merging in the order above never replays a commit: when a parent lands on
`main`, GitHub recomputes the child against the advanced `main`, and the child diff
is unchanged because it is a strict descendant.

Rollback: reverting one merge on `main` removes exactly that increment; the later
branches remain descendants of the reverted history only until they are merged, so
revert in reverse order if several increments must be withdrawn.

R4 (#2078) adds no route: it fills the seventeen routes that every non-Persian
locale previously redirected to English, so the published inventory stays at 25
documents per locale and the route matrix does not change.

R5 (#2079) adds no page either: it compiles the existing Help and feature
traceability into browser-safe registries and makes the contextual assistant cite
only what those registries record, so every locale answers with the same four
resolution levels.

R6 (#2080) is documentation and its generator: it adds no runtime path. The matrix and the
JSON registry are rendered from the committed Help registry by `npm run cubisite:matrix`, so
they cannot claim a topic the assistant would not cite.

## Validation per increment

| PR | Validation run on its own head |
| --- | --- |
| #2070 | `npm run typecheck`, `npm test`, `npm run build` (web) |
| #2071 | ten-locale public site tests, route count, `npm test`, `npm run build` |
| #2072 | `tests/test_help_reference.py`, traceability render |
| #2073 | `capability-catalog.test.ts`, `npm test` |
| #2074 | `public-site-hardening.test.ts`, responsive audit |
| #2075 | `pytest tests/test_help_reference.py`, `scripts/verify_postgres_persistence.py` (7/7 on PostgreSQL 14.24) |
| #2076 | `pytest tests/test_global_administration*.py` with PostgreSQL (8 passed), `npm test` (1206 passed), `npm run typecheck`, `npm run build` |
| #2077 | `npm test` (1208 passed), `npm run typecheck`, `npm run build` on `5e48f8d`: ten-locale catalogs, full shared-sentence coverage, ten-locale Intl date/number/collation tags; German 25-route publication on `f515e99` |
| #2078 | `npm test` (1209 passed), `npm run typecheck`, `npm run build` on `2b2f2ac`: all ten locales publish the 25 approved routes, localized headlines, canonical and hreflang alternates, no dangling internal link |
| #2079 | `npm test` (1221 src + 15 preview passed), `npm run typecheck`, `npm run build` on `93369b8`: registry parity against both traceability sources and the capability contract, direct/parent/inherited/internal-docs resolution, ten-locale labels |
| #2080 | `npm test` (1229 src + 15 preview passed), `npm run typecheck`, `npm run build` on `d7fc646`: matrix renders from the Help registry; 53/53 PDF pages and 69/69 official topics reconciled |

CI for #2076 on the final head `ad47fc9`: `typecheck (apps/web)` pass, `web` pass,
`postgres` pass, `Vercel – cubi-web-preview` pass.

## Vercel projects

| Project | Status | Meaning |
| --- | --- | --- |
| `cubi-web-preview` | passing | The supported Preview channel. Builds `apps/web` and serves the assembled site and WSGI functions. |
| `consttruction-pm-platform-web` | failing before build | Legacy project whose GitHub connection is broken. The check reports `Deployment failed.` with no deployment URL. |
| `consttruction-pm-platform-public` | failing before build | Same legacy Git connection failure. |

The two legacy failures are infrastructure, not code:

- There is no deployment URL or build log to read; a build failure would produce a
  deployment record and a log.
- The exact build commands were run locally on the same head and both succeeded:
  - root project: `bash scripts/vercel_build.sh` → `public/` assembled (9.7 MB).
  - `apps/web` project: `node scripts/vercel-project-build.mjs` → `vercel-site/`
    validated (116 HTML files) and the runtime staged.

Required owner action to remove the red checks: re-authorize the GitHub integration
for the two legacy Vercel projects, or delete/disable those projects and keep
`cubi-web-preview` as the only Preview deployment. No code change can repair a
broken Git link. Until then, code-test failures and these infrastructure failures
must not be conflated.
