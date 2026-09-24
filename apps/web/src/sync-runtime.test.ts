import assert from "node:assert/strict";
import test from "node:test";
import { WebSyncRuntime } from "./sync-runtime.ts";
import type { SyncMutation, SyncOutcome } from "../../client-sync/src/mutation-queue.ts";

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
    async post() {
      return { ok: true as const, data: outcome };
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
