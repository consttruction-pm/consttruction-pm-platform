import assert from "node:assert/strict";
import test from "node:test";
import { MobileRuntime } from "./runtime.ts";
import {
  InMemoryMobileLocalProjectStore,
  MobileProjectShell,
  type MobileLocalProject,
} from "./project-shell.ts";

const fixture: MobileLocalProject = {
  tenant_id: "t1",
  project_id: "p1",
  revision: 12,
  name: "Demo Project",
  wbs: [
    { id: "W1", code: "1", name: "Execution", parent_id: null, order: 1 },
    { id: "W2", code: "1.1", name: "Structure", parent_id: "W1", order: 2 },
  ],
  activities: [
    { id: "A1", wbs_id: "W2", name: "Foundation", order: 1 },
    { id: "A2", wbs_id: "W2", name: "Frame", order: 2 },
  ],
};

test("opens a local project into the WBS shell without network or scheduling calls", async () => {
  const runtime = new MobileRuntime();
  const shell = new MobileProjectShell(
    runtime,
    new InMemoryMobileLocalProjectStore([fixture]),
  );

  const state = await shell.openLocalProject("t1", "p1");

  assert.equal(state.screen, "wbs");
  assert.deepEqual(runtime.current(), {
    tenant_id: "t1",
    project_id: "p1",
    revision: 12,
    mode: "offline",
  });
  assert.equal(shell.listWbs().length, 2);
});

test("navigates from WBS to an activity only when activity belongs to selected WBS", async () => {
  const shell = new MobileProjectShell(
    new MobileRuntime(),
    new InMemoryMobileLocalProjectStore([fixture]),
  );
  await shell.openLocalProject("t1", "p1");

  const activities = shell.listActivities("W2");
  assert.deepEqual(activities.map((item) => item.id), ["A1", "A2"]);

  const state = shell.showActivity("W2", "A2");
  assert.equal(state.screen, "activity");
  assert.equal(state.selected_wbs_id, "W2");
  assert.equal(state.selected_activity_id, "A2");
});

test("rejects invalid local project and cross-WBS activity navigation", async () => {
  const shell = new MobileProjectShell(
    new MobileRuntime(),
    new InMemoryMobileLocalProjectStore([fixture]),
  );

  await assert.rejects(shell.openLocalProject("t1", "missing"), /LOCAL_PROJECT_NOT_FOUND/);
  await shell.openLocalProject("t1", "p1");
  await assert.rejects(shell.showActivity("W1", "A1"), /ACTIVITY_NOT_FOUND/);
  await assert.rejects(shell.listActivities("missing"), /WBS_NOT_FOUND/);
});

test("returns to WBS without losing the opened project context", async () => {
  const runtime = new MobileRuntime();
  const shell = new MobileProjectShell(
    runtime,
    new InMemoryMobileLocalProjectStore([fixture]),
  );
  await shell.openLocalProject("t1", "p1");
  shell.showActivity("W2", "A1");

  const state = shell.showWbs();
  assert.equal(state.screen, "wbs");
  assert.equal(state.selected_activity_id, null);
  assert.deepEqual(runtime.current(), {
    tenant_id: "t1",
    project_id: "p1",
    revision: 12,
    mode: "offline",
  });
});
