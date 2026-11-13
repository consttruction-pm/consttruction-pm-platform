# ACT-015 — Activity Usage Spreadsheet and Activity Usage Profile (2026-11-13)

Contract: `cubi-activity-usage-v26.v1`
Tested code: `218977dc72405061b4fc3d0f228db7e70df7e140` (squash merge of #1859)
Suite: `apps/web/e2e/activity-usage-v26.mjs`
Report: `activity-usage-v26.json` (11/11 scenarios, 0 exceptions, 0 console errors, 0 failing API responses, 0 interaction writes)
Screenshots: `01`–`10b`

## Help topics

- [The Activity Usage Spreadsheet](https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_activity_usage_spreadsheet.htm) — the spreadsheet displays activity data in a spreadsheet format; it is split into an Activity Table pane and a timescaled data pane, can filter, group and sort, and can show past-period actual values.
- [Display the Activity Usage Spreadsheet](https://docs.oracle.com/cd/G48902_01/client_help/en_US/display_the_activity_usage_spreadsheet.htm) — View, Show on Top/Bottom, Activity Usage Spreadsheet, or the Layout Options bar / Bottom Layout toolbar.
- [The Activity Usage Profile](https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_activity_usage_profile.htm) — cost or unit values over a timescale as vertical bars, for all activities or the activities selected in the Activity Table, Activity Usage Spreadsheet, Gantt Chart or Activity Network; bar value labels can be shown.
- [Display the Activity Usage Profile](https://docs.oracle.com/cd/G48902_01/client_help/en_US/display_the_activity_usage_profile.htm) — View, Show on Bottom, Activity Usage Profile; the numbers on the left correspond to the vertical bars.
- [Define the Activity Usage Profile](https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_the_activity_usage_profile.htm) — the Data tab selects Cost or Units and the filters for the data included in the profile.
- [Customize Activity Usage Spreadsheet columns](https://docs.oracle.com/cd/G48902_01/client_help/en_US/customize_activity_usage_spreadsheet_columns.htm) and [Select Activity Usage Spreadsheet fields](https://docs.oracle.com/cd/G48902_01/client_help/en_US/select_activity_usage_spreadsheet_fields.htm) — left-pane columns and right-pane fields are user-selectable (see Known limits; tracked with ACT-018/ACT-019).

## Environment

- `PYTHONPATH=src python3 -m construction_pm.preview --web-root apps/web --host 127.0.0.1 --port 4184 --database /tmp/cubi-usage-e2e.sqlite --reset`
- Fixture: Riverside Pump Station Upgrade (`preview-rps-01`), data date 2026-10-12, tenant `cubi-preview-tenant`, resource `RPS-CIVIL-CREW`.
- Fixture facts are written through the authoritative API, not seeded into the DOM:
  - assignments `AS-USE-A130-1` (8 h / 800), `AS-USE-A130-2` (2 h / 200.25), `AS-USE-A160` (10 h / 1040.50), `AS-USE-A170` (3 h / 110), each with `contract_version: p6-resource-write-api.v1`;
  - periods A130 Oct 5/500 + Nov 3/300, A160 Oct 4/400 + Dec 6/640.50, A170 Nov 1/90;
  - scenario 07 adds A170 2027-01-01 2/20 through the same write API outside the tracked interaction window.
- Viewports: en/LTR 1366×768, en/LTR 1920×1080 and fa/RTL 1280×720.

## Scenarios

| # | Proof | Result |
|---|---|---|
| 01 | Before any period is stored, Bottom Layout keeps `Activity Usage Spreadsheet` and `Activity Usage Profile` disabled (and the View menu commands are disabled) instead of drawing a fabricated zero view. | pass |
| 02 | After the write-API seed and a reload, `GET /p6/resource-assignment-periods` enables both options; the spreadsheet heading, read-only source note and 3 stored period columns are present. | pass |
| 03 | Units spreadsheet: A130 `5 / 3 = 8`, A160 `4 / – / 6 = 10`, A170 `– / 1 / – = 1`; period totals `11 / 4 / 6`; grand total `21`; no editable control in the data area; the source note names the stored period count and says nothing is derived from activity dates. | pass |
| 04 | Cost metric: A130 `700.25 / 300`, A160 `400 / – / 640.5`, A170 `– / 90 / –`; period totals `1100.25 / 390 / 640.5`; grand total `2130.75`; the metric preference survives a full reload with the usage bottom layout restored. | pass |
| 05 | Selecting A160 in the Activity Table and switching scope to `Selected activities` yields exactly one row with columns Oct/Dec, cells `4 / 6` and grand total `10`; switching back to `All activities` restores every row. | pass |
| 06 | The profile draws one labelled vertical bar per stored period: Oct `11` (100%), Nov `4` (36%), Dec `6` (55%), summary `Units: total 21 · peak 11 over 3 period(s)`. | pass |
| 07 | A new A170 period stored through the write API appears only after the Refresh action: 4 columns ending 2027-01-01, January total `2`, grand total `23`; the refresh itself issues no write. | pass |
| 08 | Selecting A100 (no stored period) with scope `Selected activities` shows the explicit `scope-empty` state, not an empty table or zero bars. | pass |
| 09 | fa/RTL 1280×720: localized heading `نیم‌رخ مصرف فعالیت`, RTL document direction, the same three stored bars and summary, no horizontal overflow. | pass |
| 10 | en/LTR 1920×1080: profile and spreadsheet both render with the same stored totals and 0 px overflow (spreadsheet captured as `10b`). | pass |
| 11 | Across all metric/scope/view switches no non-GET request to `/api/` was issued, and the final read still returns the 7 stored periods. | pass |

## What this slice changed

- `apps/web/src/workspace-activity-usage.ts` (new):
  - `buildActivityUsageSpreadsheet` groups stored periods by activity and period start, sums units or cost with the shared `addDecimalText` helper (exact decimal text, no float drift), and produces row, period and grand totals plus `storedPeriodCount`/`storedActivityCount`.
  - `buildActivityUsageProfile` aggregates the same period totals into bars, peak and total.
  - `normalizeActivityUsagePrefs`, `activityUsageStorageKey`, `readActivityUsagePrefs`, `storeActivityUsagePrefs` keep metric/scope presentation-only, scoped per tenant and project under `cubi:workspace:activity-usage:<tenant>:<project>`.
  - `renderActivityUsage` renders the spreadsheet and profile surfaces with explicit loading, error, empty and scope-empty states, metric/scope selects, a Refresh action and a read-only source note.
- `apps/web/src/workspace-view.ts`: `WorkspaceBottomLayout` gains `usage-profile`/`usage-spreadsheet`; `isWorkspaceUsageAvailable` gates the layouts on a loaded, non-empty period read; the bottom surface, incremental update, layout dialog and change handlers render and persist the usage prefs without touching schedule state.
- `apps/web/src/workspace-desktop-shell.ts` / `workspace-command-icons.ts`: View commands `view.bottom-usage-spreadsheet` / `view.bottom-usage-profile`, enabled only with `hasAssignmentPeriods`.
- `apps/web/src/main.ts`: reads stored periods once per opened project through `loadAssignmentPeriods`, exposes them as `ActivityUsageSource`, and refreshes on demand; the read is presentation-independent of the schedule.
- Both `apps/web/styles.css` copies gain the usage surface, table, sticky activity column and profile bar styles.
- Tests: `apps/web/src/workspace-activity-usage.test.ts` (10 tests: per-activity/per-period sums, cost, selected scope, 0.1+0.2 exactness, unknown activity, profile peak, markup/escaping/read-only, status states, Persian labels, prefs round-trip and storage failure) plus the browser suite above.

## Boundaries

- Data path: `GET /api/projects/{project_id}/p6/resource-assignment-periods` (requires `PROJECT_READ`) is read by `loadAssignmentPeriods` in `apps/web/src/workspace-assignments.ts` and projected verbatim; the write path (`POST /resource-assignments`, `POST /resource-assignment-periods`, `PROJECT_WRITE`) is used only by the test fixture. The views themselves issue no write.
- Presentation state (metric, scope, bottom layout) is browser-local and never enters the schedule input, the workspace revision or the API. The E2E proves 0 interaction writes to `/api/`.
- Values shown are stored period units/cost; no distribution across activity dates, no interpolation and no generated zeros. An activity without stored periods is absent from the table (and shown as scope-empty when only such activities are selected).

## Known limits

- The two-pane desktop layout (Activity Table left, timescaled fields right) is represented as one table whose first column is the activity and whose remaining columns are the stored period starts; the left-pane column chooser is ACT-018 and right-pane field selection is not implemented.
- The timescale is the set of stored period starts; user-defined calendar buckets, cumulative curves, bar/background styling and past-period-actual vs actual-to-date switching are not implemented.
- The profile reflects stored assignment periods only; remaining early/late distribution and resource-limit/overallocation overlays are out of scope for this slice.
- The Refresh action re-reads the whole project period collection; there is no incremental push. A failed read disables the views and shows the server error code.
