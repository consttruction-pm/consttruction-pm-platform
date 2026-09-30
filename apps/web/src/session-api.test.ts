import assert from "node:assert/strict";
import test from "node:test";
import { toWorkspaceContext } from "./session-api.js";

test("session API client projects authoritative context into WorkspaceContext", () => {
  assert.deepEqual(
    toWorkspaceContext({
      tenant_id: "t1", project_id: "p1", revision: 4, user_id: "u1",
    }),
    { tenant_id: "t1", project_id: "p1", revision: 4 },
  );
});
