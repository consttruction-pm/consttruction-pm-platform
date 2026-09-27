import assert from "node:assert/strict";
import test from "node:test";
import type { ProjectContext } from "./api-sync-transport.js";
import {
  WorkspaceReadCacheAdapter,
  type WorkspaceControlRoomReadTransport,
  type WorkspaceReadCacheStore,
} from "./workspace-read-cache-adapter.js";
import type { WorkspaceControlRoomReadCache } from "./workspace-read-cache.js";

const context: ProjectContext = { tenant_id: "tenant-1", project_id: "project-1", revision: 7 };

function snapshot(revision = 7): Record<string, unknown> {
  return { contract_version: "workspace-control-room-read.v1", context: { ...context, revision }, workspace: {} };
}

class MemoryStore implements WorkspaceReadCacheStore {
  cache: WorkspaceControlRoomReadCache | null = null;
  saves = 0;
  async load(): Promise<WorkspaceControlRoomReadCache | null> { return this.cache; }
  async save(cache: WorkspaceControlRoomReadCache): Promise<void> { this.cache = cache; this.saves += 1; }
}

class Transport implements WorkspaceControlRoomReadTransport {
  fetches = 0;
  revision = 7;
  async fetch(): Promise<Record<string, unknown>> { this.fetches += 1; return snapshot(this.revision); }
}

test("uses fresh cache online without refetching", async () => {
  const store = new MemoryStore(); const transport = new Transport();
  const adapter = new WorkspaceReadCacheAdapter(transport, store);
  await adapter.read(context, true); const second = await adapter.read(context, true);
  assert.equal(second.state, "fresh"); assert.equal(transport.fetches, 1); assert.equal(store.saves, 1);
});

test("refreshes stale cache online from authoritative transport", async () => {
  const store = new MemoryStore(); const transport = new Transport();
  const adapter = new WorkspaceReadCacheAdapter(transport, store);
  await adapter.read(context, true); transport.revision = 8;
  const result = await adapter.read({ ...context, revision: 8 }, true);
  assert.equal(result.state, "fresh"); assert.equal(result.cache.source_revision, 8);
  assert.equal(transport.fetches, 2); assert.equal(store.saves, 2);
});

test("serves last known snapshot offline and exposes staleness", async () => {
  const store = new MemoryStore(); const transport = new Transport();
  const adapter = new WorkspaceReadCacheAdapter(transport, store);
  await adapter.read(context, true);
  const result = await adapter.read({ ...context, revision: 8 }, false);
  assert.equal(result.mode, "offline"); assert.equal(result.state, "stale");
  assert.equal(result.cache.source_revision, 7); assert.equal(transport.fetches, 1);
});

test("fails offline when no snapshot exists", async () => {
  await assert.rejects(
    () => new WorkspaceReadCacheAdapter(new Transport(), new MemoryStore()).read(context, false),
    /WORKSPACE_READ_UNAVAILABLE_OFFLINE/,
  );
});

test("rejects refresh response bound to another revision", async () => {
  const store = new MemoryStore(); const transport = new Transport(); transport.revision = 6;
  await assert.rejects(
    () => new WorkspaceReadCacheAdapter(transport, store).read(context, true),
    /WORKSPACE_READ_REFRESH_SCOPE_MISMATCH/,
  );
});
