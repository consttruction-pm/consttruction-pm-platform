import assert from "node:assert/strict";
import test from "node:test";
import { DesktopRuntime } from "./runtime.ts";
import type { SyncOutcome } from "../../client-sync/src/mutation-queue.js";
import type { SyncProjectContext } from "../../client-sync/src/api-sync-transport.js";
import type { WorkspaceReadCacheStore, WorkspaceControlRoomReadTransport } from "../../client-sync/src/workspace-read-cache-adapter.js";
import type { WorkspaceControlRoomReadCache } from "../../client-sync/src/workspace-read-cache.js";

test("desktop syncOnce uses shared transport and clears acknowledged mutation", async () => {
  const runtime = new DesktopRuntime();
  runtime.openProject("t1", "p1", 7);
  runtime.queueMutation({ contract_version: "sync-mutation.v1", mutation_id: "m1", tenant_id: "t1", project_id: "p1", expected_revision: 7, operation: "update_activity", payload: { activity_id: "A1" }, idempotency_key: "idem-1" });
  const calls: unknown[] = [];
  const outcomes = await runtime.syncOnce({ async post<TRequest, TResponse>(path: string, request: TRequest, context: { tenant_id: string; project_id: string; revision: number }, idempotencyKey: string): Promise<{ ok: true; data: TResponse }> { calls.push({ path, request, context, idempotencyKey }); return { ok: true as const, data: { contract_version: "sync-outcome.v1" as const, mutation_id: "m1", disposition: "acknowledged" as const } as SyncOutcome as TResponse }; } });
  assert.equal(outcomes[0]?.disposition, "acknowledged");
  assert.equal(runtime.pendingMutationCount(), 0);
  assert.equal(calls.length, 1);
});

test("desktop stale revision retry requires authoritative refresh", async () => {
  const runtime = new DesktopRuntime();
  runtime.openProject("t1", "p1", 7);
  runtime.queueMutation({ contract_version: "sync-mutation.v1", mutation_id: "m1", tenant_id: "t1", project_id: "p1", expected_revision: 7, operation: "update_activity", payload: {}, idempotency_key: "idem-1" });
  const outcome: SyncOutcome = { contract_version: "sync-outcome.v1", mutation_id: "m1", disposition: "conflict", error_code: "STALE_REVISION" };

  const retried = await runtime.retryStaleRevision("m1", outcome, {
    async get<TResponse>(path: string, context: SyncProjectContext) {
      assert.equal(path, "/api/v1/sync/revision");
      assert.deepEqual(context, { tenant_id: "t1", project_id: "p1", revision: 7 });
      return { ok: true as const, data: { contract_version: "sync-project-revision.v1", tenant_id: "t1", project_id: "p1", revision: 42 } as TResponse };
    },
  });

  assert.equal(retried.expected_revision, 42);
  assert.equal(retried.idempotency_key, "idem-1:r42");
  assert.equal(runtime.current().revision, 42);
});


test("desktop runtime refreshes the project revision", async () => {
  const runtime = new DesktopRuntime();
  runtime.openProject("t1", "p1", 7);
  const state = await runtime.refreshRevision({
    async get<TResponse>(path: string, context: SyncProjectContext) {
      assert.equal(path, "/api/v1/sync/revision");
      assert.deepEqual(context, { tenant_id: "t1", project_id: "p1", revision: 7 });
      return { ok: true as const, data: { contract_version: "sync-project-revision.v1", tenant_id: "t1", project_id: "p1", revision: 8 } as TResponse };
    },
  });
  assert.equal(state.revision, 8);
});

test("desktop runtime rejects an invalid authoritative revision response", async () => {
  const runtime = new DesktopRuntime();
  runtime.openProject("t1", "p1", 7);
  await assert.rejects(
    runtime.refreshRevision({
      async get<TResponse>() {
        return { ok: true as const, data: { contract_version: "sync-project-revision.v1", tenant_id: "t1", project_id: "p1", revision: 8.5 } as TResponse };
      },
    }),
    /INVALID_PROJECT_REVISION_RESPONSE/,
  );
});

test("desktop stale retry can be acknowledged after authoritative refresh", async () => {
  const runtime = new DesktopRuntime();
  runtime.openProject("t1", "p1", 7);
  runtime.queueMutation({ contract_version: "sync-mutation.v1", mutation_id: "m1", tenant_id: "t1", project_id: "p1", expected_revision: 7, operation: "update_activity", payload: {}, idempotency_key: "idem-1" });
  const conflict: SyncOutcome = { contract_version: "sync-outcome.v1", mutation_id: "m1", disposition: "conflict", error_code: "STALE_REVISION" };
  const retried = await runtime.retryStaleRevision("m1", conflict, {
    async get<TResponse>() {
      return { ok: true as const, data: { contract_version: "sync-project-revision.v1", tenant_id: "t1", project_id: "p1", revision: 42 } as TResponse };
    },
  });
  const outcomes = await runtime.syncOnce({
    async post<TRequest, TResponse>(_path: string, request: TRequest, context: { tenant_id: string; project_id: string; revision: number }, idempotencyKey: string) {
      assert.equal((request as any).expected_revision, 42);
      assert.equal(context.revision, 42);
      assert.equal(idempotencyKey, "idem-1:r42");
      return { ok: true as const, data: { contract_version: "sync-outcome.v1", mutation_id: "m1", disposition: "acknowledged" } as TResponse };
    },
  });
  assert.equal(retried.expected_revision, 42);
  assert.equal(outcomes[0]?.disposition, "acknowledged");
  assert.equal(runtime.current().revision, 42);
  assert.equal(runtime.pendingMutationCount(), 0);
});


class WorkspaceStore implements WorkspaceReadCacheStore {
  cache: WorkspaceControlRoomReadCache | null = null;
  async load() { return this.cache; }
  async save(cache: WorkspaceControlRoomReadCache) { this.cache = cache; }
}
class WorkspaceTransport implements WorkspaceControlRoomReadTransport {
  calls = 0;
  async fetch(context: { tenant_id: string; project_id: string; revision: number }) {
    this.calls += 1;
    return { contract_version: "workspace-control-room-read.v1", context, workspace: {} };
  }
}
test("Desktop workspace read uses shared cache and exposes offline stale state", async () => {
  const runtime = new DesktopRuntime();
  runtime.openProject("t1", "p1", 7, "online");
  const transport = new WorkspaceTransport();
  const store = new WorkspaceStore();
  const adapter = new (await import("../../client-sync/src/workspace-read-cache-adapter.js")).WorkspaceReadCacheAdapter(transport, store);
  const online = await runtime.readWorkspace(adapter);
  assert.equal(online.state, "fresh");
  runtime.setMode("offline");
  runtime.advanceRevision(8);
  const offline = await runtime.readWorkspace(adapter);
  assert.equal(offline.state, "stale");
  assert.ok(offline.cache);
  assert.equal(offline.cache.source_revision, 7);
  assert.equal(transport.calls, 1);
});

test("Desktop reconciles stale offline workspace after returning online", async () => {
  const runtime = new DesktopRuntime();
  runtime.openProject("t1", "p1", 7, "online");
  const transport = new WorkspaceTransport();
  const store = new WorkspaceStore();
  const adapter = new (await import("../../client-sync/src/workspace-read-cache-adapter.js")).WorkspaceReadCacheAdapter(transport, store);
  await runtime.readWorkspace(adapter);
  runtime.advanceRevision(8);
  runtime.setMode("offline");
  const stale = await runtime.readWorkspace(adapter);
  assert.equal(stale.state, "stale");
  transport.calls = 0;
  runtime.setMode("online");
  const fresh = await runtime.readWorkspace(adapter);
  assert.equal(fresh.state, "fresh");
  assert.equal(fresh.cache.source_revision, 8);
  assert.equal(transport.calls, 1);
});