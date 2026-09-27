import assert from "node:assert/strict";
import test from "node:test";
import { WebSyncRuntime } from "./sync-runtime.js";
import type { SyncMutation, SyncOutcome } from "../../client-sync/src/mutation-queue.js";
import type { SyncProjectContext } from "../../client-sync/src/api-sync-transport.js";

import { createWebVoiceAdapters } from "./voice-adapters.ts";
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

test("web runtime requires an opened project context for mutations", () => {
  const runtime = new WebSyncRuntime();
  assert.throws(() => runtime.queueMutation(mutation), /PROJECT_CONTEXT_NOT_SET/);
  assert.deepEqual(runtime.openProject("t1", "p1", 7), {
    tenant_id: "t1",
    project_id: "p1",
    revision: 7,
  });
  runtime.queueMutation(mutation);
  assert.equal(runtime.pendingMutationCount(), 1);
});

test("web runtime rejects mutations from another project", () => {
  const runtime = new WebSyncRuntime();
  runtime.openProject("t1", "p1", 7);
  assert.throws(
    () => runtime.queueMutation({ ...mutation, project_id: "p2" }),
    /PROJECT_CONTEXT_MISMATCH/,
  );
});

test("web sync runtime consumes the shared conflict outcome contract", async () => {
  const runtime = new WebSyncRuntime();
  runtime.openProject("t1", "p1", 7);
  runtime.queueMutation(mutation);
  const outcome: SyncOutcome = {
    contract_version: "sync-outcome.v1",
    mutation_id: "m1",
    disposition: "conflict",
    error_code: "STALE_REVISION",
  };
  const outcomes = await runtime.syncOnce({
    async post<TRequest, TResponse>() {
      return { ok: true as const, data: outcome as TResponse };
    },
  });

  assert.equal(outcomes[0]?.disposition, "conflict");
  assert.equal(runtime.pendingMutationCount(), 1);
  assert.deepEqual(runtime.presentConflict(mutation, outcome), {
    mutation_id: "m1",
    error_code: "STALE_REVISION",
    expected_revision: 7,
    available_actions: ["discard", "refresh_and_retry", "defer"],
    message_key: "sync.error.STALE_REVISION",
  });
});

test("web sync runtime retries stale revision only after authoritative refresh", async () => {
  const runtime = new WebSyncRuntime();
  runtime.openProject("t1", "p1", 7);
  runtime.queueMutation(mutation);
  const outcome: SyncOutcome = {
    contract_version: "sync-outcome.v1",
    mutation_id: "m1",
    disposition: "conflict",
    error_code: "STALE_REVISION",
  };

  const retried = await runtime.retryStaleRevision("m1", outcome, {
    async get<TResponse>(path: string, context: SyncProjectContext) {
      assert.equal(path, "/api/v1/sync/revision");
      assert.deepEqual(context, { tenant_id: "t1", project_id: "p1", revision: 7 });
      return { ok: true as const, data: { contract_version: "sync-project-revision.v1", tenant_id: "t1", project_id: "p1", revision: 42 } as TResponse };
    },
  });

  assert.equal(retried.expected_revision, 42);
  assert.equal(retried.idempotency_key, "idem-1:r42");
  assert.equal(runtime.currentProject().revision, 42);
  assert.equal(runtime.pendingMutationCount(), 1);
});

test("web runtime refreshes the project revision", async () => {
  const runtime = new WebSyncRuntime();
  runtime.openProject("t1", "p1", 7);
  const revision = await runtime.refreshRevision({
    async get<TResponse>(path: string, context: SyncProjectContext) {
      assert.equal(path, "/api/v1/sync/revision");
      assert.deepEqual(context, { tenant_id: "t1", project_id: "p1", revision: 7 });
      return { ok: true as const, data: { contract_version: "sync-project-revision.v1", tenant_id: "t1", project_id: "p1", revision: 8 } as TResponse };
    },
  });
  assert.equal(revision, 8);
  assert.equal(runtime.currentProject().revision, 8);
});

test("web runtime rejects an invalid authoritative revision response", async () => {
  const runtime = new WebSyncRuntime();
  runtime.openProject("t1", "p1", 7);
  await assert.rejects(
    runtime.refreshRevision({
      async get<TResponse>() {
        return { ok: true as const, data: { contract_version: "sync-project-revision.v1", tenant_id: "t1", project_id: "p1", revision: 8.5 } as TResponse };
      },
    }),
    /INVALID_PROJECT_REVISION_RESPONSE/,
  );
});

test("web stale retry can be acknowledged after authoritative refresh", async () => {
  const runtime = new WebSyncRuntime();
  runtime.openProject("t1", "p1", 7);
  runtime.queueMutation(mutation);
  const conflict: SyncOutcome = { contract_version: "sync-outcome.v1", mutation_id: "m1", disposition: "conflict", error_code: "STALE_REVISION" };
  const retried = await runtime.retryStaleRevision("m1", conflict, {
    async get<TResponse>() {
      return { ok: true as const, data: { contract_version: "sync-project-revision.v1", tenant_id: "t1", project_id: "p1", revision: 42 } as TResponse };
    },
  });
  const outcomes = await runtime.syncOnce({
    async post<TRequest, TResponse>(_path: string, request: TRequest, context: SyncProjectContext, idempotencyKey: string) {
      assert.equal((request as SyncMutation).expected_revision, 42);
      assert.equal(context.revision, 42);
      assert.equal(idempotencyKey, "idem-1:r42");
      return { ok: true as const, data: { contract_version: "sync-outcome.v1", mutation_id: "m1", disposition: "acknowledged" } as TResponse };
    },
  });
  assert.equal(retried.expected_revision, 42);
  assert.equal(outcomes[0]?.disposition, "acknowledged");
  assert.equal(runtime.pendingMutationCount(), 0);
});

test("web runtime exposes configured voice adapter boundary", () => {
  const runtime = new WebSyncRuntime();
  const adapters = createWebVoiceAdapters({
    input: { capabilities: { input: true, output: false }, async capture() { throw new Error("not invoked"); } },
    output: { capabilities: { input: false, output: true }, async speak() {} },
  });
  assert.equal(runtime.voiceAdaptersOrNull(), null);
  runtime.setVoiceAdapters(adapters);
  assert.equal(runtime.voiceAdaptersOrNull(), adapters);
});
