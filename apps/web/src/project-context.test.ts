import assert from "node:assert/strict";
import test from "node:test";
import { ProjectContextStore } from "./project-context.js";

test("project context store requires a valid project context", () => {
  const store = new ProjectContextStore();
  assert.throws(() => store.get(), /PROJECT_CONTEXT_NOT_SET/);
  assert.throws(
    () => store.set({ tenant_id: "t1", project_id: "p1", revision: 1.5 }),
    /INVALID_PROJECT_CONTEXT/,
  );
});

test("project context store prevents revision regression", () => {
  const store = new ProjectContextStore();
  store.set({ tenant_id: "t1", project_id: "p1", revision: 7 });
  assert.throws(() => store.updateRevision(6), /REVISION_REGRESSION/);
  store.updateRevision(42);
  assert.equal(store.get().revision, 42);
});
