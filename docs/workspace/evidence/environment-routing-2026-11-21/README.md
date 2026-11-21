# Environment document routing on the deployed origin

Date: 2026-11-21
Base commit: `6113255910f30dea3ddfd9ce58168c211f4f029c` (origin/main, PR #2102)
Branch: `feat/cubi-environment-routing`

## Problem

The HTTP boundary already knows how to serve three separate workspace
documents: Engineering at `/app`, Enterprise at `/cubi/*`, and the AI Workbench
at `/ai-workbench`. The deployment layer did not preserve that separation:

1. **The root Vercel entrypoint forced the Engineering shell.** `api/shell.py`
   set `PATH_INFO = "/app"` unconditionally. Any document routed through it —
   including the retired `/enterprise` address — became the Engineering shell.
2. **Two documents had no route at all.** Neither `vercel.json` rewrote
   `/cubi` or `/ai-workbench`, so the deployed origin could not reach either.
3. **The build did not stage the documents.** `scripts/vercel_build.sh` and
   `apps/web/scripts/prepare-vercel-runtime.mjs` copied only `index.html`,
   `app.html` and `login.html`; `enterprise.html`, `ai-workbench.html` and
   `ai-workbench.css` were absent from the deployed artifact. The `apps/web`
   project also had no rewrites for the two entry bundles.

The result was exactly the failure the mission forbids: an Enterprise URL that
resolves to Engineering, and environments that exist in source but cannot be
opened on the deployed origin.

## What changed

- `src/construction_pm/deployment/workspace_routes.py`: one resolver shared by
  both entrypoints. It accepts `app`, `enterprise`, `cubi/*` and
  `ai-workbench/*`, rejects dot segments and control characters, and falls back
  to `/app` for anything else. `query_without_rewrite()` removes the platform
  `__path` marker so it cannot leak into the document query or the post-login
  `next` target.
- `api/shell.py`: restores the resolved path and cleaned query before calling
  the runtime. It no longer forces `/app`.
- `apps/web/api/shell.py`: delegates to the same resolver instead of its local
  two-route map.
- `vercel.json` and `apps/web/vercel.json`: `/cubi`, `/cubi/:path*`,
  `/ai-workbench` and `/ai-workbench/:path*` rewrite to the session-gated shell
  with `no-store`; the `apps/web` project also maps the Enterprise and Workbench
  entry bundles to the flat build output.
- `scripts/vercel_build.sh`, `apps/web/scripts/prepare-vercel-runtime.mjs`,
  `apps/web/scripts/assemble-pages-site.mjs`: stage `enterprise.html`,
  `ai-workbench.html` and `ai-workbench.css`.
- `apps/web/e2e/preview-e2e.mjs`: checks both documents and both gates against
  the real preview runtime.
- `tests/test_workspace_shell_routing.py`: pins the resolver, the query
  cleanup, the shell usage and the deployment configuration.

## Verification

| Command | Result |
|---|---|
| `PYTHONPATH=src python -m pytest tests/test_workspace_shell_routing.py -q` | 8 passed |
| `PYTHONPATH=src python -m pytest tests/test_production_web_app.py tests/test_preview_runtime.py tests/test_workspace_shell_routing.py -q` | 68 passed |
| `cd apps/web && npm run build` | bundles emitted, including `enterprise-entry` and `ai-workbench-entry` |
| `CUBI_CHROME_NO_SANDBOX=1 npm run test:e2e:preview` | passed, 114 recorded checks, 57 screenshots |

New E2E record (`apps/web/e2e/artifacts/evidence.json`):

```json
{
  "name": "environments are separate documents with independent session gates",
  "enterprise_redirect": 308,
  "enterprise_home": 200,
  "enterprise_bundle": "enterprise-entry",
  "enterprise_gate": 302,
  "workbench_gate": 302
}
```

This proves, against the real preview runtime:

- `/enterprise` returns `308` to `/cubi/`, not the Engineering document;
- `/cubi/` returns the `CUBI Enterprise Workbench` document and its own bundle;
- `/cubi/enterprise/dashboard` requires a session and preserves the deep link;
- `/ai-workbench?project=p1` requires a session and preserves its deep link.

## Limits

- The deployment configuration is asserted by reading `vercel.json` and the
  build scripts; it is not a live Vercel deployment. No production deployment or
  environment change was made.
- The preview runtime uses SQLite fixtures. The PostgreSQL composition is
  unchanged by this slice.
- `/cubi/enterprise/dashboard` still requires an Enterprise entitlement role;
  an ordinary project planner is redirected to the Personal Workbench, as
  designed. The document routing fix does not grant that entitlement.
