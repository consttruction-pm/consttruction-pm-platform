import assert from "node:assert/strict";
import test from "node:test";
import { WORKSPACE_CONTROL_ROOM_READ_VERSION } from "./workspace-read-api.js";

test("workspace read contract identity is versioned", () => {
  assert.equal(WORKSPACE_CONTROL_ROOM_READ_VERSION, "workspace-control-room-read.v1");
});
