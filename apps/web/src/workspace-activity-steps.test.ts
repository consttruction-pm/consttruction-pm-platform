import assert from "node:assert/strict";
import test from "node:test";
import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { ACTIVITY_STEP_API_VERSION, loadActivitySteps, parseActivityStep } from "./workspace-activity-steps.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 4 };
const STEP = {
  step_id: "S-01", activity_id: "A-100", sequence: 1, description: "Inspect formwork",
  weight: "12.50", start_date: "2026-11-01", finish_date: "2026-11-02",
  udf_values: [{ field_id: "crew", value: "C-01" }],
};
function stepEnvelope(step: unknown = STEP) {
  return { contract_version: ACTIVITY_STEP_API_VERSION, kind: "p6_activity_step",
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 }, step };
}
function listEnvelope(steps: unknown[] = [stepEnvelope()]) {
  return { contract_version: ACTIVITY_STEP_API_VERSION,
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 }, steps };
}
type Calls = { gets: { path: string }[] };
function transportWith(result: ApiResult<unknown>, calls: Calls = { gets: [] }): ApiTransport {
  return {
    async get(path) { calls.gets.push({ path }); return result as ApiResult<never>; },
    async post() { throw new Error("POST_NOT_EXPECTED"); },
  };
}
test("activity-step parser preserves identity, sequence, decimal weight, dates and UDF values", () => {
  assert.deepEqual(parseActivityStep(stepEnvelope(), CONTEXT), {
    stepId: "S-01", activityId: "A-100", sequence: 1, description: "Inspect formwork",
    weight: "12.50", startDate: "2026-11-01", finishDate: "2026-11-02",
    udfValues: [{ fieldId: "crew", value: "C-01" }],
  });
});
test("activity-step list loads the current project and revision and preserves ordered records", async () => {
  const calls: Calls = { gets: [] };
  const result = await loadActivitySteps(transportWith({ ok: true, data: listEnvelope([stepEnvelope(), stepEnvelope({ ...STEP, step_id: "S-02", sequence: 2 })]) }, calls), CONTEXT);
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.data.map((item) => item.stepId), ["S-01", "S-02"]);
  assert.deepEqual(calls.gets, [{ path: "/api/projects/project-1/p6/activity-steps" }]);
});
test("activity-step list fails closed on foreign contract and stale project revision", async () => {
  const wrongContract = await loadActivitySteps(transportWith({ ok: true, data: { ...listEnvelope(), contract_version: "foreign" } }), CONTEXT);
  assert.equal(wrongContract.ok, false);
  if (!wrongContract.ok) assert.equal(wrongContract.error.code, "INVALID_ACTIVITY_STEP_LIST");
  const stale = await loadActivitySteps(transportWith({ ok: true, data: { ...listEnvelope(), scope: { tenant_id: "t1", project_id: "project-1", project_revision: 3 } } }), CONTEXT);
  assert.equal(stale.ok, false);
  if (!stale.ok) assert.equal(stale.error.code, "INVALID_ACTIVITY_STEP_LIST");
});
test("activity-step parser rejects malformed identity, sequence, weight and foreign row scope", () => {
  assert.throws(() => parseActivityStep(stepEnvelope({ ...STEP, sequence: 1.5 }), CONTEXT), /INVALID_ACTIVITY_STEP_RECORD/);
  assert.throws(() => parseActivityStep(stepEnvelope({ ...STEP, weight: "12,50" }), CONTEXT), /INVALID_ACTIVITY_STEP_RECORD/);
  assert.throws(() => parseActivityStep({ ...stepEnvelope(), scope: { tenant_id: "t2", project_id: "project-1", project_revision: 4 } }, CONTEXT), /STALE_ACTIVITY_STEP_SCOPE/);
});
test("activity-step list propagates transport errors without replacing the server error", async () => {
  const result = await loadActivitySteps(transportWith({ ok: false, error: { code: "FORBIDDEN", retryable: false, message_key: "error.forbidden", available_actions: [] } }), CONTEXT);
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.error.code, "FORBIDDEN");
});
