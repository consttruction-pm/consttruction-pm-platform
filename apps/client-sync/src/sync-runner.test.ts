import assert from "node:assert/strict";
import test from "node:test";
import { OfflineMutationQueue, type SyncMutation, type SyncOutcome } from "./mutation-queue.ts";
import { ClientSyncRunner, type ClientSyncTransport } from "./sync-runner.ts";
import { ApiSyncTransport } from "./api-sync-transport.ts";

const mutation = (id: string): SyncMutation => ({
  contract_version: "sync-mutation.v1",
  mutation_id: id,
  tenant_id: "t1",
  project_id: "p1",
  expected_revision: 7,
  operation: "update_activity",
  payload: { activity_id: id },
  idempotency_key: `idem-${id}`,
});

class FakeTransport implements ClientSyncTransport {
  private readonly outcomes: SyncOutcome[];

  constructor(outcomes: SyncOutcome[]) {
    this.outcomes = outcomes;
  }

  async submit(_submitted: SyncMutation): Promise<SyncOutcome> {
    const outcome = this.outcomes.shift();
    if (!outcome) throw new Error("NO_TEST_OUTCOME");
    return outcome;
  }
}

test("acknowledged outcomes remove mutations and continue in order", async () => {
  const queue = new OfflineMutationQueue();
  queue.enqueue(mutation("m1"));
  queue.enqueue(mutation("m2"));
  const runner = new ClientSyncRunner(queue, new FakeTransport([
    { contract_version: "sync-outcome.v1", mutation_id: "m1", disposition: "acknowledged" },
    { contract_version: "sync-outcome.v1", mutation_id: "m2", disposition: "acknowledged" },
  ]));
  const outcomes = await runner.runOnce();
  assert.deepEqual(outcomes.map((item) => item.mutation_id), ["m1", "m2"]);
  assert.equal(queue.size(), 0);
});

test("retry preserves the mutation and stops the batch", async () => {
  const queue = new OfflineMutationQueue();
  queue.enqueue(mutation("m1"));
  queue.enqueue(mutation("m2"));
  const runner = new ClientSyncRunner(queue, new FakeTransport([
    { contract_version: "sync-outcome.v1", mutation_id: "m1", disposition: "retry" },
  ]));
  await runner.runOnce();
  assert.equal(queue.size(), 2);
  assert.equal(queue.peek()?.mutation_id, "m1");
});

test("conflict preserves the mutation and stops the batch", async () => {
  const queue = new OfflineMutationQueue();
  queue.enqueue(mutation("m1"));
  queue.enqueue(mutation("m2"));
  const runner = new ClientSyncRunner(queue, new FakeTransport([
    { contract_version: "sync-outcome.v1", mutation_id: "m1", disposition: "conflict" },
  ]));
  await runner.runOnce();
  assert.equal(queue.size(), 2);
  assert.equal(queue.peek()?.mutation_id, "m1");
});

test("mutation id mismatch is rejected without changing queue state", async () => {
  const queue = new OfflineMutationQueue();
  queue.enqueue(mutation("m1"));
  const runner = new ClientSyncRunner(queue, new FakeTransport([
    { contract_version: "sync-outcome.v1", mutation_id: "other", disposition: "acknowledged" },
  ]));
  await assert.rejects(runner.runOnce(), /MUTATION_ID_MISMATCH/);
  assert.equal(queue.size(), 1);
});


test("runner can consume the versioned api transport without duplicating application logic", async () => {
  const queue = new OfflineMutationQueue();
  queue.enqueue(mutation("m1"));
  const api = {
    async post<TRequest, TResponse>(): Promise<{ ok: true; data: TResponse }> {
      return {
        ok: true as const,
        data: {
          contract_version: "sync-outcome.v1" as const,
          mutation_id: "m1",
          disposition: "acknowledged" as const,
        } as TResponse,
      };
    },
  };
  const runner = new ClientSyncRunner(queue, new ApiSyncTransport(api));
  const outcomes = await runner.runOnce();
  assert.equal(outcomes[0]?.disposition, "acknowledged");
  assert.equal(queue.size(), 0);
});
