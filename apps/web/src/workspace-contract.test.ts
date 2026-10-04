import assert from "node:assert/strict";
import test from "node:test";

import {
  createWorkspaceControlRoomSnapshot,
  workspaceActivitiesFromSnapshot,
  WORKSPACE_CONTROL_ROOM_CONTRACT_VERSION,
} from "./workspace-contract.js";
import { createWorkspaceState, withActivities } from "./workspace-model.js";

const context = { tenant_id: "tenant-1", project_id: "project-1", revision: 8 };

test("control-room snapshot is versioned and round-trips typed activity data", () => {
  let state = createWorkspaceState(context, "fa", "jalali");
  state = withActivities(state, [{
    id: "A-1",
    wbsId: "W-1",
    code: "01",
    name: "Foundation",
    cells: { start: "2026-09-01T08:00:00Z", duration: 4, progress: 25 },
    gantt: {
      start: "2026-09-01T08:00:00Z",
      finish: "2026-09-04T17:00:00Z",
      progressPercent: 25,
      critical: true,
    },
  }]);

  const snapshot = createWorkspaceControlRoomSnapshot(state);
  assert.equal(snapshot.contract_version, WORKSPACE_CONTROL_ROOM_CONTRACT_VERSION);
  assert.equal(snapshot.context.project_id, "project-1");
  assert.equal(snapshot.columns[0]?.data_type, "text");
  const activities = workspaceActivitiesFromSnapshot(snapshot);
  assert.equal(activities[0]?.cells?.duration, 4);
  assert.equal(activities[0]?.gantt?.critical, true);
});

test("contract adapter rejects duplicate activity identities", () => {
  const snapshot = createWorkspaceControlRoomSnapshot(createWorkspaceState(context));
  const broken = {
    ...snapshot,
    activities: [
      { id: "A-1", wbs_id: "W-1", code: "01", name: "One", cells: {}, gantt: null },
      { id: "A-1", wbs_id: "W-1", code: "02", name: "Two", cells: {}, gantt: null },
    ],
  };
  assert.throws(
    () => workspaceActivitiesFromSnapshot(broken as never),
    /DUPLICATE_WORKSPACE_ACTIVITY/,
  );
});

test("contract adapter rejects unknown contract versions", () => {
  const snapshot = createWorkspaceControlRoomSnapshot(createWorkspaceState(context));
  const broken = { ...snapshot, contract_version: "workspace-control-room.v99" };
  assert.throws(
    () => workspaceActivitiesFromSnapshot(broken as never),
    /UNSUPPORTED_WORKSPACE_CONTRACT/,
  );
});

test("contract adapter rejects malformed collections with stable errors", () => {
  const snapshot = createWorkspaceControlRoomSnapshot(createWorkspaceState(context));
  assert.throws(
    () => workspaceActivitiesFromSnapshot({ ...snapshot, activities: null } as never),
    /INVALID_WORKSPACE_COLLECTION/,
  );
  assert.throws(
    () => workspaceActivitiesFromSnapshot({ ...snapshot, columns: null } as never),
    /INVALID_WORKSPACE_COLLECTION/,
  );
  assert.throws(
    () => workspaceActivitiesFromSnapshot({
      ...snapshot,
      activities: [{ id: "", wbs_id: "W-1", code: "01", name: "One", cells: {}, gantt: null }],
    } as never),
    /INVALID_WORKSPACE_ACTIVITY/,
  );
});
