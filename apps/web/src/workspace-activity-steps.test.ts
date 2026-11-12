import assert from "node:assert/strict";
import test from "node:test";

import {
  ACTIVITY_STEP_READ_API_VERSION,
  loadActivitySteps,
  parseActivityStepList,
} from "./workspace-activity-steps.js";
import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

const CONTEXT: ProjectContext = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  revision: 7,
};

function step(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    step_id: "STEP-A130-01",
    activity_id: "A130",
    sequence: 1,
    description: "Strip topsoil",
    weight: "25",
    start_date: null,
    finish_date: null,
    udf_values: {},
    ...overrides,
  };
}

test("activity step parsing keeps stored fields and never invents completion", () => {
  const parsed = parseActivityStepList({
    contract_version: ACTIVITY_STEP_READ_API_VERSION,
    kind: "p6_activity_step_list",
    steps: [step(), step({ step_id: "STEP-A130-02", sequence: 2, weight: null, udf_values: { crew: "civil" } })],
  });
  assert.equal(parsed.length, 2);
  assert.equal(parsed[0]?.weight, "25");
  assert.equal(parsed[1]?.weight, null);
  assert.deepEqual(parsed[1]?.udfValues, { crew: "civil" });
  assert.equal("percentComplete" in (parsed[0] ?? {}), false);
});

test("activity step parsing rejects malformed payloads instead of inventing steps", () => {
  assert.throws(() => parseActivityStepList({ contract_version: "wrong", steps: [] }), /INVALID_ACTIVITY_STEP_LIST/);
  assert.throws(() => parseActivityStepList({ contract_version: ACTIVITY_STEP_READ_API_VERSION, steps: [step({ sequence: -1 })] }), /INVALID_ACTIVITY_STEP/);
  assert.throws(() => parseActivityStepList({ contract_version: ACTIVITY_STEP_READ_API_VERSION, steps: [step({ description: "" })] }), /INVALID_ACTIVITY_STEP/);
  assert.throws(() => parseActivityStepList({ contract_version: ACTIVITY_STEP_READ_API_VERSION, steps: [step({ weight: "heavy" })] }), /INVALID_ACTIVITY_STEP/);
});

test("loadActivitySteps reads the activity-scoped endpoint and reports service errors", async () => {
  const calls: string[] = [];
  const transport: ApiTransport = {
    async get<T>(path: string): Promise<ApiResult<T>> {
      calls.push(path);
      return {
        ok: true,
        data: {
          contract_version: ACTIVITY_STEP_READ_API_VERSION,
          kind: "p6_activity_step_list",
          steps: [step({ activity_id: "A 130/1" })],
        } as T,
      };
    },
    async post<TRequest, TResponse>(): Promise<ApiResult<TResponse>> {
      throw new Error("unused");
    },
  };
  const result = await loadActivitySteps(transport, CONTEXT, "A 130/1");
  assert.equal(calls[0], "/api/projects/project-1/p6/activities/A%20130%2F1/steps");
  assert.ok(result.ok);
  assert.equal(result.ok && result.data[0]?.description, "Strip topsoil");

  const failed: ApiTransport = {
    async get<T>(): Promise<ApiResult<T>> {
      return { ok: false, error: { code: "P6_ACTIVITY_STEP_READ_UNAVAILABLE", retryable: true, message_key: "error.resource.unavailable", available_actions: [] } };
    },
    async post<TRequest, TResponse>(): Promise<ApiResult<TResponse>> {
      throw new Error("unused");
    },
  };
  const error = await loadActivitySteps(failed, CONTEXT, "A130");
  assert.equal(error.ok, false);
  assert.equal(!error.ok && error.error.code, "P6_ACTIVITY_STEP_READ_UNAVAILABLE");
});
