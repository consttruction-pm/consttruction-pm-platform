import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { formatJalaliDateInput, parseJalaliDateInput } from "./workspace-jalali-entry.js";
import {
  addCalendarHoliday,
  calendarExceptionModeLabel,
  loadCalendarExceptions,
  type CalendarHolidayLabels,
} from "./calendar-holidays.js";

const CONTEXT: ProjectContext = {
  tenant_id: "t1",
  project_id: "preview-rps-01",
  revision: 7,
};

type GetCall = { path: string; context: ProjectContext };
type PostCall = { path: string; request: unknown; context: ProjectContext; idempotencyKey?: string };

function transportWith(
  options: {
    getResult?: ApiResult<unknown>;
    postResult?: ApiResult<unknown>;
    gets?: GetCall[];
    posts?: PostCall[];
  } = {},
): ApiTransport {
  return {
    async get(path, context) {
      options.gets?.push({ path, context });
      return (options.getResult ?? {
        ok: false,
        error: {
          code: "GET_NOT_STUBBED",
          retryable: false,
          message_key: "error.test",
          available_actions: [],
        },
      }) as ApiResult<never>;
    },
    async post(path, request, context, idempotencyKey) {
      options.posts?.push({ path, request, context, idempotencyKey });
      return (options.postResult ?? {
        ok: false,
        error: {
          code: "POST_NOT_STUBBED",
          retryable: false,
          message_key: "error.test",
          available_actions: [],
        },
      }) as ApiResult<never>;
    },
  };
}

const RECORD = {
  calendar_id: "CUBI-RPS-CAL",
  calendar_version: "1",
  date: "2026-10-20",
  mode: "nonwork",
  system: "gregorian",
  total_work_hours: null,
  intervals: [],
};

test("loadCalendarExceptions reads the persisted exceptions of the selected calendar", async () => {
  const gets: GetCall[] = [];
  const transport = transportWith({
    gets,
    getResult: { ok: true, data: { contract_version: "p6-calendar-api.v1", exceptions: [RECORD] } },
  });

  const result = await loadCalendarExceptions(transport, CONTEXT, "CUBI-RPS-CAL", "1");

  assert.equal(result.ok, true);
  assert.deepEqual(gets, [
    {
      path: "/api/projects/preview-rps-01/p6/calendars/CUBI-RPS-CAL/1/exceptions",
      context: CONTEXT,
    },
  ]);
});

test("loadCalendarExceptions refuses a missing calendar reference without calling the API", async () => {
  const gets: GetCall[] = [];
  const transport = transportWith({ gets });

  const result = await loadCalendarExceptions(transport, CONTEXT, "", "1");

  assert.equal(result.ok, false);
  assert.equal(result.ok ? "" : result.error.code, "CALENDAR_REFERENCE_REQUIRED");
  assert.equal(gets.length, 0);
});

test("addCalendarHoliday stores one canonical non-working day with an idempotency key", async () => {
  const posts: PostCall[] = [];
  const transport = transportWith({
    posts,
    postResult: { ok: true, data: RECORD },
  });

  const result = await addCalendarHoliday(transport, CONTEXT, "CUBI-RPS-CAL", "1", {
    date: "2026-10-20",
    system: "gregorian",
  });

  assert.equal(result.ok, true);
  assert.equal(posts.length, 1);
  assert.equal(
    posts[0].path,
    "/api/projects/preview-rps-01/p6/calendars/CUBI-RPS-CAL/1/exceptions",
  );
  assert.deepEqual(posts[0].request, {
    date: "2026-10-20",
    mode: "nonwork",
    system: "gregorian",
    total_work_hours: null,
    intervals: [],
  });
  assert.ok(posts[0].idempotencyKey, "every write must carry a stable idempotency key");
});

test("a Jalali holiday is sent in the Jalali system and keeps the canonical Gregorian day", async () => {
  const posts: PostCall[] = [];
  const transport = transportWith({
    posts,
    postResult: { ok: true, data: { ...RECORD, date: "2027-02-08", system: "jalali" } },
  });

  const result = await addCalendarHoliday(transport, CONTEXT, "CUBI-RPS-CAL", "1", {
    date: "2027-02-08",
    system: "jalali",
  });

  assert.equal(result.ok, true);
  const request = posts[0].request as { date: string; system: string };
  const expectedJalali = formatJalaliDateInput("2027-02-08").replaceAll("/", "-");
  assert.equal(request.date, expectedJalali);
  assert.match(request.date, /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(request.system, "jalali");
  // The typed Jalali day round-trips to the same canonical Gregorian day.
  assert.equal(parseJalaliDateInput(request.date), "2027-02-08");
});

test("invalid input is rejected in the browser without a network write", async () => {
  const posts: PostCall[] = [];
  const transport = transportWith({ posts });

  const invalidDate = await addCalendarHoliday(transport, CONTEXT, "CUBI-RPS-CAL", "1", {
    date: "2026-02-30",
    system: "gregorian",
  });
  const missingCalendar = await addCalendarHoliday(transport, CONTEXT, "", "1", {
    date: "2026-10-20",
    system: "gregorian",
  });

  assert.equal(invalidDate.ok ? "" : invalidDate.error.code, "HOLIDAY_DATE_INVALID");
  assert.equal(missingCalendar.ok ? "" : missingCalendar.error.code, "CALENDAR_REFERENCE_REQUIRED");
  assert.equal(posts.length, 0);
});

test("a server refusal is returned unchanged so the panel can explain the denial", async () => {
  const transport = transportWith({
    postResult: {
      ok: false,
      error: {
        code: "authorization denied for permission=project.write",
        retryable: false,
        message_key: "error.authorization.denied",
        available_actions: [],
      },
    },
  });

  const result = await addCalendarHoliday(transport, CONTEXT, "CUBI-RPS-CAL", "1", {
    date: "2026-10-20",
    system: "gregorian",
  });

  assert.equal(result.ok, false);
  assert.match(result.ok ? "" : result.error.code, /project\.write/);
});

test("recorded modes render with explicit labels", () => {
  const labels: CalendarHolidayLabels = {
    title: "",
    intro: "",
    date: "",
    add: "",
    adding: "",
    added: "",
    failed: "",
    forbidden: "",
    alreadyRecorded: "",
    invalidDate: "",
    reading: "",
    readFailed: "",
    empty: "",
    noCalendar: "",
    nonwork: "off",
    totalHours: "total",
    detailedHours: "detailed",
    resetStandard: "reset",
    canonicalDate: "",
  };

  assert.equal(calendarExceptionModeLabel("nonwork", labels), "off");
  assert.equal(calendarExceptionModeLabel("total-work-hours", labels), "total");
  assert.equal(calendarExceptionModeLabel("detailed-work-hours", labels), "detailed");
  assert.equal(calendarExceptionModeLabel("reset-standard", labels), "reset");
  assert.equal(calendarExceptionModeLabel("unknown-mode", labels), "unknown-mode");
});
