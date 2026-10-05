import assert from "node:assert/strict";
import test from "node:test";
import { MobileRuntime } from "./runtime.ts";
import {
  InMemoryMobileLocalProjectStore,
  MobileProjectShell,
  type MobileLocalProject,
} from "./project-shell.ts";
import { MOBILE_SCHEDULING_CONTRACT_VERSION, type MobileSchedulingRequest } from "./shared-scheduling-adapter.ts";

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
  relationships: [
    { predecessor_id: "A1", successor_id: "A2", type: "FS", lag: { value: "2", unit: "WORKING_DAY" } },
    { predecessor_id: "A2", successor_id: "A1", type: "SS", lag: { value: "-1", unit: "WORKING_DAY" } },
    { predecessor_id: "A2", successor_id: "A1", type: "FF", lag: { value: "0", unit: "WORKING_DAY" } },
    { predecessor_id: "A1", successor_id: "A2", type: "SF", lag: { value: "3", unit: "WORKING_HOUR" } },
  ],
};

const schedulingRequest: MobileSchedulingRequest = {
  contract_version: MOBILE_SCHEDULING_CONTRACT_VERSION,
  project_schema_version: 2,
  tenant_id: "t1",
  project_id: "p1",
  project_revision: 12,
  calculation_schema_version: "calc.v1",
  calendar_assignments: {
    project_calendar: { calendar_id: "site", calendar_version: 3, kind: "working-day" },
  },
  scheduling_settings: {
    duration: "working-day",
    calendar: "jalali-gregorian",
    lag: "working",
    constraints: "hybrid",
    mode: "both",
  },
  project_start: "2026-10-05",
  project_finish: null,
  data_date: "2026-10-05",
  activities: [
    { id: "A1", duration: { value: "2", unit: "WORKING_DAY" } },
    { id: "A2", duration: { value: "1", unit: "WORKING_DAY" } },
  ],
  relationships: [
    { predecessor_id: "A1", successor_id: "A2", type: "FS", lag: { value: "0", unit: "WORKING_DAY" } },
  ],
  constraints: [],
};

function deterministicResult() {
  return {
    contract_version: MOBILE_SCHEDULING_CONTRACT_VERSION,
    calculation_fingerprint: "core-fp-001",
    project_finish: "2026-10-07",
    activities: [
      {
        activity_id: "A1",
        start: "2026-10-05",
        finish: "2026-10-06",
        duration: { value: "2", unit: "WORKING_DAY" as const },
        total_float: { value: "0", unit: "WORKING_DAY" as const },
        free_float: { value: "0", unit: "WORKING_DAY" as const },
        critical: true,
      },
      {
        activity_id: "A2",
        start: "2026-10-07",
        finish: "2026-10-07",
        duration: { value: "1", unit: "WORKING_DAY" as const },
        total_float: { value: "0", unit: "WORKING_DAY" as const },
        free_float: { value: "0", unit: "WORKING_DAY" as const },
        critical: true,
      },
    ],
  };
}

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
  assert.equal(state.schedule_result, null);
  assert.equal(shell.listWbs().length, 2);
});

test("creates and edits WBS and Activity locally with revision continuity", async () => {
  const runtime = new MobileRuntime();
  const store = new InMemoryMobileLocalProjectStore([fixture]);
  const shell = new MobileProjectShell(runtime, store);
  await shell.openLocalProject("t1", "p1");

  const afterWbs = await shell.addWbsNode({ id: "W3", code: "1.2", name: "Finishes", parent_id: "W1" });
  assert.equal(afterWbs.project?.revision, 13);
  assert.deepEqual(shell.listWbs().map((item) => item.id), ["W1", "W2", "W3"]);

  const afterWbsEdit = await shell.updateWbsNode("W3", { name: "Finishes & Closeout" });
  assert.equal(afterWbsEdit.project?.revision, 14);

  const afterActivity = await shell.addActivity({ id: "A3", wbs_id: "W3", name: "Closeout" });
  assert.equal(afterActivity.project?.revision, 15);
  assert.deepEqual(shell.listActivities("W3").map((item) => item.name), ["Closeout"]);

  const afterActivityEdit = await shell.updateActivity("A3", { name: "Final Closeout", wbs_id: "W2" });
  assert.equal(afterActivityEdit.project?.revision, 16);
  assert.deepEqual(shell.listActivities("W2").map((item) => item.name), ["Foundation", "Frame", "Final Closeout"]);
  assert.equal(shell.listActivities("W2")[2]?.order, 3);
  assert.equal(runtime.current().revision, 16);
  assert.equal(afterActivityEdit.schedule_result, null);
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

test("lists FS SS FF SF relationships with lag and lead for an activity", async () => {
  const shell = new MobileProjectShell(
    new MobileRuntime(),
    new InMemoryMobileLocalProjectStore([fixture]),
  );
  await shell.openLocalProject("t1", "p1");

  assert.deepEqual(shell.listRelationships("A1"), [
    { predecessor_id: "A1", successor_id: "A2", type: "FS", lag: { value: "2", unit: "WORKING_DAY" } },
    { predecessor_id: "A2", successor_id: "A1", type: "SS", lag: { value: "-1", unit: "WORKING_DAY" } },
    { predecessor_id: "A2", successor_id: "A1", type: "FF", lag: { value: "0", unit: "WORKING_DAY" } },
    { predecessor_id: "A1", successor_id: "A2", type: "SF", lag: { value: "3", unit: "WORKING_HOUR" } },
  ]);
});

test("rejects relationship lookup for an unknown activity", async () => {
  const shell = new MobileProjectShell(
    new MobileRuntime(),
    new InMemoryMobileLocalProjectStore([fixture]),
  );
  await shell.openLocalProject("t1", "p1");
  assert.throws(() => shell.listRelationships("missing"), /ACTIVITY_NOT_FOUND/);
});

test("rejects invalid WBS/Activity edits at the shell boundary", async () => {
  const shell = new MobileProjectShell(new MobileRuntime(), new InMemoryMobileLocalProjectStore([fixture]));
  await shell.openLocalProject("t1", "p1");
  await assert.rejects(shell.addWbsNode({ id: "W3", code: "1.2", name: "x", parent_id: "missing" }), /WBS_PARENT_NOT_FOUND/);
  await assert.rejects(shell.addActivity({ id: "A3", wbs_id: "missing", name: "x" }), /WBS_NOT_FOUND/);
  await assert.rejects(shell.updateActivity("missing", { name: "x" }), /ACTIVITY_NOT_FOUND/);
});

test("rejects indirect WBS parent cycles", async () => {
  const shell = new MobileProjectShell(new MobileRuntime(), new InMemoryMobileLocalProjectStore([fixture]));
  await shell.openLocalProject("t1", "p1");
  await shell.updateWbsNode("W1", { parent_id: null });
  await assert.rejects(shell.updateWbsNode("W1", { parent_id: "W2" }), /WBS_PARENT_CYCLE/);
});

test("rejects invalid local project and cross-WBS activity navigation", async () => {
  const shell = new MobileProjectShell(
    new MobileRuntime(),
    new InMemoryMobileLocalProjectStore([fixture]),
  );

  await assert.rejects(shell.openLocalProject("t1", "missing"), /LOCAL_PROJECT_NOT_FOUND/);
  await shell.openLocalProject("t1", "p1");
  assert.throws(() => shell.showActivity("W1", "A1"), /ACTIVITY_NOT_FOUND/);
  assert.throws(() => shell.listActivities("missing"), /WBS_NOT_FOUND/);
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

test("stores the validated Shared Core schedule result in the Mobile shell", async () => {
  const shell = new MobileProjectShell(
    new MobileRuntime(),
    new InMemoryMobileLocalProjectStore([fixture]),
  );
  await shell.openLocalProject("t1", "p1");

  const result = deterministicResult();
  let received: MobileSchedulingRequest | null = null;
  const core = {
    async schedule(input: MobileSchedulingRequest) {
      received = input;
      return result;
    },
  };

  const returned = await shell.schedule(core, schedulingRequest);

  assert.deepEqual(received, schedulingRequest);
  assert.deepEqual(returned, result);
  assert.deepEqual(shell.current().schedule_result, result);
  assert.equal(shell.current().schedule_result?.activities[0]?.start, "2026-10-05");
  assert.equal(shell.current().schedule_result?.activities[0]?.finish, "2026-10-06");
  assert.equal(shell.current().schedule_result?.activities[0]?.duration.value, "2");
  assert.equal(shell.current().schedule_result?.activities[0]?.total_float?.value, "0");
  assert.equal(shell.current().schedule_result?.activities[0]?.free_float?.value, "0");
  assert.equal(shell.current().schedule_result?.activities[0]?.critical, true);
});

test("preserves the runtime project-context guard when scheduling from the shell", async () => {
  const shell = new MobileProjectShell(
    new MobileRuntime(),
    new InMemoryMobileLocalProjectStore([fixture]),
  );
  await shell.openLocalProject("t1", "p1");

  await assert.rejects(
    shell.schedule(
      { async schedule() { return deterministicResult(); } },
      { ...schedulingRequest, project_revision: 11 },
    ),
    /PROJECT_CONTEXT_MISMATCH/,
  );
});
