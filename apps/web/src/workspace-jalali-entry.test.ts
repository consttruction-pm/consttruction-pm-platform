import assert from "node:assert/strict";
import test from "node:test";

import {
  formatJalaliDateInput,
  isValidCanonicalIsoDate,
  parseJalaliDateInput,
} from "./workspace-jalali-entry.js";

test("typed Jalali dates convert to the canonical ISO Gregorian date", () => {
  assert.equal(parseJalaliDateInput("1405/06/30"), "2026-09-21");
  assert.equal(parseJalaliDateInput("1405/07/15"), "2026-10-07");
  assert.equal(parseJalaliDateInput("1405/01/01"), "2026-03-21");
  assert.equal(parseJalaliDateInput("1403/12/30"), "2025-03-20");
});

test("Persian and Arabic-Indic digits and common separators are accepted", () => {
  assert.equal(parseJalaliDateInput("۱۴۰۵/۰۷/۱۵"), "2026-10-07");
  assert.equal(parseJalaliDateInput("١٤٠٥-٠٧-١٥"), "2026-10-07");
  assert.equal(parseJalaliDateInput(" 1405.7.15 "), "2026-10-07");
});

test("impossible Jalali dates fail closed instead of rolling over", () => {
  // 1404 is not a leap year, so Esfand has 29 days.
  assert.equal(parseJalaliDateInput("1404/12/30"), null);
  assert.equal(parseJalaliDateInput("1405/13/01"), null);
  assert.equal(parseJalaliDateInput("1405/00/10"), null);
  assert.equal(parseJalaliDateInput("1405/07/00"), null);
  assert.equal(parseJalaliDateInput("1405/07/32"), null);
  assert.equal(parseJalaliDateInput("not-a-date"), null);
  assert.equal(parseJalaliDateInput(""), null);
  assert.equal(parseJalaliDateInput("1000/01/01"), null);
});

test("a canonical ISO date renders as a typed Jalali value without shifting", () => {
  assert.equal(formatJalaliDateInput("2026-10-07"), "1405/07/15");
  assert.equal(formatJalaliDateInput("2026-03-20"), "1404/12/29");
  assert.equal(formatJalaliDateInput("2026-03-21"), "1405/01/01");
  assert.equal(formatJalaliDateInput("2025-03-20"), "1403/12/30");
});

test("invalid or already-display values are returned unchanged", () => {
  assert.equal(formatJalaliDateInput("1405/07/15"), "1405/07/15");
  assert.equal(formatJalaliDateInput("2026-02-30"), "2026-02-30");
  assert.equal(formatJalaliDateInput("2026-10-07T08:00:00Z"), "2026-10-07T08:00:00Z");
});

test("format and parse round-trip a leap-day boundary", () => {
  for (const iso of ["2025-03-20", "2026-03-20", "2026-03-21", "2026-10-07", "2027-03-20"]) {
    assert.equal(parseJalaliDateInput(formatJalaliDateInput(iso)), iso);
  }
});

test("canonical ISO validation rejects malformed and impossible Gregorian dates", () => {
  assert.equal(isValidCanonicalIsoDate("2026-10-07"), true);
  assert.equal(isValidCanonicalIsoDate("2026-02-30"), false);
  assert.equal(isValidCanonicalIsoDate("2026-1-7"), false);
  assert.equal(isValidCanonicalIsoDate("1405/07/15"), false);
});
