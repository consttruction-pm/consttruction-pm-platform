import assert from "node:assert/strict";
import test from "node:test";

import type { ProjectContext } from "./client.js";
import {
  CachedWorkspaceReadClient,
  type WorkspaceReadCacheReader,
} from "./workspace-read-cache.js";

const context: ProjectContext = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  revision: 7,
};

function readSnapshot(revision = context.revision): Record<string, unknown> {
  return {
    contract_version: "workspace-control-room-read.v1",
    context: { ...context, revision },
    workspace: {
      contract_version: "workspace-control-room.v1",
      context: { ...context, revision },
      columns: [{
        id: "activity_id",
        label: "Activity ID",
        data_type: "text",
        editable: false,
        formula: null,
        width: 120,
      }],
      activities: [{
        id: "A-101",
        wbs_id: "WBS-1",
        code: "A-101",
        name: "Foundation",
        cells: {
          activity_id: "A-101",
          duration: 4,
          progress: 25,
        },
        gantt: {
          start: "2026-09-01T08:00:00Z",
          finish: "2026-09-04T17:00:00Z",
          progressPercent: 25,
          critical: true,
        },
      }],
    },
    control_intelligence: null,
    field_daily_logs: [],
    field_issues: [],
    field_timecards: [],
    equipment_status_reports: [],
    inspections: [],
    quality_records: [],
    safety_observations: [],
    punch_items: [],
  };
}

class StubCacheReader implements WorkspaceReadCacheReader {
  calls = 0;
  constructor(
    private readonly result: {
      mode: "online" | "offline";
      state: "fresh" | "stale";
      cache: { workspace_read: Readonly<Record<string, unknown>> };
    },
  ) {}

  async read(): Promise<{
    mode: "online" | "offline";
    state: "fresh" | "stale";
    cache: { workspace_read: Readonly<Record<string, unknown>> };
  }> {
    this.calls += 1;
    return this.result;
  }
}

test("Web hydrates from the shared cache adapter while preserving fresh state", async () => {
  const reader = new StubCacheReader({
    mode: "online",
    state: "fresh",
    cache: { workspace_read: readSnapshot() },
  });

  const result = await new CachedWorkspaceReadClient(reader).load(context, true, {
    locale: "en",
    calendarMode: "gregorian",
  });

  assert.equal(result.mode, "online");
  assert.equal(result.cacheState, "fresh");
  assert.equal(result.data.activities[0]?.id, "A-101");
  assert.equal(result.data.activities[0]?.cells?.duration, 4);
  assert.equal(result.data.activities[0]?.gantt?.critical, true);
  assert.equal(reader.calls, 1);
});

test("Web can render a stale cached snapshot while offline without recalculating it", async () => {
  const reader = new StubCacheReader({
    mode: "offline",
    state: "stale",
    cache: { workspace_read: readSnapshot(6) },
  });

  const result = await new CachedWorkspaceReadClient(reader).load(
    { ...context, revision: 7 },
    false,
  );

  assert.equal(result.mode, "offline");
  assert.equal(result.cacheState, "stale");
  assert.equal(result.data.context.revision, 6);
  assert.equal(result.data.activities[0]?.cells?.duration, 4);
  assert.equal(result.data.activities[0]?.gantt?.progressPercent, 25);
});

test("Web does not evaluate formula columns locally", async () => {
  const snapshot = readSnapshot();
  const workspace = snapshot.workspace as Record<string, unknown>;
  const columns = workspace.columns as Array<Record<string, unknown>>;
  columns.push({
    id: "planned_value",
    label: "Planned Value",
    data_type: "decimal",
    editable: false,
    formula: "duration * 100",
    width: 120,
  });

  const reader = new StubCacheReader({
    mode: "online",
    state: "fresh",
    cache: { workspace_read: snapshot },
  });

  const result = await new CachedWorkspaceReadClient(reader).load(context, true);
  assert.equal(result.data.columns.find((column) => column.id === "planned_value")?.formula, "duration * 100");
  assert.equal(result.data.activities[0]?.cells?.planned_value, undefined);
});
