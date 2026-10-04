import assert from "node:assert/strict";
import test from "node:test";
import {
  MOBILE_SCHEDULING_CONTRACT_VERSION,
  createSharedSchedulingCoreAdapter,
  type MobileSchedulingRequest,
} from "./shared-scheduling-adapter.ts";

const request: MobileSchedulingRequest = {
  contract_version: MOBILE_SCHEDULING_CONTRACT_VERSION,
  project_schema_version: 2,
  tenant_id: "t1",
  project_id: "p1",
  project_revision: 7,
  calculation_schema_version: "calc.v1",
  calendar_assignments: {
    project_calendar: { calendar_id: "site", calendar_version: 3, kind: "working-day" },
    default_activity_calendar: { calendar_id: "site", calendar_version: 3, kind: "working-day" },
    default_relationship_lag_calendar: { calendar_id: "site", calendar_version: 3, kind: "working-day" },
  },
  scheduling_settings: {
    duration: "working-day",
    calendar: "jalali-gregorian",
    lag: "working",
    constraints: "hybrid",
    mode: "both",
  },
  project_start: "2026-10-05",
  project_finish: null,
  data_date: "2026-10-05",
  activities: [
    { id: "A1", duration: { value: "2", unit: "WORKING_DAY" } },
    { id: "A2", duration: { value: "1", unit: "WORKING_DAY" } },
  ],
  relationships: [
    {
      predecessor_id: "A1",
      successor_id: "A2",
      type: "FS",
      lag: { value: "0", unit: "WORKING_DAY" },
    },
  ],
  constraints: [],
};

function deterministicResult(): Readonly<{
  contract_version: typeof MOBILE_SCHEDULING_CONTRACT_VERSION;
  calculation_fingerprint: string;
  project_finish: string;
  activities: readonly object[];
}> {
  return {
    contract_version: MOBILE_SCHEDULING_CONTRACT_VERSION,
    calculation_fingerprint: "core-fp-001",
    project_finish: "2026-10-07",
    activities: [
      {
        activity_id: "A1",
        start: "2026-10-05",
        finish: "2026-10-06",
        duration: { value: "2", unit: "WORKING_DAY" },
        total_float: { value: "0", unit: "WORKING_DAY" },
        free_float: { value: "0", unit: "WORKING_DAY" },
        critical: true,
      },
      {
        activity_id: "A2",
        start: "2026-10-07",
        finish: "2026-10-07",
        duration: { value: "1", unit: "WORKING_DAY" },
        total_float: { value: "0", unit: "WORKING_DAY" },
        free_float: { value: "0", unit: "WORKING_DAY" },
        critical: true,
      },
    ],
  };
}

test("mobile scheduling boundary delegates unchanged to the authoritative core", async () => {
  const calls: MobileSchedulingRequest[] = [];
  const adapter = createSharedSchedulingCoreAdapter({
    async schedule(input) {
      calls.push(input);
      return deterministicResult();
    },
  });

  const result = await adapter.schedule(request);
  assert.deepEqual(result, deterministicResult());
  assert.deepEqual(calls[0], request);
});

test("the same portable input can be scheduled twice without client-side drift", async () => {
  const adapter = createSharedSchedulingCoreAdapter({
    async schedule() {
      return deterministicResult();
    },
  });

  const first = await adapter.schedule(request);
  const second = await adapter.schedule(request);
  assert.deepEqual(first, second);
  assert.equal(first.calculation_fingerprint, second.calculation_fingerprint);
});
