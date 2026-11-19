# V31 — Test results

- Tested code SHA: `894d435678796b00113d0a79855c2d4fd3314183`
- Report head: `db4fb6281` (public CSS copy only)
- PR: #2048
- Date: 2026-11-19
- Environment: local Qoder Desktop, Windows, Node 26.10.0, Python 3.11.4, local full-stack preview on `127.0.0.1:4300`.

## Web unit tests

```
cd apps/web
npm test
```

Result: **1214 pass, 0 fail** (`src/*.test.ts` + `preview-server.test.mjs`). New suites:
- `workspace-activity-copy.test.ts` — 5 pass
- `workspace-activity-renumber.test.ts` — 6 pass
- `workspace-activity-fill.test.ts` — 3 pass
- `workspace-desktop-shell.test.ts` — menu icon contract includes `edit.renumber`

Type check: `npx tsc --noEmit` — clean.

Build: `npm run build` — `main.bundle.js` produced from the committed tree.

## Python tests

```
py -3 -m pytest tests/test_activity_master_repository.py tests/test_p6_activity_master_http_routes.py -q
```

Result: **46 passed**. Added:
- `test_activity_master_renumber_moves_every_reference_and_can_reuse_ids` — relationship, WBS, code, step, expense and document JSON references follow the new ID; a vacated ID can be reused by another selected activity.
- `test_activity_master_renumber_rejects_collisions_and_stale_revisions` — 409-class guard behavior.
- `test_activity_renumber_route_moves_ids_and_enforces_revision` — HTTP 200 mapping, old identity gone, stale revision 409.

Compile check: `py -3 -m py_compile` on all three changed Python modules — clean.

## Browser E2E (real preview, real SQLite)

```
CUBI_TESTED_CODE_SHA=894d435678796b00113d0a79855c2d4fd3314183 \
CUBI_PREVIEW_URL=http://127.0.0.1:4300 node e2e/activity-v31-renumber-copy.mjs
```

Result: **pass**, 6 steps, 7 screenshots:
1. Renumber preview (`V31A878202` → `V31A878212`, count 1).
2. Renumber applied; old ID gone; activity name and FS relationship follow the new ID.
3. Copy Options: activity code and expense copied, Steps cleared, relationship to an uncopied activity retained.
4. Fill Down preview for Original Duration = 9.
5. Fill Down persisted on the target.
6. Hide All → Show All curtains with reload persistence.

Regression:

```
CUBI_TESTED_CODE_SHA=894d... node e2e/activity-edit-v30.mjs
→ pass, 10 steps, 6 screenshots

CUBI_TESTED_CODE_SHA=894d... node e2e/gantt-attachments-v30.mjs
→ pass, 11 steps, 8 screenshots
```

The Gantt attachments suite requires a freshly reset preview database; an earlier run against a database modified by the V31 suite failed its “fresh database” expectation, and passed after `--reset`. This is a fixture-precondition issue, not a product failure; the reset run is the recorded evidence.

## Pull-request CI

Head `db4fb6281` passed every PR check:

- `web` (typecheck, unit tests, build, Pages assembly, preview smoke, browser E2E)
- `typecheck (apps/web)`, `typecheck (apps/client-sync)`, `typecheck (apps/desktop)`, `typecheck (apps/mobile)`
- `postgres` integration
- `test (3.11)`, `test (3.12)`, `test (3.13)`

The first push failed only on the “workspace CSS copies are identical” test because `apps/web/public/styles.css` had not received the new dialog rules; the follow-up commit `db4fb6281` synced the copy and all checks passed.

## Not run

- PostgreSQL-specific execution of `renumber` against a live database (the `postgres` CI job exercises the wider integration suite; the renumber proof here is SQLite).
- The full 6-theme × 3-size × 2-language visual matrix for the new dialogs (see `visual-regression.md`).
