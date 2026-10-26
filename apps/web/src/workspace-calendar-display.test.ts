import assert from "node:assert/strict";
import test from "node:test";

import { formatWorkspaceCalendarDate } from "./workspace-calendar-display.js";

test("gregorian display preserves the canonical ISO date", () => {
  assert.equal(formatWorkspaceCalendarDate("2026-10-07", "gregorian"), "2026-10-07");
});

test("jalali display converts the same stored date to the Persian calendar", () => {
  assert.equal(formatWorkspaceCalendarDate("2026-10-07", "jalali"), "۱۴۰۵/۰۷/۱۵");
  assert.equal(formatWorkspaceCalendarDate("2026-03-21", "jalali"), "۱۴۰۵/۰۱/۰۱");
});

test("jalali conversion does not shift across a UTC day boundary", () => {
  // 2026-03-20 is the last day of 1404; parsing it as a local date in
  // negative-offset zones would move it into the next Jalali year.
  assert.equal(formatWorkspaceCalendarDate("2026-03-20", "jalali"), "۱۴۰۴/۱۲/۲۹");
});

test("non-date and invalid values are returned unchanged", () => {
  assert.equal(formatWorkspaceCalendarDate("—", "jalali"), "—");
  assert.equal(formatWorkspaceCalendarDate("2026-02-30", "jalali"), "2026-02-30");
  assert.equal(formatWorkspaceCalendarDate("2026-10-07T08:00:00Z", "jalali"), "2026-10-07T08:00:00Z");
});
