import assert from "node:assert/strict";
import test from "node:test";
import { MobileRuntime } from "./runtime.js";
import type { SyncOutcome } from "../../client-sync/src/mutation-queue.js";

test("mobile syncOnce uses shared transport and preserves retry", async () => {
  const runtime = new MobileRuntime();
  runtime.openProject("t1", "p1", 7);
  runtime.queueMutation({ contract_version: "sync-mutation.v1", mutation_id: "m1", tenant_id: "t1", project_id: "p1", expected_revision: 7, operation: "update_activity", payload: { activity_id: "A1" }, idempotency_key: "idem-1" });
  const outcomes = await runtime.syncOnce({ async post() { return { ok: false as const, error: { code: "TEMPORARY_UNAVAILABLE", retryable: true } }; } });
  assert.equal(outcomes[0]?.disposition, "retry");
  assert.equal(runtime.pendingMutationCount(), 1);
});

test("mobile stale revision retry updates project revision and mutation metadata", () => {
  const runtime = new MobileRuntime();
  runtime.openProject("t1", "p1", 7);
  runtime.queueMutation({ contract_version: "sync-mutation.v1", mutation_id: "m1", tenant_id: "t1", project_id: "p1", expected_revision: 7, operation: "update_activity", payload: {}, idempotency_key: "idem-1" });
  const outcome: SyncOutcome = { contract_version: "sync-outcome.v1", mutation_id: "m1", disposition: "conflict", error_code: "STALE_REVISION" };

  const retried = runtime.retryStaleRevision("m1", outcome, 8);

  assert.equal(retried.expected_revision, 8);
  assert.equal(retried.idempotency_key, "idem-1:r8");
  assert.equal(runtime.current().revision, 8);
});


test("mobile runtime refreshes the project revision", async () => {
  const runtime = new MobileRuntime();
  runtime.openProject("t1", "p1", 7);
  const state = await runtime.refreshRevision({
    async get<TResponse>(path, context) {
      assert.equal(path, "/api/v1/sync/revision");
      assert.deepEqual(context, { tenant_id: "t1", project_id: "p1", revision: 7 });
      return { ok: true as const, data: { contract_version: "sync-project-revision.v1", tenant_id: "t1", project_id: "p1", revision: 8 } as TResponse };
    },
  });
  assert.equal(state.revision, 8);
});
