import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  SCHEDULING_CONTRACT_VERSION,
  createSharedSchedulingCoreAdapter,
  validateSchedulingRequest,
  validateSchedulingResult,
  type MobileSchedulingRequest,
  type MobileSchedulingResult,
} from "./shared-scheduling-adapter.ts";

const fixture = JSON.parse(
  readFileSync(
    new URL("../../../shared/contracts/time-scheduling-parity.fixture.json", import.meta.url),
    "utf8",
  ),
) as { request: MobileSchedulingRequest; result: MobileSchedulingResult };

test("mobile uses the same canonical scheduling fixture and validator", () => {
  assert.equal(SCHEDULING_CONTRACT_VERSION, "1.0");
  assert.deepEqual(validateSchedulingRequest(fixture.request), fixture.request);
  assert.deepEqual(
    validateSchedulingResult(fixture.result, fixture.request.project_context),
    fixture.result,
  );
});

test("mobile rejects a project scope mismatch at the shared contract boundary", () => {
  assert.throws(
    () =>
      validateSchedulingResult(
        {
          ...fixture.result,
          project_context: {
            ...fixture.result.project_context,
            tenant_id: "other-tenant",
          },
        },
        fixture.request.project_context,
      ),
    /SCHEDULING_PROJECT_CONTEXT_MISMATCH/,
  );
});

test("mobile client delegates unchanged to the authoritative core", async () => {
  const calls: MobileSchedulingRequest[] = [];
  const adapter = createSharedSchedulingCoreAdapter({
    async schedule(input) {
      calls.push(input);
      return fixture.result;
    },
  });
  const actual = await adapter.schedule(validateSchedulingRequest(fixture.request));
  assert.deepEqual(calls, [fixture.request]);
  assert.deepEqual(actual, fixture.result);
});
