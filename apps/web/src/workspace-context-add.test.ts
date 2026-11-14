import assert from "node:assert/strict";
import test from "node:test";

import { contextAddCommands, type ContextAddState } from "./workspace-context-add.js";
import type { WorkspaceMenuKey } from "./workspace-model.js";

const base: ContextAddState = {
  activeMenu: "schedule",
  canWrite: true,
  hasWbs: true,
  hasSelectedActivity: true,
  hasCalendarCatalog: true,
};

function commands(overrides: Partial<ContextAddState>) {
  return contextAddCommands({ ...base, ...overrides });
}

function ids(menu: WorkspaceMenuKey, overrides: Partial<ContextAddState> = {}): string[] {
  return contextAddCommands({ ...base, activeMenu: menu, ...overrides }).map((item) => item.command);
}

test("each window receives only its real create commands", () => {
  assert.deepEqual(ids("schedule"), ["project.add-activity", "edit.link"]);
  assert.deepEqual(ids("project"), ["project.add-wbs", "project.add-activity"]);
  assert.deepEqual(ids("wbs"), ["project.add-wbs", "project.add-activity"]);
  assert.deepEqual(ids("resources"), ["resource.create", "activity.assign-resources"]);
  assert.deepEqual(ids("assignments"), ["assignment.create", "activity.assign-resources"]);
  assert.deepEqual(ids("roles"), ["role.create"]);
  assert.deepEqual(ids("calendars"), ["calendar.create"]);
  assert.deepEqual(ids("documents"), ["document.create"]);
  assert.deepEqual(ids("risks"), ["risk.create"]);
  assert.deepEqual(ids("issues"), ["issue.create"]);
  assert.deepEqual(ids("expenses"), ["expense.create"]);
  assert.deepEqual(ids("thresholds"), ["threshold.create"]);
  for (const empty of ["progress", "tracking", "control", "reports", "cost", "settings", "administration", "exchange", "backup"] as const) {
    assert.deepEqual(ids(empty), [], `${empty} has no create service and must not invent commands`);
  }
});

test("every command id is unique inside a window", () => {
  for (const menu of Object.keys({
    project: 1, wbs: 1, schedule: 1, resources: 1, assignments: 1, roles: 1, calendars: 1,
    documents: 1, risks: 1, issues: 1, expenses: 1, thresholds: 1,
  })) {
    const commands = ids(menu as WorkspaceMenuKey);
    assert.equal(new Set(commands).size, commands.length, `${menu} repeats a command`);
  }
});

test("a viewer keeps the commands visible but disabled with an exact reason", () => {
  const items = commands({ canWrite: false });
  assert.ok(items.length > 0);
  for (const item of items) {
    assert.equal(item.disabledReason?.en, "Requires the project planner or administrator role.");
  }
});

test("data preconditions disable commands with the blocking reason", () => {
  const schedule = commands({ activeMenu: "schedule", hasWbs: false, hasSelectedActivity: false });
  assert.equal(schedule[0].disabledReason?.en, "Add a WBS element before creating activities.");
  assert.equal(schedule[1].disabledReason?.en, "Select an activity in the register first.");

  const [calendar] = commands({ activeMenu: "calendars", hasCalendarCatalog: false });
  assert.equal(calendar.disabledReason?.en, "A base calendar must exist before a calendar can be created.");

  const [assign] = commands({ activeMenu: "resources", hasSelectedActivity: false }).slice(1);
  assert.equal(assign.disabledReason?.en, "Select an activity in the register first.");

  // The write role is reported first: a viewer with no WBS still reads the
  // permission reason rather than a data reason they cannot fix.
  const viewer = commands({ activeMenu: "wbs", canWrite: false, hasWbs: false });
  assert.equal(viewer[1].disabledReason?.en, "Requires the project planner or administrator role.");
});

test("labels and icons are supplied for every entry", () => {
  const items = [
    ...commands({ activeMenu: "schedule" }),
    ...commands({ activeMenu: "resources" }),
    ...commands({ activeMenu: "documents" }),
  ];
  for (const item of items) {
    assert.ok(item.label.en.length > 0);
    assert.ok(item.label.fa.length > 0);
    assert.ok(item.icon.length > 0);
  }
});
