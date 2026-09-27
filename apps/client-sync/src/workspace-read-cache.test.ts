import assert from "node:assert/strict";
import test from "node:test";

import type { ProjectContext } from "./api-sync-transport.js";
import {
  WORKSPACE_CONTROL_ROOM_CACHE_VERSION,
  classifyWorkspaceReadCache,
  createWorkspaceReadCache,
  validateWorkspaceReadCache,
} from "./workspace-read-cache.js";

const context: ProjectContext = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  revision: 7,
};

function snapshot(revision = 7): Record<string, unknown> {
  return {
    contract_version: "workspace-control-room-read.v1",
    context: { ...context, revision },
    workspace: {},
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

test("creates an immutable cache entry with authoritative scope", () => {
  const entry = createWorkspaceReadCache(snapshot(), {
    snapshot_id: "snapshot-7",
    cached_at: "2026-09-27T16:00:00Z",
  });

  assert.equal(entry.contract_version, WORKSPACE_CONTROL_ROOM_CACHE_VERSION);
  assert.equal(entry.tenant_id, "tenant-1");
  assert.equal(entry.project_id, "project-1");
  assert.equal(entry.source_revision, 7);
  assert.equal(classifyWorkspaceReadCache(entry, context), "fresh");
  assert.equal(Object.isFrozen(entry), true);
  assert.equal(Object.isFrozen(entry.workspace_read), true);
});

test("classifies a revision change as stale", () => {
  const entry = createWorkspaceReadCache(snapshot(), {
    snapshot_id: "snapshot-7",
    cached_at: "2026-09-27T16:00:00Z",
  });

  assert.equal(
    classifyWorkspaceReadCache(entry, { ...context, revision: 8 }),
    "stale",
  );
});

test("classifies a tenant or project change as stale", () => {
  const entry = createWorkspaceReadCache(snapshot(), {
    snapshot_id: "snapshot-7",
    cached_at: "2026-09-27T16:00:00Z",
  });

  assert.equal(
    classifyWorkspaceReadCache(entry, { ...context, tenant_id: "tenant-2" }),
    "stale",
  );
  assert.equal(
    classifyWorkspaceReadCache(entry, { ...context, project_id: "project-2" }),
    "stale",
  );
});

test("rejects a cache whose metadata does not match the cached read snapshot", () => {
  const entry = createWorkspaceReadCache(snapshot(), {
    snapshot_id: "snapshot-7",
    cached_at: "2026-09-27T16:00:00Z",
  });

  const invalid = {
    ...entry,
    source_revision: 6,
  } as typeof entry;

  assert.throws(
    () => validateWorkspaceReadCache(invalid),
    /CACHE_SNAPSHOT_SCOPE_MISMATCH/,
  );
});

test("rejects an unsupported cache contract", () => {
  const entry = createWorkspaceReadCache(snapshot(), {
    snapshot_id: "snapshot-7",
    cached_at: "2026-09-27T16:00:00Z",
  });

  assert.throws(
    () =>
      validateWorkspaceReadCache({
        ...entry,
        contract_version: "workspace-control-room-cache.v99",
      } as never),
    /UNSUPPORTED_WORKSPACE_READ_CACHE_CONTRACT/,
  );
});

test("does not accept a cache snapshot from a different project revision", () => {
  assert.throws(
    () =>
      createWorkspaceReadCache(snapshot(6), {
        snapshot_id: "snapshot-6",
        cached_at: "2026-09-27T16:00:00Z",
      }),
    () => false,
  );
  const entry = createWorkspaceReadCache(snapshot(6), {
    snapshot_id: "snapshot-6",
    cached_at: "2026-09-27T16:00:00Z",
  });
  assert.equal(classifyWorkspaceReadCache(entry, context), "stale");
});
