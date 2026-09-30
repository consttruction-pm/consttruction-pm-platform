import {strict as assert} from "node:assert";
import {describe, it} from "node:test";
import {toWorkspaceContext} from "./session-api.js";

describe("session API client", () => {
  it("projects only authoritative workspace context fields", () => {
    assert.deepEqual(
      toWorkspaceContext({tenant_id: "t1", project_id: "p1", revision: 4, user_id: "u1"}),
      {tenant_id: "t1", project_id: "p1", revision: 4},
    );
  });
});
