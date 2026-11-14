# SCH-001 typed schedule options and Data Date — 2026-11-14

- **Tested code:** `41d4f267` (`test(schedule): prove typed options persist and bind to the snapshot`, PR #1963).
- **Requirement:** the Schedule dialog/window must expose typed inputs, persist every calculation option, and bind the exact stored options into a calculated schedule snapshot.
- **Audit result:** already wired, now browser-proven.
  - `apps/web/src/schedule-cycle.ts` renders the settings form from `catalog.schedule_options_schema`.
  - `src/construction_pm/scheduling_code_reference_api.py::_safe_setting_schema` derives one entry per `ScheduleOptions` field from the dataclass type and default: enum → select, `date` → date input, bool → checkbox, number → numeric input, `resource_list`/`priority_list` → JSON textarea, otherwise text.
  - The panel writes mode, calendar reference, calendar system, project start/finish (Data Date), leveling priority and every generated option through `POST /api/projects/{id}/p6/schedule/settings` with `expected_record_revision`; dates switch between Gregorian and typed Jalali with fail-closed parsing.
  - The API requires `PROJECT_SCHEDULE`, honours the checkout lease, validates the stored calendar reference, rejects unknown fields and stale revisions, and returns the re-read DTO.
  - `AuthoritativeScheduleInputComposer.compose` re-reads the stored settings and copies `schedule_options` into the hashed snapshot payload, so an option change changes the snapshot identity.

## Browser assertions added

`apps/web/e2e/preview-e2e.mjs` (new recorded check `typed schedule options persist and bind to the next snapshot hash`):

1. The form renders `[data-option="maximum_multiple_float_paths"]`, `[data-option="min_float_to_preserve"]` and `[data-option="data_date"]`.
2. Publish a baseline snapshot and record its hash.
3. Save `maximum_multiple_float_paths=3`, `min_float_to_preserve=2`, `data_date=2026-09-28` through the real form; the status reads `Settings saved.` and `record_revision` advances.
4. `GET /p6/schedule/settings` returns exactly those values (`data_date` as the canonical ISO date) and the advanced revision.
5. Publish again: the snapshot hash differs from the baseline (baseline `658c9d34…`, changed `1e772e85…`), proving the options are part of the snapshot identity.
6. Restore the seed defaults so later checks keep the original calculations.

Evidence details are in `evidence.json` under `schedule_options` and `persistence.settings`.

## Evidence in this bundle

- `evidence.json` — full suite result at `git_head` `41d4f267c24dde9b492adaaab86f54d8eda0f2fd`, 98 checks passed, 52 screenshots, zero uncaught exceptions and zero API 5xx (two deliberate console errors from stale-write negative scenarios).
- `06-settings-calendar.png` — real settings form with the stored project calendar and revision.
- `07-schedule-results.png` — authoritative snapshot results and hash after a run.
- `tests.txt` — post-merge commands and results.

## Limits

- Multi-project/external-project and resource-leveling options (`include_external_res_ass`, `level_all_resources`, `priority_list`, …) persist and enter the snapshot hash but their calculation behavior depends on capabilities not yet present (SCH-005 leveling run, multi-project float).
- The settings surface is a Schedule window panel, not the V26 modal dialog form factor.
