import assert from "node:assert/strict";
import test from "node:test";
import { DesktopRuntime } from "./runtime.js";
import type { SyncOutcome } from "../../client-sync/src/mutation-queue.js";
import type { SyncProjectContext } from "../../client-sync/src/api-sync-transport.js";

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
