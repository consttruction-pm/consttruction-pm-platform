import assert from "node:assert/strict";
import test from "node:test";
import { listWorkspaceEntityComments, WORKSPACE_COMMENTS_STORAGE_KEY } from "./workspace-comments.js";

function storage(entries: readonly unknown[]) {
  return { getItem(key: string): string | null {
    return key === WORKSPACE_COMMENTS_STORAGE_KEY ? JSON.stringify(entries) : null;
  } };
}

test("local Notebook lookup is scoped to the selected project and activity", () => {
  const entries = [
    { id: "C-2", projectId: "project-1", entityKind: "activity", entityId: "A-2", author: "Planner", body: "Second note", createdAt: "2026-11-05T10:00:00Z", parentId: null },
    { id: "C-1", projectId: "project-1", entityKind: "activity", entityId: "A-2", author: "Engineer", body: "First note", createdAt: "2026-11-05T09:00:00Z", parentId: null },
    { id: "C-3", projectId: "project-1", entityKind: "activity", entityId: "A-1", author: "Other", body: "Other activity", createdAt: "2026-11-05T08:00:00Z", parentId: null },
    { id: "C-4", projectId: "project-2", entityKind: "activity", entityId: "A-2", author: "Other", body: "Other project", createdAt: "2026-11-05T07:00:00Z", parentId: null },
  ];
  const result = listWorkspaceEntityComments({ projectId: "project-1", entityKind: "activity", entityId: "A-2" }, storage(entries));
  assert.deepEqual(result.map((item) => item.id), ["C-1", "C-2"]);
  assert.equal(result[0]?.body, "First note");
});

test("local Notebook lookup ignores malformed storage and malformed records", () => {
  const malformed = { getItem: () => "not-json" };
  assert.deepEqual(listWorkspaceEntityComments({ projectId: "project-1", entityKind: "activity", entityId: "A-2" }, malformed), []);
  const invalidEntries = storage([{ id: "C-1" }, null, { id: "C-2", projectId: "project-1", entityId: "A-2", body: "Missing kind", createdAt: "2026-11-05T09:00:00Z" }]);
  assert.deepEqual(listWorkspaceEntityComments({ projectId: "project-1", entityKind: "activity", entityId: "A-2" }, invalidEntries), []);
});
