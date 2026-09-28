import test from "node:test";
import assert from "node:assert/strict";
import { ApiWorkspaceLayoutStore } from "./workspace-layout-persistence.js";
import { createDefaultLayout } from "./workspace-layout.js";

const catalog = [{ id: "activity_id", source: "standard" as const, dataType: "string" as const, subjectArea: "activity", label: "Activity ID", writable: false, computed: false, unit: null, filterable: true, orderable: true }];

test("API layout store rejects stale client revision before save", async () => {
  let called = false;
  const transport = {
    async get() { throw new Error("not used"); },
    async post<TRequest, TResponse>(): Promise<{ ok: false; error: never }> { called = true; throw new Error("not used"); },
  };
  const store = new ApiWorkspaceLayoutStore(transport, "/layout", catalog);
  const layout = createDefaultLayout("l1", "activity", "project", 2, catalog);
  const result = await store.saveToApi("k", { tenant_id: "t1", project_id: "p1", revision: 3 }, layout, "idem-1");
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.error.code, "STALE_WORKSPACE_LAYOUT_REVISION");
  assert.equal(called, false);
});

test("API layout store sends ProjectContext and idempotency key on save", async () => {
  let captured: { path?: string; context?: unknown; idempotency?: string } = {};
  const transport = {
    async get() { throw new Error("not used"); },
    async post<TRequest, TResponse>(path: string, _body: TRequest, context: unknown, idempotency?: string): Promise<{ ok: true; data: TResponse }> {
      captured = { path, context, idempotency };
      return { ok: true as const, data: createDefaultLayout("l1", "activity", "project", 2, catalog) as TResponse };
    },
  };
  const store = new ApiWorkspaceLayoutStore(transport, "/layout", catalog);
  const layout = createDefaultLayout("l1", "activity", "project", 2, catalog);
  const result = await store.saveToApi("k", { tenant_id: "t1", project_id: "p1", revision: 2 }, layout, "idem-2");
  assert.equal(result.ok, true);
  assert.equal(captured.path, "/layout");
  assert.deepEqual(captured.context, { tenant_id: "t1", project_id: "p1", revision: 2 });
  assert.equal(captured.idempotency, "idem-2");
});
