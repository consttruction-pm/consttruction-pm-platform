# Calendars — month grid (CAL-002), 2026-11-15

Tested code: `244d7aed` (`feat/calendar-month-grid`).
Environment: managed Python preview on the built bundle, one fresh SQLite
database and one port per suite (`4520`, `4521`, `4522`; `--reset`).

## Version 26 reference

HTML Help: [Edit a project calendar](https://docs.oracle.com/cd/G48902_01/client_help/en_US/edit_a_project_calendar.htm)
(Structuring Projects > Defining Calendars > Project Calendars).

- Step 4: "Choose the month you want to modify by clicking the appropriate
  arrow button next to the month-year title."
- Step 5: "To add a nonworkday, click the date you want to make a nonworkday,
  then click Nonwork."
- Step 7: "To make an exception into a workday and apply the default number of
  working hours to that day, click the exception you want to change, then click
  Standard."
- Tip: "To apply the same change to all instances of a specific weekday in the
  displayed month, click the weekday's column label."

The 815-page PDF named in the governing instruction is still absent; its page
number stays **MISSING / VERIFY**. The 303-page Professional guide does not
describe this dialog's month grid separately.

## Gap

The Calendars window had a Workweek table (per-weekday rules) and an Exceptions
list (one row per stored date), but no month surface: a planner could not see
which dates of a month were working, could not click a date to make it
nonwork, could not reset an exception to standard, and the V26 weekday-column
bulk action had no equivalent at all. The Jalali date system was only a label
on typed input, never a rendered month.

## Change

- `apps/web/src/workspace-calendars.ts`
  - `calendarWeekday` (Monday-based), `calendarMonthAnchor` (first of the
    month in Gregorian or Jalali), `shiftCalendarMonth` (year-boundary safe,
    per system) and `buildCalendarMonth` (visible days with the stored
    workweek and exceptions attached) are pure and exported.
  - A new **Calendar Month** tab (`data-calendar-panel="month"`) renders the
    month-year title with prev/next arrows, a Monday-first grid, the
    selected-date label, and Nonwork/Standard actions that stay disabled until
    a date is selected.
  - Each cell carries `data-calendar-month-day="YYYY-MM-DD"` and
    `data-calendar-month-state="workday|nonwork|<exception mode>"`; the header
    weekday cells are buttons (`data-calendar-month-weekday`).
  - Nonwork saves a `nonwork` exception for the date; Standard deletes a stored
    exception for the date; a weekday heading applies the last chosen action
    to every visible instance of that weekday. Every path re-reads
    `loadCalendarExceptions` before reporting, so the grid shows stored state.
  - Titles use `Intl.DateTimeFormat` with the `persian` or `gregory` calendar,
    so a Jalali calendar shows Aban 1405 while the cells stay ISO dates.
- `apps/web/styles.css` and the published copy: month toolbar, grid cells,
  nonwork tint, hours-exception tint, selected outline and blank cells.
- Tests: `workspace-calendars.test.ts` adds grid shape (November 2026: 30 days,
  Sunday leading offset 6, Monday working, stored exception attached), Aban
  1405 (30 days, 2026-10-23 → 2026-11-21, leading 4), and anchor/shift across
  year boundaries for both systems.

## Browser proof (all at `244d7aed`)

| Suite | Scenarios | Screenshots | Exceptions | Console errors | API 5xx |
|---|---|---|---|---|---|
| `calendars-v26.mjs` | 10/10 | 13 | 0 | 0 | 0 |
| `calendars-jalali-v26.mjs` | 6/6 | 6 | 0 | 0 | 0 |
| `calendars-usage-v26.mjs` | 6/6 | 5 | 0 | 0 | 0 |

`06b` selects 2026-11-03, marks it Nonwork and reads the stored exception back,
resets it with Standard and confirms it is gone, then bulk-marks every Tuesday
(03, 10, 17, 24) through the Tuesday heading, resets them through the same
heading, and navigates December 2026 → October 2026 (`06b-month-nonwork.png`,
`06c-month-bulk-tuesdays.png`, `06d-month-previous.png`). `04b` in the Jalali
suite opens the month tab and asserts the Aban 1405 title, 30 cells and the
2026-10-23 → 2026-11-21 ISO span (`04b-jalali-month-grid.png`).

## Gate results

- `apps/web` `npm run typecheck` — clean.
- `apps/web` `npm test` — 1168 TypeScript tests and 15 `node --test` tests
  passed, including the preview/published CSS parity test.
- `npm run build` — bundle rebuilt before the E2E runs.

## Known limits

- The grid renders one month at a time; there is no multi-month or year view.
- Weekday columns start Monday in both locales; V26 lets the locale's week
  start decide, and Persian weeks normally start Saturday.
- Bulk actions write one exception per date and stop at the first failure; there
  is no single-transaction bulk endpoint.
- Total-hours and detailed-hours exceptions are shown and can be reset to
  Standard, but the grid does not yet edit their hours; that stays in the
  Exceptions tab.
- Recurring exceptions and the Time Periods dialog from the same topic remain
  **NOT_IMPLEMENTED**.
