# Calendars — base-calendar inheritance (CAL-003), 2026-11-15

Tested code: `fd3ff6e9` (`feat/calendar-base-inheritance`).
Environment: managed Python preview on the built bundle
`apps/web/dist/web/src/main.bundle.js`; one fresh SQLite database and one port
per suite (`4512`, `4513`, `4514`; `--reset`).

## Version 26 reference

- HTML Help topic: [Edit a project calendar](https://docs.oracle.com/cd/G48902_01/client_help/en_US/edit_a_project_calendar.htm)
  (Structuring Projects > Defining Calendars > Project Calendars), step 3:
  "To base the calendar on another calendar, select a new global calendar in
  the Inherit Holidays and Exceptions from Global Calendar field."
- The same topic explains that the calendar's default hours per time period
  and its Used By assignments are part of the dialog; Used By is already
  served by `p6-calendar-usage-api.v1`.
- The 815-page PDF named in the governing instruction is not present in the
  repository or on the Oracle site; the page number stays **MISSING / VERIFY**
  and is not attributed. The 303-page Professional guide was used for the
  other Calendars topics and page numbers.

## Defect found by audit

`P6CalendarAPI.update` built a new `CalendarMaster` from the request and
saved it without inspecting `base_calendar_id` / `base_calendar_version`. A
`PATCH` could therefore:

- point a calendar at itself (`CALENDAR_BASE_SELF_REFERENCE` had no check),
- close an inheritance loop that
  `P6VersionedResourceCalendarResolver` later rejects with
  `CALENDAR_INHERITANCE_CYCLE`,
- name a base of a different `kind`, which the resolver rejects with
  `CALENDAR_INHERITANCE_KIND_MISMATCH` after the edit was already stored,
- name a base without a stored snapshot, deferring the failure to the
  schedule run.

`create` had the kind/snapshot checks inline; `update` had none. The
Calendars window also had no control for the field at all: the General tab
showed ID, version, kind, revision, system and the four time-period factors,
and `CalendarUpdateInput` carried only `name` and `calendarType`.

## Product change

- `src/construction_pm/p6_calendar_api.py` — one `_resolve_base_calendar`
  helper now validates both create and update: a complete id/version pair
  (`INCOMPLETE_BASE_CALENDAR_REFERENCE`), a stored master
  (`BASE_CALENDAR_NOT_FOUND`), the same `kind`
  (`BASE_CALENDAR_KIND_MISMATCH`), a stored definition
  (`BASE_CALENDAR_SNAPSHOT_NOT_FOUND`), no self-reference
  (`CALENDAR_BASE_SELF_REFERENCE`) and no cycle back onto the edited calendar
  (`CALENDAR_BASE_CYCLE`). The cycle walk starts from the requested base and
  follows stored `base_calendar_id` links.
- `apps/web/src/workspace-calendars.ts` — the General tab renders
  `data-calendar-base` ("Inherit Holidays and Exceptions from Global
  Calendar") in edit mode with every same-kind stored calendar plus an explicit
  "Do not inherit" option, and a hint that reports the current state.
  `CalendarUpdateInput` accepts `baseCalendarId` / `baseCalendarVersion`;
  omitting them keeps the stored pair, `null` clears it. `calendarBaseValue`
  is the single `id|version` encoder used by the editor.
- `apps/web/src/workspace-calendars.test.ts` — payload cases for preserve,
  change and clear.
- `tests/test_p6_calendar_api.py` — preserve/change/clear, self-reference,
  cycle (no mutation left behind), missing base, kind mismatch and missing
  snapshot through `update`; the kind-mismatch case seeds a `working-time`
  target so the edited calendar's own snapshot-kind guard is not the failing
  assertion.

The stored reference is not cosmetic: the preview runtime
(`preview/runtime.py`) registers `base_calendar_id` chains, and
`P6VersionedResourceCalendarResolver` layers the inherited definition and
exceptions, so the guards keep the resolver's assumptions true.

## Browser proof (all at `fd3ff6e9`)

| Suite | Scenarios | Screenshots | Exceptions | Console errors | API 5xx |
|---|---|---|---|---|---|
| `calendars-v26.mjs` | 9/9 | 10 | 0 | 0 | 0 |
| `calendars-jalali-v26.mjs` | 5/5 | 5 | 0 | 0 | 0 |
| `calendars-usage-v26.mjs` | 6/6 | 5 | 0 | 0 | 0 |

New scenario `05b` drives the real control: it opens the created calendar's
General tab, asserts the select shows `CUBI-RPS-CAL|1` and is read-only until
Edit, clears it through the UI, asserts the API record reports
`base_calendar_id: null` and the hint changes, re-selects the base, and asserts
the stored pair and the rendered select are back
(`05b-base-cleared.png`, `05c-base-restored.png`).

Scenario `01` also had a stale tab assertion: the tab strip now renders
`general,workweek,exceptions,usage` because the Used By tab shipped in
`cef505e9`; the assertion was corrected to the shipped order rather than the
tab being removed.

## Gate results

- `python3 -m pytest -q` — 4335 passed, 204 skipped.
- `apps/web` `npm run typecheck` — clean.
- `apps/web` `npm test` — 1166 TypeScript tests and 15 `node --test` tests
  passed.
- `npm run build` — bundle rebuilt before the E2E runs.

## Known limits

- The control lists same-kind calendars regardless of `calendar_type`; V26
  names the field "Global Calendar", but the resolver accepts any same-kind
  chain and CUBI calendars are project/resource/global, so no type filter is
  applied yet.
- Inheritance is by reference. A later edit of the base calendar is seen by
  the resolver, but exception rows are layered at resolution time and are not
  copied into the inheriting calendar's exception tab.
- The month-year grid, recurring exceptions and weekday-column bulk change in
  the same V26 topic are still **NOT_IMPLEMENTED** and remain the next
  Calendars unit.
