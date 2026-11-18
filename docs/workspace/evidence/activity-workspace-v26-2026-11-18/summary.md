# Activity Workspace — 2026-11-18 increment

Issue #2047, PR #2048, branch `feat/2047-activity-workspace-v26`.

## Delivered in this increment

1. **Activity Details General tab edit path** (increment 1)
   - `apps/web/src/workspace-activity-general.ts` and its 9 unit tests.
   - Loads the Activity Master record, writes only changed fields with `expected_revision`,
     surfaces `REVISION_CONFLICT`, and never derives schedule facts in the browser.
   - Editable fields: name, activity type, duration type, percent-complete type, leveling
     priority (Top/High/Normal/Low/Lowest) and cost account.
   - Browser proof: `activity-general-edit-v26.mjs` — EN 1366x768, FA RTL 1280x720 and
     1920x1080, reload persistence and restore of both the name and the leveling priority.

2. **Activity Details tab keyboard model** (increment 2)
   - ArrowLeft/ArrowRight, Home and End move focus, `aria-selected` and the visible panel
     together, wrap at both ends, and follow the rendered text direction in Persian RTL.
   - Proof inside `activity-details-v26.mjs` (EN and FA), report keys `keyboard` and
     `keyboardRtl`.

3. **Acceptance matrix**
   - `acceptance-matrix.md` in this directory: 18 required columns, 43 items, exact status
     vocabulary, classification of every gap, owner and next action.

## Verification (2026-11-18, this branch)

- `npm run typecheck` — clean.
- `npm test` — 1177 source tests + 15 preview-server tests, 0 failed.
- `npm run build` — clean.
- `node e2e/activity-details-v26.mjs` — pass: 17 tabs, keyboard EN + FA, three write paths,
  unauthorized state, stale-response guard; no console errors, no API failures.
- `node e2e/activity-general-edit-v26.mjs` — pass: 6/4/4 option catalogues, revision-guarded
  PATCH, reload persistence, restore, RTL 1280/1920.
- Evidence images:
  - `../activity-details-tabs-v26-2026-11-18/` (EN, FA keyboard)
  - `../activity-general-edit-v26-2026-11-18/` (EN, FA)

## Not verified in this run

- All other November-15 Activity suites listed in `v26-traceability.md` were not re-run on
  this head; their matrix rows stay `پیاده‌سازی‌شده ولی آزمون‌نشده`.
- Grid refresh after a Details edit and the `percent_complete_type` table cell remain
  `BLOCKED` on files owned by other active PRs.
- The approximately 815-page supplied PDF is **MISSING / VERIFY**.
