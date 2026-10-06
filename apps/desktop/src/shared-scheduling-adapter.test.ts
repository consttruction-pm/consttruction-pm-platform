import assert from "node:assert/strict";
import test from "node:test";
import {
  SCHEDULING_CONTRACT_VERSION,
  validateSchedulingRequest,
  validateSchedulingResult,
  type SchedulingRequest,
  type SchedulingResult,
} from "./shared-scheduling-adapter.ts";

const context = { tenant_id: "tenant-desktop", project_id: "project-desktop", revision: 4 };
const request: SchedulingRequest = {
  contract_version: SCHEDULING_CONTRACT_VERSION,
  project_context: context,
  calculation_context: { schedule_mode: "ALAP", project_start: "2026-10-05T08:00:00Z" },
  activities: [{
    activity_id: "A1",
    duration_value: "4",
    duration_unit: "working-hour",
    calendar: { calendar_id: "site", calendar_version: "5", kind: "working-time" },
  }],
  relationships: [],
  constraints: [],
};
const result: SchedulingResult = {
  contract_version: SCHEDULING_CONTRACT_VERSION,
  project_context: context,
  calculation_fingerprint: "sha256:desktop",
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

test("desktop uses the same scheduling contract and scope validator", () => {
  assert.deepEqual(validateSchedulingRequest(request), request);
  assert.deepEqual(validateSchedulingResult(result, context), result);
});
