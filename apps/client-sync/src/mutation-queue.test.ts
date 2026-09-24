import assert from "node:assert/strict";
import test from "node:test";
import { OfflineMutationQueue } from "./mutation-queue.ts";

test("retryAtRevision replaces the expected revision and rotates idempotency", () => {
  const queue = new OfflineMutationQueue();
  queue.enqueue({
    contract_version: "sync-mutation.v1",
    mutation_id: "m1",
    tenant_id: "t1",
    project_id: "p1",
    expected_revision: 7,
    operation: "update_activity",
    payload: { activity_id: "A1" },
    idempotency_key: "idem-1",
  });

  const retried = queue.retryAtRevision("m1", 8);

  assert.equal(retried.expected_revision, 8);
  assert.equal(retried.idempotency_key, "idem-1:r8");
  assert.equal(queue.peek()?.expected_revision, 8);
  assert.equal(queue.peek()?.idempotency_key, "idem-1:r8");
  assert.equal(queue.size(), 1);
});

test("retryAtRevision rejects unknown mutations and invalid revisions", () => {
  const queue = new OfflineMutationQueue();

  assert.throws(() => queue.retryAtRevision("missing", 1), {
    message: "MUTATION_NOT_PENDING",
  });

  queue.enqueue({
    contract_version: "sync-mutation.v1",
    mutation_id: "m1",
    tenant_id: "t1",
    project_id: "p1",
    expected_revision: 7,
    operation: "update_activity",
    payload: {},
    idempotency_key: "idem-1",
  });

  assert.throws(() => queue.retryAtRevision("m1", -1), {
    message: "INVALID_EXPECTED_REVISION",
  });
});
