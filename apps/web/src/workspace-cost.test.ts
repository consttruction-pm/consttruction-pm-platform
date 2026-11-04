import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  buildEarnedValuePayload,
  buildFinancialPeriodPayload,
  createFinancialPeriod,
  loadBaselines,
  loadFinancialPeriods,
  loadScheduleDataDate,
  measureEarnedValue,
  parseBaseline,
  parseEarnedValue,
  parseFinancialPeriod,
  parseScheduleDataDate,
} from "./workspace-cost.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 7 };

function periodEnvelope(overrides: Record<string, unknown> = {}) {
  return {
    contract_version: "p6-financial-period-api.v1",
    kind: "p6_financial_period",
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 7 },
    financial_period: {
      period_id: "FY-2026-Q4",
      name: "Q4 2026",
      start_date: "2026-10-01",
      end_date: "2026-12-31",
      status: "OPEN",
      ...overrides,
    },
  };
}

function baselineEnvelope(overrides: Record<string, unknown> = {}) {
  return {
    contract_version: "p6-baseline-api.v1",
    kind: "p6_baseline",
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 7 },
    baseline: {
      baseline_id: "BL-1",
      name: "Approved baseline",
      baseline_type: "PRIMARY",
      source_revision: 6,
      created_at: "2026-10-01T00:00:00+00:00",
      notes: null,
      ...overrides,
    },
  };
}

function earnedValueEnvelope(overrides: Record<string, unknown> = {}) {
  return {
    contract_version: "p6-earned-value-read-model.v1",
    kind: "p6_earned_value_read_model",
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 7 },
    baseline_id: "BL-1",
    data_date: "2026-10-12",
    currency: "USD",
    pv_method: "LINEAR_WORKING_DAYS_ACTIVITY_BUDGET",
    activities: [],
    wbs_rollups: [],
    cost_adjustments: [],
    earned_value: {
      planned_value: "1200.00",
      earned_value: "900.00",
      actual_cost: "800.00",
      cost_variance: "100.00",
      schedule_variance: "-300.00",
      cost_performance_index: "1.125",
      schedule_performance_index: "0.75",
      etc_method: "PF_ONE",
      budget_at_completion: "3500.00",
      estimate_to_complete: "2600.00",
      estimate_at_completion: "3400.00",
      variance_at_completion: "100.00",
      performance_factor: "1",
      ...overrides,
    },
  };
}

function transportWith(
  responses: Record<string, ApiResult<unknown>>,
  calls: { gets: { path: string }[]; posts: { path: string; request: unknown }[] },
): ApiTransport {
  return {
    async get(path) {
      calls.gets.push({ path });
      const response = responses[`GET ${path}`];
      if (!response) throw new Error(`unexpected GET ${path}`);
      return response as ApiResult<never>;
    },
    async post(path, request) {
      calls.posts.push({ path, request });
      const response = responses[`POST ${path}`];
      if (!response) throw new Error(`unexpected POST ${path}`);
      return response as ApiResult<never>;
    },
  };
}

test("financial period list reads the versioned contract and fails closed on bad rows", async () => {
  const calls = { gets: [] as { path: string }[], posts: [] as { path: string; request: unknown }[] };
  const ok = await loadFinancialPeriods(
    transportWith(
      {
        "GET /api/projects/project-1/p6/financial-periods": {
          ok: true,
          data: {
            contract_version: "p6-financial-period-api.v1",
            financial_periods: [periodEnvelope(), periodEnvelope({ period_id: "FY-2027-Q1", name: "Q1 2027" })],
          },
        },
      },
      calls,
    ),
    CONTEXT,
  );
  assert.ok(ok.ok);
  assert.deepEqual(ok.data.map((item) => item.periodId), ["FY-2026-Q4", "FY-2027-Q1"]);
  assert.deepEqual(calls.gets, [{ path: "/api/projects/project-1/p6/financial-periods" }]);

  const bad = await loadFinancialPeriods(
    transportWith(
      {
        "GET /api/projects/project-1/p6/financial-periods": {
          ok: true,
          data: {
            contract_version: "p6-financial-period-api.v1",
            financial_periods: [periodEnvelope({ status: "PENDING" })],
          },
        },
      },
      { gets: [], posts: [] },
    ),
    CONTEXT,
  );
  assert.equal(bad.ok, false);
  assert.equal(bad.ok ? "" : bad.error.code, "INVALID_FINANCIAL_PERIOD_RECORD");
});

test("financial period records require the expected envelope and a valid status", () => {
  assert.deepEqual(parseFinancialPeriod(periodEnvelope()), {
    periodId: "FY-2026-Q4",
    name: "Q4 2026",
    startDate: "2026-10-01",
    endDate: "2026-12-31",
    status: "OPEN",
  });
  assert.throws(() => parseFinancialPeriod(periodEnvelope({ status: "UNKNOWN" })), /INVALID_FINANCIAL_PERIOD_RECORD/);
  assert.throws(() => parseFinancialPeriod(periodEnvelope({ period_id: " " })), /INVALID_FINANCIAL_PERIOD_RECORD/);
  assert.throws(() => parseFinancialPeriod({ ...periodEnvelope(), kind: "p6_baseline" }), /INVALID_FINANCIAL_PERIOD_RESPONSE/);
});

test("financial period payload validates identifiers, dates and order before writing", () => {
  assert.deepEqual(
    buildFinancialPeriodPayload({
      periodId: " FY-2026-Q4 ",
      name: " Q4 2026 ",
      startDate: "2026-10-01",
      endDate: "2026-12-31",
      status: "OPEN",
    }),
    {
      period_id: "FY-2026-Q4",
      name: "Q4 2026",
      start_date: "2026-10-01",
      end_date: "2026-12-31",
      status: "OPEN",
    },
  );
  assert.throws(() => buildFinancialPeriodPayload({ periodId: "", name: "Q4", startDate: "2026-10-01", endDate: "2026-12-31", status: "OPEN" }), /PERIOD_ID_REQUIRED/);
  assert.throws(() => buildFinancialPeriodPayload({ periodId: "P1", name: "", startDate: "2026-10-01", endDate: "2026-12-31", status: "OPEN" }), /PERIOD_NAME_REQUIRED/);
  assert.throws(() => buildFinancialPeriodPayload({ periodId: "P1", name: "Q4", startDate: "2026-13-01", endDate: "2026-12-31", status: "OPEN" }), /INVALID_PERIOD_START/);
  assert.throws(() => buildFinancialPeriodPayload({ periodId: "P1", name: "Q4", startDate: "2026-12-31", endDate: "2026-10-01", status: "OPEN" }), /PERIOD_END_BEFORE_START/);
  assert.throws(() => buildFinancialPeriodPayload({ periodId: "P1", name: "Q4", startDate: "2026-10-01", endDate: "2026-12-31", status: "PENDING" }), /INVALID_PERIOD_STATUS/);
});

test("create financial period posts the typed payload and reads the stored record", async () => {
  const calls = { gets: [] as { path: string }[], posts: [] as { path: string; request: unknown }[] };
  const result = await createFinancialPeriod(
    transportWith(
      {
        "POST /api/projects/project-1/p6/financial-periods": { ok: true, data: periodEnvelope() },
      },
      calls,
    ),
    CONTEXT,
    { periodId: "FY-2026-Q4", name: "Q4 2026", startDate: "2026-10-01", endDate: "2026-12-31", status: "OPEN" },
  );
  assert.ok(result.ok);
  assert.equal(result.data.periodId, "FY-2026-Q4");
  assert.deepEqual(calls.posts, [
    {
      path: "/api/projects/project-1/p6/financial-periods",
      request: {
        period_id: "FY-2026-Q4",
        name: "Q4 2026",
        start_date: "2026-10-01",
        end_date: "2026-12-31",
        status: "OPEN",
      },
    },
  ]);
});

test("baseline list reads the versioned contract and preserves the source revision", async () => {
  const calls = { gets: [] as { path: string }[], posts: [] as { path: string; request: unknown }[] };
  const result = await loadBaselines(
    transportWith(
      {
        "GET /api/projects/project-1/p6/baselines": {
          ok: true,
          data: { contract_version: "p6-baseline-api.v1", baselines: [baselineEnvelope()] },
        },
      },
      calls,
    ),
    CONTEXT,
  );
  assert.ok(result.ok);
  assert.deepEqual(result.data[0], {
    baselineId: "BL-1",
    name: "Approved baseline",
    baselineType: "PRIMARY",
    sourceRevision: 6,
    createdAt: "2026-10-01T00:00:00+00:00",
  });
  assert.deepEqual(calls.gets, [{ path: "/api/projects/project-1/p6/baselines" }]);
  assert.throws(() => parseBaseline(baselineEnvelope({ source_revision: 1.5 })), /INVALID_BASELINE_RECORD/);
});

test("schedule settings supply the stored Data Date without inventing one", async () => {
  assert.equal(
    parseScheduleDataDate({
      contract_version: "p6-project-schedule-settings-api.v1",
      kind: "project_schedule_settings",
      schedule_options: { data_date: "2026-10-12" },
    }),
    "2026-10-12",
  );
  assert.equal(
    parseScheduleDataDate({
      contract_version: "p6-project-schedule-settings-api.v1",
      kind: "project_schedule_settings",
      schedule_options: { data_date: null },
    }),
    null,
  );
  assert.throws(
    () =>
      parseScheduleDataDate({
        contract_version: "p6-project-schedule-settings-api.v1",
        kind: "project_schedule_settings",
        schedule_options: { data_date: "12/10/2026" },
      }),
    /INVALID_SCHEDULE_DATA_DATE/,
  );

  const calls = { gets: [] as { path: string }[], posts: [] as { path: string; request: unknown }[] };
  const result = await loadScheduleDataDate(
    transportWith(
      {
        "GET /api/projects/project-1/p6/schedule/settings": {
          ok: true,
          data: {
            contract_version: "p6-project-schedule-settings-api.v1",
            kind: "project_schedule_settings",
            schedule_options: { data_date: "2026-10-12" },
          },
        },
      },
      calls,
    ),
    CONTEXT,
  );
  assert.deepEqual(result, { ok: true, data: "2026-10-12" });
  assert.deepEqual(calls.gets, [{ path: "/api/projects/project-1/p6/schedule/settings" }]);
});

test("earned-value results are read exactly as the shared read model returns them", () => {
  assert.deepEqual(parseEarnedValue(earnedValueEnvelope()), {
    baselineId: "BL-1",
    dataDate: "2026-10-12",
    currency: "USD",
    pvMethod: "LINEAR_WORKING_DAYS_ACTIVITY_BUDGET",
    plannedValue: "1200.00",
    earnedValue: "900.00",
    actualCost: "800.00",
    costVariance: "100.00",
    scheduleVariance: "-300.00",
    costPerformanceIndex: "1.125",
    schedulePerformanceIndex: "0.75",
    etcMethod: "PF_ONE",
    budgetAtCompletion: "3500.00",
    estimateToComplete: "2600.00",
    estimateAtCompletion: "3400.00",
    varianceAtCompletion: "100.00",
    performanceFactor: "1",
  });
  assert.equal(parseEarnedValue(earnedValueEnvelope({ cost_performance_index: null })).costPerformanceIndex, null);
  assert.throws(() => parseEarnedValue({ ...earnedValueEnvelope(), kind: "p6_earned_value" }), /INVALID_EARNED_VALUE_RESPONSE/);
  assert.throws(() => parseEarnedValue(earnedValueEnvelope({ planned_value: "n/a" })), /INVALID_EARNED_VALUE_RECORD/);
});

test("earned-value payload carries only the selection, never computed values", () => {
  assert.deepEqual(
    buildEarnedValuePayload({
      baselineId: "BL-1",
      dataDate: "2026-10-12",
      currency: "USD",
      etcMethod: "PF_CPI",
      performanceFactor: "9",
    }),
    {
      contract_version: "p6-earned-value-read-model.v1",
      baseline_id: "BL-1",
      data_date: "2026-10-12",
      currency: "USD",
      etc_method: "PF_CPI",
    },
  );
  assert.deepEqual(
    buildEarnedValuePayload({
      baselineId: "BL-1",
      dataDate: "2026-10-12",
      currency: "USD",
      etcMethod: "USER_PF",
      performanceFactor: "1.2",
    }),
    {
      contract_version: "p6-earned-value-read-model.v1",
      baseline_id: "BL-1",
      data_date: "2026-10-12",
      currency: "USD",
      etc_method: "USER_PF",
      performance_factor: "1.2",
    },
  );
  assert.throws(() => buildEarnedValuePayload({ baselineId: "", dataDate: "2026-10-12", currency: "USD", etcMethod: "PF_ONE", performanceFactor: "" }), /BASELINE_REQUIRED/);
  assert.throws(() => buildEarnedValuePayload({ baselineId: "BL-1", dataDate: "", currency: "USD", etcMethod: "PF_ONE", performanceFactor: "" }), /DATA_DATE_REQUIRED/);
  assert.throws(() => buildEarnedValuePayload({ baselineId: "BL-1", dataDate: "2026-02-30", currency: "USD", etcMethod: "PF_ONE", performanceFactor: "" }), /INVALID_DATA_DATE/);
  assert.throws(() => buildEarnedValuePayload({ baselineId: "BL-1", dataDate: "2026-10-12", currency: "", etcMethod: "PF_ONE", performanceFactor: "" }), /CURRENCY_REQUIRED/);
  assert.throws(() => buildEarnedValuePayload({ baselineId: "BL-1", dataDate: "2026-10-12", currency: "USD", etcMethod: "GUESS", performanceFactor: "" }), /INVALID_ETC_METHOD/);
  assert.throws(() => buildEarnedValuePayload({ baselineId: "BL-1", dataDate: "2026-10-12", currency: "USD", etcMethod: "USER_PF", performanceFactor: "0" }), /INVALID_PERFORMANCE_FACTOR/);
});

test("measure earned value posts the selection and returns the authoritative result", async () => {
  const calls = { gets: [] as { path: string }[], posts: [] as { path: string; request: unknown }[] };
  const result = await measureEarnedValue(
    transportWith(
      {
        "POST /api/projects/project-1/p6/earned-value": { ok: true, data: earnedValueEnvelope() },
      },
      calls,
    ),
    CONTEXT,
    { baselineId: "BL-1", dataDate: "2026-10-12", currency: "USD", etcMethod: "PF_ONE", performanceFactor: "" },
  );
  assert.ok(result.ok);
  assert.equal(result.data.estimateAtCompletion, "3400.00");
  assert.deepEqual(calls.posts, [
    {
      path: "/api/projects/project-1/p6/earned-value",
      request: {
        contract_version: "p6-earned-value-read-model.v1",
        baseline_id: "BL-1",
        data_date: "2026-10-12",
        currency: "USD",
        etc_method: "PF_ONE",
      },
    },
  ]);

  const failed = await measureEarnedValue(
    transportWith(
      {
        "POST /api/projects/project-1/p6/earned-value": {
          ok: false,
          error: { code: "EVM_BASELINE_ACTIVITIES_EMPTY:BL-1", retryable: false, message_key: "error.p6.baseline.not_found", available_actions: [] },
        },
      },
      { gets: [], posts: [] },
    ),
    CONTEXT,
    { baselineId: "BL-1", dataDate: "2026-10-12", currency: "USD", etcMethod: "PF_ONE", performanceFactor: "" },
  );
  assert.equal(failed.ok, false);
  assert.equal(failed.ok ? "" : failed.error.code, "EVM_BASELINE_ACTIVITIES_EMPTY:BL-1");
});
