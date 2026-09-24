import assert from "node:assert/strict";
import test from "node:test";
import { MobileRuntime } from "./runtime.ts";
import type { SyncOutcome } from "../../client-sync/src/mutation-queue.ts";

test("mobile syncOnce uses shared transport and preserves retry", async () => {
  const runtime = new MobileRuntime();
  runtime.openProject("t1", "p1", 7);
  runtime.queueMutation({ contract_version: "sync-mutation.v1", mutation_id: "m1", tenant_id: "t1", project_id: "p1", expected_revision: 7, operation: "update_activity", payload: { activity_id: "A1" }, idempotency_key: "idem-1" });
  const outcomes = await runtime.syncOnce({ async post() { return { ok: false as const, error: { code: "TEMPORARY_UNAVAILABLE", retryable: true } }; } });
  assert.equal(outcomes[0]?.disposition, "retry");
  assert.equal(runtime.pendingMutationCount(), 1);
});
