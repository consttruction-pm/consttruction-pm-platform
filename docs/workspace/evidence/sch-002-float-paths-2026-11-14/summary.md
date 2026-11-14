# SCH-002 CPM, float, critical path and multiple float paths — 2026-11-14

- **Tested code:** `5d923063` (`feat(schedule): render calculated float paths in the run results`, PR #1965).
- **Requirement:** the shared calculation core must produce CPM early/late dates, total and free float, critical activities and multiple float paths, and the schedule results must expose them without browser math.

## Audit

- `src/construction_pm/scheduling/forward_pass.py` implements the forward pass (all relationship types, lags, calendars, constraints, Data Date fallback to project start), and `scheduling/schedule.py` runs the backward pass, float calculation, criticality (float threshold, longest path, open-ended option) and `_multiple_float_paths`.
- `src/construction_pm/backend_p0/authoritative_schedule_query.py` returns start/finish, early/late dates, duration, total/free float, critical and `float_path`/`float_path_order`.
- `apps/web/src/workspace-model.ts::applyAuthoritativeScheduleFacts` maps those facts into the activity cells `activity.early_start`, `activity.early_finish`, `activity.late_start`, `activity.late_finish`, `activity.total_float`, `activity.free_float`, `activity.float_path`, `activity.float_path_order` and `activity.is_critical`, all present in `p6_field_registry.py`.
- The Run Schedule result table previously dropped the float-path fields. It now renders **Float path** and **Float path order** columns (en/fa) whenever the authoritative response carries them, with `data-float-path`/`data-float-path-order` cells. Missing values render as an em dash; the browser computes nothing.

## Browser proof

`apps/web/e2e/preview-e2e.mjs` recorded check `multiple float paths are calculated and rendered per activity`:

1. Enable `multiple_float_paths_enabled`, set `maximum_multiple_float_paths=2`, save through `POST /p6/schedule/settings` (revision advances to 5).
2. Publish a snapshot and query the authoritative schedule.
3. Assert the result headers include `Float path` and `Float path order`.
4. Assert every activity carrying a path has a positive integer path and order; observed rows: `A100 path 1 order 1`, `A110 path 1 order 2`, `A120 path 1 order 3`, `A130 path 1 order 4`, `A145 path 2 order 1`.
5. Restore the seed defaults.

The suite also keeps the pre-existing CPM assertions: 14 authoritative rows, a substantial snapshot hash, A130 fully populated, and deterministic results after a settings round-trip. Full run at `5d923063`: 99/99 checks, 53 screenshots, zero uncaught exceptions and zero API 5xx.

## Unit and server coverage at the same code

- `tests/scheduling/test_forward_pass.py` (all relationship types, lag calendars, determinism, cycles, expected finish, activity-scoped resolvers).
- `tests/scheduling/test_schedule.py` (backward pass, zero float on the critical chain, float threshold, open-ended criticality, longest-path criticality, multiple float paths).
- `tests/scheduling/test_multi_project_float.py`, `test_oos_policy.py`, `test_out_of_sequence.py`, `test_authoritative_schedule.py`, `test_authoritative_schedule_batch.py`.
- Python `4290 passed, 194 skipped`; Web `1151 + 14` pass; `tsc` + esbuild clean.

## Evidence in this bundle

- `evidence.json` — full suite result at `git_head` `5d9230636be2c086d987f4b58b50ced1bf3ae705`, 99 checks, 53 screenshots.
- `06-settings-form.png` — the real schedule settings form that carried the float-path options.

## Limits

- **External Version 26 fixture comparison is `BLOCKED_EXTERNAL`:** no licensed V26 output fixture/schedule export is available in the repository, so parity is asserted against the documented V26 behavior catalogue and the internal full-dataset CPM/float/multi-path tests rather than an external binary baseline.
- The Run Schedule table shows only start/finish/duration/total float/float path/critical; early/late dates, free float and diagnostics are available through the grid columns and the schedule query rather than this table.
