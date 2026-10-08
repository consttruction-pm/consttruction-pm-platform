import assert from "node:assert/strict";
import test from "node:test";

import { createGanttBarGeometry, createGanttScale } from "./workspace-gantt.js";

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
