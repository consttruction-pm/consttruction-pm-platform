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


test("conflict refresh uses authoritative revision before explicit retry", async () => {
  const queue = new OfflineMutationQueue();
  queue.enqueue(mutation("m1"));
  const runner = new ClientSyncRunner(queue, new FakeTransport([
    {
      contract_version: "sync-outcome.v1",
      mutation_id: "m1",
      disposition: "conflict",
      error_code: "STALE_REVISION",
    },
  ]));

  await runner.runOnce();

  const seen: Array<{ tenant_id: string; project_id: string; revision: number }> = [];
  const revisionTransport = {
    async refresh(context: { tenant_id: string; project_id: string; revision: number }) {
      seen.push(context);
      return {
        contract_version: "sync-project-revision.v1" as const,
        tenant_id: "t1",
        project_id: "p1",
        revision: 8,
      };
    },
  };

  const retried = await runner.retryConflictAtAuthoritativeRevision("m1", revisionTransport);
  assert.deepEqual(seen, [{ tenant_id: "t1", project_id: "p1", revision: 7 }]);
  assert.equal(retried.expected_revision, 8);
  assert.equal(retried.idempotency_key, "idem-m1:r8");
  assert.equal(queue.peek()?.expected_revision, 8);
});

test("conflict refresh rejects an unsafe authoritative revision", async () => {
  const queue = new OfflineMutationQueue();
  queue.enqueue(mutation("m1"));
  const runner = new ClientSyncRunner(queue, new FakeTransport([
    { contract_version: "sync-outcome.v1", mutation_id: "m1", disposition: "conflict", error_code: "STALE_REVISION" },
  ]));
  await runner.runOnce();

  const revisionTransport = {
    async refresh() {
      return {
        contract_version: "sync-project-revision.v1" as const,
        tenant_id: "t1",
        project_id: "p1",
        revision: Number.MAX_SAFE_INTEGER + 1,
      };
    },
  };

  await assert.rejects(
    runner.retryConflictAtAuthoritativeRevision("m1", revisionTransport),
    /INVALID_PROJECT_REVISION_RESPONSE/,
  );
  assert.equal(queue.peek()?.expected_revision, 7);
});


test("conflict refresh does not guess or locally increment the revision", async () => {
  const queue = new OfflineMutationQueue();
  queue.enqueue(mutation("m1"));
  const runner = new ClientSyncRunner(queue, new FakeTransport([
    {
      contract_version: "sync-outcome.v1",
      mutation_id: "m1",
      disposition: "conflict",
      error_code: "STALE_REVISION",
    },
  ]));

  await runner.runOnce();

  const revisionTransport = {
    async refresh() {
      return {
        contract_version: "sync-project-revision.v1" as const,
        tenant_id: "t1",
        project_id: "p1",
        revision: 42,
      };
    },
  };

  const retried = await runner.retryConflictAtAuthoritativeRevision("m1", revisionTransport);
  assert.equal(retried.expected_revision, 42);
  assert.notEqual(retried.expected_revision, 8);
});


test("runner carries all versioned api sync outcomes end-to-end", async () => {
  const cases: Array<{ disposition: SyncOutcome["disposition"]; error?: string; retryable?: boolean }> = [
    { disposition: "acknowledged" },
    { disposition: "retry", error: "TEMPORARY_UNAVAILABLE", retryable: true },
    { disposition: "conflict", error: "STALE_REVISION", retryable: false },
    { disposition: "rejected", error: "FORBIDDEN", retryable: false },
  ];

  for (const current of cases) {
    const queue = new OfflineMutationQueue();
    queue.enqueue(mutation("m1"));
    const api = {
      async post<TRequest, TResponse>(): Promise<
        | { ok: true; data: TResponse }
        | { ok: false; error: { code: string; retryable: boolean } }
      > {
        if (current.disposition === "acknowledged" || current.disposition === "conflict") {
          return {
            ok: true,
            data: {
              contract_version: "sync-outcome.v1",
              mutation_id: "m1",
              disposition: current.disposition,
              ...(current.error ? { error_code: current.error } : {}),
            } as SyncOutcome as TResponse,
          };
        }
        return {
          ok: false,
          error: {
            code: current.error!,
            retryable: current.retryable!,
          },
        };
      },
    };

    const outcomes = await new ClientSyncRunner(queue, new ApiSyncTransport(api)).runOnce();
    assert.equal(outcomes[0]?.disposition, current.disposition);
    assert.equal(queue.size(), current.disposition === "acknowledged" ? 0 : 1);
  }
});


test("api transport rejects a successful response with the wrong outcome contract", async () => {
  const api = {
    async post<TRequest, TResponse>(): Promise<{ ok: true; data: TResponse }> {
      return {
        ok: true,
        data: {
          contract_version: "sync-project-revision.v1",
          mutation_id: "m1",
          disposition: "acknowledged",
        } as unknown as TResponse,
      };
    },
  };

  await assert.rejects(
    new ApiSyncTransport(api).submit(mutation("m1")),
    /INVALID_SYNC_OUTCOME_RESPONSE/,
  );
});

test("api transport rejects a successful response with the wrong disposition", async () => {
  const api = {
    async post<TRequest, TResponse>(): Promise<{ ok: true; data: TResponse }> {
      return {
        ok: true,
        data: {
          contract_version: "sync-outcome.v1",
          mutation_id: "m1",
          disposition: "unknown",
        } as unknown as TResponse,
      };
    },
  };

  await assert.rejects(
    new ApiSyncTransport(api).submit(mutation("m1")),
    /INVALID_SYNC_OUTCOME_RESPONSE/,
  );
});


test("revision transport rejects a non-integer authoritative revision", async () => {
  const { ApiRevisionTransport } = await import("./revision-transport.ts");
  const api = {
    async get<TResponse>(): Promise<{ ok: true; data: TResponse }> {
      return {
        ok: true,
        data: {
          contract_version: "sync-project-revision.v1",
          tenant_id: "t1",
          project_id: "p1",
          revision: 8.5,
        } as unknown as TResponse,
      };
    },
  };

  await assert.rejects(
    new ApiRevisionTransport(api).refresh({ tenant_id: "t1", project_id: "p1", revision: 7 }),
    /INVALID_PROJECT_REVISION_RESPONSE/,
  );
});

test("revision transport rejects an unsafe integer authoritative revision", async () => {
  const { ApiRevisionTransport } = await import("./revision-transport.ts");
  const api = {
    async get<TResponse>(): Promise<{ ok: true; data: TResponse }> {
      return {
        ok: true,
        data: {
          contract_version: "sync-project-revision.v1",
          tenant_id: "t1",
          project_id: "p1",
          revision: Number.MAX_SAFE_INTEGER + 1,
        } as unknown as TResponse,
      };
    },
  };

  await assert.rejects(
    new ApiRevisionTransport(api).refresh({ tenant_id: "t1", project_id: "p1", revision: 7 }),
    /INVALID_PROJECT_REVISION_RESPONSE/,
  );
});
