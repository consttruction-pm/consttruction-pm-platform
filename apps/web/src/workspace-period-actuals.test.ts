import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  buildPeriodActualPayload,
  loadPeriodActuals,
  parsePeriodActual,
  parsePeriodActualList,
  periodActualErrorNotice,
  periodActualId,
  periodActualsPath,
  savePeriodActual,
} from "./workspace-period-actuals.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 4 };

const ACTUAL = {
  contract_version: "p6-activity-period-actual-api.v1",
  kind: "p6_activity_period_actual",
  scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 },
  activity_period_actual: {
    actual_id: "SPP-A140-2026-09",
    activity_id: "A140",
    period_id: "2026-09",
    actual_units: "3.125",
    actual_cost: "20.50",
    unit: "h",
    currency: "USD",
    note: "period actual",
  },
};

type Calls = {
  gets: { path: string }[];
  posts: { path: string; request: unknown }[];
};

function transportWith(result: ApiResult<unknown>, calls: Calls = { gets: [], posts: [] }): ApiTransport {
  return {
    async get(path) {
      calls.gets.push({ path });
      return result as ApiResult<never>;
    },
    async post(path, request) {
      calls.posts.push({ path, request });
      return result as ApiResult<never>;
    },
  };
}

test("parses a stored period actual and its list envelope", () => {
  assert.deepEqual(parsePeriodActual(ACTUAL), {
    actualId: "SPP-A140-2026-09",
    activityId: "A140",
    periodId: "2026-09",
    actualUnits: "3.125",
    actualCost: "20.50",
    unit: "h",
    currency: "USD",
    note: "period actual",
  });
  assert.deepEqual(
    parsePeriodActualList({
      contract_version: "p6-activity-period-actual-api.v1",
      activity_period_actuals: [ACTUAL],
    }),
    [parsePeriodActual(ACTUAL)],
  );
  const sparse = parsePeriodActual({
    ...ACTUAL,
    activity_period_actual: {
      ...ACTUAL.activity_period_actual,
      actual_cost: null,
      unit: null,
      currency: null,
      note: null,
    },
  });
  assert.equal(sparse.actualCost, null);
  assert.equal(sparse.note, null);
});

test("rejects malformed period actual responses", () => {
  assert.throws(() => parsePeriodActual({ ...ACTUAL, contract_version: "v0" }), /INVALID_PERIOD_ACTUAL/);
  assert.throws(() => parsePeriodActual({ ...ACTUAL, kind: "other" }), /INVALID_PERIOD_ACTUAL/);
  assert.throws(
    () => parsePeriodActual({ ...ACTUAL, activity_period_actual: { ...ACTUAL.activity_period_actual, activity_id: "" } }),
    /INVALID_PERIOD_ACTUAL/,
  );
  assert.throws(
    () => parsePeriodActual({ ...ACTUAL, activity_period_actual: { ...ACTUAL.activity_period_actual, actual_units: "1,5" } }),
    /INVALID_PERIOD_ACTUAL/,
  );
  assert.throws(
    () => parsePeriodActualList({ contract_version: "p6-activity-period-actual-api.v1", activity_period_actuals: {} }),
    /INVALID_PERIOD_ACTUAL_LIST/,
  );
});

test("builds the exact period actual payload with a deterministic identity", () => {
  assert.equal(periodActualId(" A140 ", " 2026-09 "), "SPP-A140-2026-09");
  assert.deepEqual(
    buildPeriodActualPayload({
      activityId: " A140 ",
      periodId: " 2026-09 ",
      actualUnits: "3.125",
      actualCost: "",
      unit: " h ",
      currency: "",
      note: " period actual ",
    }),
    {
      contract_version: "p6-activity-period-actual-api.v1",
      actual_id: "SPP-A140-2026-09",
      activity_id: "A140",
      period_id: "2026-09",
      actual_units: "3.125",
      actual_cost: null,
      unit: "h",
      currency: null,
      note: "period actual",
    },
  );
});

test("period actual payload rejects missing scope, missing values and malformed decimals", () => {
  assert.throws(
    () => buildPeriodActualPayload({ activityId: "", periodId: "2026-09", actualUnits: "1", actualCost: "", unit: "", currency: "", note: "" }),
    /PERIOD_ACTUAL_SCOPE_REQUIRED/,
  );
  assert.throws(
    () => buildPeriodActualPayload({ activityId: "A140", periodId: "2026-09", actualUnits: "", actualCost: "", unit: "", currency: "", note: "" }),
    /PERIOD_ACTUAL_VALUE_REQUIRED/,
  );
  assert.throws(
    () => buildPeriodActualPayload({ activityId: "A140", periodId: "2026-09", actualUnits: "1.2.3", actualCost: "", unit: "", currency: "", note: "" }),
    /INVALID_ACTUAL_UNITS/,
  );
  assert.throws(
    () => buildPeriodActualPayload({ activityId: "A140", periodId: "2026-09", actualUnits: "", actualCost: "abc", unit: "", currency: "", note: "" }),
    /INVALID_ACTUAL_COST/,
  );
});

test("period actual list and write use the project path and query filters", async () => {
  assert.equal(
    periodActualsPath(CONTEXT, { activityId: "A 140", periodId: "2026-09" }),
    "/api/projects/project-1/p6/activity-period-actuals?activity_id=A+140&period_id=2026-09",
  );
  const calls: Calls = { gets: [], posts: [] };
  const listResult = await loadPeriodActuals(
    transportWith({ ok: true, data: { contract_version: "p6-activity-period-actual-api.v1", activity_period_actuals: [ACTUAL] } }, calls),
    CONTEXT,
    { activityId: "A140" },
  );
  assert.equal(listResult.ok, true);
  assert.deepEqual(calls.gets, [{ path: "/api/projects/project-1/p6/activity-period-actuals?activity_id=A140" }]);

  const writeCalls: Calls = { gets: [], posts: [] };
  const saved = await savePeriodActual(
    transportWith({ ok: true, data: ACTUAL }, writeCalls),
    CONTEXT,
    { activityId: "A140", periodId: "2026-09", actualUnits: "3.125", actualCost: "20.50", unit: "h", currency: "USD", note: "period actual" },
  );
  assert.equal(saved.ok, true);
  assert.deepEqual(writeCalls.posts, [
    {
      path: "/api/projects/project-1/p6/activity-period-actuals",
      request: {
        contract_version: "p6-activity-period-actual-api.v1",
        actual_id: "SPP-A140-2026-09",
        activity_id: "A140",
        period_id: "2026-09",
        actual_units: "3.125",
        actual_cost: "20.50",
        unit: "h",
        currency: "USD",
        note: "period actual",
      },
    },
  ]);
});

test("period actual write short-circuits invalid input without a POST", async () => {
  const calls: Calls = { gets: [], posts: [] };
  const result = await savePeriodActual(
    transportWith({ ok: true, data: ACTUAL }, calls),
    CONTEXT,
    { activityId: "A140", periodId: "2026-09", actualUnits: "", actualCost: "", unit: "", currency: "", note: "" },
  );
  assert.equal(result.ok, false);
  assert.equal(!result.ok && result.error.code, "PERIOD_ACTUAL_VALUE_REQUIRED");
  assert.deepEqual(calls.posts, []);
});

test("period actual rejections are explained in English and Persian", () => {
  assert.match(periodActualErrorNotice("IMMUTABLE_ACTIVITY_PERIOD_ACTUAL", "en"), /immutable/i);
  assert.match(periodActualErrorNotice("IMMUTABLE_ACTIVITY_PERIOD_ACTUAL", "fa-IR"), /تغییرناپذیر/);
  assert.match(periodActualErrorNotice("P6_ACTIVITY_PERIOD_ACTUAL_PERIOD_NOT_FOUND", "en"), /financial period/i);
  assert.match(periodActualErrorNotice("AUTHORIZATION_PERMISSION_DENIED", "fa"), /اجازهٔ/);
  assert.equal(
    periodActualErrorNotice("SOMETHING_ELSE", "en"),
    "Period actual was not stored (SOMETHING_ELSE)",
  );
});
