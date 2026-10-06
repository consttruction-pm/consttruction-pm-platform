import assert from "node:assert/strict";
import test from "node:test";
import {
  SCHEDULING_CONTRACT_VERSION,
  validateSchedulingRequest,
  validateSchedulingResult,
  type SchedulingRequest,
  type SchedulingResult,
} from "./shared-scheduling-adapter.ts";

const context = { tenant_id: "tenant-web", project_id: "project-web", revision: 2 };
const request: SchedulingRequest = {
  contract_version: SCHEDULING_CONTRACT_VERSION,
  project_context: context,
  calculation_context: { schedule_mode: "EARLIEST", project_start: "2026-10-05T08:00:00Z" },
  activities: [{
    activity_id: "A1",
    duration_value: "2",
    duration_unit: "working-day",
    calendar: { calendar_id: "site", calendar_version: "1", kind: "working-day" },
  }],
  relationships: [],
  constraints: [],
};
const result: SchedulingResult = {
  contract_version: SCHEDULING_CONTRACT_VERSION,
  project_context: context,
  calculation_fingerprint: "sha256:web",
  project_finish: "2026-10-07T08:00:00Z",
  activities: [{
    activity_id: "A1",
    start: "2026-10-05T08:00:00Z",
    finish: "2026-10-06T08:00:00Z",
    duration: { value: "2", unit: "working-day" },
    total_float: null,
    free_float: null,
    critical: false,
  }],
};

test("web uses the same scheduling contract and scope validator", () => {
  assert.deepEqual(validateSchedulingRequest(request), request);
  assert.deepEqual(validateSchedulingResult(result, context), result);
});
