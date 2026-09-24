import assert from "node:assert/strict";
import test from "node:test";
import type { SyncMutation, SyncOutcome } from "./mutation-queue.ts";
import { ApiSyncTransport, type VersionedSyncApi, type SyncApiResult, type SyncProjectContext } from "./api-sync-transport.ts";

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

test("api transport preserves context, revision and idempotency key", async () => {
  let received: unknown;
  const api: VersionedSyncApi = {
    async post<TRequest, TResponse>(path: string, request: TRequest, context: SyncProjectContext, idempotencyKey: string): Promise<SyncApiResult<TResponse>> {
      received = { path, request, context, idempotencyKey };
      return {
        ok: true,
        data: {
          contract_version: "sync-outcome.v1",
          mutation_id: "m1",
          disposition: "acknowledged",
        } as SyncOutcome,
      };
    },
  };

  const outcome = await new ApiSyncTransport(api).submit(mutation);

  assert.equal(outcome.disposition, "acknowledged");
  assert.deepEqual(received, {
    path: "/api/v1/sync/mutations",
    request: mutation,
    context: { tenant_id: "t1", project_id: "p1", revision: 7 },
    idempotencyKey: "idem-1",
  });
});

test("retryable api errors become retry outcomes", async () => {
  const api: VersionedSyncApi = {
    async post<TRequest, TResponse>(): Promise<SyncApiResult<TResponse>> {
      return { ok: false, error: { code: "TEMPORARY_UNAVAILABLE", retryable: true } };
    },
  };

  assert.deepEqual(await new ApiSyncTransport(api).submit(mutation), {
    contract_version: "sync-outcome.v1",
    mutation_id: "m1",
    disposition: "retry",
    error_code: "TEMPORARY_UNAVAILABLE",
  });
});

test("non-retryable api errors become rejected outcomes", async () => {
  const api: VersionedSyncApi = {
    async post() {
      return { ok: false, error: { code: "FORBIDDEN", retryable: false } };
    },
  };

  assert.deepEqual(await new ApiSyncTransport(api).submit(mutation), {
    contract_version: "sync-outcome.v1",
    mutation_id: "m1",
    disposition: "rejected",
    error_code: "FORBIDDEN",
  });
});

test("mismatched successful outcome is rejected", async () => {
  const api: VersionedSyncApi = {
    async post() {
      return {
        ok: true,
        data: {
          contract_version: "sync-outcome.v1",
          mutation_id: "other",
          disposition: "acknowledged",
        } as SyncOutcome,
      };
    },
  };

  await assert.rejects(new ApiSyncTransport(api).submit(mutation), /MUTATION_ID_MISMATCH/);
});
