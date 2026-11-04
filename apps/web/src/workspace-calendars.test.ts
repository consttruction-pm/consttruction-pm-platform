import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { formatJalaliDateInput, parseJalaliDateInput } from "./workspace-jalali-entry.js";
import {
  buildExceptionRequest,
  copyCalendar,
  deleteCalendar,
  loadCalendarCatalogue,
  loadCalendarExceptions,
  loadCalendarSnapshot,
  saveCalendarException,
  updateCalendar,
  type CalendarExceptionInput,
} from "./workspace-calendars.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 4 };

const CALENDAR = {
  calendar_id: "CAL-PRJ",
  calendar_version: "1",
  kind: "working-time",
  calendar_type: "project",
  name: "Project calendar",
  record_revision: 3,
};

const SNAPSHOT = {
  contract_version: "p6-calendar-read-api.v1",
  kind: "calendar_snapshot",
  scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 },
  calendar: CALENDAR,
  snapshot: {
    kind: "working-time",
    system: "gregorian",
    working_weekdays: [5, 6, 0, 1, 2],
    holidays: ["2026-01-01"],
    daily_intervals: { "0": [["08:00", "12:00"], ["13:00", "17:00"]] },
    time_period_factors: {
      hours_per_day: "8",
      hours_per_week: "40",
      hours_per_month: "173.33",
      hours_per_year: "2080",
    },
  },
};

type Calls = {
  gets: { path: string; context: ProjectContext }[];
  posts: { path: string; request: unknown; idempotencyKey?: string }[];
  patches: { path: string; request: unknown }[];
  deletes: { path: string; request: unknown }[];
};

function transportWith(
  result: ApiResult<unknown>,
  calls: Calls = { gets: [], posts: [], patches: [], deletes: [] },
): ApiTransport {
  return {
    async get(path, context) {
      calls.gets.push({ path, context });
      return result as ApiResult<never>;
    },
    async post(path, request, _context, idempotencyKey) {
      calls.posts.push({ path, request, idempotencyKey });
      return result as ApiResult<never>;
    },
    async patch(path, request) {
      calls.patches.push({ path, request });
      return result as ApiResult<never>;
    },
    async delete(path, request) {
      calls.deletes.push({ path, request });
      return result as ApiResult<never>;
    },
  };
}

test("calendar snapshot read preserves persisted working time and factors", async () => {
  const calls: Calls = { gets: [], posts: [], patches: [], deletes: [] };
  const result = await loadCalendarSnapshot(transportWith({ ok: true, data: SNAPSHOT }, calls), CONTEXT, "CAL-PRJ", "1");
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(calls.gets[0].path, "/api/projects/project-1/p6/calendars/CAL-PRJ/1/snapshot");
  assert.deepEqual(result.data.snapshot.workingWeekdays, [5, 6, 0, 1, 2]);
  assert.deepEqual(result.data.snapshot.holidays, ["2026-01-01"]);
  assert.deepEqual(result.data.snapshot.dailyIntervals["0"], [["08:00", "12:00"], ["13:00", "17:00"]]);
  assert.equal(result.data.snapshot.factors.hours_per_month, "173.33");
  assert.equal(result.data.snapshot.system, "gregorian");
  assert.equal(result.data.calendar.recordRevision, 3);
});

test("calendar snapshot read fails closed on a different calendar reference or contract", async () => {
  const mismatch = await loadCalendarSnapshot(
    transportWith({ ok: true, data: { ...SNAPSHOT, calendar: { ...CALENDAR, calendar_id: "OTHER" } } }),
    CONTEXT,
    "CAL-PRJ",
    "1",
  );
  assert.equal(mismatch.ok, false);
  if (!mismatch.ok) assert.equal(mismatch.error.code, "CALENDAR_REFERENCE_MISMATCH");

  const wrongContract = await loadCalendarSnapshot(
    transportWith({ ok: true, data: { ...SNAPSHOT, contract_version: "v0" } }),
    CONTEXT,
    "CAL-PRJ",
    "1",
  );
  assert.equal(wrongContract.ok, false);
  if (!wrongContract.ok) assert.equal(wrongContract.error.code, "INVALID_CALENDAR_SNAPSHOT");

  const badWeekday = await loadCalendarSnapshot(
    transportWith({ ok: true, data: { ...SNAPSHOT, snapshot: { ...SNAPSHOT.snapshot, working_weekdays: [9] } } }),
    CONTEXT,
    "CAL-PRJ",
    "1",
  );
  assert.equal(badWeekday.ok, false);
  if (!badWeekday.ok) assert.equal(badWeekday.error.code, "INVALID_CALENDAR_SNAPSHOT");
});

test("calendar catalogue read uses the read contract and rejects unknown shapes", async () => {
  const ok = await loadCalendarCatalogue(
    transportWith({
      ok: true,
      data: { contract_version: "p6-calendar-read-api.v1", kind: "calendar_catalog", calendars: [CALENDAR] },
    }),
    CONTEXT,
  );
  assert.equal(ok.ok, true);
  if (ok.ok) assert.equal(ok.data[0].calendarId, "CAL-PRJ");

  const invalid = await loadCalendarCatalogue(transportWith({ ok: true, data: { kind: "calendar_catalog" } }), CONTEXT);
  assert.equal(invalid.ok, false);
  if (!invalid.ok) assert.equal(invalid.error.code, "INVALID_CALENDAR_CATALOG");
});

test("calendar exceptions are read with their stored mode, hours and intervals", async () => {
  const result = await loadCalendarExceptions(
    transportWith({
      ok: true,
      data: {
        contract_version: "p6-calendar.v1",
        exceptions: [
          { calendar_id: "CAL-PRJ", calendar_version: "1", date: "2026-01-02", mode: "nonwork", system: "gregorian", total_work_hours: null, intervals: [] },
          { calendar_id: "CAL-PRJ", calendar_version: "1", date: "2026-01-03", mode: "detailed-work-hours", system: "gregorian", total_work_hours: null, intervals: [["09:00", "12:00"]] },
        ],
      },
    }),
    CONTEXT,
    "CAL-PRJ",
    "1",
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.data.length, 2);
  assert.deepEqual(result.data[1].intervals, [["09:00", "12:00"]]);
});

test("calendar update uses PATCH with the persisted revision and kind", async () => {
  const calls: Calls = { gets: [], posts: [], patches: [], deletes: [] };
  const calendar = {
    calendarId: "CAL-PRJ",
    calendarVersion: "1",
    name: "Project calendar",
    kind: "working-time",
    calendarType: "project",
    recordRevision: 3,
  };
  const result = await updateCalendar(
    transportWith({ ok: true, data: { ...CALENDAR, name: "Renamed", record_revision: 4 } }, calls),
    CONTEXT,
    calendar,
    { name: "  Renamed  ", calendarType: "project" },
  );
  assert.equal(result.ok, true);
  assert.equal(calls.patches[0].path, "/api/projects/project-1/p6/calendars/CAL-PRJ/1");
  assert.deepEqual(calls.patches[0].request, {
    contract_version: "p6-calendar.v1",
    calendar_id: "CAL-PRJ",
    calendar_version: "1",
    calendar_type: "project",
    kind: "working-time",
    name: "Renamed",
    expected_revision: 3,
  });

  const missingName = await updateCalendar(transportWith({ ok: true, data: CALENDAR }), CONTEXT, calendar, { name: " ", calendarType: "project" });
  assert.equal(missingName.ok, false);
  if (!missingName.ok) assert.equal(missingName.error.code, "CALENDAR_NAME_REQUIRED");
});

test("calendar copy refuses a self-target and posts the target reference", async () => {
  const calendar = {
    calendarId: "CAL-PRJ",
    calendarVersion: "1",
    name: "Project calendar",
    kind: "working-time",
    calendarType: "project",
    recordRevision: 3,
  };
  const calls: Calls = { gets: [], posts: [], patches: [], deletes: [] };
  const copied = await copyCalendar(
    transportWith({ ok: true, data: { ...CALENDAR, calendar_id: "CAL-2", calendar_version: "1" } }, calls),
    CONTEXT,
    calendar,
    "CAL-2",
    "1",
  );
  assert.equal(copied.ok, true);
  assert.equal(calls.posts[0].path, "/api/projects/project-1/p6/calendars/CAL-PRJ/1/copy");
  assert.deepEqual(calls.posts[0].request, { target_calendar_id: "CAL-2", target_calendar_version: "1" });

  const self = await copyCalendar(transportWith({ ok: true, data: CALENDAR }), CONTEXT, calendar, "CAL-PRJ", "1");
  assert.equal(self.ok, false);
  if (!self.ok) assert.equal(self.error.code, "CALENDAR_TARGET_ALREADY_SELECTED");
});

test("calendar delete sends the expected revision and requires a real deletion", async () => {
  const calendar = {
    calendarId: "CAL-PRJ",
    calendarVersion: "1",
    name: "Project calendar",
    kind: "working-time",
    calendarType: "project",
    recordRevision: 3,
  };
  const calls: Calls = { gets: [], posts: [], patches: [], deletes: [] };
  const deleted = await deleteCalendar(transportWith({ ok: true, data: { deleted: true } }, calls), CONTEXT, calendar);
  assert.equal(deleted.ok, true);
  assert.equal(calls.deletes[0].path, "/api/projects/project-1/p6/calendars/CAL-PRJ/1");
  assert.deepEqual(calls.deletes[0].request, { expected_revision: 3 });

  const fake = await deleteCalendar(transportWith({ ok: true, data: { deleted: false } }), CONTEXT, calendar);
  assert.equal(fake.ok, false);
  if (!fake.ok) assert.equal(fake.error.code, "INVALID_CALENDAR_DELETE_RESPONSE");
});

test("exception request keeps modes and converts Jalali days without shifting the date", () => {
  const nonwork: CalendarExceptionInput = { date: "2026-03-21", mode: "nonwork", totalWorkHours: null, start: null, end: null };
  assert.deepEqual(buildExceptionRequest(nonwork, "gregorian"), {
    date: "2026-03-21",
    mode: "nonwork",
    system: "gregorian",
    total_work_hours: null,
    intervals: [],
  });

  const jalali = buildExceptionRequest(nonwork, "jalali");
  assert.ok(jalali);
  const typed = String(jalali.date);
  assert.equal(typed, formatJalaliDateInput("2026-03-21").replaceAll("/", "-"));
  assert.ok(parseJalaliDateInput(typed));
  assert.equal(jalali.system, "jalali");

  assert.equal(buildExceptionRequest({ ...nonwork, mode: "total-work-hours", totalWorkHours: "0" }, "gregorian")?.total_work_hours, "0");
  assert.equal(buildExceptionRequest({ ...nonwork, mode: "total-work-hours", totalWorkHours: "eight" }, "gregorian"), null);
  assert.equal(
    buildExceptionRequest({ ...nonwork, mode: "detailed-work-hours", start: "13:00", end: "12:00" }, "gregorian"),
    null,
  );
  assert.deepEqual(
    buildExceptionRequest({ ...nonwork, mode: "detailed-work-hours", start: "08:00", end: "12:00" }, "gregorian")?.intervals,
    [["08:00", "12:00"]],
  );
  assert.equal(buildExceptionRequest({ ...nonwork, date: "2026-02-30", mode: "nonwork" }, "gregorian"), null);
});

test("exception save posts to the calendar exception route and surfaces failure codes", async () => {
  const calendar = {
    calendarId: "CAL-PRJ",
    calendarVersion: "1",
    name: "Project calendar",
    kind: "working-time",
    calendarType: "project",
    recordRevision: 3,
  };
  const calls: Calls = { gets: [], posts: [], patches: [], deletes: [] };
  const saved = await saveCalendarException(
    transportWith(
      { ok: true, data: { calendar_id: "CAL-PRJ", calendar_version: "1", date: "2026-01-02", mode: "nonwork", system: "gregorian", total_work_hours: null, intervals: [] } },
      calls,
    ),
    CONTEXT,
    calendar,
    "gregorian",
    { date: "2026-01-02", mode: "nonwork", totalWorkHours: null, start: null, end: null },
  );
  assert.equal(saved.ok, true);
  assert.equal(calls.posts[0].path, "/api/projects/project-1/p6/calendars/CAL-PRJ/1/exceptions");

  const rejected = await saveCalendarException(
    transportWith({ ok: false, error: { code: "CALENDAR_EXCEPTION_DUPLICATE", retryable: false, message_key: "error.test", available_actions: [] } }),
    CONTEXT,
    calendar,
    "gregorian",
    { date: "2026-01-02", mode: "nonwork", totalWorkHours: null, start: null, end: null },
  );
  assert.equal(rejected.ok, false);
  if (!rejected.ok) assert.equal(rejected.error.code, "CALENDAR_EXCEPTION_DUPLICATE");
});
