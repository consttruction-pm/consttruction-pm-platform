import assert from "node:assert/strict";
import test from "node:test";
import {
  MOBILE_SCHEDULING_CONTRACT_VERSION,
  createSharedSchedulingCoreAdapter,
  validateSchedulingRequest,
  type MobileSchedulingRequest,
  type MobileSchedulingResult,
} from "./shared-scheduling-adapter.ts";

const request: MobileSchedulingRequest = {
  contract_version: MOBILE_SCHEDULING_CONTRACT_VERSION,
  project_context: { tenant_id: "t1", project_id: "p1", revision: 7 },
  calculation_context: {
    schedule_mode: "EARLIEST",
    project_start: "2026-10-05T08:00:00Z",
    data_date: "2026-10-05T08:00:00Z",
    project_calendar: { calendar_id: "site", calendar_version: "3", kind: "working-time" },
  },
  activities: [{
    activity_id: "A1",
    duration_value: "4",
    duration_unit: "working-hour",
    calendar: { calendar_id: "site", calendar_version: "3", kind: "working-time" },
  }],
  relationships: [],
  constraints: [],
};

const result: MobileSchedulingResult = {
  contract_version: MOBILE_SCHEDULING_CONTRACT_VERSION,
  project_context: request.project_context,
  calculation_fingerprint: "sha256:mobile",
  project_finish: "2026-10-05T12:00:00Z",
  activities: [{
    activity_id: "A1",
    start: "2026-10-05T08:00:00Z",
    finish: "2026-10-05T12:00:00Z",
    duration: { value: "4", unit: "working-hour" },
    total_float: null,
    free_float: null,
    critical: false,
  }],
};

test("mobile adapter uses canonical shared scheduling contract", () => {
  assert.deepEqual(validateSchedulingRequest(request), request);
});

test("mobile client delegates unchanged to the authoritative core", async () => {
  const adapter = createSharedSchedulingCoreAdapter({
    async schedule(input) {
      assert.deepEqual(input, request);
      return result;
    },
  });
  assert.deepEqual(await adapter.schedule(request), result);
});
