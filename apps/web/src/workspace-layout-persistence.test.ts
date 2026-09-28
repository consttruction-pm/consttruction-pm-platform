import test from "node:test";
import assert from "node:assert/strict";
import {
  ApiWorkspaceLayoutStore,
  workspaceLayoutCacheKey,
} from "./workspace-layout-persistence.js";
import { createDefaultLayout } from "./workspace-layout.js";

const catalog = [{
  id: "activity_id",
  source: "standard" as const,
  dataType: "string" as const,
  subjectArea: "activity",
  label: "Activity ID",
  writable: false,
  computed: false,
  unit: null,
  nullable: null,
  allowedValues: [],
  p6Field: "ActivityId",
  filterable: true,
  orderable: true,
}];

test("API layout store rejects stale client revision before save", async () => {
  let called = false;
  const transport = {
    async get() { throw new Error("not used"); },
    async post<TRequest, TResponse>(): Promise<{ ok: false; error: never }> {
      called = true;
      throw new Error("not used");
    },
  };
  const store = new ApiWorkspaceLayoutStore(transport, "/layout", catalog);
  const layout = createDefaultLayout("l1", "activity", "project", 2, catalog);
  const result = await store.saveToApi(
    "k",
    { tenant_id: "t1", project_id: "p1", revision: 3 },
    layout,
    "idem-1",
  );
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.error.code, "STALE_WORKSPACE_LAYOUT_REVISION");
  assert.equal(called, false);
});

test("API layout store sends ProjectContext and idempotency key on save", async () => {
  let captured: { path?: string; context?: unknown; idempotency?: string } = {};
  const transport = {
    async get() { throw new Error("not used"); },
    async post<TRequest, TResponse>(
      path: string,
      _body: TRequest,
      context: unknown,
      idempotency?: string,
    ): Promise<{ ok: true; data: TResponse }> {
      captured = { path, context, idempotency };
      return {
        ok: true as const,
        data: createDefaultLayout("l1", "activity", "project", 2, catalog) as TResponse,
      };
    },
  };
  const store = new ApiWorkspaceLayoutStore(transport, "/layout", catalog);
  const layout = createDefaultLayout("l1", "activity", "project", 2, catalog);
  const result = await store.saveToApi(
    "k",
    { tenant_id: "t1", project_id: "p1", revision: 2 },
    layout,
    "idem-2",
  );
  assert.equal(result.ok, true);
  assert.equal(captured.path, "/layout");
  assert.deepEqual(captured.context, { tenant_id: "t1", project_id: "p1", revision: 2 });
  assert.equal(captured.idempotency, "idem-2");
});

test("cache keys isolate tenant, project, scope and layout identity", () => {
  const context = { tenant_id: "t1", project_id: "p1", revision: 4 };
  const base = { subjectArea: "activity", layoutId: "main" } as const;
  assert.notEqual(workspaceLayoutCacheKey(context, { ...base, scope: "global" }), workspaceLayoutCacheKey(context, { ...base, scope: "project" }));
  assert.notEqual(workspaceLayoutCacheKey(context, { ...base, scope: "project" }), workspaceLayoutCacheKey({ ...context, project_id: "p2" }, { ...base, scope: "project" }));
  assert.notEqual(workspaceLayoutCacheKey(context, { ...base, scope: "user" }, "user-a"), workspaceLayoutCacheKey(context, { ...base, scope: "user" }, "user-b"));
});

test("load sends explicit layout identity and rejects a server revision conflict", async () => {
  let path = "";
  const transport = {
    async get<T>(requestPath: string): Promise<{ ok: true; data: T }> {
      path = requestPath;
      return { ok: true as const, data: { revision: 9 } as T };
    },
    async post() { throw new Error("not used"); },
  };
  const store = new ApiWorkspaceLayoutStore(transport, "/layout?format=json", catalog);
  const result = await store.loadFromApi(
    "k",
    { tenant_id: "t1", project_id: "p1", revision: 8 },
    "activity",
    "project",
    "main",
  );
  assert.equal(path, "/layout?format=json&subject_area=activity&scope=project&layout_id=main");
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.error.code, "WORKSPACE_LAYOUT_REVISION_CONFLICT");
});

test("load migrates a matching server layout and caches it", async () => {
  const layout = createDefaultLayout("main", "activity", "user", 4, catalog);
  const transport = {
    async get<T>(): Promise<{ ok: true; data: T }> {
      return { ok: true as const, data: layout as T };
    },
    async post() { throw new Error("not used"); },
  };
  const store = new ApiWorkspaceLayoutStore(transport, "/layout", catalog);
  const result = await store.loadFromApi(
    "tenant::project::user::activity::main",
    { tenant_id: "t1", project_id: "p1", revision: 4 },
    "activity",
    "user",
    "main",
  );
  assert.equal(result.ok, true);
  assert.equal(store.load("tenant::project::user::activity::main")?.layout_id, "main");
});
