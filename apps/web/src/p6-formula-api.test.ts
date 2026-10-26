import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { createP6FormulaAuthority } from "./p6-formula-api.js";

const CONTEXT: ProjectContext = {
  tenant_id: "t1",
  project_id: "preview-rps-01",
  revision: 7,
};

type Call = {
  path: string;
  request: unknown;
  context: ProjectContext;
};

function transportWith(result: ApiResult<unknown>, calls: Call[] = []): ApiTransport {
  return {
    async get() {
      throw new Error("GET_NOT_EXPECTED");
    },
    async post(path, request, context) {
      calls.push({ path, request, context });
      return result as ApiResult<never>;
    },
  };
}

test("formula authority posts the expression and context field to the shared API", async () => {
  const calls: Call[] = [];
  const authority = createP6FormulaAuthority(
    transportWith(
      {
        ok: true,
        data: {
          contract_version: "p6-formula-authority-api.v1",
          validation: { valid: true, error_code: null, message_key: null },
          dependencies: { field_ids: ["activity.planned_duration"] },
          result_type: { data_type: "double" },
        },
      },
      calls,
    ),
    CONTEXT,
  );

  const result = await authority.validate(
    "planned_duration * 2",
    "activity.total_float",
  );

  assert.equal(calls.length, 1);
  assert.equal(
    calls[0].path,
    "/api/projects/preview-rps-01/p6/formulas/p6-field-registry.v1",
  );
  assert.deepEqual(calls[0].request, {
    expression: "planned_duration * 2",
    context_field_id: "activity.total_float",
  });
  assert.deepEqual(calls[0].context, CONTEXT);
  assert.equal(result.validation.valid, true);
  assert.deepEqual(result.dependencies.field_ids, ["activity.planned_duration"]);
  assert.equal(result.result_type.data_type, "double");
});

test("invalid formula results keep the authoritative null result type", async () => {
  const authority = createP6FormulaAuthority(
    transportWith({
      ok: true,
      data: {
        validation: {
          valid: false,
          error_code: "FORMULA_SELF_REFERENCE",
          message_key: "p6.formula.validation.error",
        },
        dependencies: { field_ids: [] },
        result_type: { data_type: null },
      },
    }),
    CONTEXT,
  );

  const result = await authority.validate("planned_duration + 1", "activity.planned_duration");
  assert.equal(result.validation.valid, false);
  assert.equal(result.validation.error_code, "FORMULA_SELF_REFERENCE");
  assert.equal(result.result_type.data_type, null);
});

test("formula authority surfaces API denial instead of returning a fabricated result", async () => {
  const authority = createP6FormulaAuthority(
    transportWith({
      ok: false,
      error: {
        code: "PERMISSION_DENIED",
        retryable: false,
        message_key: "error.authorization.denied",
        available_actions: [],
      },
    }),
    CONTEXT,
  );

  await assert.rejects(authority.validate("1 + 1"), /PERMISSION_DENIED/);
});

test("formula authority rejects a malformed authoritative response", async () => {
  const authority = createP6FormulaAuthority(
    transportWith({
      ok: true,
      data: {
        validation: { valid: true, error_code: null, message_key: null },
        dependencies: { field_ids: [] },
        result_type: { data_type: "not-a-field-type" },
      },
    }),
    CONTEXT,
  );

  await assert.rejects(authority.validate("1 + 1"), /INVALID_P6_FORMULA_RESULT_TYPE/);
});
