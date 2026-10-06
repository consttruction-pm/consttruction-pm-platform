import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  validateSchedulingRequest,
  validateSchedulingResult,
  type SchedulingRequest,
  type SchedulingResult,
} from "./shared-scheduling-adapter.ts";

const fixture = JSON.parse(
  readFileSync(new URL("../../../shared/contracts/time-scheduling-parity.fixture.json", import.meta.url), "utf8"),
) as { request: SchedulingRequest; result: SchedulingResult };

test("desktop uses the same shared scheduling fixture and validator", () => {
  assert.deepEqual(validateSchedulingRequest(fixture.request), fixture.request);
  assert.deepEqual(validateSchedulingResult(fixture.result, fixture.request.project_context), fixture.result);
});
