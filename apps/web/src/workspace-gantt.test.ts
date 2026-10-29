import assert from "node:assert/strict";
import test from "node:test";

import { createGanttAxisTicks, createGanttBarGeometry, createGanttLinkGeometry, createGanttScale } from "./workspace-gantt.js";

const activities = [
  {
    id: "A-1",
    wbsId: "W-1",
    code: "01",
    name: "Foundation",
    gantt: {
      start: "2026-09-01T08:00:00Z",
      finish: "2026-09-05T17:00:00Z",
      progressPercent: 35,
      critical: true,
    },
  },
  {
    id: "A-2",
    wbsId: "W-1",
    code: "02",
    name: "Structure",
    gantt: {
      start: "2026-09-04T08:00:00Z",
      finish: "2026-09-10T17:00:00Z",
      progressPercent: 10,
      critical: false,
    },
  },
] as const;

test("Gantt scale derives only from authoritative activity dates", () => {
  const scale = createGanttScale(activities);
  assert.ok(scale);
  assert.equal(scale?.startMs, Date.parse("2026-09-01T08:00:00Z"));
  assert.equal(scale?.endMs, Date.parse("2026-09-10T17:00:00Z"));
});

test("unchanged Gantt presentation data reuses cached scale and geometry", () => {
  const scale = createGanttScale(activities);
  assert.ok(scale);
  const repeatedScale = createGanttScale(activities);
  assert.strictEqual(repeatedScale, scale);

  const geometry = createGanttBarGeometry(activities[0], scale);
  const repeatedGeometry = createGanttBarGeometry(activities[0], scale);
  assert.ok(geometry);
  assert.strictEqual(repeatedGeometry, geometry);
});

test("repeated Gantt presentation renders eliminate repeated date parsing", () => {
  const renderActivities = activities.map((activity) => ({ ...activity, gantt: activity.gantt ? { ...activity.gantt } : undefined }));
  let parseCount = 0;
  const originalParse = Date.parse;
  Date.parse = ((value: string) => {
    parseCount += 1;
    return originalParse(value);
  }) as typeof Date.parse;

  try {
    const scale = createGanttScale(renderActivities);
    assert.ok(scale);
    renderActivities.forEach((activity) => {
      createGanttBarGeometry(activity, scale);
    });
    const firstRenderParses = parseCount;

    parseCount = 0;
    const repeatedScale = createGanttScale(renderActivities);
    assert.strictEqual(repeatedScale, scale);
    renderActivities.forEach((activity) => {
      createGanttBarGeometry(activity, scale);
    });

    assert.equal(firstRenderParses, renderActivities.length * 4);
    assert.equal(parseCount, 0);
  } finally {
    Date.parse = originalParse;
  }
});

test("Gantt bar geometry maps scheduled dates to visual percentages", () => {
  const scale = createGanttScale(activities);
  assert.ok(scale);
  const bar = createGanttBarGeometry(activities[0], scale);
  assert.ok(bar);
  assert.equal(bar?.activityId, "A-1");
  assert.equal(bar?.leftPercent, 0);
  assert.equal(bar?.critical, true);
  assert.equal(bar?.progressPercent, 35);
  assert.ok((bar?.widthPercent ?? 0) > 0);
});

test("missing scheduled dates produce no Gantt geometry", () => {
  const scale = createGanttScale(activities);
  assert.ok(scale);
  const bar = createGanttBarGeometry(
    { id: "A-3", wbsId: "W-1", code: "03", name: "Unscheduled" },
    scale,
  );
  assert.equal(bar, null);
});

test("zero-duration activities are reported as milestones", () => {
  const scheduled = [
    { id: "M-1", wbsId: "W-1", code: "M1", name: "Start milestone", gantt: { start: "2026-09-01T00:00:00Z", finish: "2026-09-01T00:00:00Z", progressPercent: 0, critical: true } },
    { id: "A-1", wbsId: "W-1", code: "01", name: "Work", gantt: { start: "2026-09-01T00:00:00Z", finish: "2026-09-03T00:00:00Z", progressPercent: 0, critical: true } },
  ];
  const scale = createGanttScale(scheduled);
  assert.ok(scale);
  assert.equal(createGanttBarGeometry(scheduled[0], scale)?.milestone, true);
  assert.equal(createGanttBarGeometry(scheduled[1], scale)?.milestone, false);
});

test("Gantt links keep the persisted FS and SS semantics without conversion", () => {
  const scheduled = [
    { id: "A-1", wbsId: "W-1", code: "01", name: "Excavate", gantt: { start: "2026-09-02T00:00:00Z", finish: "2026-09-03T00:00:00Z", progressPercent: 0, critical: true } },
    { id: "A-2", wbsId: "W-1", code: "02", name: "Concrete", gantt: { start: "2026-09-03T00:00:00Z", finish: "2026-09-05T00:00:00Z", progressPercent: 0, critical: true } },
  ];
  const scale = createGanttScale(scheduled);
  assert.ok(scale);
  const bars = scheduled
    .map((activity) => createGanttBarGeometry(activity, scale))
    .filter((bar): bar is NonNullable<typeof bar> => bar !== null);
  const links = createGanttLinkGeometry([
    { id: "R-FS", predecessorId: "A-1", successorId: "A-2", type: "FS", lagValue: "0", lagUnit: "working-day", recordRevision: 1 },
    { id: "R-SS", predecessorId: "A-1", successorId: "A-2", type: "SS", lagValue: "1", lagUnit: "working-day", recordRevision: 1 },
  ], bars);
  assert.equal(links.length, 2);
  const fs = links.find((link) => link.relationshipId === "R-FS");
  const ss = links.find((link) => link.relationshipId === "R-SS");
  assert.equal(fs?.type, "FS");
  assert.equal(ss?.type, "SS");
  assert.equal(fs?.predecessorId, "A-1");
  assert.equal(fs?.successorId, "A-2");
  assert.equal(fs?.critical, true);
  // A-1 finishes at 33.33%, A-2 starts at 33.33% of the shared 3-day scale.
  assert.match(fs?.path ?? "", /^M 33\.33 50 H 34\.83 V 150 H 33\.33$/);
  // SS departs from the predecessor start (0%) and enters the successor start (33.33%).
  assert.match(ss?.path ?? "", /^M 0 50 H 0 V 150 H 33\.33$/);
});

test("Gantt links skip relationships whose endpoints are filtered out", () => {
  const scale = createGanttScale(activities);
  assert.ok(scale);
  const bars = [createGanttBarGeometry(activities[0], scale)].filter((bar) => bar !== null);
  const links = createGanttLinkGeometry([
    { id: "R-1", predecessorId: "A-1", successorId: "A-2", type: "FS", lagValue: "0", lagUnit: "working-day", recordRevision: 1 },
  ], bars);
  assert.deepEqual(links, []);
});

test("Gantt axis ticks follow the selected day/week/month/quarter/year scale", () => {
  const scale = {
    startMs: Date.parse("2026-09-28T00:00:00Z"),
    endMs: Date.parse("2028-11-05T00:00:00Z"),
    rangeMs: Date.parse("2028-11-05T00:00:00Z") - Date.parse("2026-09-28T00:00:00Z"),
  };
  const day = createGanttAxisTicks(scale, "day");
  assert.equal(day[0].date, "2026-09-28");
  assert.equal(day[0].leftPercent, 0);
  assert.equal(day[1].date, "2026-09-29");

  const week = createGanttAxisTicks(scale, "week");
  assert.deepEqual(week.slice(0, 3).map((tick) => tick.date), ["2026-09-28", "2026-10-05", "2026-10-12"]);

  const month = createGanttAxisTicks(scale, "month");
  assert.deepEqual(month.slice(0, 4).map((tick) => tick.date), ["2026-09-28", "2026-10-01", "2026-11-01", "2026-12-01"]);

  const quarter = createGanttAxisTicks(scale, "quarter");
  assert.deepEqual(quarter.slice(0, 5).map((tick) => tick.date), ["2026-09-28", "2027-01-01", "2027-04-01", "2027-07-01", "2027-10-01"]);

  const year = createGanttAxisTicks(scale, "year");
  assert.deepEqual(year.map((tick) => tick.date), ["2026-09-28", "2027-01-01", "2028-01-01"]);
  assert.ok(year[2].leftPercent > 85 && year[2].leftPercent <= 100);
});
