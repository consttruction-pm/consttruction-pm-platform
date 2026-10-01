import test from "node:test";
import assert from "node:assert/strict";

import type { P6FormulaEditorState } from "./p6-formula-editor.js";
import { renderP6FormulaEditor } from "./p6-formula-editor-view.js";

const labels = {
  title: "Formula Editor",
  expression: "Expression",
  validating: "Validating…",
  valid: "Valid",
  invalid: "Invalid",
  dependencies: "Dependencies",
  resultType: "Result type",
  validate: "Validate",
};

function state(overrides: Partial<P6FormulaEditorState> = {}): P6FormulaEditorState {
  return {
    field_id: "activity-cost",
    expression: "Original Duration * Units",
    validating: false,
    authoritative: null,
    ...overrides,
  };
}

test("renders expression and empty authoritative state without inventing calculation results", () => {
  const html = renderP6FormulaEditor(state(), labels);

  assert.match(html, /<textarea[^>]*data-p6-formula-expression[^>]*>Original Duration \* Units<\/textarea>/);
  assert.match(html, /data-p6-formula-dependencies><\/dd>/);
  assert.match(html, /data-p6-formula-result-type><\/dd>/);
  assert.match(html, /data-p6-formula-validate/);
  assert.doesNotMatch(html, /Valid<\/div>/);
});

test("renders authoritative validation, dependencies and result type", () => {
  const html = renderP6FormulaEditor(state({
    authoritative: {
      validation: { valid: true, error_code: null, message_key: null },
      dependencies: { field_ids: ["activity-duration", "activity-units"] },
      result_type: { data_type: "double" },
    },
  }), labels);

  assert.match(html, /role="status"[^>]*>Valid<\/div>/);
  assert.match(html, /activity-duration, activity-units/);
  assert.match(html, /data-p6-formula-result-type>double<\/dd>/);
});

test("renders validation error from authoritative message key only", () => {
  const html = renderP6FormulaEditor(state({
    authoritative: {
      validation: { valid: false, error_code: "TYPE_MISMATCH", message_key: "formula.typeMismatch" },
      dependencies: { field_ids: [] },
      result_type: { data_type: "double" },
    },
  }), labels);

  assert.match(html, /data-p6-formula-error="TYPE_MISMATCH">formula\.typeMismatch<\/div>/);
  assert.doesNotMatch(html, /TYPE_MISMATCH.*TYPE_MISMATCH/);
});
