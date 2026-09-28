import test from "node:test";
import assert from "node:assert/strict";
import {
  applyAuthoritativeValidation,
  canSubmitFormula,
  createFormulaEditorState,
  setFormulaExpression,
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
