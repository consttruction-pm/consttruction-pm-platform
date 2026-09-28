import test from "node:test";
import assert from "node:assert/strict";
import { ApiWorkspaceLayoutStore } from "./workspace-layout-persistence.js";
import { createDefaultLayout } from "./workspace-layout.js";

const catalog = [{ id: "activity_id", dataType: "text", subjectArea: "activity", displayName: "Activity ID", writable: false, computed: false }];

test("API layout store rejects stale client revision before save", async () => {
  let called = false;
  const transport = {
    async get() { throw new Error("not used"); },
    async post() { called = true; throw new Error("not used"); },
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
    async post(path: string, _body: unknown, context: unknown, idempotency?: string) {
      captured = { path, context, idempotency };
      return { ok: true as const, data: createDefaultLayout("l1", "activity", "project", 2, catalog) };
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
