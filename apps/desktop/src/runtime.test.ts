import assert from "node:assert/strict";
import test from "node:test";
import { DesktopRuntime } from "./runtime.ts";

test("desktop syncOnce uses shared transport and clears acknowledged mutation", async () => {
  const runtime = new DesktopRuntime();
  runtime.openProject("t1", "p1", 7);
  runtime.queueMutation({ contract_version: "sync-mutation.v1", mutation_id: "m1", tenant_id: "t1", project_id: "p1", expected_revision: 7, operation: "update_activity", payload: { activity_id: "A1" }, idempotency_key: "idem-1" });
  const calls: unknown[] = [];
  const outcomes = await runtime.syncOnce({ async post(path, request, context, idempotencyKey) { calls.push({ path, request, context, idempotencyKey }); return { ok: true as const, data: { contract_version: "sync-outcome.v1" as const, mutation_id: "m1", disposition: "acknowledged" as const } }; } });
  assert.equal(outcomes[0]?.disposition, "acknowledged");
  assert.equal(runtime.pendingMutationCount(), 0);
  assert.equal(calls.length, 1);
});
