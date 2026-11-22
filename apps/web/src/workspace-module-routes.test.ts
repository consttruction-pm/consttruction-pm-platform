import assert from "node:assert/strict";
import test from "node:test";

import { WORKSPACE_MODULE_PATH_MENUS, moduleMenuFromPath } from "./workspace-module-routes.js";

test("a module address selects that workspace window on refresh", () => {
  assert.equal(moduleMenuFromPath("/app/activities/"), "schedule");
  assert.equal(moduleMenuFromPath("/app/wbs/"), "wbs");
  assert.equal(moduleMenuFromPath("/app/calendars"), "calendars");
  assert.equal(moduleMenuFromPath("/app/costs/"), "cost");
  assert.equal(moduleMenuFromPath("/app/relationships/"), undefined);
});

test("the plain workspace address keeps the remembered window", () => {
  assert.equal(moduleMenuFromPath("/app"), undefined);
  assert.equal(moduleMenuFromPath("/app/"), undefined);
  assert.equal(moduleMenuFromPath("/app/unknown-module/"), undefined);
  assert.equal(moduleMenuFromPath("/workbench/"), undefined);
  assert.equal(moduleMenuFromPath("/"), undefined);
});

test("every published module path maps to a real window key", () => {
  const keys = new Set(Object.values(WORKSPACE_MODULE_PATH_MENUS));
  for (const key of keys) {
    assert.match(key, /^[a-z]+$/);
  }
  assert.equal(WORKSPACE_MODULE_PATH_MENUS.activities, "schedule");
});
