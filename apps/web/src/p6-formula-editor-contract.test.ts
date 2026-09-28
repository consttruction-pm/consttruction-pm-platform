import test from "node:test";
import assert from "node:assert/strict";
import {
  applyAuthoritativeValidation,
  canSubmitFormula,
  createFormulaEditorState,
  setFormulaExpression,
  validateFormulaAuthoritatively,
} from "./p6-formula-editor-contract.js";

test("formula editor consumes authoritative validation and dependency results", () => {
  let state = createFormulaEditorState();
  state = setFormulaExpression(state, "ActualDuration / PlannedDuration");
  state = applyAuthoritativeValidation(state, {
    status: "valid",
    message_key: null,
    result_type: "percentage",
    result_unit: "%",
    authoritative: true,
    dependencies: [
      { field_id: "actual_duration", dependency_type: "field", subject_area: "activity" },
      { field_id: "planned_duration", dependency_type: "field", subject_area: "activity" },
    ],
  });

  assert.equal(canSubmitFormula(state), true);
  assert.equal(state.validation?.dependencies.length, 2);
  assert.equal(state.declared_result_type, "percentage");
});

test("client cannot submit without an authoritative valid result", () => {
  const state = setFormulaExpression(createFormulaEditorState(), "1 + 1");
  assert.equal(canSubmitFormula(state), false);
});

test("validation API rejects a response that is not authoritative", async () => {
  const transport = {
    async get<T>() { throw new Error("not used") as never as T; },
    async post<TRequest, TResponse>(_path: string, _request: TRequest): Promise<{ ok: true; data: TResponse }> {
      return {
        ok: true as const,
        data: {
          status: "valid",
          message_key: null,
          result_type: "number",
          result_unit: null,
          dependencies: [],
          authoritative: false,
        } as unknown as TResponse,
      };
    },
  };

  const result = await validateFormulaAuthoritatively(
    transport,
    "/formula/validate",
    { tenant_id: "t1", project_id: "p1", revision: 7 },
    { formula_id: null, version: null, expression: "1 + 1", subject_area: "activity" },
  );

  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.error.code, "NON_AUTHORITATIVE_FORMULA_RESULT");
});

test("validation API returns the authoritative result without client evaluation", async () => {
  let captured: unknown;
  const transport = {
    async get() { throw new Error("not used"); },
    async post<TRequest, TResponse>(_path: string, request: TRequest): Promise<{ ok: true; data: TResponse }> {
      captured = request;
      return {
        ok: true as const,
        data: {
          status: "valid",
          message_key: null,
          result_type: "percentage",
          result_unit: "%",
          dependencies: [
            { field_id: "actual_duration", dependency_type: "field", subject_area: "activity" },
          ],
          authoritative: true,
        } as unknown as TResponse,
      };
    },
  };

  const result = await validateFormulaAuthoritatively(
    transport,
    "/formula/validate",
    { tenant_id: "t1", project_id: "p1", revision: 7 },
    { formula_id: "f1", version: "2", expression: "ActualDuration / PlannedDuration", subject_area: "activity" },
  );

  assert.deepEqual(captured, {
    formula_id: "f1",
    version: "2",
    expression: "ActualDuration / PlannedDuration",
    subject_area: "activity",
  });
  assert.equal(result.ok, true);
  if (result.ok) assert.equal(result.data.authoritative, true);
});
