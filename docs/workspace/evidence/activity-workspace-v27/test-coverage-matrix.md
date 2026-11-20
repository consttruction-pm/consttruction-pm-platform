# V27 Test Coverage Matrix — Activities Workspace

- Tested head: `b71cd61f46ebe358d1b15eee21068977b03493cf`
- Branch: `feat/2047-activity-workspace-v26`
- Environment: Hasan's Qoder Desktop on Windows 10.0.17763, local full-stack
  preview, headless Chrome (pinned `en-US`), fresh SQLite database per suite group.
- No Vercel, no external deployment, no production database.

## 1. Static and unit tests

| Command | Result | Notes |
|---|---|---|
| `npm run typecheck` | **0 errors** | After the final details/main.ts change |
| `npm run build` | **success** | `main.bundle.js` 3.1 MB, assistant 247.7 KB, landing 225.0 KB |
| `npm test` | **1178 passed / 0 failed** + **15 passed / 0 failed** | Source tests via `tsx --test`, preview server tests via `node --test`, at `b71cd61f4` |
| `tests/workspace-activity-filters.test.ts` | included in 1178 | 9 operators, ranges, built-ins, persistence |
| `tests/workspace-windows.test.ts` | included | tab reorder survives per-project restore |
| `tests/workspace-activity-general.test.ts` | included | revision guard, changed-field-only payload |
| `tests/toolbar` / `workspace-desktop-shell.test.ts` | included | menu labels EN/FA, shortcut uniqueness, disabled reasons |

## 2. Python backend

| Command | Result | Notes |
|---|---|---|
| `pytest -q tests/backend_p0/test_workspace_read_provider.py tests/test_preview_runtime.py` | **30 passed** | Includes the new `activity.percent_complete_type == "DURATION"` assertion and 21-column layout |
| Broad suite excluding 8 Windows-incompatible modules | **4676 passed, 224 skipped, 4 failed** | Failures are environment-only: `ModuleNotFoundError: resource` (POSIX-only) ×3 and a Vercel path test expecting `/tmp` on Windows |
| 8 modules not collectable on Windows | collection error | `tests/scheduling/test_benchmark_fixtures.py`, `test_free_float_closed_form.py`, `test_offline_schedule_runtime.py`, `test_scheduling_job_executor.py`, `test_time_float_execution_policy.py`, `test_time_float_parallelism.py`, `test_time_float_search.py` (`resource`), `tests/test_report_export.py` (`pypdf` absent) |

No Python failure is caused by V27. The V27 backend change is additive (one cell)
and its tests pass.

## 3. Browser E2E executed at `b71cd61f4`

All runs used `CUBI_EVIDENCE_DATE=2026-11-18` and a fresh preview database.

| Suite | Result | Key assertions | Evidence |
|---|---|---|---|
| `activity-general-edit-v26` | **PASS** | Six activity types, four duration types, four percent-complete types, five priorities; PATCH carries `expected_revision` and `leveling_priority`; details repaint; **grid re-read (`gridRefresh.refreshed = true`)**; persistence after reload; original name restored; RTL editor at 1280/1920; 0 exceptions, 0 5xx | `activity-general-edit-v26-2026-11-18/` |
| `activity-percent-complete-v27` | **PASS** | Registry label `Percent Complete Type`; column hidden → visible at index 8; stored cell `DURATION`; survives reload; hidden again to restore the layout; 0 exceptions | `activity-workspace-v27/percent-complete-column.json` + PNG |
| `workspace-responsive-v26` | **PASS 11/11** | 1280×720 no document scroll; 1366×768; 1920×1080; 844×390 own scroller; menus inside viewport; Ctrl+A from body; full screen (headless limitation recorded); splitters; RTL; no schedule write | `workspace-responsive-v26-2026-11-18/` (JSON + 10 PNGs) |

## 4. Browser E2E executed on the identical working tree (recorded HEAD `f349d474`)

These suites ran after `npm run build` with all V27 code present; only the commit
had not yet been created, so their JSON `testedCodeSha` reads `f349d474`.
Disclosed as D-V27-14.

| Suite | Result | Evidence |
|---|---|---|
| `activity-columns-v26` | **PASS 11/11** | columns dialog, applied/reloaded, RTL, 0 exceptions |
| `activity-details-v26` | **PASS** — 17 tabs, keyboard EN+FA, writes for resources/expenses/issues, empty state, unauthorized, stale response, customize | `activity-details-tabs-v26-2026-11-18/` |
| `field-chooser-v26` | **PASS 4/4** | Seeded layout has 0 available fields (new field included), Persian Add-all, reload behavior |
| `workspace-window-tabs-v26` | **PASS 11/11** | Order persisted, dirty tab, close guard, RTL 1280 |
| `toolbars-v26` | **PASS 6/6** | Command routing and disabled reasons |
| `workspace-shell-v26` | **PASS 7/7** | One shell, direct links, reload, viewer |
| `activities-v26-scenarios` | **PASS 18/18** | Filters, grouping, columns, data date, integrity |
| `workspace-visual-acceptance-v26` | **PASS 6 visual cells** (EN/FA × 1280/1366/1920) | 24 screenshots, canonical visual set updated |

## 5. Viewports

| Viewport | Covered by | Result |
|---|---|---|
| 1280×720 | responsive 01, visual acceptance, percent-complete, general edit | PASS |
| 1366×768 | responsive 02, visual acceptance, general edit | PASS |
| 1440×900 | visual evidence set (`24-splitters-1440x900`) | Captured; not re-run in V27 |
| 1920×1080 | responsive 03, visual acceptance, general edit RTL | PASS |
| 844×390 | responsive 04, 05 | PASS |

## 6. Suite health issues encountered and corrected

| Issue | Diagnosis | Resolution |
|---|---|---|
| Stale `node e2e/*.mjs` processes from earlier runs held Chrome and contended for port 4193/SQLite | Pre-existing hung suite processes; killing them was blocked by the environment classifier | Ran verification on isolated ports/databases (4194–4197) instead; did not terminate processes outside this session |
| `workspace-responsive-v26` never exited after printing results | Suite did not stop Chrome or call `process.exit` | Added explicit `chrome.stop()` in `finally` + `process.exit(0)`; reran → exit 0 |
| `field-chooser-v26` first attempt saw 17 available fields | The preceding columns suite had mutated the shared layout (`Copied First`, revision 7) | Reran on a fresh database → PASS 4/4 |
| General edit initially failed "details pane did not repaint" | Full bootstrap refresh dropped selection and the confirmation | Replaced with a project re-read that preserves the selected activity and re-applies the notice; reran → PASS |

## 7. What is not covered

- Real 409 conflict provocation in the preview runtime (unit-tested only).
- Headed-browser Full Screen transition.
- Per-theme screenshot grid.
- Activity Codes / Notebook / Steps / Document-link writes (no contracts).
- Production or external deployment (explicitly out of scope).

Evidence files are stored beside this document under
`docs/workspace/evidence/activity-workspace-v27/` and the dated `*-v26-2026-11-18/`
directories.
