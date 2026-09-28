import assert from "node:assert/strict";
import test from "node:test";

import { BETA_NAVIGATION, getBetaMenu } from "./beta-navigation.js";

test("V1 beta navigation contains every top-level workspace menu", () => {
  const keys = BETA_NAVIGATION.map((menu) => menu.key);
  assert.deepEqual(keys, [
    "project",
    "schedule",
    "progress",
    "resources",
    "cost",
    "documents",
    "reports",
    "control",
    "settings",
  ]);
});

test("each beta menu has at least one submenu and a completion status", () => {
  for (const menu of BETA_NAVIGATION) {
    assert.ok(menu.items.length > 0);
    for (const item of menu.items) {
      assert.ok(item.id);
      assert.ok(item.label);
      assert.ok(["Implemented", "Partial", "Preview"].includes(item.status));
    }
  }
});

test("schedule submenu exposes core P6 workflow surfaces", () => {
  const schedule = getBetaMenu("schedule");
  assert.deepEqual(
    schedule.items.map((item) => item.id),
    [
      "schedule.activities",
      "schedule.relationships",
      "schedule.calendars",
      "schedule.options",
      "schedule.recalculate",
      "schedule.float",
      "schedule.gantt",
    ],
  );
});
