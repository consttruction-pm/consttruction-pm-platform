import assert from "node:assert/strict";
import test from "node:test";
import {
  SCHEDULING_CONTRACT_VERSION,
  createSharedSchedulingCoreAdapter,
  type SchedulingRequest,
  type SchedulingResult,
  validateSchedulingRequest,
  validateSchedulingResult,
} from "./scheduling-adapter.ts";

const request: SchedulingRequest = {
  contract_version: SCHEDULING_CONTRACT_VERSION,
  project_context: { tenant_id: "t1", project_id: "p1", revision: 7 },
  calculation_context: {
    schedule_mode: "EARLIEST",
    project_start: "2026-10-05T08:00:00Z",
    project_finish: null,
    data_date: "2026-10-05T08:00:00Z",
    project_calendar: { calendar_id: "site", calendar_version: "3", kind: "working-time" },
    default_activity_calendar: { calendar_id: "site", calendar_version: "3", kind: "working-time" },
    default_relationship_lag_calendar: { calendar_id: "site", calendar_version: "3", kind: "working-time" },
  },
  activities: [
    {
      activity_id: "A1",
      duration_value: "4",
      duration_unit: "working-hour",
      calendar: { calendar_id: "site", calendar_version: "3", kind: "working-time" },
    },
  ],
  relationships: [],
  constraints: [],
};

const result: SchedulingResult = {
  contract_version: SCHEDULING_CONTRACT_VERSION,
  project_context: request.project_context,
  calculation_fingerprint: "sha256:001",
  project_finish: "2026-10-05T12:00:00Z",
  activities: [{
    activity_id: "A1",
    start: "2026-10-05T08:00:00Z",
    finish: "2026-10-05T12:00:00Z",
    duration: { value: "4", unit: "working-hour" },
    total_float: { value: "0", unit: "working-hour" },
    free_float: { value: "0", unit: "working-hour" },
    critical: true,
  }],
};

test("canonical request validates against one cross-client contract", () => {
  assert.deepEqual(validateSchedulingRequest(request), request);
});

test("canonical result preserves project scope and calculation identity", () => {
  assert.deepEqual(validateSchedulingResult(result, request.project_context), result);
});

test("result from a different project scope is rejected", () => {
  assert.throws(
    () => validateSchedulingResult({
      ...result,
      project_context: { ...result.project_context, project_id: "other-project" },
    }, request.project_context),
    /SCHEDULING_PROJECT_CONTEXT_MISMATCH/,
  );
});

test("clients delegate unchanged to the authoritative core", async () => {
  const calls: SchedulingRequest[] = [];
  const adapter = createSharedSchedulingCoreAdapter({
    async schedule(input) {
      calls.push(input);
      return result;
    },
  });
  const actual = await adapter.schedule(validateSchedulingRequest(request));
  assert.deepEqual(calls, [request]);
  assert.deepEqual(actual, result);
});
