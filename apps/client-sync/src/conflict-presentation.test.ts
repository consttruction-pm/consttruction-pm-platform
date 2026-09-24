import test from "node:test";
import assert from "node:assert/strict";
import { presentSyncConflict } from "./conflict-presentation.ts";
import type { SyncMutation, SyncOutcome } from "./mutation-queue.ts";

const mutation: SyncMutation = {
  contract_version: "sync-mutation.v1",
  mutation_id: "mutation-1",
  tenant_id: "tenant-1",
  project_id: "project-1",
  expected_revision: 7,
  operation: "update_activity",
  payload: { activity_id: "A-1" },
  idempotency_key: "idem-1",
};

test("presents stale revision with shared actions", () => {
  const outcome: SyncOutcome = {
    contract_version: "sync-outcome.v1",
    mutation_id: "mutation-1",
    disposition: "conflict",
    error_code: "STALE_REVISION",
  };

  assert.deepEqual(presentSyncConflict(mutation, outcome), {
    mutation_id: "mutation-1",
    error_code: "STALE_REVISION",
    expected_revision: 7,
    available_actions: ["discard", "refresh_and_retry", "defer"],
    message_key: "sync.error.STALE_REVISION",
  });
});

test("non-conflict outcomes are not presented as conflicts", () => {
  const outcome: SyncOutcome = {
    contract_version: "sync-outcome.v1",
    mutation_id: "mutation-1",
    disposition: "acknowledged",
  };

  assert.equal(presentSyncConflict(mutation, outcome), null);
});
