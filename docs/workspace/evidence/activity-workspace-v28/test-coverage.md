# V28 Test Coverage

- Base HEAD at mission start: `b3df87eb6` (tree clean, CI 10/10).
- V28 code commit: **`2b7d035a1fc459ea71f8563bb8e285b218aa957f`**; the lookahead and
  theme suites were re-run after the commit and record this SHA.
- All tests ran locally in Qoder Desktop with isolated ports/databases. No Vercel,
  no deployment, no production database.

## 1. Code and unit

| Command | Result |
|---|---|
| `npm run typecheck` | 0 errors |
| `npm run build` | success |
| `npm test` | **1178 / 1178** source tests + **15 / 15** preview-server tests, 0 failed |
| `npx tsx --test src/workspace-activity-filters.test.ts` | 17 / 17, including the new blank-value negative-criteria test |

## 2. Browser E2E

| Suite | Port / DB | Result | Key evidence |
|---|---|---|---|
| `activity-lookahead-v28` | 4198 / `v28-lookahead.sqlite3` (fresh) | **PASS** | exact PDF recipe (Start within CD…CF+6w AND Activity % Complete != 100), 10/14 matched, Replace applied 10 rows, saved and reloaded, 0 schedule writes |
| `activity-filters-v26` | 4198 / `v28-filters.sqlite3` (fresh) | **PASS 14/14** | full filter regression after semantic/label change |
| `theme-acceptance-v28` | 4199 / `v28-themes.sqlite3` (fresh) | **PASS** | six distinct skins, Graphite 13.65:1 and Midnight 14.14:1 row contrast, midnight persisted after reload, classic restored |
| `workspace-responsive-v26` | 4199 / same DB | **PASS 11/11** | 1280×720, 1366×768, 1920×1080, 844×390, RTL, splitters, no schedule writes |

Evidence files: `lookahead-filter.json`, three lookahead screenshots,
`theme-acceptance.json`, seven theme screenshots, and the refreshed
`workspace-responsive-v26-2026-11-18` directory.

## 3. Backend

No backend change was made in V28. The V27 results remain the latest verification:
30 targeted Python tests passed; broad suite 4676 passed / 224 skipped / 4
Windows-environment failures (`resource`, `pypdf`, POSIX `/tmp`).
They must be re-run for the final V28 commit if any backend file changes.

## 4. Suite hygiene

- Every run used a dedicated port and fresh SQLite database.
- Chrome is stopped and the process exits explicitly; exit codes were captured
  (all 0 for the runs above).
- The first lookahead attempt failed on a real product defect (blank values under
  negative criteria) and the second on an over-broad "no writes" assertion that
  counted the documented layout save. Both are recorded, not hidden.

## 5. Not covered in this stage

- A real 409 conflict in the preview runtime.
- Headed-browser Full Screen.
- Steps/Notebook/Codes/document writes (no HTTP contract).
- 1440×900 theme screenshots (Classic 1440 evidence exists from V26).
- Full line-by-line verification of every one of the 264 PDF topics; the inventory
  is complete, the per-row comparison is staged and partially recorded.
