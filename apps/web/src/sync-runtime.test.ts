import assert from "node:assert/strict";
import test from "node:test";
import { WebSyncRuntime } from "./sync-runtime.js";
import type { SyncMutation, SyncOutcome } from "../../client-sync/src/mutation-queue.js";
import type { SyncProjectContext } from "../../client-sync/src/api-sync-transport.js";

const mutation: SyncMutation = {
  contract_version: "sync-mutation.v1",
  mutation_id: "m1",
  tenant_id: "t1",
  project_id: "p1",
  expected_revision: 7,
  operation: "update_activity",
  payload: { activity_id: "A1" },
  idempotency_key: "idem-1",
};

test("web sync runtime consumes the shared conflict outcome contract", async () => {
  const runtime = new WebSyncRuntime();
  runtime.queueMutation(mutation);
  const outcome: SyncOutcome = {
    contract_version: "sync-outcome.v1",
    mutation_id: "m1",
    disposition: "conflict",
    error_code: "STALE_REVISION",
  };
  const outcomes = await runtime.syncOnce({
    async post<TRequest, TResponse>() {
      return { ok: true as const, data: outcome as TResponse };
    },
  });

  assert.equal(outcomes[0]?.disposition, "conflict");
  assert.equal(runtime.pendingMutationCount(), 1);
  assert.deepEqual(runtime.presentConflict(mutation, outcome), {
    mutation_id: "m1",
    error_code: "STALE_REVISION",
    expected_revision: 7,
    available_actions: ["discard", "refresh_and_retry", "defer"],
    message_key: "sync.error.STALE_REVISION",
  });
});

test("web sync runtime retries stale revision only after authoritative refresh", async () => {
  const runtime = new WebSyncRuntime();
  runtime.queueMutation(mutation);
  const outcome: SyncOutcome = {
    contract_version: "sync-outcome.v1",
    mutation_id: "m1",
    disposition: "conflict",
    error_code: "STALE_REVISION",
  };

  const retried = await runtime.retryStaleRevision("m1", outcome, {
    async get<TResponse>(path: string, context: SyncProjectContext) {
      assert.equal(path, "/api/v1/sync/revision");
      assert.deepEqual(context, { tenant_id: "t1", project_id: "p1", revision: 7 });
      return { ok: true as const, data: { contract_version: "sync-project-revision.v1", tenant_id: "t1", project_id: "p1", revision: 42 } as TResponse };
    },
  });

  assert.equal(retried.expected_revision, 42);
  assert.equal(retried.idempotency_key, "idem-1:r42");
  assert.equal(runtime.pendingMutationCount(), 1);
});


test("web runtime refreshes the project revision", async () => {
  const runtime = new WebSyncRuntime();
  const revision = await runtime.refreshRevision({
    async get<TResponse>(path: string, context: SyncProjectContext) {
      assert.equal(path, "/api/v1/sync/revision");
      assert.deepEqual(context, { tenant_id: "t1", project_id: "p1", revision: 7 });
      return { ok: true as const, data: { contract_version: "sync-project-revision.v1", tenant_id: "t1", project_id: "p1", revision: 8 } as TResponse };
    },
  }, "t1", "p1", 7);
  assert.equal(revision, 8);
});
