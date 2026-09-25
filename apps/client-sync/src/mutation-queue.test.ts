import assert from "node:assert/strict";
import test from "node:test";

import type { SyncMutation, SyncOutcome } from "./mutation-queue.ts";

import {
  OfflineMutationQueue,
  fromAuthoritativeSyncOutcome,
  toAuthoritativeSyncOutcome,
} from "./mutation-queue.ts";

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

function outcome(disposition: SyncOutcome["disposition"]): SyncOutcome {
  return {
    contract_version: "sync-outcome.v1",
    mutation_id: mutation.mutation_id,
    disposition,
    error_code: disposition === "conflict" ? "STALE_REVISION" : null,
  };
}

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

test("acknowledged maps to authoritative applied", () => {
  assert.deepEqual(toAuthoritativeSyncOutcome(mutation, outcome("acknowledged")), {
    contract_version: "client-sync-outcome.v1",
    status: "applied",
    operation: "update_activity",
    error_code: null,
    retryable: null,
    idempotency_key: "idem-1",
  });
});

test("conflict and rejected preserve their status and error", () => {
  assert.equal(toAuthoritativeSyncOutcome(mutation, outcome("conflict")).status, "conflict");
  assert.equal(toAuthoritativeSyncOutcome(mutation, outcome("conflict")).error_code, "STALE_REVISION");
  assert.equal(toAuthoritativeSyncOutcome(mutation, outcome("rejected")).status, "rejected");
});

test("retry is rejected because authoritative outcome has no retry status", () => {
  assert.throws(
    () => toAuthoritativeSyncOutcome(mutation, outcome("retry")),
    /UNREPRESENTABLE_RETRY_OUTCOME/,
  );
});

test("mutation identity mismatch is rejected", () => {
  assert.throws(
    () => toAuthoritativeSyncOutcome(mutation, { ...outcome("acknowledged"), mutation_id: "other" }),
    /MUTATION_ID_MISMATCH/,
  );
});

test("applied and replayed map back to acknowledged", () => {
  for (const status of ["applied", "replayed"] as const) {
    assert.deepEqual(
      fromAuthoritativeSyncOutcome(mutation, {
        contract_version: "client-sync-outcome.v1",
        status,
        operation: mutation.operation,
        idempotency_key: mutation.idempotency_key,
      }),
      {
        contract_version: "sync-outcome.v1",
        mutation_id: "m1",
        disposition: "acknowledged",
        error_code: null,
      },
    );
  }
});

test("authoritative conflict and rejected map back without changing semantics", () => {
  for (const status of ["conflict", "rejected"] as const) {
    assert.equal(
      fromAuthoritativeSyncOutcome(mutation, {
        contract_version: "client-sync-outcome.v1",
        status,
        operation: mutation.operation,
        idempotency_key: mutation.idempotency_key,
        error_code: "E1",
      }).disposition,
      status,
    );
  }
});

test("idempotency and operation mismatches are rejected", () => {
  assert.throws(
    () => fromAuthoritativeSyncOutcome(mutation, {
      contract_version: "client-sync-outcome.v1",
      status: "applied",
      idempotency_key: "other",
    }),
    /IDEMPOTENCY_KEY_MISMATCH/,
  );
  assert.throws(
    () => fromAuthoritativeSyncOutcome(mutation, {
      contract_version: "client-sync-outcome.v1",
      status: "applied",
      operation: "delete_activity",
    }),
    /OPERATION_MISMATCH/,
  );
});


test("retryAtRevision rejects unsafe and fractional revisions", () => {
  const queue = new OfflineMutationQueue();
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

  for (const revision of [8.5, Number.MAX_SAFE_INTEGER + 1, NaN, Infinity]) {
    assert.throws(() => queue.retryAtRevision("m1", revision), {
      message: "INVALID_EXPECTED_REVISION",
    });
  }
});

test("retryAtRevision is idempotent when revision is unchanged", () => {
  const queue = new OfflineMutationQueue();
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

  const retried = queue.retryAtRevision("m1", 7);
  assert.equal(retried.idempotency_key, "idem-1");
  assert.equal(queue.size(), 1);
});
