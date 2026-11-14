# RES-004 stored usage profile — 2026-11-14

- **Tested code:** `14e3c16f` (`feat(resources): chart the stored usage profile by timescale`, PR #1961).
- **Requirement:** the Resource Usage tab must expose the stored, time-phased usage without inventing bucket widths or spread types and without running schedule/leveling math in the browser.
- **Change:** the Usage tab now renders a **Stored usage profile** chart above the existing comparison table.
  - `apps/web/src/resource-usage.ts` adds `RESOURCE_USAGE_TIMESCALES` (`day`, `week`, `month`), `resourceUsageBucketBounds` and `groupResourceUsageBuckets`.
  - A bucket sums only the stored period values whose `period_start` falls inside it, using exact decimal addition. A stored amount is never spread across days and no bucket width, spread type or overtime is inferred.
  - Weeks are Monday–Sunday in UTC; months run first-to-last day. Invalid stored dates stay in their own bucket instead of being dropped.
  - Overallocation stays evaluated per stored period in the existing table; a bar is marked `is-overallocated` only when one of its stored periods is overallocated.
  - The chart exposes `data-resource-usage-chart`, `data-timescale`, `data-resource-usage-bar` with `data-bucket-start/end/demand/periods`, and a `data-resource-usage-timescale` Day/Week/Month select. English and Persian labels are both covered.
- **Boundary:** assignment period rows still carry only `period_start`, `units` and `cost`; the chart is a display grouping of those stored rows, not a time-phased spread, and the hint says so in both locales.

## Evidence in this bundle

- `resources-v26.json` — full browser report; `testedCodeSha` = `14e3c16f`, 14/14 scenarios, zero page exceptions, console errors and API 5xx.
- `05b-usage-profile-day.png` — Day buckets after the real seed: `2026-09-30` (16 units, overallocated, red) and `2026-10-16` (4 units, within).
- `05c-usage-profile-month.png` — after switching to Month: `2026-09` (16, overallocated) and `2026-10` (4, within).
- `13-usage-profile-fa.png` — Persian RTL chart at 1280×720 with `روز/هفته/ماه` options and the Persian no-spread hint.
- `12-resource-1280x720.png` — Resources window layout at the same viewport.
- `tests.txt` — commands and results at the tested code.

## Scenario assertions (browser, fresh SQLite preview)

`apps/web/e2e/resources-v26.mjs` scenario `05b` seeds two real assignments and three stored periods, resolves capacity `8` for `2026-09-30` through the existing service, then asserts:

| Timescale | Bars (start → end, demand, stored period starts, overallocated) |
|---|---|
| Day | `2026-09-30 → 2026-09-30`, 16, 1, yes; `2026-10-16 → 2026-10-16`, 4, 1, no |
| Week | `2026-09-28 → 2026-10-04`, 16, 1, yes; `2026-10-12 → 2026-10-18`, 4, 1, no |
| Month | `2026-09-01 → 2026-09-30`, 16, 1, yes; `2026-10-01 → 2026-10-31`, 4, 1, no |

Scenario `12` repeats the chart in Persian RTL and asserts the `روز/هفته/ماه` options, both bar facts and the Persian hint.

## Limits

- No overtime, no stored bucket-width/spread-type input, no actual/remaining/forecast spread profiles, and no leveling run/apply; those remain outside this slice (see `docs/workspace/architecture/p6-resource-curve-shift-contract-request.md`).
- The chart counts stored period **starts**: two assignments sharing one start appear as one period in a bucket (and as two assignments in the table row).
