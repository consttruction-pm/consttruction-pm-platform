import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  SCHEDULING_CONTRACT_VERSION,
  createSharedSchedulingCoreAdapter,
  type SchedulingRequest,
  type SchedulingResult,
  validateSchedulingRequest,
  validateSchedulingResult,
} from "./scheduling-adapter.ts";

const fixture = JSON.parse(
  readFileSync(new URL("../../../shared/contracts/time-scheduling-parity.fixture.json", import.meta.url), "utf8"),
) as { request: SchedulingRequest; result: SchedulingResult };

test("shared parity fixture validates against the canonical scheduling contract", () => {
  assert.deepEqual(validateSchedulingRequest(fixture.request), fixture.request);
  assert.deepEqual(validateSchedulingResult(fixture.result, fixture.request.project_context), fixture.result);
});

test("contract version mismatch is rejected before scheduling", () => {
  assert.throws(
    () => validateSchedulingRequest({
      ...fixture.request,
      contract_version: "0.9",
    } as unknown as SchedulingRequest),
    /INVALID_SCHEDULING_CONTRACT_VERSION/,
  );
});

test("result scope mismatch is rejected", () => {
  assert.throws(
    () => validateSchedulingResult({
      ...fixture.result,
      project_context: { ...fixture.result.project_context, project_id: "other-project" },
    }, fixture.request.project_context),
    /SCHEDULING_PROJECT_CONTEXT_MISMATCH/,
  );
});

test("clients delegate unchanged to the authoritative core", async () => {
  const calls: SchedulingRequest[] = [];
  const adapter = createSharedSchedulingCoreAdapter({
    async schedule(input) {
      calls.push(input);
      return fixture.result;
    },
  });
  const actual = await adapter.schedule(validateSchedulingRequest(fixture.request));
  assert.equal(SCHEDULING_CONTRACT_VERSION, "1.0");
  assert.deepEqual(calls, [fixture.request]);
  assert.deepEqual(actual, fixture.result);
});
