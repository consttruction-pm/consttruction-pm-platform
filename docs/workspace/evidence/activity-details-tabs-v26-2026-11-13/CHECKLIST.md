# ACT-014 — Activity Details tabs and field completeness (2026-11-13)

Contract: `cubi-activity-details-tabs-v26.v1`
Tested code: `8d27c88f041e061f013042c4ed14cbfe213959b0` (squash merge of #1861)
Suite: `apps/web/e2e/activity-details-v26.mjs`
Report: `activity-details-tabs-v26.json` (17 tabs, 3 write paths, customize persistence; 0 exceptions, 0 console errors, 0 failing API responses)
Screenshot: `details-en-1366.png`

## Help topics

- [Activity Details](https://docs.oracle.com/cd/G48902_01/client_help/en_US/activity_details.htm) — the bottom layout shows the selected activity's details across the tab set.
- [Customize Activity Details](https://docs.oracle.com/cd/G48902_01/client_help/en_US/customize_activity_details.htm) — tabs can be added, removed and reordered for the display set.
- [Activity Usage Spreadsheet](https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_activity_usage_spreadsheet.htm) context is covered by ACT-015; the Details bottom view is the `details` option in `data-bottom-layout`.
- Steps follow the V26 activity-step read contract `p6-activity-step-read-api.v1` (`apps/web/src/workspace-activity-steps.ts`).

## Environment

- `PYTHONPATH=src python3 -m construction_pm.preview --web-root apps/web --host 127.0.0.1 --port 4184 --database /tmp/cubi-details-e2e.sqlite --reset`
- Fixture: Riverside Pump Station Upgrade (`preview-rps-01`), administrator session, 1366×768 en/LTR.
- A130 carries three seeded step definitions (`Strip topsoil…`, `Cut and fill…`, `Compact and survey…`); the read APIs seed no activity assignments, expenses or issues, so those tabs start empty and are populated by the suite through their own forms.

## Scenarios

| # | Proof | Result |
|---|---|---|
| 01 | The bottom Details pane exposes all 16 Version 26 tabs in order plus the CUBI Calendar tab last (17 total). | pass |
| 02 | Every data tab issues its authoritative read and settles: Resources, Expenses, Issues, Risks, Steps, UDFs and Update History each show a Reload action, no loading spinner and no error surface. | pass |
| 03 | A130's Steps tab lists the three stored step definitions in sequence order with their weights; the panel states that completion percentage is not stored rather than inventing one. | pass |
| 04 | Resources write: the form saves a 12 h / 900 USD assignment for `RPS-CIVIL-CREW`, reports `Saved. The list was reloaded from the project service.` and the reloaded table shows the resource. | pass |
| 05 | Expenses write: `E2E concrete` (material, 1500 USD) is saved and read back from the project service. | pass |
| 06 | Issues write: `E2E schedule risk` (schedule, open, high) is saved and read back from the project service. | pass |
| 07 | Customize Tabs: removing Status, applying and confirming leaves 16 tabs without Status; a full reload restores the same display set from `cubi:activity-details-visible-tabs:v2`. | pass |
| 08 | No uncaught exception, console error or 5xx response occurs during the run. | pass |

## What this slice changed

- `apps/web/e2e/activity-details-v26.mjs` now stamps `contract`, `testedCodeSha` and `gitHead` into the report, copies its screenshot into `docs/workspace/evidence/activity-details-tabs-v26-<date>/` and writes the same JSON there (report-only change; the product code was already on `main`).

## Boundaries

- General, Status, Predecessors, Successors, Relationships, Codes, Summary and Calendar read the in-memory authoritative workspace state; Resources, Expenses, Issues, Risks, Steps, UDFs and Update History read their project-service endpoints on tab activation.
- Only Resources, Expenses, Issues and UDFs write; Steps, Risks, WPs & Docs and Update History are read-only in this slice and say so. No tab mutates activity dates, durations or relationships.
- Writes go through the existing endpoints (`/p6/resource-assignments`, `/p6/expenses`, `/p6/issues`, UDF value PUT) under `PROJECT_WRITE`; the suite's viewer path is covered by the UDF suite (403).
- The Calendar tab is the CUBI addition recorded as part of the tab contract; Tasks, Discussion and Feedback are P6 EPPM-only and are not offered.

## Known limits

- Risks is read-only: the risk model has no activity reference, so the pane explains that the project-level register cannot be filtered by activity.
- WPs & Docs and Update History are read surfaces; no document record is linked to an activity in the preview fixture.
- Notebook uses the browser-local Comments rail rather than a stored per-activity notebook record.
- The customize dialog reorders the display set but does not change tab content or the underlying registry.
