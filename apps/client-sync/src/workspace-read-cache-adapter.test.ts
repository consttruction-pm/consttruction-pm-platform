import assert from "node:assert/strict";
import test from "node:test";
import type { SyncProjectContext } from "./api-sync-transport.js";
import {
  WorkspaceReadCacheAdapter,
  type WorkspaceControlRoomReadTransport,
  type WorkspaceReadCacheStore,
} from "./workspace-read-cache-adapter.js";
import type { WorkspaceControlRoomReadCache } from "./workspace-read-cache.js";

const context: SyncProjectContext = { tenant_id: "tenant-1", project_id: "project-1", revision: 7 };

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
  assert.ok(result.cache);
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

test("does not reuse a cache from another tenant or project", async () => {
  const store = new MemoryStore(); const transport = new Transport();
  const adapter = new WorkspaceReadCacheAdapter(transport, store);
  await adapter.read(context, true);
  const result = await adapter.read(
    { tenant_id: "tenant-2", project_id: "project-2", revision: 7 },
    true,
  );
  assert.equal(result.state, "fresh");
  assert.equal(result.cache.tenant_id, "tenant-2");
  assert.equal(result.cache.project_id, "project-2");
  assert.equal(transport.fetches, 2);
});

test("online stale cache is replaced only by an authoritative snapshot at the requested revision", async () => {
  const store = new MemoryStore(); const transport = new Transport();
  const adapter = new WorkspaceReadCacheAdapter(transport, store);
  await adapter.read(context, true);
  transport.revision = 8;
  const result = await adapter.read({ ...context, revision: 8 }, true);
  assert.equal(result.mode, "online");
  assert.equal(result.state, "fresh");
  assert.equal(result.cache.source_revision, 8);
  assert.equal((result.cache.workspace_read.context as { revision: number }).revision, 8);
  assert.equal(store.cache?.source_revision, 8);
});

test("stale cache is never relabeled as fresh when requested revision is newer", async () => {
  const store = new MemoryStore(); const transport = new Transport();
  const adapter = new WorkspaceReadCacheAdapter(transport, store);
  await adapter.read(context, true);
  const result = await adapter.read({ ...context, revision: 9 }, false);
  assert.equal(result.state, "stale");
  assert.ok(result.cache);
  assert.equal(result.cache.source_revision, 7);
});

test("reconciles an offline stale snapshot when returning online", async () => {
  const store = new MemoryStore(); const transport = new Transport();
  const adapter = new WorkspaceReadCacheAdapter(transport, store);
  await adapter.read(context, true);
  const offline = await adapter.read({ ...context, revision: 8 }, false);
  assert.equal(offline.state, "stale");
  assert.ok(offline.cache);
  assert.equal(offline.cache.source_revision, 7);
  transport.revision = 8;
  const online = await adapter.read({ ...context, revision: 8 }, true);
  assert.equal(online.mode, "online");
  assert.equal(online.state, "fresh");
  assert.equal(online.cache.source_revision, 8);
  assert.equal(store.cache?.source_revision, 8);
  assert.equal(transport.fetches, 2);
});
test("returning online does not promote a stale snapshot without authoritative refresh", async () => {
  const store = new MemoryStore(); const transport = new Transport();
  const adapter = new WorkspaceReadCacheAdapter(transport, store);
  await adapter.read(context, true);
  const offline = await adapter.read({ ...context, revision: 8 }, false);
  assert.equal(offline.state, "stale");
  transport.revision = 7;
  await assert.rejects(
    () => adapter.read({ ...context, revision: 8 }, true),
    /WORKSPACE_READ_REFRESH_SCOPE_MISMATCH/,
  );
  assert.equal(store.cache?.source_revision, 7);
});
