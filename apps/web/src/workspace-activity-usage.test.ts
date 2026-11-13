import assert from "node:assert/strict";
import test from "node:test";
import {
  ACTIVITY_USAGE_DEFAULT_PREFS,
  buildActivityUsageProfile,
  buildActivityUsageSpreadsheet,
  normalizeActivityUsagePrefs,
  readActivityUsagePrefs,
  renderActivityUsage,
  storeActivityUsagePrefs,
  type ActivityUsageSource,
} from "./workspace-activity-usage.js";
import type { AssignmentPeriod } from "./workspace-assignments.js";

const activities = [
  { id: "A110", code: "A110", name: "Design" },
  { id: "A120", code: "A120", name: "Procure" },
];

function period(
  assignmentId: string,
  activityId: string,
  periodStart: string,
  units: string,
  cost: string,
  resourceId = "R1",
): AssignmentPeriod {
  return { assignmentId, activityId, resourceId, periodStart, units, cost };
}

const periods: AssignmentPeriod[] = [
  period("AS-1", "A120", "2026-11-01", "4", "400"),
  period("AS-1", "A120", "2026-10-01", "6", "600"),
  period("AS-1", "A110", "2026-10-01", "2", "250"),
  period("AS-2", "A110", "2026-10-01", "1", "125.5"),
  period("AS-2", "A110", "2026-11-01", "3", "300"),
];

function source(overrides: Partial<ActivityUsageSource> = {}): ActivityUsageSource {
  return { status: "loaded", errorCode: null, periods, ...overrides };
}

test("activity usage spreadsheet sums stored periods per activity and period", () => {
  const model = buildActivityUsageSpreadsheet({ periods, activities, metric: "units", scope: "all" });
  assert.deepEqual(model.periods, ["2026-10-01", "2026-11-01"]);
  assert.deepEqual(model.rows.map((row) => row.activityId), ["A110", "A120"]);
  assert.deepEqual(model.rows[0]?.values.map((cell) => cell.value), ["3", "3"]);
  assert.deepEqual(model.rows[1]?.values.map((cell) => cell.value), ["6", "4"]);
  assert.equal(model.rows[0]?.total, "6");
  assert.equal(model.rows[1]?.total, "10");
  // Two assignments (AS-1 2 + AS-2 1) are summed, never averaged.
  assert.deepEqual(model.periodTotals.map((cell) => cell.value), ["9", "7"]);
  assert.equal(model.grandTotal, "16");
  assert.equal(model.storedPeriodCount, 5);
  assert.equal(model.storedActivityCount, 2);
});

test("activity usage cost metric reads the stored cost, not a derived rate", () => {
  const model = buildActivityUsageSpreadsheet({ periods, activities, metric: "cost", scope: "all" });
  assert.deepEqual(model.rows[0]?.values.map((cell) => cell.value), ["375.5", "300"]);
  assert.deepEqual(model.periodTotals.map((cell) => cell.value), ["975.5", "700"]);
  assert.equal(model.grandTotal, "1675.5");
});

test("activity usage selection scope filters rows without inventing values", () => {
  const selected = buildActivityUsageSpreadsheet({
    periods,
    activities,
    metric: "units",
    scope: "selected",
    selectedIds: ["A120"],
  });
  assert.deepEqual(selected.rows.map((row) => row.activityId), ["A120"]);
  assert.deepEqual(selected.periods, ["2026-10-01", "2026-11-01"]);
  assert.equal(selected.grandTotal, "10");
  const none = buildActivityUsageSpreadsheet({
    periods,
    activities,
    metric: "units",
    scope: "selected",
    selectedIds: [],
  });
  assert.deepEqual(none.rows, []);
  assert.deepEqual(none.periods, []);
  assert.equal(none.grandTotal, null);
  assert.equal(none.storedPeriodCount, periods.length);
});

test("activity usage keeps exact decimal sums and unknown activity ids", () => {
  const exact = buildActivityUsageSpreadsheet({
    periods: [period("AS-1", "GHOST", "2026-10-01", "0.1", "0.1"), period("AS-2", "GHOST", "2026-10-01", "0.2", "0.2")],
    activities,
    metric: "units",
    scope: "all",
  });
  assert.equal(exact.rows[0]?.activityId, "GHOST");
  assert.equal(exact.rows[0]?.label, "GHOST");
  assert.equal(exact.rows[0]?.values[0]?.value, "0.3");
  assert.equal(exact.rows[0]?.total, "0.3");
});

test("activity usage profile aggregates the same stored facts into one bar per period", () => {
  const model = buildActivityUsageSpreadsheet({ periods, activities, metric: "units", scope: "all" });
  const profile = buildActivityUsageProfile(model);
  assert.deepEqual(profile.points.map((point) => [point.periodStart, point.value]), [
    ["2026-10-01", "9"],
    ["2026-11-01", "7"],
  ]);
  assert.equal(profile.total, "16");
  assert.equal(profile.peak, "9");
  assert.equal(buildActivityUsageProfile(buildActivityUsageSpreadsheet({ periods: [], activities, metric: "units", scope: "all" })).peak, null);
});

test("activity usage spreadsheet renders read-only cells, totals and escaped labels", () => {
  const html = renderActivityUsage({
    view: "spreadsheet",
    source: source(),
    activities: [{ id: "A110", code: "A110", name: "<b>Design</b>" }],
    selectedIds: [],
    locale: "en",
    prefs: ACTIVITY_USAGE_DEFAULT_PREFS,
  });
  assert.match(html, /data-usage-view="spreadsheet"/);
  assert.match(html, /data-usage-metric="units"/);
  assert.match(html, /data-usage-scope="all"/);
  assert.match(html, /data-usage-cell data-activity-id="A110" data-period-start="2026-10-01" data-value="3"/);
  assert.match(html, /data-usage-period-total data-period-start="2026-10-01" data-value="9"/);
  assert.match(html, /data-usage-grand-total data-value="16"/);
  assert.match(html, /data-usage-row-total="6"/);
  assert.doesNotMatch(html, /<b>Design<\/b>/);
  assert.match(html, /&lt;b&gt;Design&lt;\/b&gt;/);
  assert.match(html, /Read-only projection of 5 stored assignment period/);
});

test("activity usage renderer explains loading, errors, empty projects and empty scopes", () => {
  const loading = renderActivityUsage({
    view: "profile",
    source: source({ status: "loading", periods: [] }),
    activities,
    selectedIds: [],
    locale: "en",
    prefs: ACTIVITY_USAGE_DEFAULT_PREFS,
  });
  assert.match(loading, /data-usage-status="loading"/);
  const error = renderActivityUsage({
    view: "spreadsheet",
    source: source({ status: "error", errorCode: "READ_FAILED", periods: [] }),
    activities,
    selectedIds: [],
    locale: "en",
    prefs: ACTIVITY_USAGE_DEFAULT_PREFS,
  });
  assert.match(error, /data-usage-status="error"/);
  assert.match(error, /READ_FAILED/);
  const empty = renderActivityUsage({
    view: "spreadsheet",
    source: source({ periods: [] }),
    activities,
    selectedIds: [],
    locale: "en",
    prefs: ACTIVITY_USAGE_DEFAULT_PREFS,
  });
  assert.match(empty, /data-usage-status="empty"/);
  const scopeEmpty = renderActivityUsage({
    view: "profile",
    source: source(),
    activities,
    selectedIds: [],
    locale: "en",
    prefs: { metric: "units", scope: "selected" },
  });
  assert.match(scopeEmpty, /data-usage-status="scope-empty"/);
});

test("activity usage profile renderer labels each bar and uses presentation prefs", () => {
  const html = renderActivityUsage({
    view: "profile",
    source: source(),
    activities,
    selectedIds: [],
    locale: "en",
    prefs: { metric: "cost", scope: "all" },
  });
  assert.match(html, /data-usage-view="profile"/);
  assert.match(html, /data-usage-metric="cost"/);
  assert.match(html, /data-usage-profile-bar data-period-start="2026-10-01" data-value="975.5"/);
  assert.match(html, /data-usage-profile-bar data-period-start="2026-11-01" data-value="700"/);
  assert.match(html, /style="height:100%"/);
  assert.match(html, /style="height:72%"/);
  assert.match(html, /data-usage-profile-summary/);
  assert.match(html, /total 1675.5/);
  assert.match(html, /peak 975.5/);
});

test("activity usage renderer localizes Persian headings and controls", () => {
  const html = renderActivityUsage({
    view: "profile",
    source: source(),
    activities,
    selectedIds: [],
    locale: "fa-IR",
    prefs: ACTIVITY_USAGE_DEFAULT_PREFS,
  });
  assert.match(html, /نیم‌رخ مصرف فعالیت/);
  assert.match(html, /همهٔ فعالیت‌ها/);
  assert.match(html, /واحدها/);
});

test("activity usage preferences round-trip per tenant and project and survive failures", () => {
  const rows = new Map<string, string>();
  const storage = {
    getItem: (key: string) => rows.get(key) ?? null,
    setItem: (key: string, value: string) => { rows.set(key, value); },
  };
  const context = { tenant_id: "tenant-1", project_id: "preview-rps-01" };
  assert.deepEqual(readActivityUsagePrefs(storage, context), ACTIVITY_USAGE_DEFAULT_PREFS);
  storeActivityUsagePrefs(storage, context, { metric: "cost", scope: "selected" });
  assert.deepEqual(readActivityUsagePrefs(storage, context), { metric: "cost", scope: "selected" });
  assert.deepEqual(readActivityUsagePrefs(storage, { ...context, project_id: "other" }), ACTIVITY_USAGE_DEFAULT_PREFS);
  rows.set("cubi:workspace:activity-usage:tenant-1:preview-rps-01", "not-json");
  assert.deepEqual(readActivityUsagePrefs(storage, context), ACTIVITY_USAGE_DEFAULT_PREFS);
  assert.deepEqual(normalizeActivityUsagePrefs({ metric: "cost", scope: "bogus" }), { metric: "cost", scope: "all" });
  assert.deepEqual(normalizeActivityUsagePrefs(null), ACTIVITY_USAGE_DEFAULT_PREFS);
  const broken = { getItem: () => { throw new Error("denied"); }, setItem: () => { throw new Error("denied"); } };
  assert.deepEqual(readActivityUsagePrefs(broken, context), ACTIVITY_USAGE_DEFAULT_PREFS);
  assert.deepEqual(storeActivityUsagePrefs(broken, context, { metric: "cost", scope: "selected" }), { metric: "cost", scope: "selected" });
});
