import assert from "node:assert/strict";
import test from "node:test";

import type { SyncMutation, SyncOutcome } from "./mutation-queue.ts";
import { fromAuthoritativeSyncOutcome, toAuthoritativeSyncOutcome } from "./mutation-queue.ts";

const adapterMutation: SyncMutation = {
  contract_version: "sync-mutation.v1", mutation_id: "adapter-m1", tenant_id: "t1",
  project_id: "p1", expected_revision: 7, operation: "update_activity",
  payload: { activity_id: "A1" }, idempotency_key: "adapter-idem-1",
};
const adapterOutcome = (disposition: SyncOutcome["disposition"]): SyncOutcome => ({
  contract_version: "sync-outcome.v1", mutation_id: adapterMutation.mutation_id, disposition,
  error_code: disposition === "conflict" ? "STALE_REVISION" : null,
});

test("authoritative adapter maps acknowledged without losing identity", () => {
  assert.deepEqual(toAuthoritativeSyncOutcome(adapterMutation, adapterOutcome("acknowledged")), {
    contract_version: "client-sync-outcome.v1", status: "applied", operation: "update_activity",
    error_code: null, retryable: null, idempotency_key: "adapter-idem-1",
  });
});
test("authoritative adapter rejects unrepresentable retry metadata", () => {
  assert.throws(() => toAuthoritativeSyncOutcome(adapterMutation, {...adapterOutcome("conflict"), retry_after_seconds: 5}), /UNREPRESENTABLE_RETRY_METADATA/);
  assert.throws(() => toAuthoritativeSyncOutcome(adapterMutation, adapterOutcome("retry")), /UNREPRESENTABLE_RETRY_OUTCOME/);
});
test("reverse authoritative adapter rejects lossy metadata", () => {
  assert.throws(() => fromAuthoritativeSyncOutcome(adapterMutation, {contract_version:"client-sync-outcome.v1", status:"conflict", revision:8}), /UNREPRESENTABLE_REVISION/);
  assert.throws(() => fromAuthoritativeSyncOutcome(adapterMutation, {contract_version:"client-sync-outcome.v1", status:"conflict", retryable:true}), /UNREPRESENTABLE_RETRYABLE/);
});
test("reverse authoritative adapter preserves representable status and identity", () => {
  assert.deepEqual(fromAuthoritativeSyncOutcome(adapterMutation, {
    contract_version:"client-sync-outcome.v1", status:"replayed", operation:adapterMutation.operation, idempotency_key:adapterMutation.idempotency_key,
  }), {contract_version:"sync-outcome.v1", mutation_id:"adapter-m1", disposition:"acknowledged", error_code:null});
});
