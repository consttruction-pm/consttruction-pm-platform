import assert from "node:assert/strict";
import test from "node:test";

import {
  allowedTargets,
  assertTransition,
  canTransition,
} from "./field-assurance-workflows.js";

test("inspection workflow exposes lifecycle transitions and terminal states", () => {
  assert.deepEqual(allowedTargets("inspection", "draft"), ["scheduled", "in_progress", "cancelled"]);
  assert.equal(canTransition({ resource: "inspection", from: "in_progress", to: "completed" }), true);
  assert.equal(canTransition({ resource: "inspection", from: "completed", to: "in_progress" }), false);
});

test("quality workflow supports verification and closeout without bypassing verification", () => {
  assert.deepEqual(
    allowedTargets("quality_record", "pending_verification"),
    ["accepted", "rejected"],
  );
  assert.equal(canTransition({ resource: "quality_record", from: "accepted", to: "closed" }), true);
  assert.equal(canTransition({ resource: "quality_record", from: "in_progress", to: "closed" }), false);
});

test("safety workflow requires resolution before close", () => {
  assert.equal(canTransition({ resource: "safety_observation", from: "open", to: "resolved" }), true);
  assert.equal(canTransition({ resource: "safety_observation", from: "open", to: "closed" }), false);
  assert.deepEqual(allowedTargets("safety_observation", "closed"), []);
});

test("punch workflow requires verification readiness before closeout", () => {
  assert.equal(canTransition({ resource: "punch_item", from: "in_progress", to: "ready_for_verification" }), true);
  assert.equal(canTransition({ resource: "punch_item", from: "in_progress", to: "closed" }), false);
  assert.equal(canTransition({ resource: "punch_item", from: "ready_for_verification", to: "closed" }), true);
});

test("invalid transitions fail with a stable workflow error", () => {
  assert.throws(
    () => assertTransition({
      resource: "punch_item",
      from: "closed",
      to: "in_progress",
    }),
    /INVALID_PUNCH_ITEM_TRANSITION:closed->in_progress/,
  );
});
